from django.urls import path
from .views import (
    register, login, upload_document, my_documents,
    delete_document, search, download_document,
    preview_image, es_health,
    request_access, incoming_requests, approve_request, deny_request, my_requests,
)

urlpatterns = [
    path('register/', register),
    path('login/', login),
    path('upload/', upload_document),
    path('my-documents/', my_documents),
    path('documents/<int:doc_id>/delete/', delete_document),
    path('documents/<int:doc_id>/download/', download_document),
    path('documents/<int:doc_id>/preview/', preview_image),
    path('documents/<int:doc_id>/request-access/', request_access),   # POST — send request
    path('access-requests/incoming/', incoming_requests),              # GET  — owner's inbox
    path('access-requests/<int:request_id>/approve/', approve_request),# POST — approve
    path('access-requests/<int:request_id>/deny/', deny_request),      # POST — deny
    path('access-requests/my/', my_requests),                          # GET  — my sent requests
    path('es-health/', es_health),
    path('search/', search),
]