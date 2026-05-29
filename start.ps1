# SNP Detection — Start both servers
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host "Starting SNP Detection App..." -ForegroundColor Cyan
Write-Host ""

# Start FastAPI backend in background
Write-Host "[1/2] Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Yellow
$backend = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--port", "8000" `
    -WorkingDirectory "$root\backend" `
    -PassThru -WindowStyle Normal

Start-Sleep -Seconds 2

# Start Vite frontend
Write-Host "[2/2] Starting React frontend on http://localhost:5173 ..." -ForegroundColor Yellow
Write-Host ""
Write-Host "App ready at: http://localhost:5173" -ForegroundColor Green
Write-Host "API docs at:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop frontend. Backend PID: $($backend.Id)" -ForegroundColor Gray

Set-Location "$root\frontend"
npm run dev

# Cleanup backend on exit
if ($backend -and !$backend.HasExited) {
    Stop-Process -Id $backend.Id -Force
    Write-Host "Backend stopped." -ForegroundColor Gray
}
