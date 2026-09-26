import base64
import io
import uuid

import qrcode


def generate_qr_token() -> str:
    return str(uuid.uuid4())


def build_checkin_url(qr_token: str, base_url: str = "qrevent://checkin") -> str:
    return f"{base_url}/{qr_token}"


def generate_qr_base64(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
