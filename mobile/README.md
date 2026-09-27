# QR Event mobile app

This is the Expo/React Native frontend for the FastAPI backend.

## Run it

From this folder:

```bash
npm install
npx expo start
```

The app defaults to `http://10.0.2.2:8000` for an Android emulator. For a physical phone, set the API URL to the computer's LAN address before starting Expo:

```bash
EXPO_PUBLIC_API_URL=http://YOUR_COMPUTER_IP:8000 npx expo start
```

On Windows PowerShell:

```powershell
$env:EXPO_PUBLIC_API_URL="http://YOUR_COMPUTER_IP:8000"
npx expo start
```

Start the backend from the project root with:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0
```

The current app connects login/register, event listing, event creation, attendee management, personal QR generation, personal QR check-in, device-token registration, and Notify All. Each attendee now has a separate personal QR code that can be shown from the event detail screen.
