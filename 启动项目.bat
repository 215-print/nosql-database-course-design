@echo off
setlocal
cd /d "%~dp0"

echo Starting the Redis campus parcel station project...
echo Redis must be reachable using the settings in backend\.env.
echo Backend: http://127.0.0.1:8000/docs
echo User app: http://127.0.0.1:5173
echo Admin app: http://127.0.0.1:5174

start "Parcel station backend" /D "%~dp0backend" cmd /k run.bat
start "Parcel station user app" /D "%~dp0frontend" cmd /k "pnpm dev"
start "Parcel station admin app" /D "%~dp0frontend" cmd /k "pnpm dev:admin"

echo Three service windows have been opened. Close each window to stop its service.
endlocal
