@echo off
echo === Steve Appointment Booker Startup ===
echo.

:: Kill any existing processes
echo Stopping any existing processes...
taskkill /F /IM ngrok.exe 2>nul
taskkill /F /IM node.exe 2>nul
taskkill /F /IM python.exe 2>nul
timeout /t 1 >nul

:: Start the application
echo Starting the application...
python bootup.py

if %ERRORLEVEL% NEQ 0 (
    echo Error starting the application!
    echo Press any key to exit...
    pause >nul
) 