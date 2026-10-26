from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, File, Form
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, desc
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.dependencies import current_user
from app.models.entities import User, Routine, RoutineSchedule, RoutineEvent, EventStatus, WebhookReceipt, RoutineStatus, PrescriptionRecord, PrescriptionStatus, RoutineCategory
from app.schemas import RegisterIn, LoginIn, TokenOut, UserOut, RoutineCreate, RoutineOut, CheckInIn, EventOut, PrescriptionOut, PrescriptionReviewIn
from app.workers.tasks import send_routine_reminder
from app.prescription_service import ALLOWED_MIME, extract_text, safe_store, extract_medicine_candidates_with_gemini

router = APIRouter()

@router.post("/auth/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    try: password_hash = hash_password(payload.password)
    except ValueError as e: raise HTTPException(422, str(e))
    user = User(email=email, full_name=payload.full_name, password_hash=password_hash,
                phone_e164=payload.phone_e164, timezone=payload.timezone,
                messaging_consent=payload.messaging_consent, caregiver_alert_consent=payload.caregiver_alert_consent)
    db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active: raise HTTPException(403, "Account disabled")
    return TokenOut(access_token=create_access_token(user.id))

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)): return user

@router.patch("/me/consent", response_model=UserOut)
def update_consent(payload: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    allowed = {"messaging_consent", "caregiver_alert_consent", "phone_e164", "timezone"}
    for key, value in payload.items():
        if key not in allowed: raise HTTPException(422, f"Unsupported field: {key}")
        setattr(user, key, value)
    db.commit(); db.refresh(user)
    return user

@router.post("/routines", response_model=RoutineOut, status_code=201)
def create_routine(payload: RoutineCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if any(s.reminder_channel not in {"whatsapp_text", "whatsapp_voice", "in_app"} for s in payload.schedules):
        raise HTTPException(422, "Supported reminder channels: whatsapp_text, whatsapp_voice, in_app")
    if any(day < 0 or day > 6 for s in payload.schedules for day in s.repeat_days):
        raise HTTPException(422, "repeat_days uses Python weekdays 0=Monday through 6=Sunday")
    routine = Routine(owner_id=user.id, category=payload.category, title=payload.title.strip(),
                      instructions=payload.instructions, timezone=payload.timezone)
    routine.schedules = [RoutineSchedule(**s.model_dump()) for s in payload.schedules]
    db.add(routine); db.commit()
    return db.scalar(select(Routine).options(selectinload(Routine.schedules)).where(Routine.id == routine.id))

@router.get("/routines", response_model=list[RoutineOut])
def list_routines(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Routine).options(selectinload(Routine.schedules)).where(Routine.owner_id == user.id).order_by(desc(Routine.created_at))).unique())

@router.patch("/routines/{routine_id}/status", response_model=RoutineOut)
def set_routine_status(routine_id: str, payload: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    routine = db.scalar(select(Routine).options(selectinload(Routine.schedules)).where(Routine.id == routine_id, Routine.owner_id == user.id))
    if not routine: raise HTTPException(404, "Routine not found")
    try: routine.status = RoutineStatus(payload.get("status"))
    except (ValueError, TypeError): raise HTTPException(422, "status must be active, paused, or archived")
    db.commit(); db.refresh(routine); return routine

@router.get("/events", response_model=list[EventOut])
def list_events(limit: int = 50, user: User = Depends(current_user), db: Session = Depends(get_db)):
    limit = max(1, min(limit, 100))
    return list(db.scalars(select(RoutineEvent).join(RoutineSchedule).join(Routine).where(Routine.owner_id == user.id).order_by(desc(RoutineEvent.due_at)).limit(limit)))

@router.post("/events/{event_id}/check-in", response_model=EventOut)
def check_in(event_id: str, payload: CheckInIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if payload.status not in {EventStatus.completed, EventStatus.skipped}:
        raise HTTPException(422, "Check-in status must be completed or skipped")
    event = db.scalar(select(RoutineEvent).join(RoutineSchedule).join(Routine).where(RoutineEvent.id == event_id, Routine.owner_id == user.id))
    if not event: raise HTTPException(404, "Event not found")
    event.status = payload.status
    event.confirmed_at = datetime.now(timezone.utc)
    event.confirmation_source = payload.source[:32]
    db.commit(); db.refresh(event)
    return event

@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """Minimal webhook receiver. Configure Meta verify token; signature validation is mandatory before production."""
    body = await request.json()
    # Idempotently record inbound provider message IDs. Message-to-user matching needs phone normalization
    # and an explicit opt-in / verified account mapping before automatically applying check-ins.
    messages = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            messages.extend(change.get("value", {}).get("messages", []))
    for message in messages:
        message_id = message.get("id")
        if message_id and not db.get(WebhookReceipt, message_id):
            db.add(WebhookReceipt(id=message_id, processed=False))
    db.commit()
    return {"received": True, "messages_recorded": len(messages), "auto_checkin": False}

@router.get("/webhooks/whatsapp")
def verify_whatsapp_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == settings.whatsapp_verify_token and settings.whatsapp_verify_token:
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(403, "Webhook verification failed")

@router.post("/internal/dispatch-reminder/{event_id}")
def dispatch_reminder(event_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Owner-scoped development trigger. Production scheduler should enqueue due events, not expose internal endpoints."""
    event = db.scalar(select(RoutineEvent).join(RoutineSchedule).join(Routine).where(RoutineEvent.id == event_id, Routine.owner_id == user.id))
    if not event: raise HTTPException(404, "Event not found")
    if event.status in {EventStatus.completed, EventStatus.skipped}: raise HTTPException(409, "Routine event already checked in")
    task = send_routine_reminder.delay(event.id)
    return {"queued": True, "task_id": task.id}


@router.post("/prescriptions", response_model=PrescriptionOut, status_code=201)
async def upload_prescription(file: UploadFile = File(...), allow_ai_processing: bool = Form(False), user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Upload a prescription for OCR. Extracted text is a draft, never medical advice."""
    mime = (file.content_type or "").lower()
    if mime not in ALLOWED_MIME:
        raise HTTPException(415, "Upload a JPEG, PNG, WEBP image or PDF")
    max_bytes = max(1, settings.prescription_max_upload_mb) * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if not content or len(content) > max_bytes:
        raise HTTPException(413, f"File must be smaller than {settings.prescription_max_upload_mb} MB")
    try:
        extracted = extract_text(content, mime)
    except Exception as exc:
        raise HTTPException(422, f"Could not read this file. Try a clear image or text-based PDF. Details: {str(exc)[:180]}")
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}[mime]
    record_id = str(uuid4())
    try:
        stored_path = safe_store(settings.prescription_upload_dir, record_id, ext, content)
    except Exception:
        raise HTTPException(500, "Could not securely store the prescription")
    candidates = []
    if allow_ai_processing:
        if not settings.prescription_ai_enabled or not settings.gemini_api_key:
            Path(stored_path).unlink(missing_ok=True)
            raise HTTPException(400, "AI extraction is not enabled by the operator. Upload without AI processing or contact support.")
        try:
            candidates = await extract_medicine_candidates_with_gemini(extracted, settings.gemini_api_key, settings.gemini_model)
        except Exception:
            # Keep the upload and OCR text available for manual review if the optional AI service fails.
            candidates = []
    record = PrescriptionRecord(id=record_id, owner_id=user.id, original_filename=(file.filename or "prescription")[:255],
        stored_path=stored_path, mime_type=mime, extracted_text=extracted, extracted_medicines=candidates, status=PrescriptionStatus.pending_review)
    db.add(record); db.commit(); db.refresh(record)
    return record

@router.get("/prescriptions", response_model=list[PrescriptionOut])
def list_prescriptions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(PrescriptionRecord).where(PrescriptionRecord.owner_id == user.id).order_by(desc(PrescriptionRecord.created_at)).limit(100)))

