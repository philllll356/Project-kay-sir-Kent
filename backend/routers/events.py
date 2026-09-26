from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_coordinator, get_event_for_coordinator
from backend.database import get_db
from backend.models.db_models import Coordinator, Event, CheckInStatus
from backend.models.schemas import EventCreate, EventUpdate, EventOut
from backend.services.qr_service import generate_qr_token

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    """Create a new event with an auto-generated QR token."""
    event = Event(
        title=payload.title,
        description=payload.description,
        location=payload.location,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=payload.status,
        coordinator_id=current.id,
        qr_token=generate_qr_token(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _event_with_counts(event)


@router.get("", response_model=list[EventOut])
def list_events(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    """List all events for the current coordinator (the Event Book)."""
    query = db.query(Event).filter(Event.coordinator_id == current.id)
    if status_filter:
        query = query.filter(Event.status == status_filter)
    events = query.order_by(Event.created_at.desc()).all()
    return [_event_with_counts(e) for e in events]


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    """Get event detail with attendee counts."""
    event = get_event_for_coordinator(db, event_id, current)
    return _event_with_counts(event)


@router.patch("/{event_id}", response_model=EventOut)
def update_event(
    event_id: int,
    payload: EventUpdate,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    """Update event fields. Only provided fields are changed."""
    event = get_event_for_coordinator(db, event_id, current)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return _event_with_counts(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    """Delete an event and all its attendees (via cascade)."""
    event = get_event_for_coordinator(db, event_id, current)
    db.delete(event)
    db.commit()


def _event_with_counts(event: Event) -> dict:
    """Compute attendee_count and checked_in_count for an event."""
    attendees = event.attendees or []
    total = len(attendees)
    checked_in = sum(1 for a in attendees if a.check_in_status == CheckInStatus.checked_in)
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "coordinator_id": event.coordinator_id,
        "status": event.status,
        "qr_token": event.qr_token,
        "created_at": event.created_at,
        "attendee_count": total,
        "checked_in_count": checked_in,
    }
