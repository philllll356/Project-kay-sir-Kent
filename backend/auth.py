import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.db_models import AttendeeAccount, Coordinator, CoordinatorRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
JWT_ISSUER = os.getenv("JWT_ISSUER", "qrevent-api")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "qrevent-mobile")

if JWT_ALGORITHM != "HS256":
    raise RuntimeError("Only HS256 JWT signing is supported")
if not 5 <= JWT_EXPIRE_MINUTES <= 1440 * 7:
    raise RuntimeError("JWT_EXPIRE_MINUTES must be between 5 minutes and 7 days")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except (ValueError, TypeError):
        return False


def create_access_token(coordinator_id: int) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(coordinator_id),
        "kind": "coordinator",
        "iat": now,
        "exp": expire,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_attendee_access_token(account_id: int) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(account_id),
        "kind": "attendee",
        "iat": now,
        "exp": expire,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_coordinator(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Coordinator:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
        sub = payload.get("sub")
        if sub is None or payload.get("kind") != "coordinator":
            raise credentials_exception
        coordinator_id = int(sub)
    except (jwt.PyJWTError, ValueError, TypeError):
        raise credentials_exception

    coordinator = db.query(Coordinator).filter(Coordinator.id == coordinator_id).first()
    if not coordinator or not coordinator.is_active:
        raise credentials_exception
    return coordinator


def get_current_attendee(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> AttendeeAccount:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid attendee token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
        sub = payload.get("sub")
        if sub is None or payload.get("kind") != "attendee":
            raise credentials_exception
        account_id = int(sub)
    except (jwt.PyJWTError, ValueError, TypeError):
        raise credentials_exception

    account = db.query(AttendeeAccount).filter(AttendeeAccount.id == account_id).first()
    if not account or not account.is_active:
        raise credentials_exception
    return account


def get_event_for_coordinator(db: Session, event_id: int, coordinator: Coordinator):
    from backend.models.db_models import Event

    query = db.query(Event).filter(Event.id == event_id)
    if coordinator.role != CoordinatorRole.admin:
        query = query.filter(Event.coordinator_id == coordinator.id)
    event = query.first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def require_admin(current: Coordinator = Depends(get_current_coordinator)) -> Coordinator:
    if current.role != CoordinatorRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return current
