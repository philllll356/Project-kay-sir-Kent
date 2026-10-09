"""Run the end-to-end API regression suite against a dedicated PostgreSQL test database."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, OperationalError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE_URL = f"http://127.0.0.1:{os.getenv('TEST_API_PORT', '8765')}"


def require_test_database_url() -> str:
    load_dotenv(ROOT / ".env")
    test_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not test_url:
        raise RuntimeError(
            "TEST_DATABASE_URL is required and must point to a dedicated PostgreSQL test database."
        )
    if "<" in test_url or ">" in test_url:
        raise RuntimeError(
            "Replace the <test-user> and <password> placeholders in TEST_DATABASE_URL with real values."
        )

    try:
        parsed = make_url(test_url)
    except ArgumentError as error:
        raise RuntimeError(
            "TEST_DATABASE_URL is not valid. Use postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE."
        ) from error
    database_name = (parsed.database or "").lower()
    if parsed.drivername.startswith("sqlite"):
        raise RuntimeError("The API regression suite requires PostgreSQL, not SQLite.")
    if "test" not in database_name:
        raise RuntimeError("TEST_DATABASE_URL database name must include 'test'.")
    if test_url == os.getenv("DATABASE_URL", "").strip():
        raise RuntimeError("TEST_DATABASE_URL must not be the application's real DATABASE_URL.")
    return test_url


def api_request(method: str, path: str, token: str | None = None, body: object | None = None,
                headers: dict[str, str] | None = None) -> tuple[int, object]:
    request_headers = {"Accept": "application/json"}
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    if headers:
        request_headers.update(headers)
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = Request(BASE_URL + path, data=payload, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except HTTPError as error:
        raw = error.read()
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw.decode("utf-8", errors="replace")
        return error.code, parsed


def expect(label: str, actual: tuple[int, object], expected_status: int) -> object:
    status_code, body = actual
    if status_code != expected_status:
        raise AssertionError(f"{label}: expected {expected_status}, got {status_code}: {body}")
    print(f"PASS {label} ({status_code})")
    return body


def multipart_csv(csv_text: str) -> tuple[bytes, str]:
    boundary = f"----qrevent-{uuid.uuid4().hex}"
    content = csv_text.encode("utf-8")
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="attendees.csv"\r\n'
        "Content-Type: text/csv\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


def wait_for_api() -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            status_code, body = api_request("GET", "/health")
            if status_code == 200 and isinstance(body, dict) and body.get("status") == "ok":
                return
        except (URLError, OSError):
            pass
        time.sleep(0.25)
    raise RuntimeError("The test API did not become healthy within 30 seconds.")


def run_suite(admin_email: str, admin_password: str) -> None:
    suffix = uuid.uuid4().hex[:10]
    admin_login = expect(
        "admin login",
        api_request("POST", "/api/auth/login", body={"email": admin_email, "password": admin_password}),
        200,
    )
    admin_token = admin_login["access_token"]
    admin_profile = expect("admin profile", api_request("GET", "/api/auth/me", admin_token), 200)
    expect("unauthenticated events rejected", api_request("GET", "/api/events"), 401)
    expect("admin coordinators fetch", api_request("GET", "/api/admin/coordinators", admin_token), 200)
    expect("admin students fetch", api_request("GET", "/api/admin/students", admin_token), 200)
    provider_status = expect("notification provider status fetch", api_request("GET", "/api/admin/notification-status", admin_token), 200)
    if set(provider_status) != {"firebase_configured", "smtp_configured"}:
        raise AssertionError("notification status exposed unexpected fields")
    expect(
        "public host registration rejected",
        api_request(
            "POST",
            "/api/auth/register",
            body={"name": "Blocked", "email": f"blocked-{suffix}@example.com", "password": "Passw0rd!"},
        ),
        403,
    )

    student = {
        "full_name": "Regression Student",
        "email": f"student-{suffix}@example.com",
        "student_id": f"STUDENT-{suffix}",
        "password": "SmokePassw0rd!",
    }
    student_login = expect("student registration", api_request("POST", "/api/auth/attendee/register", body=student), 200)
    student_token = student_login["access_token"]
    expect(
        "student login",
        api_request("POST", "/api/auth/attendee/login", body={"email": student["email"], "password": student["password"]}),
        200,
    )
    student_profile = expect("student profile", api_request("GET", "/api/auth/attendee/me", student_token), 200)
    student_qr = expect("student QR", api_request("GET", "/api/auth/attendee/qr", student_token), 200)
    expect("student cannot access coordinator events", api_request("GET", "/api/events", student_token), 401)

    start = datetime.now(timezone.utc).replace(microsecond=0)
    end = start + timedelta(hours=1)
    event = expect(
        "create draft event",
        api_request(
            "POST",
            "/api/events",
            admin_token,
            {
                "title": f"Regression Event {suffix}",
                "location": "Test Room",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
        ),
        201,
    )
    event_id = event["id"]
    if not event.get("start_time") or not event.get("end_time"):
        raise AssertionError("event schedule was not persisted")
    expect("events list fetch", api_request("GET", "/api/events", admin_token), 200)
    expect("event detail fetch", api_request("GET", f"/api/events/{event_id}", admin_token), 200)
    expect("event QR fetch", api_request("GET", f"/api/events/{event_id}/qr", admin_token), 200)
    expect("draft check-in rejected", api_request("GET", f"/api/checkin/{event['qr_token']}", admin_token), 409)

    bulk = expect(
        "bulk roster import",
        api_request(
            "POST",
            f"/api/events/{event_id}/attendees/bulk",
            admin_token,
            {"attendees": [
                {"full_name": "Bulk One", "email": f"bulk1-{suffix}@example.com"},
                {"full_name": "Bulk Two", "email": f"bulk2-{suffix}@example.com"},
            ]},
        ),
        201,
    )
    if len(bulk) != 2:
        raise AssertionError("bulk import did not add two attendees")
    csv_body, csv_content_type = multipart_csv(
        f"full_name,email,student_id\nCSV One,csv1-{suffix}@example.com,CSV1-{suffix}\n"
        f",invalid@example.com,BAD-{suffix}\nCSV Two,csv2-{suffix}@example.com,CSV2-{suffix}\n"
    )
    # The standard request helper handles JSON only, so send the multipart
    # request directly with the correctly formed body below.
    request = Request(
        BASE_URL + f"/api/events/{event_id}/attendees/upload-csv",
        data=csv_body,
        headers={"Authorization": f"Bearer {admin_token}", "Content-Type": csv_content_type},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        csv_result = json.loads(response.read())
    if csv_result.get("added") != 2 or csv_result.get("skipped") != 1:
        raise AssertionError(f"unexpected CSV result: {csv_result}")
    print("PASS CSV result counts")

    student_attendee = expect(
        "add linked student",
        api_request(
            "POST",
            f"/api/events/{event_id}/attendees",
            admin_token,
            {"full_name": student["full_name"], "email": student["email"], "student_id": student["student_id"]},
        ),
        201,
    )
    guest = expect(
        "add guest",
        api_request(
            "POST",
            f"/api/events/{event_id}/attendees",
            admin_token,
            {"full_name": "Regression Guest", "email": f"guest-{suffix}@example.com"},
        ),
        201,
    )
    if student_attendee.get("account_id") != student_profile.get("id"):
        raise AssertionError("student roster row was not linked to account")
    guest_qr = expect("guest QR fetch", api_request("GET", f"/api/events/{event_id}/attendees/{guest['id']}/qr", admin_token), 200)
    expect("publish event", api_request("PATCH", f"/api/events/{event_id}", admin_token, {"status": "active"}), 200)
    expect("active event QR lookup", api_request("GET", f"/api/checkin/{event['qr_token']}", admin_token), 200)
    expect("student account QR check-in", api_request("POST", f"/api/events/{event_id}/checkin/account/{student_qr['qr_token']}", admin_token), 200)
    expect("guest QR lookup", api_request("GET", f"/api/checkin/attendee/{guest_qr['qr_token']}", admin_token), 200)
    expect("guest QR check-in", api_request("POST", f"/api/checkin/attendee/{guest_qr['qr_token']}", admin_token), 200)
    expect("duplicate student scan rejected", api_request("POST", f"/api/events/{event_id}/checkin/account/{student_qr['qr_token']}", admin_token), 409)
    report = expect("attendance report fetch", api_request("GET", f"/api/events/{event_id}/report", admin_token), 200)
    if report["checked_in"] != 2 or report["total_attendees"] != 6:
        raise AssertionError(f"unexpected attendance report: {report}")
    print("PASS attendance totals")

    from backend.models.db_models import NotificationLog
    from backend.database import SessionLocal
    with SessionLocal() as db:
        db.add(NotificationLog(event_id=event_id, sent_by=admin_profile["id"], message="test log", recipient_count=6))
        db.commit()
    expect("notification history fetch", api_request("GET", f"/api/events/{event_id}/notifications", admin_token), 200)
    expect("complete event", api_request("PATCH", f"/api/events/{event_id}", admin_token, {"status": "completed"}), 200)
    expect("completed check-in rejected", api_request("GET", f"/api/checkin/{event['qr_token']}", admin_token), 409)
    expect("delete event with notification log", api_request("DELETE", f"/api/events/{event_id}", admin_token), 204)
    expect("deleted event unavailable", api_request("GET", f"/api/events/{event_id}", admin_token), 404)
    print("API regression suite passed")


def main() -> int:
    try:
        test_database_url = require_test_database_url()
    except RuntimeError as error:
        print(f"TEST SETUP ERROR: {error}", file=sys.stderr)
        return 2

    os.environ["DATABASE_URL"] = test_database_url
    from backend.database import Base
    from backend.models import db_models  # noqa: F401

    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        with engine.connect():
            pass
    except OperationalError as error:
        print(
            "TEST DATABASE CONNECTION ERROR: check the PostgreSQL user, password, host, port, and database name.",
            file=sys.stderr,
        )
        print(f"Database driver message: {error.orig}", file=sys.stderr)
        engine.dispose()
        return 2
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    suffix = uuid.uuid4().hex[:10]
    admin_email = f"admin-{suffix}@example.com"
    admin_password = "AdminPassw0rd!"
    child_env = os.environ.copy()
    child_env.update({
        "APP_ENV": "development",
        "DATABASE_URL": test_database_url,
        "BOOTSTRAP_ADMIN_EMAIL": admin_email,
        "BOOTSTRAP_ADMIN_PASSWORD": admin_password,
        "BOOTSTRAP_ADMIN_NAME": "Regression Admin",
        "ALLOW_PUBLIC_HOST_REGISTRATION": "false",
    })
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", os.getenv("TEST_API_PORT", "8765")],
        cwd=ROOT,
        env=child_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_api()
        run_suite(admin_email, admin_password)
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        Base.metadata.drop_all(engine)
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
