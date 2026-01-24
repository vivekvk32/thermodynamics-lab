@echo off
echo ===================================================
echo Starting Thermodynamics Digital Lab Manual
echo ===================================================
echo.

REM Check for virtual environment and activate if exists
if exist venv\Scripts\activate.bat (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [INFO] No virtual environment found in 'venv', using system python...
)

echo.
echo [INFO] Launching Flask Server...
echo [INFO] Browser will open automatically...
REM Open browser after 2 seconds (parallel wait)
start /min cmd /c "timeout /t 2 >nul && start http://127.0.0.1:5000"

echo.
echo [INFO] Seeding database (if needed)...
python seed.py

python run.py

echo.
echo [INFO] Server stopped.
pause
