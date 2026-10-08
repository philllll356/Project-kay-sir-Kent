# QR Event System — Product and Engineering Plan

Last updated: 2026-10-08

## 1. Product goal

QR Event System is a school-ready event attendance platform. An administrator
creates controlled host accounts, hosts create events and rosters, students
use their own account QR code, and a host scans that QR code to verify event
membership and record one reliable check-in.

The current priority is system correctness and security. Deployment and app
store publication are later phases.

## 2. Current verified status

### Completed

- FastAPI backend with PostgreSQL as the active local database.
- SQLite-to-PostgreSQL migration with backup, preserved IDs, and foreign-key validation.
- Restricted PostgreSQL runtime role ('qrevent_app'), not the database administrator.
- Host and student login, password hashing, active/inactive account controls, and JWT authentication.
- Admin center for creating hosts and activating or deactivating hosts and students.
- Event Book with event ownership rules for hosts and all-event access for administrators.
- Student account QR generation and host-only roster membership check-in.
- Duplicate check-in protection and event ownership checks.
- Manual, bulk, and bounded CSV roster import.
- Security headers, explicit CORS methods, request-size limits, login throttling, and production configuration checks.
- Google Sign-In integration code, pending Google OAuth client IDs.
- Backend compilation, mobile type checking, PostgreSQL health checks, and protected-route tests.

### Current data and known configuration gaps

- PostgreSQL currently contains 1 host, 2 events, 2 attendees, and 2 notification logs.
- There are currently 0 student accounts, so a successful student QR check-in still needs an acceptance test account.
- Google Sign-In is implemented but intentionally returns 503 until GOOGLE_CLIENT_IDS is configured.
- Firebase push notifications and SMTP email are optional and are not configured yet.
- No external deployment work is included in the current phase.

## 3. Roles and permissions

| Role | Allowed actions |
|---|---|
| Administrator | Manage hosts and students; view all events; use administrative controls |
| Host | Manage only owned events, rosters, QR codes, check-ins, reports, and notifications |
| Student | Sign in, view personal QR, and own account status |
| Unauthenticated visitor | No protected event, roster, or check-in data |

Public host registration is allowed only for development. School operation must
use administrator-provisioned host accounts.

## 4. Functional requirements

### Accounts and identity

- FR-01: A host can sign in with email/password when the account is active.
- FR-02: A student can register or sign in with email/password and student ID.
- FR-03: An administrator can create host accounts without exposing host passwords.
- FR-04: Inactive accounts cannot sign in or use protected endpoints.
- FR-05: Google Sign-In accepts only Google-issued, verified ID tokens whose audience is configured.
- FR-06: Google Sign-In links only to an existing host or student account; unknown accounts are rejected.
- FR-07: Account recovery and session refresh are required before public rollout.

### Events and rosters

- FR-08: Hosts can create, edit, list, and delete only their own events.
- FR-09: Administrators can review all events without becoming event owners.
- FR-10: Hosts can add attendees manually, in bulk, or through bounded UTF-8 CSV import.
- FR-11: A roster entry can link to a student account by normalized email or student ID.
- FR-12: Duplicate roster entries for the same event are rejected or skipped with a clear result.
- FR-13: Event status supports draft, active, and completed states with validated transitions.

### QR and attendance

- FR-14: Every student account has one persistent, unguessable account QR token.
- FR-15: Only an authenticated host or administrator can perform a check-in mutation.
- FR-16: The scanned student must be active and present on the selected event roster.
- FR-17: A second check-in is rejected without changing the original timestamp.
- FR-18: Check-in writes are atomic under concurrent scans.
- FR-19: Hosts can view attendance totals and attendee status for owned events.
- FR-20: QR and roster endpoints do not expose protected data to unauthenticated clients.

### Notifications and reporting

- FR-21: Hosts can send a rate-limited event notification to roster recipients.
- FR-22: Push and email delivery results are recorded separately from intended recipient count.
- FR-23: Hosts can view event attendance and notification reports.
- FR-24: Notification failures must not roll back a successful attendance change.

## 5. Non-functional requirements

### Security

- NFR-01: Passwords are bcrypt-hashed and limited to a safe length.
- NFR-02: JWTs use an explicit algorithm, issuer, audience, expiry, and unique ID.
- NFR-03: Login attempts are throttled; the limiter must move to shared storage before multiple workers are used.
- NFR-04: Protected reads and writes require the correct role and resource ownership.
- NFR-05: The application database role has no superuser, database-creation, or role-creation privileges.
- NFR-06: Production requires a strong secret, explicit CORS origins, trusted hosts, and disabled public host registration.
- NFR-07: Secrets, Google client secrets, Firebase keys, and SMTP credentials never enter source control or mobile code.
- NFR-08: API errors do not expose SQL, stack traces, credentials, or internal file paths.

### Reliability and data quality

