# QR Event System

QR Event System is a coordinator-focused event management application. It combines a FastAPI REST API, PostgreSQL for the active system database, and an Expo/React Native app for event management, attendee registration, QR check-in, and notifications. SQLite remains available as a local fallback.

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
- School mode with student accounts and permanent student QR codes
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
├── qrevent.db                  # SQLite fallback/migration source
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

Set a long random value for `JWT_SECRET` in `.env`. The checked-in example uses SQLite for zero-setup development; the current project workspace uses PostgreSQL with the restricted `qrevent_app` runtime role.

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at:

- Local browser: <http://127.0.0.1:8000>
- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

For a real deployment, set `APP_ENV=production`, use a long random `JWT_SECRET`, configure `DATABASE_URL` with a managed PostgreSQL database, and set `CORS_ORIGINS` to the exact web origins that should access the API. The included `Dockerfile` runs the backend on port `8000`; deploy it behind HTTPS and point the mobile build's `EXPO_PUBLIC_API_URL` at the HTTPS API URL.

The host event screen refreshes attendance automatically every five seconds, so check-ins from another phone appear without manually pressing Refresh.

## Admin Center

Set `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`, and optionally `BOOTSTRAP_ADMIN_NAME` before starting the backend to create or promote the first administrator. The administrator can then use the **Admin Center** to create host accounts, activate/deactivate hosts and students, and review account event counts. Public host registration remains available for development; for a school rollout, use the Admin Center to provision host accounts.

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

## School account mode

Students can register with a name, email, and student ID. The app creates one permanent QR code for each student account. A host adds the student to an event by email or student ID, then opens that event and selects **Scan student QR**. The backend checks that the scanned account is on that event's roster before marking the student checked in.

School account endpoints:

- `POST /api/auth/attendee/register` — create a student account
- `POST /api/auth/attendee/login` — student login
- `GET /api/auth/attendee/qr` — get the student's permanent QR image
- `POST /api/events/{event_id}/checkin/account/{account_qr_token}` — verify roster membership and check in

The existing event-attendee QR flow remains available as a fallback. Existing roster rows are automatically linked to a student account when the email or student ID matches.

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

The application is currently configured to use the local PostgreSQL database `qrevent`.
The original SQLite file, `qrevent.db`, is kept as a local backup/source and is not
deleted by the migration.

Database structure is defined in `backend/models/db_models.py`. The application calls `init_db()` during startup, which creates missing tables and applies the current QR-token compatibility migration.

For normal development and testing:

- Create or remove events and attendees through the app or API.
- Change table structure in the SQLAlchemy models and migration logic.
- Do not commit real attendee data or secrets.
- Back up the database before manual database experiments.

To repeat the one-time SQLite-to-PostgreSQL migration on another local copy,
create a SQLite backup first, set `POSTGRES_URL` in the shell, and run:

```powershell
Copy-Item qrevent.db qrevent.sqlite.backup.db
$env:POSTGRES_URL = "postgresql+psycopg://postgres:<password>@127.0.0.1:5432/qrevent"
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_postgres.py
```

The migration refuses to merge into a PostgreSQL database that already has
application data, preserves IDs, and validates foreign-key references.

## Security baseline

- Check-in changes and roster lookups require an authenticated host or administrator.
- Student QR accounts must be active and must belong to the event roster.
- Login endpoints are throttled and return generic credential errors to reduce account discovery.
- Passwords are bcrypt-hashed, JWTs include issuer/audience validation, and request payloads are bounded.
- The running application uses the restricted `qrevent_app` PostgreSQL role rather than the database administrator.
- In production, set a strong `JWT_SECRET`, explicit `CORS_ORIGINS`, `TRUSTED_HOSTS`, and `ALLOW_PUBLIC_HOST_REGISTRATION=false`.

## Google Sign-In

The app supports Google OpenID Connect sign-in for already-provisioned host and
student accounts. Add the allowed Google client IDs to `GOOGLE_CLIENT_IDS` in
the backend `.env`, then add the matching platform client IDs to
`mobile/.env` using [mobile/.env.example](mobile/.env.example). Google ID
tokens are verified by the backend; they are never trusted from decoded client
data alone. A Google email must match an existing account before it can sign in.

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
