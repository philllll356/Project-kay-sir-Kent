from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import create_access_token, get_current_coordinator, hash_password, verify_password
from backend.database import get_db
from backend.models.db_models import Coordinator
from backend.models.schemas import CoordinatorLogin, CoordinatorOut, CoordinatorRegister, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: CoordinatorRegister, db: Session = Depends(get_db)):
    normalized_email = payload.email.lower().strip()
    existing = db.query(Coordinator).filter(Coordinator.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    coordinator = Coordinator(
        name=payload.name,
        email=normalized_email,
        password_hash=hash_password(payload.password),
    )
    db.add(coordinator)
    db.commit()
    db.refresh(coordinator)
    return TokenResponse(access_token=create_access_token(coordinator.id))


@router.post("/login", response_model=TokenResponse)
def login(payload: CoordinatorLogin, db: Session = Depends(get_db)):
    normalized_email = payload.email.lower().strip()
    coordinator = db.query(Coordinator).filter(Coordinator.email == normalized_email).first()
    if not coordinator or not verify_password(payload.password, coordinator.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(coordinator.id))


@router.get("/me", response_model=CoordinatorOut)
def me(current: Coordinator = Depends(get_current_coordinator)):
    return current
