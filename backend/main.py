from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers import auth as auth_router
from backend.routers import events as events_router
from backend.routers import attendees as attendees_router
from backend.routers import qr as qr_router
from backend.routers import checkin as checkin_router
from backend.routers import notifications as notifications_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    init_db()
    yield


app = FastAPI(
    title="QR Event System",
    description="QR-based event management with Event Book, check-in, and push notifications.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow mobile app and local dev access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(auth_router.router)
app.include_router(events_router.router)
app.include_router(attendees_router.router)
app.include_router(qr_router.router)
app.include_router(checkin_router.router)
app.include_router(notifications_router.router)


@app.get("/")
def root():
    return {"message": "QR Event System API", "docs": "/docs"}
