import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

def uid(): return str(uuid.uuid4())
def utcnow(): return datetime.now(timezone.utc)

class RoutineCategory(str, enum.Enum):
    medication = "medication"
    supplement = "supplement"
    hydration = "hydration"
    fitness = "fitness"
    sleep = "sleep"
    custom = "custom"

class RoutineStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"

class EventStatus(str, enum.Enum):
    scheduled = "scheduled"
    sent = "sent"
    completed = "completed"
    skipped = "skipped"
    unconfirmed = "unconfirmed"

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    messaging_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    caregiver_alert_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    routines: Mapped[list["Routine"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

class Routine(Base):
    __tablename__ = "routines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[RoutineCategory] = mapped_column(Enum(RoutineCategory), default=RoutineCategory.custom)
    title: Mapped[str] = mapped_column(String(160))
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    status: Mapped[RoutineStatus] = mapped_column(Enum(RoutineStatus), default=RoutineStatus.active)
    medication_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # optional; never auto-interpreted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    owner: Mapped[User] = relationship(back_populates="routines")
    schedules: Mapped[list["RoutineSchedule"]] = relationship(back_populates="routine", cascade="all, delete-orphan")

class RoutineSchedule(Base):
    __tablename__ = "routine_schedules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    routine_id: Mapped[str] = mapped_column(ForeignKey("routines.id", ondelete="CASCADE"), index=True)
    local_time: Mapped[str] = mapped_column(String(5)) # HH:MM in routine timezone
    repeat_days: Mapped[list] = mapped_column(JSON, default=lambda: [0,1,2,3,4,5,6]) # Python weekday numbers
    reminder_channel: Mapped[str] = mapped_column(String(24), default="whatsapp_text")
    confirmation_required: Mapped[bool] = mapped_column(Boolean, default=True)
    escalation_after_minutes: Mapped[int] = mapped_column(Integer, default=30)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    routine: Mapped[Routine] = relationship(back_populates="schedules")
    events: Mapped[list["RoutineEvent"]] = relationship(back_populates="schedule", cascade="all, delete-orphan")

class RoutineEvent(Base):
    __tablename__ = "routine_events"
    __table_args__ = (UniqueConstraint("schedule_id", "due_at", name="uq_schedule_due_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("routine_schedules.id", ondelete="CASCADE"), index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.scheduled)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmation_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    escalation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    schedule: Mapped[RoutineSchedule] = relationship(back_populates="events")

class WebhookReceipt(Base):
    __tablename__ = "webhook_receipts"
    id: Mapped[str] = mapped_column(String(160), primary_key=True) # provider event/message id for idempotency
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)


class PrescriptionStatus(str, enum.Enum):
    pending_review = "pending_review"
    confirmed = "confirmed"
    rejected = "rejected"

class PrescriptionRecord(Base):
    __tablename__ = "prescriptions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(1024))
    mime_type: Mapped[str] = mapped_column(String(100))
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    extracted_medicines: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[PrescriptionStatus] = mapped_column(Enum(PrescriptionStatus), default=PrescriptionStatus.pending_review)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
