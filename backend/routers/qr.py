import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.auth import get_current_coordinator, get_event_for_coordinator
from backend.database import get_db
from backend.models.db_models import Coordinator
from backend.models.schemas import QRResponse
from backend.services.qr_service import generate_qr_base64, build_checkin_url

import qrcode

router = APIRouter(prefix="/api/events", tags=["qr"])


@router.get("/{event_id}/qr", response_model=QRResponse)
def get_qr_data(
    event_id: int,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    """Get QR code data as base64 string for display in the app."""
    event = get_event_for_coordinator(db, event_id, current)
    checkin_url = build_checkin_url(event.qr_token)
    qr_base64 = generate_qr_base64(checkin_url)
    return QRResponse(
        qr_token=event.qr_token,
        qr_base64=qr_base64,
        checkin_url=checkin_url,
    )


@router.get("/{event_id}/qr.png")
def get_qr_image(
    event_id: int,
    db: Session = Depends(get_db),
    current: Coordinator = Depends(get_current_coordinator),
):
    """Get QR code as a downloadable/printable PNG image."""
    event = get_event_for_coordinator(db, event_id, current)
    checkin_url = build_checkin_url(event.qr_token)

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(checkin_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="event-{event_id}-qr.png"'},
    )
