# MediTrack — Personal health routine companion

A full-stack starter for medication, supplement, hydration, fitness and custom-routine reminders. It includes an initial prescription upload/OCR workflow, routine APIs, and a responsive landing page/app shell.

## What's included
- Responsive Next.js landing page in a warm off-white/deep-green visual style and a basic app workspace.
- FastAPI REST API with registration/login, JWT auth, routine CRUD, check-ins, consent fields and health checks.
- PostgreSQL schema using SQLAlchemy models; development auto-creates tables.
- Redis + Celery task worker and a WhatsApp Cloud API text adapter that safely stays in stub mode without credentials.
- Prescription upload (JPEG/PNG/WEBP/text-based PDF), local OCR, optional opt-in Gemini draft extraction, private local file storage, review/confirm endpoint, and optional reminder creation after explicit review.
- Docker Compose, environment template, a small test and a production hardening checklist.

## Run locally
1. Install Docker Desktop and ensure Docker Compose is available.
2. Copy `.env.example` to `.env`.
3. Set `JWT_SECRET` to a long random value. The sample database credentials are for local development only.
4. From the project root, run `docker compose -f infra/docker-compose.yml up --build`.
5. Website: http://localhost:3000. API docs: http://localhost:8000/docs.
6. Create an account in the app, sign in, then upload a prescription. You need a clear image or a text-based PDF for OCR.

The app container's `.env` values are loaded by Compose; set `NEXT_PUBLIC_API_URL` to the public API URL before building the web app for deployment. Do not put server secrets in `NEXT_PUBLIC_*` variables.

## Prescription workflow and safety boundary
1. Upload a prescription. The server validates basic file type/size, stores it privately, and extracts text locally.
2. Optional Gemini extraction can draft medicine names/strength/instructions from OCR text only when the operator enables `PRESCRIPTION_AI_ENABLED=true`, supplies `GEMINI_API_KEY`, and the user checks the explicit opt-in. This sends extracted prescription text to Google Gemini.
3. The user reviews the extracted text and edits/enters medicine details. OCR and AI can misread handwriting, decimal points, strengths and names.
4. The user may save the review without reminders, or explicitly create reminders with reviewed `HH:MM` times and confirmation that the routine repeats daily.
5. The OCR/AI does **not** verify a drug reference or decide how/when a medicine should be taken. AI extraction is a draft transcription, not clinical interpretation. It does not infer food instructions, dosage, route, duration, interactions or substitutions. Confirm all details with the prescription and a clinician/pharmacist. The UI currently edits one candidate per review submission; the API accepts multiple medicines.
6. This starter stores uploaded files on a local private volume. Use encrypted private object storage and a retention/deletion policy before production.

## Important limitations
- WhatsApp currently supports a text adapter; voice note delivery, approved templates, verified webhook signatures, automatic inbound reply matching, and provider delivery reconciliation still need implementation.
- Calls are a stub/provider interface. Calling availability and rules depend on your provider/account/country.
- Billing is not connected. Do not accept payments until server-side payment webhooks are implemented.
- Basic JWT auth is included, but email verification, password reset, rate limiting, refresh tokens, MFA and full security review are not.
- Do not use real patient information during development.

## Before production
Read `docs/PRODUCTION_CHECKLIST.md`. Add provider credentials through a secrets manager, never source code. An API key alone is not enough: Meta business verification, WhatsApp opt-in/templates, payment setup, pharmacy partnerships, privacy/legal review, secure storage, monitoring and backups may also be required.

## Architecture
- Web: Next.js App Router + TypeScript
- API: Python FastAPI
- Data: PostgreSQL + SQLAlchemy
- Queue: Redis + Celery
- Prescription OCR: Tesseract + PDF text extraction
- Integrations: WhatsApp Cloud API adapter; calling/payment integrations are not production-enabled

## API endpoints
- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/me`
- `POST /api/v1/routines`, `GET /api/v1/routines`, `PATCH /api/v1/routines/{id}/status`
- `GET /api/v1/events`, `POST /api/v1/events/{id}/check-in`
- `POST /api/v1/prescriptions`, `GET /api/v1/prescriptions`, `GET /api/v1/prescriptions/{id}`, `POST /api/v1/prescriptions/{id}/review`, `DELETE /api/v1/prescriptions/{id}`
- `GET /health/live`, `GET /health/ready`
