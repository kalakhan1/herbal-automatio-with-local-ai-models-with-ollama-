# Setup script for Herbal Content Automation System
Write-Host "===========================================" -ForegroundColor Green
Write-Host " Herbal Automation - Setup" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

# Check Python
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) {
    Write-Host "ERROR: Python not found. Install Python 3.10+ from python.org" -ForegroundColor Red
    exit 1
}
python --version

# Create venv
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
}

# Activate and install
Write-Host "Activating venv and installing packages..." -ForegroundColor Cyan
& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements.txt

# Copy .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Edit it to add WordPress credentials." -ForegroundColor Yellow
}

# Check Ollama
$ollama = (Get-Command ollama -ErrorAction SilentlyContinue)
if (-not $ollama) {
    Write-Host ""
    Write-Host "WARNING: Ollama is not installed." -ForegroundColor Yellow
    Write-Host "Download from: https://ollama.com/download/windows" -ForegroundColor Yellow
    Write-Host "After installing, run:" -ForegroundColor Yellow
    Write-Host "  ollama pull llama3.2:3b" -ForegroundColor Yellow
} else {
    Write-Host "Ollama detected." -ForegroundColor Green
    Write-Host "Verifying model..." -ForegroundColor Cyan
    ollama list
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host " Setup complete!" -ForegroundColor Green
Write-Host " Run: .\start.ps1" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green