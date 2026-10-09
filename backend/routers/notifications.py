import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_coordinator, get_event_for_coordinator
from backend.database import get_db
from backend.models.db_models import AccountDeviceToken, Coordinator, Attendee, DeviceToken, NotificationLog, CheckInStatus
from backend.models.schemas import NotifyAllRequest, NotifyAllResponse, NotificationLogOut, AttendanceReport, AttendeeOut
from backend.services.notification_service import send_push_batch, send_email_batch, default_notify_message

router = APIRouter(prefix="/api/events", tags=["notifications"])


@router.post("/{event_id}/notify-all", response_model=NotifyAllResponse)
async def notify_all(
    event_id: int,
    request: NotifyAllRequest,
    db: Session = Depends(get_db),
    coordinator: Coordinator = Depends(get_current_coordinator),
):
    """Send push notification to all attendees. Rate-limited to once per 5 minutes."""
    event = get_event_for_coordinator(db, event_id, coordinator)

    # --- Rate limit check ---
    rate_limit_minutes = int(os.getenv("NOTIFY_RATE_LIMIT_MINUTES", "5"))

    last_log = (
        db.query(NotificationLog)
        .filter(NotificationLog.event_id == event.id)
        .order_by(NotificationLog.sent_at.desc())
        .first()
    )

    if last_log:
        now = datetime.now(timezone.utc)
        last_sent = last_log.sent_at.replace(tzinfo=timezone.utc) if last_log.sent_at.tzinfo is None else last_log.sent_at
        diff = now - last_sent
        cooldown = timedelta(minutes=rate_limit_minutes)
        if diff < cooldown:
            remaining = int((cooldown - diff).total_seconds() / 60) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining} minute(s) before sending another notification.",
            )

    # --- Build notification message ---
    message = request.message or default_notify_message(event.title, event.location)

    # --- Collect recipients ---
    attendees = db.query(Attendee).filter(Attendee.event_id == event.id).all()

    # Get active legacy attendee tokens for guest/older registrations.
    fcm_tokens = []
    attendee_ids_with_tokens = set()
    if attendees:
        device_tokens = (
            db.query(DeviceToken)
            .filter(
                DeviceToken.attendee_id.in_([a.id for a in attendees]),
                DeviceToken.is_active == True,
            )
            .all()
        )
        for dt in device_tokens:
            fcm_tokens.append(dt.fcm_token)
            attendee_ids_with_tokens.add(dt.attendee_id)

    # Get active tokens registered by the student account itself.
    account_ids = {a.account_id for a in attendees if a.account_id is not None}
    account_ids_with_tokens = set()
    if account_ids:
        account_tokens = (
            db.query(AccountDeviceToken)
            .filter(
                AccountDeviceToken.account_id.in_(account_ids),
                AccountDeviceToken.is_active.is_(True),
            )
            .all()
        )
        for token in account_tokens:
            fcm_tokens.append(token.fcm_token)
            account_ids_with_tokens.add(token.account_id)

    # Email fallback: attendees without device tokens who have email
    email_recipients = []
    for a in attendees:
        if a.id not in attendee_ids_with_tokens and a.account_id not in account_ids_with_tokens and a.email:
            email_recipients.append((a.email, f"Event: {event.title}", message))

    # --- Send notifications ---
    push_count = send_push_batch(fcm_tokens, event.title, message) if fcm_tokens else 0
    email_count = await send_email_batch(email_recipients) if email_recipients else 0

    # --- Log the notification ---
    log = NotificationLog(
        event_id=event.id,
        sent_by=coordinator.id,
        message=message,
        recipient_count=len(attendees),
        push_count=push_count,
        email_count=email_count,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()

    return NotifyAllResponse(
        recipient_count=len(attendees),
        push_count=push_count,
        email_count=email_count,
        message=f"Sent to {push_count + email_count} of {len(attendees)} attendees",
    )


@router.get("/{event_id}/notifications", response_model=list[NotificationLogOut])
def get_notifications(
    event_id: int,
    db: Session = Depends(get_db),
    coordinator: Coordinator = Depends(get_current_coordinator),
):
    """Get notification history for an event."""
    event = get_event_for_coordinator(db, event_id, coordinator)

    logs = (
        db.query(NotificationLog)
        .filter(NotificationLog.event_id == event.id)
        .order_by(NotificationLog.sent_at.desc())
        .all()
    )
    return logs


@router.get("/{event_id}/report", response_model=AttendanceReport)
def get_report(
    event_id: int,
    db: Session = Depends(get_db),
    coordinator: Coordinator = Depends(get_current_coordinator),
):
    """Get attendance summary report for an event."""
    event = get_event_for_coordinator(db, event_id, coordinator)

    attendees = db.query(Attendee).filter(Attendee.event_id == event.id).all()
    total = len(attendees)
    checked_in = sum(1 for a in attendees if a.check_in_status == CheckInStatus.checked_in)

    logs = db.query(NotificationLog).filter(NotificationLog.event_id == event.id).all()
    notifications_sent = len(logs)

    # Compute has_device_token per attendee
    token_attendee_ids = set()
    if attendees:
        active_tokens = (
            db.query(DeviceToken.attendee_id)
            .filter(
                DeviceToken.attendee_id.in_([a.id for a in attendees]),
                DeviceToken.is_active == True,
            )
            .all()
        )
        token_attendee_ids = {t[0] for t in active_tokens}

    attendee_list = []
    for a in attendees:
        attendee_list.append(
            AttendeeOut(
                id=a.id,
                event_id=a.event_id,
                full_name=a.full_name,
                email=a.email,
                phone=a.phone,
                student_id=a.student_id,
                check_in_status=a.check_in_status,
                checked_in_at=a.checked_in_at,
                has_device_token=a.id in token_attendee_ids,
            )
        )

    return AttendanceReport(
        event_id=event.id,
        title=event.title,
        total_attendees=total,
        checked_in=checked_in,
        pending=total - checked_in,
        notifications_sent=notifications_sent,
        attendees=attendee_list,
    )
