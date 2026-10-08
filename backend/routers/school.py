from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_coordinator, get_event_for_coordinator
from backend.database import get_db
from backend.models.db_models import Attendee, AttendeeAccount, CheckInStatus, Coordinator, DeviceToken
from backend.models.schemas import AttendeeOut

router = APIRouter(prefix="/api/events", tags=["school check-in"])


def _attendee_to_out(attendee: Attendee, db: Session) -> dict:
    has_token = db.query(DeviceToken).filter(
        DeviceToken.attendee_id == attendee.id,
        DeviceToken.is_active.is_(True),
    ).first() is not None
    result = {column.name: getattr(attendee, column.name) for column in attendee.__table__.columns}
    result["has_device_token"] = has_token
    return result


@router.post("/{event_id}/checkin/account/{account_qr_token}", response_model=AttendeeOut)
def check_in_account(
    event_id: int,
    account_qr_token: str,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    event = get_event_for_coordinator(db, event_id, current)
    account = db.query(AttendeeAccount).filter(
        AttendeeAccount.qr_token == account_qr_token,
        AttendeeAccount.is_active.is_(True),
    ).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student QR code not found")

    attendee = db.query(Attendee).filter(
        Attendee.event_id == event.id,
        Attendee.account_id == account.id,
    ).with_for_update().first()
    if not attendee:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student is not on this event list")
    if attendee.check_in_status == CheckInStatus.checked_in:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student already checked in")

    attendee.check_in_status = CheckInStatus.checked_in
    attendee.checked_in_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(attendee)
    return _attendee_to_out(attendee, db)
