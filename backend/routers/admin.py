from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import hash_password, require_admin
from backend.database import get_db
from backend.models.db_models import AttendeeAccount, Coordinator, Event
from backend.models.schemas import AdminAccountStatus, AdminCoordinatorOut, AdminCreateHost, AdminStudentOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/coordinators", response_model=list[AdminCoordinatorOut])
def list_coordinators(
    db: Session = Depends(get_db),
    _admin: Coordinator = Depends(require_admin),
):
    coordinators = db.query(Coordinator).order_by(Coordinator.name.asc()).all()
    return [
        AdminCoordinatorOut(
            id=coordinator.id,
            name=coordinator.name,
            email=coordinator.email,
            role=coordinator.role,
            is_active=coordinator.is_active,
            event_count=db.query(Event).filter(Event.coordinator_id == coordinator.id).count(),
        )
        for coordinator in coordinators
    ]


@router.post("/coordinators", response_model=AdminCoordinatorOut, status_code=status.HTTP_201_CREATED)
def create_host(
    payload: AdminCreateHost,
    db: Session = Depends(get_db),
    _admin: Coordinator = Depends(require_admin),
):
    normalized_email = payload.email.lower().strip()
    if db.query(Coordinator).filter(Coordinator.email == normalized_email).first():
        raise HTTPException(status_code=409, detail="A host account with this email already exists")

    coordinator = Coordinator(
        name=payload.name.strip(),
        email=normalized_email,
        password_hash=hash_password(payload.password),
    )
    db.add(coordinator)
    db.commit()
    db.refresh(coordinator)
    return AdminCoordinatorOut(
        id=coordinator.id,
        name=coordinator.name,
        email=coordinator.email,
        role=coordinator.role,
        is_active=coordinator.is_active,
        event_count=0,
    )


@router.patch("/coordinators/{coordinator_id}/status", response_model=AdminCoordinatorOut)
def update_host_status(
    coordinator_id: int,
    payload: AdminAccountStatus,
    db: Session = Depends(get_db),
    current_admin: Coordinator = Depends(require_admin),
):
    coordinator = db.query(Coordinator).filter(Coordinator.id == coordinator_id).first()
    if not coordinator:
        raise HTTPException(status_code=404, detail="Host account not found")
    if coordinator.id == current_admin.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own administrator account")
    coordinator.is_active = payload.is_active
    db.commit()
    db.refresh(coordinator)
    return AdminCoordinatorOut(
        id=coordinator.id,
        name=coordinator.name,
        email=coordinator.email,
        role=coordinator.role,
        is_active=coordinator.is_active,
        event_count=db.query(Event).filter(Event.coordinator_id == coordinator.id).count(),
    )


@router.get("/students", response_model=list[AdminStudentOut])
def list_students(
    db: Session = Depends(get_db),
    _admin: Coordinator = Depends(require_admin),
):
    students = db.query(AttendeeAccount).order_by(AttendeeAccount.full_name.asc()).all()
    return [
        AdminStudentOut(
            id=student.id,
            full_name=student.full_name,
            email=student.email,
            student_id=student.student_id,
            is_active=student.is_active,
            event_count=len(student.event_memberships),
        )
        for student in students
    ]


@router.patch("/students/{student_id}/status", response_model=AdminStudentOut)
def update_student_status(
    student_id: int,
    payload: AdminAccountStatus,
    db: Session = Depends(get_db),
    _admin: Coordinator = Depends(require_admin),
):
    student = db.query(AttendeeAccount).filter(AttendeeAccount.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student account not found")
    student.is_active = payload.is_active
    db.commit()
    db.refresh(student)
    return AdminStudentOut(
        id=student.id,
        full_name=student.full_name,
        email=student.email,
        student_id=student.student_id,
        is_active=student.is_active,
        event_count=len(student.event_memberships),
    )