- NFR-09: PostgreSQL is the system-of-record database for shared or pilot use.
- NFR-10: Database schema changes use explicit migrations; the runtime role must not require table ownership.
- NFR-11: Foreign keys, unique constraints, active-account checks, and event ownership rules are enforced server-side.
- NFR-12: Migration and backup procedures are repeatable and validated by row counts and relationship checks.
- NFR-13: Core API health and authorization checks run before every milestone.

### Usability and privacy

- NFR-14: A host can complete a scan and receive a clear success, duplicate, unregistered, inactive, or wrong-event message.
- NFR-15: Student personal data is returned only to authorized host/admin workflows.
- NFR-16: The mobile app stores its session using secure storage on native platforms.
- NFR-17: Camera permission failures and unavailable backend services have clear user-facing messages.

## 6. System architecture

~~~text
Expo / React Native mobile app
  ├─ host mode: Event Book, roster, scanner, reports, notifications
  └─ student mode: account, permanent QR, optional Google sign-in
                 │ HTTPS REST API
                 ▼
FastAPI backend
  ├─ authentication and role authorization
  ├─ event, roster, QR, check-in, admin, notification services
  └─ bounded inputs, audit-ready errors, rate limits, security headers
                 │ SQLAlchemy + psycopg
                 ▼
PostgreSQL (qrevent, restricted qrevent_app runtime role)
  ├─ coordinators / admin roles
  ├─ attendee_accounts / Google subject links
  ├─ events / attendees / device_tokens
  └─ notification_logs
~~~

SQLite remains a local fallback and migration source, not the shared system of
record.

## 7. API contract groups

| Group | Protected by | Purpose |
|---|---|---|
| /api/auth/* | Public for login/register; throttled | Email/password and Google identity exchange |
| /api/admin/* | Administrator | Host/student account administration |
| /api/events/* | Host/admin + ownership | Event Book, rosters, QR, reports, notifications |
| /api/events/{id}/checkin/account/* | Host/admin + ownership | Primary school QR check-in flow |
| /api/checkin/* | Host/admin | Legacy event/personal QR operations, retained but protected |
| /health | Public health probe | Database availability only; no private data |

## 8. Delivery phases

### Phase A — Core system baseline — complete

- [x] School accounts, host accounts, admin role, and role-aware authorization.
- [x] PostgreSQL installation, database creation, data migration, and restricted runtime role.
- [x] Host-scans-student-account-QR workflow.
- [x] Security hardening and negative authorization tests.
- [x] Google Sign-In code path and mobile configuration placeholders.

### Phase B — Acceptance and correctness — next

- [ ] Create controlled test accounts: administrator, host, active student, inactive student, and unlinked Google account.
- [ ] Run the complete event workflow against PostgreSQL: create event, add roster, link account, scan QR, refresh status.
- [ ] Test invalid QR, wrong event, duplicate scan, inactive student, inactive host, expired token, and non-owner access.
- [ ] Test CSV limits, malformed rows, duplicate rows, and rollback behavior.
- [ ] Validate event status transitions and prevent check-in outside the intended event state.
- [ ] Add automated backend tests so these checks run repeatedly instead of manually.

### Phase C — Identity completion

- [ ] Add Google OAuth client IDs and test host/student Google sign-in.
- [ ] Add account recovery with expiring, single-use reset tokens.
- [ ] Add refresh-token/session revocation strategy and sign-out invalidation.
- [ ] Add school-domain restrictions where required.
- [ ] Add an audit log for administrator actions, account changes, roster changes, and check-ins.

### Phase D — Notifications and operations

- [ ] Configure Firebase and test push delivery on real Android/iOS devices.
- [ ] Configure SMTP fallback and verify delivery failures are visible.
- [ ] Add notification confirmation and delivery history UI.
- [ ] Add pagination and search for large student, event, and roster lists.
- [ ] Add database backup/restore drill and migration versioning.

### Phase E — Deployment — later

- [ ] HTTPS API hosting and managed PostgreSQL.
- [ ] Secret management, logs, metrics, alerting, and health monitoring.
- [ ] Multiple-worker deployment with a shared rate limiter.
- [ ] Expo/EAS builds, app signing, store metadata, and release checklist.

## 9. Definition of done for the system phase

The system phase is complete when:

1. An administrator can provision a host.
2. A student can create or receive an active account and display a QR code.
3. A host can create an event, add the student, and scan the student QR.
4. The API rejects an unregistered, inactive, duplicate, wrong-event, or unauthenticated check-in.
5. PostgreSQL records the correct single attendance result under repeated or concurrent scans.
6. The same checks pass after restarting the backend.
7. Google Sign-In, if enabled, accepts only verified configured tokens and never auto-links an unknown account.

## 10. Verification commands

~~~powershell
# Backend syntax/import checks
.\.venv\Scripts\python.exe -m compileall -q backend scripts
.\.venv\Scripts\python.exe -c "from backend.main import app; print(len(app.openapi()['paths']))"

# Mobile type check
cd mobile
npm run typecheck
cd ..

# Working-tree formatting check
git diff --check
~~~

The next implementation target is Phase B, not deployment: create controlled
test accounts and automate the full PostgreSQL event/check-in acceptance flow.
