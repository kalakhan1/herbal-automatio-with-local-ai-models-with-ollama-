# Start Herbal Content Automation System
Write-Host "Starting Herbal Automation..." -ForegroundColor Green

if (-not (Test-Path ".venv")) {
    Write-Host "ERROR: venv not found. Run .\setup.ps1 first." -ForegroundColor Red
    exit 1
}

& ".\.venv\Scripts\Activate.ps1"

# Check Ollama
# Check Ollama
try {
    Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -UseBasicParsing | Out-Null
    Write-Host "✓ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Ollama not running. Start it with: ollama serve" -ForegroundColor Yellow
}

python main.py