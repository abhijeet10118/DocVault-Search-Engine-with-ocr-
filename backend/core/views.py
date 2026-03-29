from django.contrib.auth import authenticate
from django.http import FileResponse, Http404
from elasticsearch import Elasticsearch
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
import os

from .extract_text import extract_text, IMAGE_EXTENSIONS
from .models import Document, AccessRequest
from .serializers import RegisterSerializer

es = Elasticsearch(
    "https://127.0.0.1:9200",
    basic_auth=("elastic", "eoTny-muxm_VZR1BCOO*"),
    verify_certs=False,
    ssl_show_warn=False,
    request_timeout=30,
    retry_on_timeout=True,
    max_retries=3,
)


def _is_image(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in IMAGE_EXTENSIONS


# ── AUTH ──────────────────────────────────────

@api_view(['POST'])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Registration successful."}, status=201)
    return Response({"errors": serializer.errors}, status=400)


@api_view(['POST'])
def login(request):
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")
    if not username or not password:
        return Response({"error": "Username and password are required."}, status=400)
    user = authenticate(username=username, password=password)
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Login successful.",
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "branch": user.branch,
            "username": user.username,
        })
    return Response({"error": "Invalid credentials."}, status=401)


# ── UPLOAD ────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_document(request):
    file = request.FILES.get('file')
    if not file:
        return Response({"error": "No file uploaded."}, status=400)

    user = request.user
    branch = user.branch

    doc = Document.objects.create(title=file.name, file=file, uploaded_by=user, branch=branch)

    content = extract_text(doc.file.path)
    if not content.strip():
        doc.delete()
        return Response({"error": "Could not extract text. File may be empty or unsupported."}, status=400)

    try:
        es.index(
            index="documents",
            id=str(doc.id),
            document={
                "filename": doc.title,
                "content": content,
                "branch": branch,
                "doc_id": doc.id,
                "is_image": _is_image(doc.title),
            },
        )
    except Exception as e:
        print("ES indexing error:", e)

    return Response({"message": "Document uploaded successfully.", "doc_id": doc.id})


# ── LIST MY DOCUMENTS ─────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_documents(request):
    docs = Document.objects.filter(uploaded_by=request.user).order_by('-uploaded_at')
    return Response([{
        "doc_id": d.id,
        "filename": d.title,
        "branch": d.branch,
        "uploaded_at": d.uploaded_at.strftime("%d %b %Y, %H:%M"),
        "is_image": _is_image(d.title),
    } for d in docs])


# ── DELETE ────────────────────────────────────

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_document(request, doc_id):
    try:
        doc = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        raise Http404

    if doc.uploaded_by != request.user:
        return Response({"error": "You can only delete your own documents."}, status=403)

    try:
        if doc.file and os.path.isfile(doc.file.path):
            os.remove(doc.file.path)
    except Exception as e:
        print(f"File removal warning: {e}")

    try:
        es.delete(index="documents", id=doc_id, ignore=[404])
    except Exception as e:
        print(f"ES delete warning: {e}")

    doc.delete()
    return Response({"message": "Document deleted successfully."})


# ── SEARCH ────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return Response({"error": "Query parameter 'q' is required."}, status=400)

    user_branch = request.user.branch

    try:
        res = es.search(
            index="documents",
            query={"match": {"content": query}},
            size=50,
        )
    except Exception as e:
        print(f"[ES SEARCH ERROR] {type(e).__name__}: {e}")
        return Response({"error": f"Search service unavailable: {str(e)}"}, status=503)

    # Fetch all approved access request doc IDs for this user
    approved_doc_ids = set(
        AccessRequest.objects.filter(
            requester=request.user, status='approved'
        ).values_list('document_id', flat=True)
    )

    # Fetch pending request doc IDs to show correct button state
    pending_doc_ids = set(
        AccessRequest.objects.filter(
            requester=request.user, status='pending'
        ).values_list('document_id', flat=True)
    )

    results = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        doc_branch = src.get("branch", "")
        doc_id = src.get("doc_id")
        same_branch = (doc_branch == user_branch)
        has_approved = doc_id in approved_doc_ids

        results.append({
            "doc_id": doc_id,
            "filename": src.get("filename"),
            "branch": doc_branch,
            "score": hit["_score"],
            "can_open": same_branch or has_approved,
            "is_image": src.get("is_image", False),
            "access_requested": doc_id in pending_doc_ids,
            "access_approved": has_approved,
        })

    return Response(results)


