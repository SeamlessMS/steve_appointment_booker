# Steve Appointment Booker Startup Script
Write-Host "`n=== Steve Appointment Booker Startup ===`n" -ForegroundColor Cyan

# Stop existing processes
Write-Host "Stopping any existing processes..." -ForegroundColor Yellow
Get-Process -Name ngrok -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name Python -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -eq '' -and $_.Name -eq 'Python'} | Stop-Process -Force
Start-Sleep -Seconds 1

# Get current directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Start Python bootup script
Write-Host "Starting the application..." -ForegroundColor Green
try {
    python bootup.py
}
catch {
    Write-Host "Error starting the application: $_" -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} 