# Simple script to start backend and frontend
# This script is meant to be run from VS Code's integrated terminal
# It will print commands that you can run in separate terminal tabs

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  iFlow Robot - Local Development Setup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = Get-Location

Write-Host "To start the servers, open 2 terminal tabs in VS Code and run:" -ForegroundColor Yellow
Write-Host ""

Write-Host "Tab 1 - Backend:" -ForegroundColor Green
Write-Host "  cd app\backend" -ForegroundColor White
Write-Host "  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor White
Write-Host ""

Write-Host "Tab 2 - Frontend:" -ForegroundColor Green
Write-Host "  cd web" -ForegroundColor White
Write-Host "  npm run dev" -ForegroundColor White
Write-Host ""

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Ask user if they want to start backend in this terminal
$response = Read-Host "Start BACKEND in this terminal? (y/n)"

if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host ""
    Write-Host "Starting backend..." -ForegroundColor Green
    Write-Host "Open another terminal tab and run the frontend commands above" -ForegroundColor Yellow
    Write-Host ""

    Set-Location (Join-Path $projectRoot "app\backend")

    # Wait a moment then open browser
    Start-Job -ScriptBlock {
        Start-Sleep -Seconds 5

        # Wait for backend to be ready
        $maxAttempts = 30
        $attempt = 0
        $ready = $false

        while (-not $ready -and $attempt -lt $maxAttempts) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    $ready = $true
                }
            } catch {
                $attempt++
                Start-Sleep -Seconds 1
            }
        }

        if ($ready) {
            Start-Sleep -Seconds 3
            Start-Process "http://localhost:5173"
        }
    } | Out-Null

    python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
} else {
    Write-Host ""
    Write-Host "No problem! Run the commands above in separate terminal tabs." -ForegroundColor Yellow
    Write-Host ""
}
