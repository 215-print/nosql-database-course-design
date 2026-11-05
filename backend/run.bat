@echo off
setlocal
cd /d "%~dp0"

echo Starting the backend at http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/docs
echo Press Ctrl+C to stop.

set "PYTHON_EXE="
if exist "D:\Anaconda\envs\redis-cjh\python.exe" set "PYTHON_EXE=D:\Anaconda\envs\redis-cjh\python.exe"
if not defined PYTHON_EXE if defined CONDA_PREFIX if exist "%CONDA_PREFIX%\python.exe" set "PYTHON_EXE=%CONDA_PREFIX%\python.exe"
if not defined PYTHON_EXE set "PYTHON_EXE=python"

echo Python: %PYTHON_EXE%
"%PYTHON_EXE%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

if errorlevel 1 (
    echo.
    echo Backend failed to start. Check that Python, uvicorn, and backend dependencies are installed.
    pause
)

endlocal
