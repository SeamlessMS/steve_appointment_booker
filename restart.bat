@echo off
echo Killing processes on port 5003 (backend)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5003') do (
    taskkill /F /PID %%a 2>nul
    if not errorlevel 1 (
        echo Killed process on port 5003.
    )
)

echo Killing processes on port 3000 (frontend)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do (
    taskkill /F /PID %%a 2>nul
    if not errorlevel 1 (
        echo Killed process on port 3000.
    )
)

echo Cleaning up any node processes...
taskkill /F /IM node.exe 2>nul

echo Cleaning up any Python processes...
taskkill /F /IM python.exe 2>nul

echo Installing dependencies...
cd backend
pip install -r requirements.txt
cd ..
cd frontend
npm install
cd ..

echo Resetting database...
cd backend
python reset_db.py
cd ..

echo Starting backend server on port 5003...
start "Backend Server" cmd /c "cd backend && python app.py --port=5003"

echo Starting frontend server on port 3000...
start "Frontend Server" cmd /c "cd frontend && npm start"

echo Both servers should now be running!
echo Access frontend at: http://localhost:3000
echo Backend API available at: http://localhost:5003/api

echo.
echo To add your test lead, use the 'Add Lead' button and enter the following information:
echo    - Name: Trout Mobile
echo    - Phone: 7204887700
echo    - Industry: Mobile Services
echo    - City: Denver
echo    - State: CO
echo    - Employee Count: 10+
echo    - Uses Mobile Devices: Yes 