# QR Event System

QR-based event management with a FastAPI backend and an Expo/React Native mobile app.

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the full plan and [mobile/README.md](mobile/README.md) for frontend setup.

## Start the backend

The original environment pointed to a removed Python installation. The repaired environment is now `.venv`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0
```
