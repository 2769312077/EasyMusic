@echo off
setlocal enabledelayedexpansion
title EasyMusic Launcher

echo.
echo  =============================================
echo    EasyMusic ^| LLM Prompt-to-MIDI Generator
echo  =============================================
echo.

cd /d "%~dp0"
set "PROJECT_DIR=%CD%"
set "PYTHONPATH=%PROJECT_DIR%\src"
echo  [*] Project: %PROJECT_DIR%
echo  [*] Source : %PYTHONPATH%

REM --- Python check ---
where python >nul 2>&1
if errorlevel 1 (
    echo  [X] Python not found in PATH.
    echo      Install Python 3.10+ and ensure it is added to PATH.
    goto :fail
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo  [*] Python: %%v

REM --- Package check: easymusic ---
python -c "import easymusic" >nul 2>&1
if errorlevel 1 (
    echo  [X] easymusic package not importable.
    echo      Ensure PYTHONPATH includes the project src/ directory,
    echo      and all dependencies are installed:
    echo        pip install -e "%PROJECT_DIR%"
    goto :fail
)

REM --- uvicorn check ---
where uvicorn >nul 2>&1
if errorlevel 1 (
    echo  [X] uvicorn not found.
    echo      Run: pip install uvicorn fastapi PyYAML mido openai pydantic
    goto :fail
)

REM --- Verify project structure ---
if not exist "%PROJECT_DIR%\src\easymusic\backend\main.py" (
    echo  [X] Backend module not found.
    echo      Expected: src\easymusic\backend\main.py
    goto :fail
)
if not exist "%PROJECT_DIR%\src\easymusic\frontend\index.html" (
    echo  [X] Frontend not found.
    echo      Expected: src\easymusic\frontend\index.html
    goto :fail
)
echo  [OK] Project structure verified.

REM --- Find free random port ---
echo  [*] Scanning for an available port...
set "PORT="
for /L %%i in (1,1,200) do (
    set /a "CANDIDATE=!random! %% 9000 + 1000"
    netstat -ano 2>nul | find ":!CANDIDATE! " >nul 2>&1
    if errorlevel 1 (
        set "PORT=!CANDIDATE!"
        goto :port_found
    )
)
:port_found
if "%PORT%"=="" (
    echo  [X] No available port found in range 1000-9999.
    goto :fail
)
echo  [OK] Port %PORT% selected.

REM --- Start backend server ---
echo  [*] Launching backend server on port %PORT%...
set "PYTHONPATH=%PROJECT_DIR%\src"
start "EasyMusic Backend [%PORT%]" /D "%PROJECT_DIR%" /MIN cmd /c "title EasyMusic Backend [%PORT%] && set PYTHONPATH=%PROJECT_DIR%\src && uvicorn easymusic.backend.main:app --host 0.0.0.0 --port %PORT% --log-level warning"

REM --- Health-check loop ---
echo  [*] Waiting for backend to become ready...
set /a "ATTEMPT=0"
:health_loop
timeout /t 1 /nobreak >nul 2>&1
set /a "ATTEMPT+=1"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try {$r=Invoke-WebRequest -Uri 'http://localhost:%PORT%/api/health' -TimeoutSec 3 -UseBasicParsing; if($r.Content -match 'ok'){exit 0}else{exit 1}}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto :backend_ready
if %ATTEMPT% geq 30 (
    echo  [X] Backend did not respond within 30 seconds.
    echo      Check the minimized "EasyMusic Backend" window for error details.
    echo      Common causes: missing Python packages, config.yaml errors,
    echo      port permission denied, or easymusic import errors.
    echo.
    echo      Install dependencies:
    echo        pip install -e "%PROJECT_DIR%"
    echo        pip install uvicorn fastapi PyYAML mido openai pydantic
    taskkill /FI "WINDOWTITLE eq EasyMusic Backend*" /T /F >nul 2>&1
    goto :fail
)
echo      ... waiting (%ATTEMPT%/30^)
goto :health_loop

:backend_ready
echo  [OK] Backend healthy on http://localhost:%PORT%

REM --- Open web UI ---
echo  [*] Opening EasyMusic Web UI...
start "" "http://localhost:%PORT%/?backend=http://localhost:%PORT%"
echo  [OK] Web UI launched.

echo.
echo  =============================================
echo    EasyMusic is ready.
echo.
echo    Web UI    http://localhost:%PORT%/
echo    API       http://localhost:%PORT%/api/
echo    Health    http://localhost:%PORT%/api/health
echo    Docs      http://localhost:%PORT%/docs
echo.
echo    Press any key in this window to stop
echo    the backend and clean up.
echo  =============================================
pause >nul

REM --- Cleanup ---
echo.
echo  [*] Stopping backend...
taskkill /FI "WINDOWTITLE eq EasyMusic Backend*" /T /F >nul 2>&1
echo  [OK] Backend stopped.
timeout /t 2 /nobreak >nul 2>&1
exit /b 0

:fail
echo.
echo  =============================================
echo    EasyMusic failed to start.
echo    Review the errors above and try again.
echo.
echo    Quick setup:
echo      pip install -e "%PROJECT_DIR%"
echo      pip install uvicorn fastapi PyYAML
echo      copy src\easymusic\backend\.env.example src\easymusic\backend\.env
echo  =============================================
pause >nul
exit /b 1