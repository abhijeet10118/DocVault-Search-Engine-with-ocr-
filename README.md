# DocVault

A branch-based document management system with full-text search (Elasticsearch + OCR), JWT authentication, and cross-branch access requests.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup — Backend](#setup--backend)
- [Setup — Frontend](#setup--frontend)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [What to Put in .gitignore](#what-to-put-in-gitignore)
- [Creating the GitHub Repository](#creating-the-github-repository)
- [API Endpoints](#api-endpoints)
- [Feature Overview](#feature-overview)
- [Future Updates — Scaling to Terabytes](#future-updates--scaling-to-terabytes)

---

## Project Structure

```
docvault/
├── backend/                  # Django REST API
│   ├── core/                 # Main Django app
│   │   ├── models.py         # User, Document, AccessRequest
│   │   ├── views.py          # All API views
│   │   ├── urls.py           # URL routing
│   │   ├── serializers.py    # DRF serializers
│   │   ├── extract_text.py   # Text extraction (PDF, DOCX, images, etc.)
│   │   ├── ocr.py            # SmartOCR class for image text extraction
│   │   └── apps.py
│   ├── docvault/             # Django project settings
│   │   ├── settings.py
│   │   └── urls.py
│   ├── scripts/
│   │   └── remove_registered_users.py   # Pre-push cleanup script
│   ├── media/                # Uploaded files (gitignored)
│   ├── .env                  # Secret config (gitignored)
│   ├── .env.example          # Template — commit this
│   ├── .gitignore
│   ├── manage.py
│   └── requirements.txt
│
└── frontend/                 # React app
    ├── src/
    │   ├── pages/
    │   │   ├── Login.js
    │   │   ├── Register.js
    │   │   ├── Search.js
    │   │   ├── Upload.js
    │   │   └── Requests.js   # Access request management
    │   ├── api.js            # Axios instance with JWT interceptor
    │   ├── App.js
    │   └── index.js
    ├── .env.local            # Secret config (gitignored)
    ├── .env.example          # Template — commit this
    ├── .gitignore
    └── package.json
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, React Router, Axios |
| Backend | Django, Django REST Framework |
| Auth | JWT via `djangorestframework-simplejwt` |
| Search | Elasticsearch 8.x |
| OCR | Custom `SmartOCR` class (Tesseract / pytesseract) |
| Document parsing | PyPDF2, python-docx, python-pptx, pandas |

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- Elasticsearch 8.x running locally (or remote)
- Tesseract OCR installed (for image text extraction)

---

## Setup — Backend

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/docvault.git
cd docvault/backend

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your SECRET_KEY and Elasticsearch credentials

# 5. Apply migrations
python manage.py migrate

# 6. Create a superuser (optional)
python manage.py createsuperuser

# 7. Run the development server
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/`.

---

## Setup — Frontend

```bash
cd docvault/frontend

# 1. Install dependencies
npm install

# 2. Copy and fill in environment variables
cp .env.example .env.local
# Edit .env.local if your backend runs on a different port

# 3. Start the development server
npm start
```

The React app will open at `http://localhost:3000`.

---

## Environment Variables

### Backend — `backend/.env`

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DEBUG` | Debug mode | `True` (dev) / `False` (prod) |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `ES_HOST` | Elasticsearch URL | `https://127.0.0.1:9200` |
| `ES_USERNAME` | ES username | `elastic` |
| `ES_PASSWORD` | ES password | `your-password` |

> Copy `backend/.env.example` to `backend/.env` and fill in your values. Never commit `.env`.

### Frontend — `frontend/.env.local`

| Variable | Description | Default |
|----------|-------------|---------|
| `REACT_APP_API_BASE_URL` | Django API base URL | `http://127.0.0.1:8000/api/` |

> Copy `frontend/.env.example` to `frontend/.env.local`. Never commit `.env.local`.

---

## Database Migrations

After cloning or pulling changes that include model updates, always run:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

The `AccessRequest` model (added for cross-branch access requests) requires a migration. If you see errors about a missing `core_accessrequest` table, this migration hasn't been applied yet.

---

## What to Put in .gitignore

### Backend (`backend/.gitignore`)

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd

# Virtual environments
venv/
.venv/
env/

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# User-uploaded files — NEVER commit these
media/

# Collected static files
staticfiles/
static/

# Environment secrets — NEVER commit these
.env
.env.*
!.env.example

# IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# Tests
.coverage
htmlcov/
.pytest_cache/
```

**Key rules:**
- `media/` — this is where Django stores uploaded files. These are user data, often large, and should never be in version control.
- `.env` — contains your `SECRET_KEY` and database/Elasticsearch passwords. Committing this is a security incident.
- `db.sqlite3` — contains all your data including password hashes. Never commit.
- `__pycache__/` — compiled Python bytecode, machine-specific.

### Frontend (`frontend/.gitignore`)

```gitignore
# Dependencies
node_modules/

# Build output
build/
dist/

# Environment secrets
.env
.env.*
!.env.example
.env.local
.env.development.local
.env.test.local
.env.production.local

# Logs
npm-debug.log*
yarn-debug.log*

# IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# Tests
coverage/
```

**Key rules:**
- `node_modules/` — can be hundreds of MB, always regenerated via `npm install`.
- `.env.local` — contains your API base URL and any keys. Use `.env.example` as the committed template.
- `build/` — compiled output, regenerated via `npm run build`.

---

## Creating the GitHub Repository

### Option A — New repo from scratch (recommended)

```bash
# 1. Create the repo on GitHub (no README, no .gitignore — you're adding your own)
#    https://github.com/new

# 2. In your project root
cd docvault
git init
git add .
git commit -m "Initial commit"

# 3. Link to GitHub and push
git remote add origin https://github.com/YOUR_USERNAME/docvault.git
git branch -M main
git push -u origin main
```

### Option B — Existing repo

```bash
cd docvault
git remote add origin https://github.com/YOUR_USERNAME/docvault.git
git pull origin main --allow-unrelated-histories   # if repo has an existing README
git push -u origin main
```

### Pre-push checklist

Before running `git push` for the first time:

- [ ] `media/` folder is empty or gitignored
- [ ] `db.sqlite3` is gitignored
- [ ] `.env` files are gitignored (only `.env.example` files are committed)
- [ ] `SECRET_KEY` and passwords are NOT hardcoded anywhere in committed files
- [ ] `SECRET_KEY` and passwords are NOT hardcoded anywhere in committed files
- [ ] `requirements.txt` is up to date: `pip freeze > requirements.txt`
- [ ] `package.json` reflects correct dependencies

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/register/` | No | Create account |
| POST | `/api/login/` | No | Get JWT tokens |
| POST | `/api/upload/` | Yes | Upload a document |
| GET | `/api/my-documents/` | Yes | List your uploads |
| DELETE | `/api/documents/<id>/delete/` | Yes | Delete your document |
| GET | `/api/documents/<id>/download/` | Yes | Download (same branch or approved) |
| GET | `/api/documents/<id>/preview/` | Yes | Image preview (same branch or approved) |
| GET | `/api/search/?q=<query>` | Yes | Full-text search across all branches |
| POST | `/api/documents/<id>/request-access/` | Yes | Request access to locked doc |
| GET | `/api/access-requests/incoming/` | Yes | View pending requests on your docs |
| POST | `/api/access-requests/<id>/approve/` | Yes | Approve a request |
| POST | `/api/access-requests/<id>/deny/` | Yes | Deny a request |
| GET | `/api/access-requests/my/` | Yes | View your sent requests |
| GET | `/api/es-health/` | No | Elasticsearch connection check |

---

## Feature Overview

### Branch isolation
Users register under one of three branches: **Engineering**, **Commerce**, or **Architecture**. Documents are stored per branch. Search results show documents from all branches but downloads are gated.

### OCR on images
When an image file (JPG, PNG, BMP, TIFF, WEBP) is uploaded, `SmartOCR` extracts text from it automatically so it's fully searchable alongside PDFs and Word documents.

### Cross-branch access requests
Users can request access to documents from other branches. The document owner sees incoming requests in the **Requests** page and can approve or deny them. Approved users can download the document as if it were in their own branch.

### JWT authentication
All protected endpoints require a `Bearer` token in the `Authorization` header. Tokens are issued on login and stored in `localStorage` on the frontend.

---

## Future Updates — Scaling to Terabytes

The current architecture is designed for a single institution with a modest document load. Below is a full roadmap for evolving DocVault into a system that can handle **terabytes of concurrent uploads, indexing, and search without crashing** — the kind of load seen at large universities, law firms, or enterprise document platforms.

---

### The Core Problem at Scale

Right now, three things happen in a single synchronous Django request when a file is uploaded:

1. The file is saved to the local disk.
2. Text is extracted (OCR can take 5–30 seconds per image).
3. The result is indexed into Elasticsearch.

At scale, this blocks the web server, starves other requests, causes timeouts, and creates a single point of failure. Everything below addresses a specific part of that problem.

---

### 1. Decouple File Storage — Move Off Local Disk

**Problem:** Files stored in `media/` on the Django server can't be accessed by multiple backend instances, and a single disk fills up fast.

**Solution:** Replace Django's `FileField` with object storage.

- **AWS S3 / Cloudflare R2 / MinIO (self-hosted)** — store every uploaded file as an object with a unique key. Unlimited capacity, replicated across availability zones automatically.
- Use `django-storages` + `boto3` to make the swap nearly transparent to the rest of the codebase — `doc.file.url` just becomes an S3 URL instead of a local path.
- Files are served directly from S3 via pre-signed URLs, removing Django from the download path entirely and dramatically reducing bandwidth load on the API server.

```python
# settings.py — after adding django-storages
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'docvault-documents'
AWS_S3_REGION_NAME = 'ap-south-1'
```

---

### 2. Async Upload Processing — Task Queues

**Problem:** OCR on a 50-page scanned PDF can take minutes. Running that inside a web request kills the server under concurrent load.

**Solution:** Hand off all heavy work to a background task queue.

- **Celery + Redis** is the standard Django pairing. The upload endpoint saves the file and immediately returns `202 Accepted`. A Celery worker picks up the task, runs OCR and text extraction, and indexes into Elasticsearch — all outside the request cycle.
- The frontend can poll a `/api/documents/<id>/status/` endpoint to show a "Processing…" state until indexing completes.
- Workers can be scaled horizontally — spin up 10, 50, or 100 workers on separate machines to process a surge of uploads in parallel.

```
Upload request → Django (saves file, enqueues task) → 202 response
                                  ↓
                           Redis task queue
                                  ↓
                     Celery worker pool (N workers)
                       ├── extract_text()
                       ├── OCR if image
                       └── es.index()
```

---

### 3. Scale the Database — Move From SQLite to PostgreSQL

**Problem:** SQLite uses file-level locking — concurrent writes serialize and eventually time out. It is not designed for multi-user production workloads.

**Solution:** Switch to **PostgreSQL**, which handles thousands of concurrent connections with row-level locking and is the standard choice for Django at any serious scale.

- For very high read loads, add **read replicas** — Django's database router can direct `SELECT` queries to replicas and writes to the primary.
- For the access request approval flow specifically, PostgreSQL's `SELECT FOR UPDATE` prevents race conditions where two approvals arrive simultaneously.

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'docvault',
        'HOST': 'your-postgres-host',
        'PORT': '5432',
    }
}
```

---

### 4. Scale Elasticsearch — Cluster Mode

**Problem:** A single-node Elasticsearch instance is a single point of failure. It also has a hard ceiling on indexing throughput and search concurrency.

**Solution:** Run a **multi-node Elasticsearch cluster**.

- **Dedicated node roles** — separate master nodes (cluster coordination), data nodes (storage + search), and ingest nodes (text analysis pipelines). Each can be scaled independently.
- **Index sharding** — instead of one `documents` index, shard by branch or date: `documents-engineering-2025`, `documents-commerce-2025`. Each index is distributed across multiple data nodes, so searches run in parallel.
- **Index aliases** — the API always points at an alias (`documents`), so re-indexing or rolling over to a new index is transparent to the application.
- **Ingest pipelines** — move the text extraction step into Elasticsearch's own ingest pipeline using the `attachment` processor. Files go directly from S3 into ES, bypassing Django for the heavy lifting.

For truly massive datasets (100TB+), look at **Elasticsearch ILM (Index Lifecycle Management)** to automatically move old indices to cheaper "warm" or "cold" storage tiers.

---

### 5. Scale the API — Multiple Django Instances Behind a Load Balancer

**Problem:** A single Django process (`runserver` or even a single Gunicorn instance) is CPU-bound and can only handle so many concurrent requests.

**Solution:** Horizontal scaling behind a load balancer.

- Run **Gunicorn with multiple workers** (`--workers 4` to start, typically `2 × CPU cores + 1`).
- Put **Nginx** in front as a reverse proxy and static file server.
- For true horizontal scaling, containerize with **Docker** and orchestrate with **Kubernetes** or **AWS ECS**. The load balancer distributes requests across N identical Django pods. Adding pods takes seconds.
- Since session state lives in JWT tokens (stateless) and files live in S3, every Django instance is identical — no sticky sessions needed.

```
Internet
   ↓
Nginx / AWS ALB  (load balancer)
   ↓         ↓         ↓
Django-1   Django-2   Django-3   (Gunicorn, 4 workers each)
   ↓              ↓
PostgreSQL    Elasticsearch cluster
   ↓
Redis (Celery broker + cache)
   ↓
S3 (file storage)
```

---

### 6. Caching — Stop Hitting the Database for Every Request

**Problem:** Popular search queries, document lists, and access checks hit the database and Elasticsearch on every request.

**Solution:** Add **Redis as a cache layer**.

- Cache frequent search queries with a short TTL (30–60 seconds). A query for "structural analysis" by 200 users simultaneously becomes one Elasticsearch query instead of 200.
- Cache user branch and access grant lookups — these change rarely but are checked on every protected request.
- Use Django's built-in cache framework with the `django-redis` backend. No application logic changes needed for most cases.

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://your-redis-host:6379/1",
    }
}
```

---

### 7. OCR at Scale — Dedicated OCR Workers

**Problem:** OCR is the most CPU-intensive step. Mixing it with other Celery tasks means a flood of image uploads starves document indexing tasks.

**Solution:** Separate Celery **queues with dedicated worker pools**.

- `ocr_queue` — high-memory, high-CPU workers (e.g., 8-core machines). Run Tesseract or a GPU-accelerated OCR model like **PaddleOCR** or **TrOCR** for dramatically better throughput on scanned documents.
- `index_queue` — lightweight workers that just call `es.index()` after text is ready.
- `default_queue` — everything else (access requests, notifications, etc.).

This way an upload surge of 10,000 scanned images doesn't block a routine document upload from being searchable.

---

### 8. File Upload — Bypass Django Entirely for Large Files

**Problem:** Uploading a 500MB file through Django means it buffers in memory, ties up a worker, and is slow.

**Solution:** **Presigned S3 uploads** — the frontend uploads directly to S3, Django never touches the bytes.

1. Frontend requests a presigned upload URL from the API (`POST /api/upload-url/`).
2. Django generates a time-limited S3 presigned URL and returns it (this is instant).
3. Frontend uploads the file directly to S3 from the browser — bypassing Django entirely.
4. S3 triggers a webhook / SNS notification → Celery picks it up → extracts text → indexes.

This removes Django from the upload path completely. A 10GB file upload is no longer Django's problem.

---

### 9. Monitoring and Alerting — Know Before It Crashes

At terabyte scale, silent failures are catastrophic (a Celery worker dies, OCR stops running, 10,000 documents go unindexed with no error shown).

- **Sentry** — captures every unhandled exception in Django and Celery workers in real time.
- **Prometheus + Grafana** — metrics dashboards for request latency, queue depth, worker throughput, ES index rate, disk I/O.
- **Elasticsearch monitoring** — built-in cluster health API (`/_cluster/health`) exposed via the existing `/api/es-health/` endpoint, but extended with shard counts, JVM heap usage, and indexing rate.
- **Celery Flower** — a real-time web UI for inspecting task queues, worker status, and failure rates.

Set alerts for: queue depth > 1000 tasks, ES cluster status yellow/red, Django p95 latency > 2s, disk usage > 80%.

---

### Summary — Migration Path

| Stage | Scale | Key Changes |
|-------|-------|-------------|
| Current | ~10 GB, single server | SQLite, local disk, sync OCR |
| Stage 1 | ~100 GB, moderate load | PostgreSQL, S3 storage, Celery + Redis |
| Stage 2 | ~1 TB, multi-user production | Gunicorn + Nginx, ES cluster, Redis cache |
| Stage 3 | ~10 TB, enterprise load | Kubernetes, dedicated OCR workers, presigned uploads |
| Stage 4 | 100 TB+, massive scale | ES ILM tiering, CDN for previews, GPU OCR, multi-region |


