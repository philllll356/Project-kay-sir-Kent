import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.auth import get_current_coordinator, get_event_for_coordinator
from backend.database import get_db
from backend.models.db_models import Coordinator, Attendee
from backend.models.schemas import AttendeeCreate, AttendeeBulkCreate, AttendeeOut
from backend.services.qr_service import generate_qr_token

router = APIRouter(prefix="/api/events", tags=["attendees"])


def _attendee_to_out(attendee: Attendee) -> dict:
    """Convert an Attendee ORM object to a dict with has_device_token computed."""
    return {
        "id": attendee.id,
        "event_id": attendee.event_id,
        "full_name": attendee.full_name,
        "email": attendee.email,
        "phone": attendee.phone,
        "student_id": attendee.student_id,
        "check_in_status": attendee.check_in_status,
        "checked_in_at": attendee.checked_in_at,
        "has_device_token": len(attendee.device_tokens) > 0,
    }


@router.post("/{event_id}/attendees", response_model=AttendeeOut, status_code=status.HTTP_201_CREATED)
def create_attendee(
    event_id: int,
    attendee: AttendeeCreate,
    db: Session = Depends(get_db),
    current_coordinator: Coordinator = Depends(get_current_coordinator),
):
    """Add a single attendee to the event's attendee list."""
    event = get_event_for_coordinator(db, event_id, current_coordinator)

    db_attendee = Attendee(**attendee.model_dump(), event_id=event_id, qr_token=generate_qr_token())
    db.add(db_attendee)
    try:
        db.commit()
        db.refresh(db_attendee)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Attendee with this email already exists for this event")

    return _attendee_to_out(db_attendee)


@router.post("/{event_id}/attendees/bulk", response_model=list[AttendeeOut], status_code=status.HTTP_201_CREATED)
def create_attendees_bulk(
    event_id: int,
    data: AttendeeBulkCreate,
    db: Session = Depends(get_db),
    current_coordinator: Coordinator = Depends(get_current_coordinator),
):
    """Add multiple attendees at once. Duplicates are skipped."""
    event = get_event_for_coordinator(db, event_id, current_coordinator)

    added_attendees = []
    for attendee_data in data.attendees:
        db_attendee = Attendee(**attendee_data.model_dump(), event_id=event_id, qr_token=generate_qr_token())
        db.add(db_attendee)
        try:
            db.commit()
            db.refresh(db_attendee)
            added_attendees.append(_attendee_to_out(db_attendee))
        except IntegrityError:
            db.rollback()
            continue

    return added_attendees


@router.post("/{event_id}/attendees/upload-csv")
def upload_csv(
    event_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_coordinator: Coordinator = Depends(get_current_coordinator),
):
    """Import attendees from a CSV file. Expected columns: full_name, email, phone, student_id."""
    event = get_event_for_coordinator(db, event_id, current_coordinator)

    contents = file.file.read()
    buffer = io.StringIO(contents.decode("utf-8"))
    csv_reader = csv.DictReader(buffer)

    added = 0
    skipped = 0
    added_attendees = []

    for row in csv_reader:
        if "full_name" not in row or not row["full_name"].strip():
            skipped += 1
            continue

        db_attendee = Attendee(
            event_id=event_id,
            full_name=row["full_name"].strip(),
            email=row.get("email", "").strip() or None,
            phone=row.get("phone", "").strip() or None,
            student_id=row.get("student_id", "").strip() or None,
            qr_token=generate_qr_token(),
        )
        db.add(db_attendee)
        try:
            db.commit()
            db.refresh(db_attendee)
            added_attendees.append(_attendee_to_out(db_attendee))
            added += 1
        except IntegrityError:
            db.rollback()
            skipped += 1

    return {"added": added, "skipped": skipped, "attendees": added_attendees}


@router.get("/{event_id}/attendees", response_model=list[AttendeeOut])
def list_attendees(
    event_id: int,
    db: Session = Depends(get_db),
    current_coordinator: Coordinator = Depends(get_current_coordinator),
):
    """List all attendees for an event with their check-in status."""
    event = get_event_for_coordinator(db, event_id, current_coordinator)

    attendees = db.query(Attendee).filter(Attendee.event_id == event_id).all()
    return [_attendee_to_out(a) for a in attendees]


@router.delete("/{event_id}/attendees/{attendee_id}")
def delete_attendee(
    event_id: int,
    attendee_id: int,
    db: Session = Depends(get_db),
    current_coordinator: Coordinator = Depends(get_current_coordinator),
):
    """Remove an attendee from the event."""
    event = get_event_for_coordinator(db, event_id, current_coordinator)

    attendee = db.query(Attendee).filter(
        Attendee.id == attendee_id, Attendee.event_id == event_id
    ).first()
    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    db.delete(attendee)
    db.commit()

    return {"detail": "Attendee removed"}
