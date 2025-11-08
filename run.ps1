# Requires: PowerShell 7+, Python 3.11+, Node 18+
$ErrorActionPreference = "Stop"

Write-Host "== 5e-ai-character-forge :: bootstrap =="

$envPath = ".\.env"
if (-not (Test-Path $envPath)) { Copy-Item ".\.env.example" ".\.env"; Write-Host "Created .env from .env.example" }

# --- Python venv + deps ---
if (-not (Test-Path ".venv")) {
  Write-Host "Creating venv..."
  py -3 -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
Copy-Item -Force ".\api\requirements.txt" ".\api\requirements.lock.txt" -ErrorAction SilentlyContinue
& .\.venv\Scripts\pip.exe install -r .\api\requirements.txt

# --- Frontend scaffold (Vite) ---
if (-not (Test-Path ".\web\package.json")) {
  Write-Host "Scaffolding Vite (React+TS) in /web..."
  npm create vite@latest web -- --template react-ts
  Push-Location web
  npm i
  npm i axios
  Pop-Location
} else {
  Push-Location web
  npm i
  Pop-Location
}

# --- Start API + Web concurrently ---
.\.venv\Scripts\uvicorn.exe api.app.main:app --host 0.0.0.0 --port 8000 --reload
$api = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
Write-Host "API started (PID $($api.Id)) at http://localhost:8000"

Push-Location web
npm run dev
Pop-Location
