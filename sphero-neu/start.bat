@echo off
setlocal
if exist "%~dp0sphero-neu" (
    cd /d "%~dp0sphero-neu"
) else (
    cd /d "%~dp0"
)

REM Detect Python executable (virtualenv or system)
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else if exist "..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=..\.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_EXE=python"
    ) else (
        where py >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            set "PYTHON_EXE=py"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [HIBA / ERROR] Python nem talalhato / Python not found!
    echo Kerlek telepitsd a Python 3.10+ verziojat es add hozza a PATH-hoz. / Please install Python 3.10+.
    pause
    exit /b 1
)

echo [*] Starting Sphero Web Server using %PYTHON_EXE%...
"%PYTHON_EXE%" web\server.py --host 0.0.0.0 --port 8080 %*
if %ERRORLEVEL% neq 0 (
    echo [!] Server exited with code %ERRORLEVEL%
    pause
)
endlocal
