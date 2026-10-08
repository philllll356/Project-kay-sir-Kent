from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from backend.auth import get_current_coordinator, get_event_for_coordinator
from backend.database import get_db
from backend.models.db_models import Event, Attendee, Coordinator, DeviceToken, CheckInStatus
from backend.models.schemas import CheckInRequest, AttendeeOut, EventPublicOut, DeviceTokenRegister, PersonalCheckInOut

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


def _attendee_to_out(attendee: Attendee, db: Session) -> dict:
    has_token = db.query(DeviceToken).filter(
        DeviceToken.attendee_id == attendee.id,
        DeviceToken.is_active == True,
    ).first() is not None
    attendee_dict = {
        column.name: getattr(attendee, column.name)
        for column in attendee.__table__.columns
    }
    attendee_dict["has_device_token"] = has_token
    return attendee_dict

@router.get("/{qr_token}", response_model=EventPublicOut)
def get_event_by_qr(
    qr_token: str,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    event = db.query(Event).filter(Event.qr_token == qr_token).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    get_event_for_coordinator(db, event.id, current)
    
    attendees_out = []
    for attendee in event.attendees:
        attendees_out.append(_attendee_to_out(attendee, db))
    
    event_dict = {
        column.name: getattr(event, column.name) 
        for column in event.__table__.columns
    }
    event_dict['attendees'] = attendees_out
    
    return event_dict


@router.get("/attendee/{attendee_qr_token}", response_model=PersonalCheckInOut)
def get_attendee_by_qr(
    attendee_qr_token: str,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    attendee = db.query(Attendee).filter(Attendee.qr_token == attendee_qr_token).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee QR code not found")
    get_event_for_coordinator(db, attendee.event_id, current)
    return PersonalCheckInOut(
        event_id=attendee.event_id,
        event_title=attendee.event.title,
        attendee=_attendee_to_out(attendee, db),
    )

@router.post("/{qr_token}", response_model=AttendeeOut)
def check_in_attendee(
    qr_token: str,
    request: CheckInRequest,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    event = db.query(Event).filter(Event.qr_token == qr_token).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    get_event_for_coordinator(db, event.id, current)
    attendee = db.query(Attendee).filter(
        Attendee.id == request.attendee_id, 
        Attendee.event_id == event.id
    ).with_for_update().first()
    
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found for this event")
        
    if attendee.check_in_status == CheckInStatus.checked_in:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendee already checked in")
        
    attendee.check_in_status = CheckInStatus.checked_in
    attendee.checked_in_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(attendee)
    
    has_token = db.query(DeviceToken).filter(
        DeviceToken.attendee_id == attendee.id, 
        DeviceToken.is_active == True
    ).first() is not None
    
    attendee_dict = {
        column.name: getattr(attendee, column.name) 
        for column in attendee.__table__.columns
    }
    attendee_dict['has_device_token'] = has_token
    
    return attendee_dict


@router.post("/attendee/{attendee_qr_token}", response_model=AttendeeOut)
def check_in_attendee_by_qr(
    attendee_qr_token: str,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    attendee = db.query(Attendee).filter(Attendee.qr_token == attendee_qr_token).with_for_update().first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee QR code not found")
    get_event_for_coordinator(db, attendee.event_id, current)
    if attendee.check_in_status == CheckInStatus.checked_in:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendee already checked in")

    attendee.check_in_status = CheckInStatus.checked_in
    attendee.checked_in_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(attendee)
    return _attendee_to_out(attendee, db)

@router.post("/register-device/{attendee_id}")
def register_device(
    attendee_id: int,
    request: DeviceTokenRegister,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    get_event_for_coordinator(db, attendee.event_id, current)
        
    new_token = DeviceToken(
        attendee_id=attendee_id,
        fcm_token=request.fcm_token,
        platform=request.platform,
        is_active=True,
    )
    db.add(new_token)
    
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_token = db.query(DeviceToken).filter(
            DeviceToken.attendee_id == attendee_id,
            DeviceToken.fcm_token == request.fcm_token,
        ).first()
        if existing_token:
            existing_token.is_active = True
            db.commit()
            
    return {"message": "Device token registered successfully"}
