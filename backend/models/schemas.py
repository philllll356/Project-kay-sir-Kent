from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from backend.models.db_models import CheckInStatus, EventStatus, Platform


class CoordinatorRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=6)


class CoordinatorLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CoordinatorOut(BaseModel):
    id: int
    name: str
    email: str

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: EventStatus = EventStatus.draft


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[EventStatus] = None


class EventOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    location: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    coordinator_id: int
    status: EventStatus
    qr_token: str
    created_at: datetime
    attendee_count: int = 0
    checked_in_count: int = 0

    model_config = {"from_attributes": True}


class AttendeeCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    student_id: Optional[str] = None


class AttendeeBulkCreate(BaseModel):
    attendees: list[AttendeeCreate]


class AttendeeOut(BaseModel):
    id: int
    event_id: int
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    student_id: Optional[str]
    check_in_status: CheckInStatus
    checked_in_at: Optional[datetime]
    has_device_token: bool = False

    model_config = {"from_attributes": True}


class CheckInRequest(BaseModel):
    attendee_id: int


class CheckInByEmailRequest(BaseModel):
    email: EmailStr


class DeviceTokenRegister(BaseModel):
    fcm_token: str
    platform: Platform


class NotifyAllRequest(BaseModel):
    message: Optional[str] = None


class NotifyAllResponse(BaseModel):
    recipient_count: int
    push_count: int
    email_count: int
    message: str


class NotificationLogOut(BaseModel):
    id: int
    event_id: int
    message: str
    recipient_count: int
    push_count: int
    email_count: int
    sent_at: datetime

    model_config = {"from_attributes": True}


class QRResponse(BaseModel):
    qr_token: str
    qr_base64: str
    checkin_url: str


class EventPublicOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    location: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    status: EventStatus

    model_config = {"from_attributes": True}


class AttendanceReport(BaseModel):
    event_id: int
    title: str
    total_attendees: int
    checked_in: int
    pending: int
    notifications_sent: int
    attendees: list[AttendeeOut]
