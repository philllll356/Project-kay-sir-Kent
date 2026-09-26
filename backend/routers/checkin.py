from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from backend.database import get_db
from backend.models.db_models import Event, Attendee, DeviceToken, CheckInStatus
from backend.models.schemas import CheckInRequest, AttendeeOut, EventPublicOut, DeviceTokenRegister

router = APIRouter(prefix="/api/checkin", tags=["checkin"])

@router.get("/{qr_token}", response_model=EventPublicOut)
def get_event_by_qr(qr_token: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.qr_token == qr_token).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    attendees_out = []
    for attendee in event.attendees:
        has_token = db.query(DeviceToken).filter(
            DeviceToken.attendee_id == attendee.id, 
            DeviceToken.is_active == True
        ).first() is not None
        
        attendee_dict = {
            column.name: getattr(attendee, column.name) 
            for column in attendee.__table__.columns
        }
        attendee_dict['has_device_token'] = has_token
        attendees_out.append(attendee_dict)
    
    event_dict = {
        column.name: getattr(event, column.name) 
        for column in event.__table__.columns
    }
    event_dict['attendees'] = attendees_out
    
    return event_dict

@router.post("/{qr_token}", response_model=AttendeeOut)
def check_in_attendee(qr_token: str, request: CheckInRequest, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.qr_token == qr_token).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    attendee = db.query(Attendee).filter(
        Attendee.id == request.attendee_id, 
        Attendee.event_id == event.id
    ).first()
    
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

@router.post("/register-device/{attendee_id}")
def register_device(attendee_id: int, request: DeviceTokenRegister, db: Session = Depends(get_db)):
    attendee = db.query(Attendee).filter(Attendee.id == attendee_id).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
        
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
