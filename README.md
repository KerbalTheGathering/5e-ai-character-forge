# 5e-ai-character-forge

Local-first Vite + FastAPI app that will generate playable 5e character sheets with AI backstories and portraits.

## Quickstart

**Windows**
```powershell
.\run.ps1
```
**MacOS**
```bash
chmod +x run.sh
./run.sh
```

API: http://localhost:8000
Web: http://localhost:5173

Env
Copy .env.example to .env and set:
GOOGLE_API_KEY (for Gemini)
GEMINI_MODEL_TEXT=gemini-2.5-pro
GEMINI_MODEL_IMAGE=gemini-flash-2.5