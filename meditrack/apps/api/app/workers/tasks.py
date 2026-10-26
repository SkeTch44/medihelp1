import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.workers.celery_app import celery
from app.core.database import SessionLocal
from app.models.entities import RoutineEvent, RoutineSchedule, Routine, User, EventStatus, RoutineStatus
from app.integrations.whatsapp import WhatsAppProvider

@celery.task(bind=True, max_retries=3, default_retry_delay=30)
def send_routine_reminder(self, event_id: str):
    db = SessionLocal()
    try:
        event = db.get(RoutineEvent, event_id)
        if not event or event.status in {EventStatus.completed, EventStatus.skipped}: return {"sent": False, "reason": "event missing or already checked in"}
        schedule = db.get(RoutineSchedule, event.schedule_id)
        routine = db.get(Routine, schedule.routine_id) if schedule else None
        user = db.get(User, routine.owner_id) if routine else None
        if not schedule or not routine or not user or not schedule.enabled or routine.status != RoutineStatus.active:
            return {"sent": False, "reason": "schedule inactive"}
        if not user.messaging_consent or not user.phone_e164 or schedule.reminder_channel == "in_app":
            return {"sent": False, "reason": "messaging not consented/configured"}
        body = f"MediTrack reminder: {routine.title}. Reply DONE when complete, or SKIP if you are not doing it now. This is a routine reminder, not medical advice."
        result = asyncio.run(WhatsAppProvider().send_text(user.phone_e164, body))
        if result.get("messages"):
            event.status = EventStatus.sent
            event.provider_message_id = result["messages"][0].get("id")
            db.commit()
            return {"sent": True, "provider_message_id": event.provider_message_id}
        # Do not claim a stub or unaccepted message was sent.
        return {"sent": False, "provider": result}
    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc)
    finally:
        db.close()

@celery.task

def dispatch_due_reminders():
    """Minute-level scheduler. Unique(schedule_id, due_at) protects duplicate beat runs."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError
    from app.models.entities import RoutineSchedule
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    queued = 0
    db = SessionLocal()
    try:
        schedules = db.scalars(select(RoutineSchedule).where(RoutineSchedule.enabled.is_(True))).all()
        for schedule in schedules:
            routine = db.get(Routine, schedule.routine_id)
            if not routine or routine.status != RoutineStatus.active:
                continue
            try:
                local_now = now.astimezone(ZoneInfo(routine.timezone))
            except (ZoneInfoNotFoundError, ValueError):
                continue
            if local_now.strftime("%H:%M") != schedule.local_time or local_now.weekday() not in (schedule.repeat_days or []):
                continue
            event = RoutineEvent(schedule_id=schedule.id, due_at=now, status=EventStatus.scheduled)
            db.add(event)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                continue
            send_routine_reminder.delay(event.id)
            queued += 1
        return {"queued": queued, "checked_at": now.isoformat()}
    finally:
        db.close()
