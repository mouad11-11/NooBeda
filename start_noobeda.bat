@echo off
setlocal enabledelayedexpansion
title NoobEDA - 1-Click Launcher

echo ==============================================================================
echo            ⚡ NoobEDA - Open-Source FPGA & Digital Design Studio ⚡
echo ==============================================================================
echo.

:: 1. Verify Python availability
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] Python was not found in your system PATH.
    echo.
    where winget >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo [*] Attempting automated Python 3 installation via Windows Package Manager...
        winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
        echo.
        echo [OK] Python installed! Please close and re-run start_noobeda.bat
        pause
        exit /b 0
    ) else (
        echo [ERROR] Please install Python (3.8+) from https://www.python.org/
        echo Make sure to check the box: "Add python.exe to PATH" during installation.
        pause
        exit /b 1
    )
)

:: 2. Check and auto-install Python graphics dependencies (PyMuPDF & Pillow)
python -c "import fitz, PIL" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] Setting up in-app vector graphics viewer (pymupdf, pillow)...
    python -m pip install pymupdf pillow --quiet --disable-pip-version-check
    if %ERRORLEVEL% neq 0 (
        echo [!] Warning: Optional graphics libraries failed to install.
        echo     NoobEDA will fall back to viewing schematics in your web browser.
    ) else (
        echo [OK] In-app graphics viewer ready.
    )
)

:: 3. Check and auto-download OSS CAD Suite if missing
python "%~dp0setup_toolchain.py"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] Toolchain check encountered an issue. Starting NoobEDA anyway...
)

:: 4. Inject local tools into session PATH if present
if exist "%~dp0tools\oss-cad-suite\bin" (
    set "PATH=%~dp0tools\oss-cad-suite\bin;%~dp0tools\oss-cad-suite\lib;!PATH!"
    set "YOSYSHQ_ROOT=%~dp0tools\oss-cad-suite"
)

:: 5. Launch NoobEDA GUI
echo.
echo [*] Launching NoobEDA Cockpit...
start "" pythonw "%~dp0noobeda.py"

:: Clean exit
timeout /t 1 >nul
exit /b 0
