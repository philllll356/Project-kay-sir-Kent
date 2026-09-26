import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class EventStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"


class CheckInStatus(str, enum.Enum):
    pending = "pending"
    checked_in = "checked_in"


class Platform(str, enum.Enum):
    android = "android"
    ios = "ios"


class Coordinator(Base):
    __tablename__ = "coordinators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    events: Mapped[list["Event"]] = relationship("Event", back_populates="coordinator")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    coordinator_id: Mapped[int] = mapped_column(ForeignKey("coordinators.id"), nullable=False)
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.draft)
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    coordinator: Mapped["Coordinator"] = relationship("Coordinator", back_populates="events")
    attendees: Mapped[list["Attendee"]] = relationship("Attendee", back_populates="event", cascade="all, delete-orphan")
    notification_logs: Mapped[list["NotificationLog"]] = relationship("NotificationLog", back_populates="event")


class Attendee(Base):
    __tablename__ = "attendees"
    __table_args__ = (UniqueConstraint("event_id", "email", name="uq_attendee_event_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    student_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    check_in_status: Mapped[CheckInStatus] = mapped_column(Enum(CheckInStatus), default=CheckInStatus.pending)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    event: Mapped["Event"] = relationship("Event", back_populates="attendees")
    device_tokens: Mapped[list["DeviceToken"]] = relationship("DeviceToken", back_populates="attendee", cascade="all, delete-orphan")


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (UniqueConstraint("attendee_id", "fcm_token", name="uq_device_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attendee_id: Mapped[int] = mapped_column(ForeignKey("attendees.id"), nullable=False, index=True)
    fcm_token: Mapped[str] = mapped_column(String(512), nullable=False)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attendee: Mapped["Attendee"] = relationship("Attendee", back_populates="device_tokens")


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    sent_by: Mapped[int] = mapped_column(ForeignKey("coordinators.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
    push_count: Mapped[int] = mapped_column(Integer, default=0)
    email_count: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    event: Mapped["Event"] = relationship("Event", back_populates="notification_logs")
