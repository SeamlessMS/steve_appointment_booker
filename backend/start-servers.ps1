Write-Host "Starting backend server on port 5003..." -ForegroundColor Yellow
# Start backend server 
Start-Process -FilePath "cmd" -ArgumentList "/c python app.py --port=5003" -WorkingDirectory $PWD.Path

# Go back to root directory
Set-Location -Path ".."

Write-Host "Starting frontend server on port 3000..." -ForegroundColor Yellow
# Start frontend server
Start-Process -FilePath "cmd" -ArgumentList "/c cd frontend && npm start" -WorkingDirectory $PWD.Path

Write-Host "Both servers should now be running!" -ForegroundColor Green
Write-Host "Access frontend at: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Backend API available at: http://localhost:5003/api" -ForegroundColor Cyan 