# ── DOWNLOAD ──────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_document(request, doc_id):
    try:
        doc = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        raise Http404

    same_branch = doc.branch == request.user.branch
    approved = AccessRequest.objects.filter(
        document=doc, requester=request.user, status='approved'
    ).exists()

    if not same_branch and not approved:
        return Response({"error": "Access denied."}, status=403)

    if not doc.file or not os.path.isfile(doc.file.path):
        return Response({"error": "File not found on server."}, status=404)

    return FileResponse(doc.file.open('rb'), as_attachment=True, filename=doc.title)


# ── IMAGE PREVIEW ──────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def preview_image(request, doc_id):
    try:
        doc = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        raise Http404

    same_branch = doc.branch == request.user.branch
    approved = AccessRequest.objects.filter(
        document=doc, requester=request.user, status='approved'
    ).exists()

    if not same_branch and not approved:
        return Response({"error": "Access denied."}, status=403)

    if not _is_image(doc.title):
        return Response({"error": "Not an image document."}, status=400)

    if not doc.file or not os.path.isfile(doc.file.path):
        return Response({"error": "File not found on server."}, status=404)

    import mimetypes
    mime, _ = mimetypes.guess_type(doc.file.path)
    mime = mime or "image/jpeg"

    return FileResponse(doc.file.open('rb'), content_type=mime)


# ── ACCESS REQUESTS ───────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_access(request, doc_id):
    """Requester sends an access request for a locked document."""
    try:
        doc = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        raise Http404

    if doc.branch == request.user.branch:
        return Response({"error": "Document is already in your branch."}, status=400)

    if doc.uploaded_by == request.user:
        return Response({"error": "You own this document."}, status=400)

    obj, created = AccessRequest.objects.get_or_create(
        document=doc,
        requester=request.user,
        defaults={"status": "pending"},
    )

    if not created:
        if obj.status == 'approved':
            return Response({"error": "You already have access."}, status=400)
        if obj.status == 'pending':
            return Response({"error": "Request already sent."}, status=400)
        # If denied, allow re-request
        obj.status = 'pending'
        obj.save()

    return Response({"message": "Access request sent."}, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def incoming_requests(request):
    """Owner sees all pending requests on their documents."""
    reqs = AccessRequest.objects.filter(
        document__uploaded_by=request.user,
        status='pending',
    ).select_related('requester', 'document').order_by('-created_at')

    return Response([{
        "request_id": r.id,
        "doc_id": r.document.id,
        "filename": r.document.title,
        "requester_username": r.requester.username,
        "requester_branch": r.requester.branch,
        "created_at": r.created_at.strftime("%d %b %Y, %H:%M"),
    } for r in reqs])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_request(request, request_id):
    """Owner approves an access request."""
    try:
        req = AccessRequest.objects.get(id=request_id, document__uploaded_by=request.user)
    except AccessRequest.DoesNotExist:
        raise Http404

    req.status = 'approved'
    req.save()
    return Response({"message": "Request approved."})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deny_request(request, request_id):
    """Owner denies an access request."""
    try:
        req = AccessRequest.objects.get(id=request_id, document__uploaded_by=request.user)
    except AccessRequest.DoesNotExist:
        raise Http404

    req.status = 'denied'
    req.save()
    return Response({"message": "Request denied."})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_requests(request):
    """Requester sees all their sent requests and their statuses."""
    reqs = AccessRequest.objects.filter(
        requester=request.user,
    ).select_related('document').order_by('-created_at')

    return Response([{
        "request_id": r.id,
        "doc_id": r.document.id,
        "filename": r.document.title,
        "doc_branch": r.document.branch,
        "owner_username": r.document.uploaded_by.username,
        "status": r.status,
        "created_at": r.created_at.strftime("%d %b %Y, %H:%M"),
        "updated_at": r.updated_at.strftime("%d %b %Y, %H:%M"),
    } for r in reqs])


# ── ES HEALTH ─────────────────────────────────

@api_view(['GET'])
def es_health(request):
    try:
        info = es.info()
        return Response({"status": "connected", "version": info["version"]["number"]})
    except Exception as e:
        print(f"[ES HEALTH ERROR] {type(e).__name__}: {e}")
        return Response({"status": "error", "detail": str(e)}, status=503)