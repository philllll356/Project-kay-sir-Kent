import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.auth import JWT_SECRET, hash_password
from backend.database import SessionLocal, get_db, init_db
from backend.models.db_models import Coordinator, CoordinatorRole
from backend.routers import auth as auth_router
from backend.routers import events as events_router
from backend.routers import attendees as attendees_router
from backend.routers import qr as qr_router
from backend.routers import checkin as checkin_router
from backend.routers import notifications as notifications_router
from backend.routers import school as school_router
from backend.routers import admin as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env == "production":
        if JWT_SECRET == "dev-secret-change-in-production" or len(JWT_SECRET) < 32:
            raise RuntimeError("JWT_SECRET must be a long random value in production")
        if os.getenv("CORS_ORIGINS", "").strip() in {"", "*"}:
            raise RuntimeError("CORS_ORIGINS must explicitly list trusted production origins")
    init_db()
    bootstrap_admin()
    yield


def bootstrap_admin() -> None:
    """Create or promote the first admin when explicit bootstrap settings exist."""
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").lower().strip()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
    name = os.getenv("BOOTSTRAP_ADMIN_NAME", "School Administrator").strip()
    if not email or not password:
        return

    db = SessionLocal()
    try:
        coordinator = db.query(Coordinator).filter(Coordinator.email == email).first()
        if coordinator:
            coordinator.role = CoordinatorRole.admin
            coordinator.is_active = True
        else:
            db.add(Coordinator(
                name=name,
                email=email,
                password_hash=hash_password(password),
                role=CoordinatorRole.admin,
                is_active=True,
            ))
        db.commit()
    finally:
        db.close()


app_env = os.getenv("APP_ENV", "development").lower()
app = FastAPI(
    title="QR Event System",
    description="QR-based event management with Event Book, check-in, and push notifications.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if app_env == "production" else "/docs",
    redoc_url=None if app_env == "production" else "/redoc",
)

cors_origins = [origin.strip() for origin in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8081,http://localhost:8082,http://127.0.0.1:8081,http://127.0.0.1:8082",
).split(",") if origin.strip()]

# CORS — native mobile clients do not require CORS; browser clients use the
# explicit allow-list configured above.
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

trusted_hosts = [host.strip() for host in os.getenv("TRUSTED_HOSTS", "").split(",") if host.strip()]
if trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    max_body_bytes = int(os.getenv("MAX_REQUEST_BYTES", str(10 * 1024 * 1024)))
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_body_bytes:
        return JSONResponse(status_code=413, content={"detail": "Request body is too large"})

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=()"
    response.headers["Cache-Control"] = "no-store"
    if app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Register all routers
app.include_router(auth_router.router)
app.include_router(events_router.router)
app.include_router(attendees_router.router)
app.include_router(qr_router.router)
app.include_router(checkin_router.router)
app.include_router(notifications_router.router)
app.include_router(school_router.router)
app.include_router(admin_router.router)


@app.get("/")
def root():
    return {
        "message": "QR Event System API",
        "docs": "/docs" if app_env != "production" else None,
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ok", "environment": os.getenv("APP_ENV", "development")}
