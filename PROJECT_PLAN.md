# QR Event System — Project Plan

> Native mobile app for QR-based event management with Event Book, check-in, and push notifications.

---

## Overview

We are building a **QR-based event system** as a **native mobile app** (Android + iOS). The event coordinator creates events and pre-loads an attendee list in the **Event Book**. The system generates QR codes for each event. When it's time for attendees to show up, the coordinator taps a **Notify All** button to send a push notification to everyone on the list (e.g., *"It's time to attend"*).

---

## Core Features

| Feature | Description |
|---------|-------------|
| **Event Book** | Coordinator creates events and pre-loads attendee lists before the event |
| **QR Codes** | System auto-generates a unique QR code per event for check-in |
| **QR Scanning** | Attendees scan the QR with the app camera to check in |
| **Push Notifications** | Coordinator taps one button to notify **all attendees** at once |
| **Check-in Tracking** | See who has checked in vs who is still pending |
| **Attendance Report** | Summary of check-ins and notification delivery |

---

## Best Tech Stack

### Recommended (best balance of speed, quality, and maintainability)

| Layer | Technology | Why this choice |
|-------|-----------|-----------------|
| **Mobile App** | **React Native + Expo** | One codebase for Android & iOS; built-in camera, push, and store publishing |
| **Backend API** | **Python + FastAPI** | Fast REST API; great libraries for QR and Firebase; easy to test |
| **Database** | **SQLite** → PostgreSQL later | Zero setup for development; upgrade when scaling |
| **QR Generation** | **`qrcode` (Python)** + **`react-native-qrcode-svg`** | Server generates QR; app can also display it |
| **QR Scanning** | **`expo-camera`** | Native camera access for scanning QR codes |
| **Push Notifications** | **Firebase Cloud Messaging (FCM)** | Real push on Android/iOS, works when app is closed |
| **Authentication** | **JWT + bcrypt** | Secure coordinator login; token stored in app |
| **App Publishing** | **Expo EAS Build** | Build and submit to Play Store / App Store without deep native setup |
| **Email Fallback** | **aiosmtplib (SMTP)** | Notify attendees who don't have the app installed |

### Why NOT other options?

| Alternative | Why we skipped it |
|-------------|-------------------|
| Flutter | Also good, but React Native + Expo has simpler push/camera setup for beginners |
| Pure native (Kotlin/Swift) | Two separate codebases — too slow for a school/group project |
| Web app / PWA | User confirmed they want a **native mobile app** |
| Streamlit dashboard | Not a mobile app; doesn't support camera scan or native push |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  MOBILE APP (Expo)                      │
│                                                         │
│  Coordinator Mode          Attendee Mode (no login)     │
│  ┌─────────────────┐      ┌──────────────────────┐     │
│  │ Login/Register  │      │ Scan QR (camera)     │     │
│  │ Event Book      │      │ Check In             │     │
│  │ Create Event    │      │ Allow Notifications  │     │
│  │ Add Attendees   │      └──────────────────────┘     │
│  │ Event Detail    │                                   │
│  │  - Show QR      │                                   │
│  │  - Notify All ◄─┼── Push button                     │
│  └────────┬────────┘                                   │
└───────────┼─────────────────────────────────────────────┘
            │ REST API (HTTPS)
            ▼
