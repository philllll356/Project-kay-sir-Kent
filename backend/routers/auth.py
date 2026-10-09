from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import create_access_token, create_attendee_access_token, get_current_attendee, get_current_coordinator, hash_password, verify_password
from backend.database import get_db
from backend.models.db_models import AccountDeviceToken, Attendee, AttendeeAccount, Coordinator
from backend.models.schemas import AttendeeAccountLogin, AttendeeAccountOut, AttendeeAccountRegister, CoordinatorLogin, CoordinatorOut, CoordinatorRegister, DeviceTokenRegister, GoogleSignInRequest, QRResponse, TokenResponse
from backend.security import allow_public_host_registration, rate_limit_auth
from backend.services.google_auth import verify_google_id_token
from backend.services.qr_service import build_account_qr_url, generate_qr_base64, generate_qr_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(
    payload: CoordinatorRegister,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
):
    if not allow_public_host_registration():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public host registration is disabled. Ask an administrator for an account.",
        )
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
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    db.refresh(coordinator)
    return TokenResponse(access_token=create_access_token(coordinator.id))


@router.post("/login", response_model=TokenResponse)
def login(
    payload: CoordinatorLogin,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
):
    normalized_email = payload.email.lower().strip()
    coordinator = db.query(Coordinator).filter(Coordinator.email == normalized_email).first()
    if not coordinator or not coordinator.is_active or not verify_password(payload.password, coordinator.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(coordinator.id))


@router.get("/me", response_model=CoordinatorOut)
def me(current: Coordinator = Depends(get_current_coordinator)):
    return current


@router.post("/attendee/register", response_model=TokenResponse)
def register_attendee(
    payload: AttendeeAccountRegister,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
):
    normalized_email = payload.email.lower().strip()
    normalized_student_id = payload.student_id.strip()
    existing = db.query(AttendeeAccount).filter(
        (AttendeeAccount.email == normalized_email) | (AttendeeAccount.student_id == normalized_student_id)
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or student ID already registered")

    account = AttendeeAccount(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        student_id=normalized_student_id,
        password_hash=hash_password(payload.password),
        qr_token=generate_qr_token(),
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or student ID already registered")
    db.refresh(account)
    # Link any existing school roster rows that were imported before the
    # student created an account.
    db.query(Attendee).filter(
        Attendee.account_id.is_(None),
        ((func.lower(Attendee.email) == normalized_email) | (Attendee.student_id == normalized_student_id)),
    ).update({Attendee.account_id: account.id}, synchronize_session=False)
    db.commit()
    return TokenResponse(access_token=create_attendee_access_token(account.id))


@router.post("/attendee/login", response_model=TokenResponse)
def login_attendee(
    payload: AttendeeAccountLogin,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
):
    normalized_email = payload.email.lower().strip()
    account = db.query(AttendeeAccount).filter(AttendeeAccount.email == normalized_email).first()
    if not account or not account.is_active or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=create_attendee_access_token(account.id))


@router.post("/google", response_model=TokenResponse)
def login_with_google(
    payload: GoogleSignInRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit_auth),
):
    """Verify a Google ID token and sign in an already-provisioned account."""
    identity = verify_google_id_token(payload.id_token)

    if payload.account_type == "host":
        account_by_google = db.query(Coordinator).filter(Coordinator.google_sub == identity.subject).first()
        account_by_email = db.query(Coordinator).filter(Coordinator.email == identity.email).first()
        if account_by_google and account_by_email and account_by_google.id != account_by_email.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google account link conflict")
        coordinator = account_by_google or account_by_email
        if not coordinator:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google account is not linked to a host account")
        if not coordinator.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This host account is inactive")
        if coordinator.google_sub and coordinator.google_sub != identity.subject:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google account link conflict")
        if not coordinator.google_sub:
            coordinator.google_sub = identity.subject
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Google account is already linked")
        return TokenResponse(access_token=create_access_token(coordinator.id))

    account_by_google = db.query(AttendeeAccount).filter(AttendeeAccount.google_sub == identity.subject).first()
    account_by_email = db.query(AttendeeAccount).filter(AttendeeAccount.email == identity.email).first()
    if account_by_google and account_by_email and account_by_google.id != account_by_email.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google account link conflict")
    account = account_by_google or account_by_email
    if not account:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google account is not linked to a student account")
    if not account.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This student account is inactive")
    if account.google_sub and account.google_sub != identity.subject:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google account link conflict")
    if not account.google_sub:
        account.google_sub = identity.subject
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Google account is already linked")
    return TokenResponse(access_token=create_attendee_access_token(account.id))


@router.get("/attendee/me", response_model=AttendeeAccountOut)
def attendee_me(current: AttendeeAccount = Depends(get_current_attendee)):
    return current


@router.get("/attendee/qr", response_model=QRResponse)
def attendee_qr(current: AttendeeAccount = Depends(get_current_attendee)):
    checkin_url = build_account_qr_url(current.qr_token)
    return QRResponse(
        qr_token=current.qr_token,
        qr_base64=generate_qr_base64(checkin_url),
        checkin_url=checkin_url,
    )


@router.post("/attendee/device-token")
def register_attendee_device(
    request: DeviceTokenRegister,
    db: Session = Depends(get_db),
    current: AttendeeAccount = Depends(get_current_attendee),
):
    """Register a student's own device for event notifications."""
    device = db.query(AccountDeviceToken).filter(
        AccountDeviceToken.account_id == current.id,
        AccountDeviceToken.fcm_token == request.fcm_token,
    ).first()
    if device:
        device.platform = request.platform
        device.is_active = True
    else:
        db.add(AccountDeviceToken(
            account_id=current.id,
            fcm_token=request.fcm_token,
            platform=request.platform,
            is_active=True,
        ))
    db.commit()
    return {"message": "Student device token registered successfully"}
