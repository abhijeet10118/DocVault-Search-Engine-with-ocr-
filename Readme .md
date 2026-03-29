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
- [Removing Test / Registered Users Before First Push](#removing-test--registered-users-before-first-push)
- [What to Put in .gitignore](#what-to-put-in-gitignore)
- [Creating the GitHub Repository](#creating-the-github-repository)
- [API Endpoints](#api-endpoints)
- [Feature Overview](#feature-overview)

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

| Layer            | Technology                                        |
| ---------------- | ------------------------------------------------- |
| Frontend         | React, React Router, Axios                        |
| Backend          | Django, Django REST Framework                     |
| Auth             | JWT via `djangorestframework-simplejwt`           |
| Search           | Elasticsearch 8.x                                 |
| OCR              | Custom `SmartOCR` class (Tesseract / pytesseract) |
| Document parsing | PyPDF2, python-docx, python-pptx, pandas          |

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

| Variable        | Description                   | Example                       |
| --------------- | ----------------------------- | ----------------------------- |
| `SECRET_KEY`    | Django secret key             | `django-insecure-...`         |
| `DEBUG`         | Debug mode                    | `True` (dev) / `False` (prod) |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1`         |
| `ES_HOST`       | Elasticsearch URL             | `https://127.0.0.1:9200`      |
| `ES_USERNAME`   | ES username                   | `elastic`                     |
| `ES_PASSWORD`   | ES password                   | `your-password`               |

> Copy `backend/.env.example` to `backend/.env` and fill in your values. Never commit `.env`.

### Frontend — `frontend/.env.local`

| Variable                 | Description         | Default                      |
| ------------------------ | ------------------- | ---------------------------- |
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

## Removing Test / Registered Users Before First Push

If you used your local dev environment to test the app, you likely have dummy user accounts and uploaded test documents in the database and `media/` folder. **Clean these out before your first push** so the repo starts with a clean slate.

### Step 1 — Open the script and configure it

Open `backend/scripts/remove_registered_users.py` and add any real accounts you want to **keep** to the `KEEP_USERNAMES` set:

```python
KEEP_USERNAMES = {
    "admin",       # keep your superuser
    "yourname",    # keep any real account
}
```

Leave it empty `{}` to delete **all** users.

### Step 2 — Run the script

With your virtual environment active:

```bash
cd backend
python manage.py shell < scripts/remove_registered_users.py
```

The script will:

1. List every user it plans to delete and how many documents they own.
2. Ask you to type `YES` to confirm.
3. Delete the physical files from `media/documents/`.
4. Remove the corresponding Elasticsearch index entries.
5. Delete the database rows (users + documents + access requests cascade automatically).

### Step 3 — Verify

```bash
python manage.py shell -c "from core.models import User, Document; print(User.objects.count(), 'users,', Document.objects.count(), 'docs')"
```

Should print `0 users, 0 docs` (or however many you kept).

### Step 4 — Clear the media folder manually if needed

The script removes files for documents it knows about. If you have orphaned files in `media/`, remove them manually:

```bash
rm -rf backend/media/documents/*
```

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
- [ ] Test users and documents have been removed (see section above)
- [ ] `SECRET_KEY` and passwords are NOT hardcoded anywhere in committed files
- [ ] `requirements.txt` is up to date: `pip freeze > requirements.txt`
- [ ] `package.json` reflects correct dependencies

---

## API Endpoints

| Method | Endpoint                              | Auth | Description                             |
| ------ | ------------------------------------- | ---- | --------------------------------------- |
| POST   | `/api/register/`                      | No   | Create account                          |
| POST   | `/api/login/`                         | No   | Get JWT tokens                          |
| POST   | `/api/upload/`                        | Yes  | Upload a document                       |
| GET    | `/api/my-documents/`                  | Yes  | List your uploads                       |
| DELETE | `/api/documents/<id>/delete/`         | Yes  | Delete your document                    |
| GET    | `/api/documents/<id>/download/`       | Yes  | Download (same branch or approved)      |
| GET    | `/api/documents/<id>/preview/`        | Yes  | Image preview (same branch or approved) |
| GET    | `/api/search/?q=<query>`              | Yes  | Full-text search across all branches    |
| POST   | `/api/documents/<id>/request-access/` | Yes  | Request access to locked doc            |
| GET    | `/api/access-requests/incoming/`      | Yes  | View pending requests on your docs      |
| POST   | `/api/access-requests/<id>/approve/`  | Yes  | Approve a request                       |
| POST   | `/api/access-requests/<id>/deny/`     | Yes  | Deny a request                          |
| GET    | `/api/access-requests/my/`            | Yes  | View your sent requests                 |
| GET    | `/api/es-health/`                     | No   | Elasticsearch connection check          |

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
