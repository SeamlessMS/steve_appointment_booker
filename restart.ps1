Write-Host "Stopping processes on port 5003 (backend)..." -ForegroundColor Yellow
$process5003 = Get-NetTCPConnection -LocalPort 5003 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -ErrorAction SilentlyContinue
if ($process5003) {
    try {
        Stop-Process -Id $process5003 -Force
        Write-Host "Process on port 5003 has been terminated." -ForegroundColor Green
    } catch {
        Write-Host "Could not terminate process on port 5003: $_" -ForegroundColor Red
    }
} else {
    Write-Host "No process found on port 5003." -ForegroundColor Green
}

Write-Host "Stopping processes on port 3000 (frontend)..." -ForegroundColor Yellow
$process3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -ErrorAction SilentlyContinue
if ($process3000) {
    try {
        Stop-Process -Id $process3000 -Force
        Write-Host "Process on port 3000 has been terminated." -ForegroundColor Green
    } catch {
        Write-Host "Could not terminate process on port 3000: $_" -ForegroundColor Red
    }
} else {
    Write-Host "No process found on port 3000." -ForegroundColor Green
}

# Also kill any node.exe processes that might be running the servers
Write-Host "Cleaning up any node processes..." -ForegroundColor Yellow
Get-Process node -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $_.Kill()
        Write-Host "Node process $($_.Id) terminated." -ForegroundColor Green
    } catch {
        Write-Host "Could not terminate node process $($_.Id): $_" -ForegroundColor Red
    }
}

# Also kill any Python processes that might be running the backend
Write-Host "Cleaning up any Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $_.Kill()
        Write-Host "Python process $($_.Id) terminated." -ForegroundColor Green
    } catch {
        Write-Host "Could not terminate Python process $($_.Id): $_" -ForegroundColor Red
    }
}

# Check and install dependencies
Write-Host "Checking for required dependencies..." -ForegroundColor Yellow
Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
Set-Location -Path "backend"
pip install -r requirements.txt
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location -Path "../frontend"
npm install
Set-Location -Path ".."

# Reset the database if needed
Write-Host "Resetting database..." -ForegroundColor Yellow
Set-Location -Path "backend" 
python reset_db.py
Set-Location -Path ".."

# Start the backend
Write-Host "Starting backend server on port 5003..." -ForegroundColor Yellow
Start-Process -FilePath "powershell" -ArgumentList "-Command cd backend; python app.py --port=5003" -WindowStyle Minimized

# Start the frontend
Write-Host "Starting frontend server on port 3000..." -ForegroundColor Yellow
Start-Process -FilePath "powershell" -ArgumentList "-Command cd frontend; npm start" -WindowStyle Minimized

Write-Host "Both servers should now be running!" -ForegroundColor Green
Write-Host "Access frontend at: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Backend API available at: http://localhost:5003/api" -ForegroundColor Cyan

# Provide instructions on adding test lead
Write-Host "`nTo add your test lead, use the 'Add Lead' button and enter the following information:" -ForegroundColor Magenta
Write-Host "   - Name: Trout Mobile" -ForegroundColor White
Write-Host "   - Phone: 7204887700" -ForegroundColor White
Write-Host "   - Industry: Mobile Services" -ForegroundColor White
Write-Host "   - City: Denver" -ForegroundColor White
Write-Host "   - State: CO" -ForegroundColor White
Write-Host "   - Employee Count: 10+" -ForegroundColor White
Write-Host "   - Uses Mobile Devices: Yes" -ForegroundColor White 