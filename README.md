# QR Event System

QR Event System is a coordinator-focused event management application. It combines a FastAPI REST API, a SQLite database for local development, and an Expo/React Native app for event management, attendee registration, QR check-in, and notifications.

The current check-in flow uses one personal QR code per attendee. Coordinators display or share an attendee's QR code, scan it at the event, and confirm that specific attendee's check-in.

## Features

- Coordinator registration and JWT login
- Event Book with event creation, editing, and deletion
- Manual, bulk, and CSV attendee import
- Unique personal QR codes for every attendee
- Coordinator QR scanning and attendee-specific check-in
- Check-in status tracking and attendance reports
- Optional push notifications through Firebase Cloud Messaging
- Optional email fallback through SMTP
- Interactive API documentation through FastAPI/Swagger

## Architecture

```text
QR Event System/
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── database.py             # SQLAlchemy engine and database initialization
│   ├── auth.py                 # JWT authentication helpers
│   ├── models/
│   │   ├── db_models.py        # SQLAlchemy database models
│   │   └── schemas.py          # Pydantic request/response schemas
│   ├── routers/                # Auth, events, attendees, QR, check-in, notifications
│   └── services/               # QR generation and notification services
├── mobile/
│   ├── App.tsx                 # Expo application and navigation
│   └── src/
│       ├── api.ts              # Typed API client
│       └── types.ts            # Frontend API types
├── qrevent.db                  # Local SQLite database (development only)
├── .env.example                # Environment variable template
├── PROJECT_PLAN.md             # Product plan and implementation status
└── requirements.txt            # Python dependencies
```

## Prerequisites

- Python 3.11 or newer
- Node.js and npm
- A phone and development computer on the same Wi-Fi network for physical-device testing

## Backend setup

From the repository root, create the Python environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a long random value for `JWT_SECRET` in `.env`. SQLite is used by default, so no separate database server is required for local development.

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at:

- Local browser: <http://127.0.0.1:8000>
- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

Use `127.0.0.1` or `localhost` in a browser. `0.0.0.0` is a server bind address, not a browser address.

## Mobile setup

From the `mobile` directory:

```powershell
cd mobile
npm install
$env:EXPO_PUBLIC_API_URL="http://127.0.0.1:8000"
npx expo start
```

To run the web version:

```powershell
npx expo start --web
```

For a physical phone, replace `127.0.0.1` with the computer's LAN address, for example:

```powershell
$env:EXPO_PUBLIC_API_URL="http://192.168.1.25:8000"
npx expo start
```

The phone and computer must be on the same network, and Windows Firewall must allow port `8000`.

## Personal QR check-in flow

1. Register or log in as a coordinator.
2. Create an event.
3. Add attendees manually, in bulk, or by CSV.
4. Open the event details and select `QR` beside an attendee.
5. The attendee's personal QR code is generated and displayed.
6. Open `Scan QR` and scan the attendee's code.
7. Review the attendee and event shown by the app, then confirm check-in.

Each attendee has a server-generated token stored in the `attendees.qr_token` column. The token is not returned in normal attendee list responses. Existing databases are backfilled when the backend starts.

## API overview

All coordinator management endpoints require a JWT bearer token. Full request and response schemas are available in Swagger at `/docs`.

| Area | Method | Endpoint | Purpose |
|---|---:|---|---|
| Auth | `POST` | `/api/auth/register` | Create a coordinator account |
| Auth | `POST` | `/api/auth/login` | Get a JWT access token |
| Events | `GET` | `/api/events` | List coordinator events |
| Events | `POST` | `/api/events` | Create an event |
| Events | `PATCH` | `/api/events/{event_id}` | Update an event |
| Events | `DELETE` | `/api/events/{event_id}` | Delete an event |
| Attendees | `POST` | `/api/events/{event_id}/attendees` | Add one attendee |
| Attendees | `GET` | `/api/events/{event_id}/attendees` | List attendees |
| Attendees | `DELETE` | `/api/events/{event_id}/attendees/{attendee_id}` | Remove an attendee |
| QR | `GET` | `/api/events/{event_id}/attendees/{attendee_id}/qr` | Get a personal attendee QR |
| Check-in | `GET` | `/api/checkin/attendee/{attendee_qr_token}` | Look up a personal QR |
| Check-in | `POST` | `/api/checkin/attendee/{attendee_qr_token}` | Check in that attendee |
| Notifications | `POST` | `/api/events/{event_id}/notify-all` | Notify event attendees |
| Reports | `GET` | `/api/events/{event_id}/report` | Get attendance summary |

## Database

The default local database is `qrevent.db`. Open it with a SQLite Viewer extension in VS Code to inspect tables and records.

Database structure is defined in `backend/models/db_models.py`. The application calls `init_db()` during startup, which creates missing tables and applies the current QR-token compatibility migration.

For normal development:

- Create or remove events and attendees through the app or API.
- Change table structure in the SQLAlchemy models and migration logic.
- Do not commit real attendee data or secrets.
- Back up `qrevent.db` before manual database experiments.

## Notifications

Notifications are optional during local development. To enable them, configure the relevant values in `.env`:

```env
FIREBASE_CREDENTIALS_PATH=firebase-service-account.json
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
```

Do not commit `.env`, Firebase service-account files, SMTP passwords, or other credentials.

## Verification commands

Run these checks before pushing changes:

```powershell
# Frontend type check
cd mobile
npm run typecheck

# Frontend production export
npx expo export --platform web

# Return to the repository root and verify the backend imports
cd ..
.\.venv\Scripts\python.exe -c "from backend.main import app; print('backend import ok')"

# Check for whitespace errors in the pending Git diff
git diff --check
```

## Common problems

### `uvicorn` is not recognized

Run it through the virtual environment instead of relying on the system PATH:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### The phone cannot connect to the API

Use the computer's LAN IP in `EXPO_PUBLIC_API_URL`, keep both devices on the same Wi-Fi network, and allow Python through Windows Firewall.

### Registration returns a server error

Install the pinned dependencies again. The project pins `bcrypt==4.0.1` for compatibility with the current password-hashing stack:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Development workflow

1. Pull the latest changes: `git pull origin main`
2. Make a focused change in `backend/` or `mobile/`.
3. Run the verification commands above.
4. Review the diff: `git status` and `git diff`.
5. Commit with a descriptive message.
6. Push to `main` or open a feature branch for review.

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the product roadmap and [mobile/README.md](mobile/README.md) for frontend-specific notes.
