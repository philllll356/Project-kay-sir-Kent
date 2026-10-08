from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from backend.models.db_models import CheckInStatus, CoordinatorRole, EventStatus, Platform


class CoordinatorRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class CoordinatorLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoogleSignInRequest(BaseModel):
    id_token: str = Field(min_length=100, max_length=8192)
    account_type: Literal["host", "attendee"]


class CoordinatorOut(BaseModel):
    id: int
    name: str
    email: str
    role: CoordinatorRole
    is_active: bool

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    location: Optional[str] = Field(default=None, max_length=255)
    start_time: datetime
    end_time: Optional[datetime] = None
    status: EventStatus = EventStatus.draft


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=4000)
    location: Optional[str] = Field(default=None, max_length=255)
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
    phone: Optional[str] = Field(default=None, max_length=50)
    student_id: Optional[str] = Field(default=None, max_length=100)


class AttendeeBulkCreate(BaseModel):
    attendees: list[AttendeeCreate] = Field(max_length=500)


class AttendeeOut(BaseModel):
    id: int
    event_id: int
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    student_id: Optional[str]
    account_id: Optional[int] = None
    check_in_status: CheckInStatus
    checked_in_at: Optional[datetime]
    has_device_token: bool = False

    model_config = {"from_attributes": True}


class CheckInRequest(BaseModel):
    attendee_id: int = Field(gt=0)


class CheckInByEmailRequest(BaseModel):
    email: EmailStr


class DeviceTokenRegister(BaseModel):
    fcm_token: str = Field(min_length=1, max_length=512)
    platform: Platform


class NotifyAllRequest(BaseModel):
    message: Optional[str] = Field(default=None, max_length=1000)


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


class AttendeeAccountRegister(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    student_id: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=72)


class AttendeeAccountLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class AttendeeAccountOut(BaseModel):
    id: int
    full_name: str
    email: str
    student_id: str
    is_active: bool

    model_config = {"from_attributes": True}


class AdminCreateHost(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class AdminAccountStatus(BaseModel):
    is_active: bool


class AdminCoordinatorOut(CoordinatorOut):
    event_count: int = 0


class AdminStudentOut(AttendeeAccountOut):
    event_count: int = 0


class PersonalCheckInOut(BaseModel):
    event_id: int
    event_title: str
    attendee: AttendeeOut


class EventPublicOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    location: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    status: EventStatus
    attendees: list[AttendeeOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AttendanceReport(BaseModel):
    event_id: int
    title: str
    total_attendees: int
    checked_in: int
    pending: int
    notifications_sent: int
    attendees: list[AttendeeOut]
