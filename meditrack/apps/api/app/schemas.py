from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.entities import RoutineCategory, RoutineStatus, EventStatus

class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=10, max_length=128)
    phone_e164: str | None = None
    timezone: str = "Asia/Kolkata"
    messaging_consent: bool = False
    caregiver_alert_consent: bool = False

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: str
    phone_e164: str | None
    timezone: str
    messaging_consent: bool
    caregiver_alert_consent: bool

class ScheduleIn(BaseModel):
    local_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    repeat_days: list[int] = Field(default_factory=lambda: [0,1,2,3,4,5,6])
    reminder_channel: str = "whatsapp_text"
    confirmation_required: bool = True
    escalation_after_minutes: int = Field(default=30, ge=5, le=1440)

class RoutineCreate(BaseModel):
    category: RoutineCategory
    title: str = Field(min_length=1, max_length=160)
    instructions: str | None = Field(default=None, max_length=2000)
    timezone: str = "Asia/Kolkata"
    schedules: list[ScheduleIn] = Field(min_length=1, max_length=12)

class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    local_time: str
    repeat_days: list
    reminder_channel: str
    confirmation_required: bool
    escalation_after_minutes: int
    enabled: bool

class RoutineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    category: RoutineCategory
    title: str
    instructions: str | None
    timezone: str
    status: RoutineStatus
    schedules: list[ScheduleOut]

class CheckInIn(BaseModel):
    status: EventStatus
    source: str = "web"

class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    schedule_id: str
    due_at: datetime
    status: EventStatus
    confirmed_at: datetime | None
    confirmation_source: str | None

class MedicineReviewItem(BaseModel):
    medicine_name: str = Field(min_length=1, max_length=160)
    strength: str | None = Field(default=None, max_length=120)
    instructions_as_written: str | None = Field(default=None, max_length=1000)
    schedule_times: list[str] = Field(default_factory=list, max_length=12)
    source_excerpt: str | None = Field(default=None, max_length=500)
    needs_human_review: bool = True
    repeat_days: list[int] = Field(default_factory=lambda: [0,1,2,3,4,5,6])

class PrescriptionReviewIn(BaseModel):
    medicines: list[MedicineReviewItem] = Field(min_length=1, max_length=50)
    review_note: str | None = Field(default=None, max_length=2000)
    create_reminders: bool = False

class PrescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    original_filename: str
    mime_type: str
    extracted_text: str
    extracted_medicines: list
    status: str
    review_note: str | None
    created_at: datetime
    reviewed_at: datetime | None