┌─────────────────────────────────────────────────────────┐
│              BACKEND (FastAPI + SQLite)                 │
│                                                         │
│  Auth │ Events │ Attendees │ QR │ Check-in │ Notify    │
└───────────┬─────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────┐    ┌──────────────────────────┐
│   SQLite Database    │    │  Firebase Cloud Messaging │
│  - coordinators      │    │  (push to all devices)    │
│  - events            │    └──────────────────────────┘
│  - attendees         │
│  - device_tokens     │
│  - notification_logs │
└──────────────────────┘
```

---

## User Flows

### Coordinator (Event Creator)

1. Register / Log in
2. Tap **Create Event** → enter title, date, time, location
3. Add attendees to the **Event Book** (manual entry or CSV import)
4. Open **Event Detail** → view QR code (print or display at venue)
5. Monitor check-ins as attendees scan
6. Tap **"Notify All — Time to Attend"** → all attendees get a push notification

### Attendee

1. Open app → tap **Scan QR** (no login needed)
2. Point camera at event QR code
3. Select their name from the pre-loaded list → **Check In**
4. Allow notification permission when prompted
5. Receive push reminder when coordinator taps Notify All

---

## Database Tables

### `coordinators`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| name | TEXT | Full name |
| email | TEXT UNIQUE | Login email |
| password_hash | TEXT | bcrypt hashed |

### `events` (Event Book entries)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| title | TEXT | Event name |
| description | TEXT | Optional |
| location | TEXT | Venue |
| start_time | DATETIME | |
| end_time | DATETIME | |
| coordinator_id | FK → coordinators | Owner |
| status | TEXT | `draft` / `active` / `completed` |
| qr_token | TEXT UNIQUE | Embedded in QR code |
| created_at | DATETIME | |

### `attendees` (pre-loaded Event Book list)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| event_id | FK → events | |
| full_name | TEXT | |
| email | TEXT | For fallback email |
| phone | TEXT | Optional |
| student_id | TEXT | Optional |
| check_in_status | TEXT | `pending` / `checked_in` |
| checked_in_at | DATETIME | Null until checked in |

### `device_tokens`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| attendee_id | FK → attendees | |
| fcm_token | TEXT | Firebase device token |
| platform | TEXT | `android` / `ios` |
| is_active | BOOLEAN | |
| registered_at | DATETIME | |

### `notification_logs`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| event_id | FK → events | |
| sent_by | FK → coordinators | |
| message | TEXT | Notification body |
| recipient_count | INTEGER | How many received it |
| sent_at | DATETIME | |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create coordinator account |
| POST | `/api/auth/login` | Login, returns JWT token |
| POST | `/api/events` | Create new event |
| GET | `/api/events` | List coordinator's events (Event Book) |
| GET | `/api/events/{id}` | Event detail |
| POST | `/api/events/{id}/attendees` | Add/import attendees |
| GET | `/api/events/{id}/attendees` | List attendees |
| GET | `/api/events/{id}/qr` | Get QR code image |
| POST | `/api/checkin/{qr_token}` | Attendee check-in via QR |
| POST | `/api/attendees/{id}/register-device` | Save FCM device token |
| POST | `/api/events/{id}/notify-all` | **Push notify all attendees** |
| GET | `/api/events/{id}/notifications` | Notification history |

---

## Project Folder Structure

```
for our project/
├── backend/
│   ├── main.py                      # FastAPI entry point
│   ├── database.py                  # SQLite connection
│   ├── models/                      # Database models
│   ├── routers/
│   │   ├── auth.py
│   │   ├── events.py
│   │   ├── attendees.py
│   │   ├── qr.py
│   │   ├── checkin.py
│   │   └── notifications.py
│   └── services/
│       ├── qr_service.py
│       └── notification_service.py
├── mobile/                          # React Native + Expo app
│   ├── app.json
│   ├── eas.json
│   ├── src/
│   │   ├── navigation/
│   │   ├── screens/
│   │   │   ├── auth/                # Login, Register
│   │   │   ├── coordinator/         # EventBook, CreateEvent, EventDetail
│   │   │   └── attendee/            # ScanQR, CheckIn
│   │   ├── components/
│   │   ├── services/                # API, notifications, auth
│   │   └── types/
│   └── assets/                      # App icon, splash
├── requirements.txt
├── .env.example
├── PROJECT_PLAN.md                  # This file
└── README.md
```

---

## What We Need To Do (Task List)

### Phase 1 — Backend + App Shell
- [ ] Set up FastAPI project with SQLite database
- [ ] Create all database models (coordinators, events, attendees, device_tokens, notification_logs)
- [ ] Build auth endpoints (register, login, JWT)
- [ ] Scaffold Expo React Native app with React Navigation
- [ ] Build Login and Register screens
- [ ] Connect app to backend API

**Goal:** Coordinator can register, log in, and communicate with the API.

---

### Phase 2 — Event Book + QR
- [ ] Build Create Event screen (title, date, location, description)
- [ ] Build Add Attendees screen (manual entry + CSV import)
- [ ] Build Event Book list screen (all coordinator events)
- [ ] Build Event Detail screen (attendee list, check-in stats)
- [ ] Implement QR code generation (backend + display in app)
- [ ] Build Scan QR screen with camera (`expo-camera`)
- [ ] Build Check-In screen (pick name from pre-loaded list)
- [ ] Wire up check-in API

**Goal:** Full event lifecycle — create, add attendees, generate QR, scan, check in.

---

### Phase 3 — Push Notifications
- [ ] Set up Firebase project (Android + iOS apps)
- [ ] Integrate FCM in backend (`firebase-admin`)
- [ ] Integrate `expo-notifications` in mobile app
- [ ] Register device token after attendee check-in
- [ ] Build **Notify All** button on Event Detail screen
- [ ] Add confirmation dialog before sending
- [ ] Log notifications in `notification_logs`
- [ ] Show delivery result to coordinator ("Sent to X of Y")

**Goal:** Coordinator taps one button → all attendees receive push notification.

---

### Phase 4 — Polish + Store Ready
- [ ] Email fallback for attendees without the app
- [ ] CSV attendee import via document picker
- [ ] Attendance report screen
- [ ] Event status lifecycle (draft → active → completed)
- [ ] App icon and splash screen
- [ ] Deep link config for QR codes
- [ ] EAS Build config for Play Store / App Store
- [ ] Write README with setup instructions

**Goal:** Publishable app ready for demo and store submission.

---

## Dependencies

### Backend (`requirements.txt`)
```
fastapi
uvicorn
sqlalchemy
python-multipart
qrcode[pil]
pyjwt
passlib[bcrypt]
python-dotenv
firebase-admin
aiosmtplib
```

### Mobile (`mobile/package.json`)
```
expo
expo-camera
expo-notifications
react-native-qrcode-svg
@react-navigation/native
@react-navigation/stack
axios
expo-secure-store
expo-document-picker
```

---

## Security Rules

- Only the **event owner** can view, edit, generate QR, and send notifications for their events
- QR tokens must be unguessable (UUID v4)
- Rate-limit Notify All to once every 5 minutes per event (prevent accidental spam)
- Store Firebase keys and JWT secret in `.env` — never commit to Git
- Hash passwords with bcrypt

---

## Testing Checklist

- [ ] Coordinator registers and logs in on a real phone
- [ ] Creates event with 3 test attendees → shows in Event Book
- [ ] QR code displays on Event Detail screen
- [ ] Second phone scans QR → check-in page loads with correct event
- [ ] Attendee checks in → status updates for coordinator
- [ ] Attendee grants notification permission → device token saved
- [ ] Coordinator taps Notify All → all test phones receive push
- [ ] Notification log shows correct count and time
- [ ] Non-owner cannot access another coordinator's events

---

## One-Time Setup (Before Coding)

1. **Install tools:** Node.js, Python 3.11+, Expo CLI, Git
2. **Create Firebase project** at [console.firebase.google.com](https://console.firebase.google.com)
   - Add Android app → download `google-services.json`
   - Add iOS app → download `GoogleService-Info.plist`
   - Enable Cloud Messaging
   - Generate service account key for backend
3. **Create `.env` file** from `.env.example` with Firebase credentials and JWT secret
4. **Run backend:** `uvicorn backend.main:app --reload`
5. **Run mobile app:** `cd mobile && npx expo start`

---

*Last updated: September 21, 2026*
