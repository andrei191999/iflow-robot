# Quick Test Local - PowerShell
# Run this before pushing to GitHub

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "Running Backend Tests Locally" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

cd app\backend

Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt
pip install -q pytest

Write-Host "`nRunning tests..." -ForegroundColor Yellow
python -m pytest tests/api/test_settings.py -vv

$exitCode = $LASTEXITCODE

Write-Host "`n========================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "✅ All tests PASSED!" -ForegroundColor Green
} else {
    Write-Host "❌ Some tests FAILED - fix before pushing!" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