@router.get("/prescriptions/{prescription_id}", response_model=PrescriptionOut)
def get_prescription(prescription_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    record = db.scalar(select(PrescriptionRecord).where(PrescriptionRecord.id == prescription_id, PrescriptionRecord.owner_id == user.id))
    if not record: raise HTTPException(404, "Prescription not found")
    return record

@router.post("/prescriptions/{prescription_id}/review", response_model=PrescriptionOut)
def review_prescription(prescription_id: str, payload: PrescriptionReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Save human-reviewed fields. Reminders are created only when explicitly requested and times supplied."""
    record = db.scalar(select(PrescriptionRecord).where(PrescriptionRecord.id == prescription_id, PrescriptionRecord.owner_id == user.id))
    if not record: raise HTTPException(404, "Prescription not found")
    if record.status != PrescriptionStatus.pending_review:
        raise HTTPException(409, "This prescription has already been reviewed")
    for medicine in payload.medicines:
        if any(day < 0 or day > 6 for day in medicine.repeat_days):
            raise HTTPException(422, "repeat_days must use 0=Monday through 6=Sunday")
        if any(not __import__('re').match(r'^([01]\d|2[0-3]):[0-5]\d$', t) for t in medicine.schedule_times):
            raise HTTPException(422, "Schedule times must use HH:MM 24-hour format")
        if payload.create_reminders and not medicine.schedule_times:
            raise HTTPException(422, f"Add reviewed schedule times for {medicine.medicine_name} or turn off reminder creation")
        if payload.create_reminders and not medicine.repeat_days:
            raise HTTPException(422, f"Confirm the repeat days for {medicine.medicine_name} before creating reminders")
    record.extracted_medicines = [m.model_dump() for m in payload.medicines]
    record.review_note = payload.review_note
    record.status = PrescriptionStatus.confirmed
    record.reviewed_at = datetime.now(timezone.utc)
    if payload.create_reminders:
        for medicine in payload.medicines:
            instructions = medicine.instructions_as_written or "Follow the prescription instructions confirmed by you or your clinician."
            routine = Routine(owner_id=user.id, category=RoutineCategory.medication, title=medicine.medicine_name.strip(),
                instructions=instructions, timezone=user.timezone, medication_details={"strength": medicine.strength, "instructions_as_written": medicine.instructions_as_written, "prescription_id": record.id, "human_reviewed": True})
            routine.schedules = [RoutineSchedule(local_time=t, repeat_days=medicine.repeat_days, reminder_channel="whatsapp_text", confirmation_required=True, escalation_after_minutes=30) for t in medicine.schedule_times]
            db.add(routine)
    db.commit(); db.refresh(record)
    return record

@router.delete("/prescriptions/{prescription_id}", status_code=204)
def delete_prescription(prescription_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    record = db.scalar(select(PrescriptionRecord).where(PrescriptionRecord.id == prescription_id, PrescriptionRecord.owner_id == user.id))
    if not record: raise HTTPException(404, "Prescription not found")
    try: Path(record.stored_path).unlink(missing_ok=True)
    except OSError: pass
    db.delete(record); db.commit()
    return Response(status_code=204)
