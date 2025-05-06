# Cleanup script for Steve Appointment Booker
Write-Host "Cleaning up processes..."
Get-Process -Name ngrok -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name Python -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -eq ''} | Stop-Process -Force
Write-Host "Cleanup complete."
