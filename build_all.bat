@echo off
echo ============================================
echo   TodoMate Widget - Build Script
echo ============================================
echo.

cd /d "%~dp0"

echo [1/6] Clean previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist installer_output rmdir /s /q installer_output
echo       Done.
echo.

echo [2/6] Setup venv + install packages...
if not exist venv (
    python -m venv venv
)
call .\venv\Scripts\activate.bat
pip install --quiet pywebview pystray Pillow pyinstaller
if errorlevel 1 (
    echo [ERROR] pip install failed!
    pause
    exit /b 1
)
echo       Done.
echo.

echo [3/6] Generate icons...
python create_icons.py
if errorlevel 1 (
    echo [ERROR] Icon generation failed!
    pause
    exit /b 1
)
echo.

echo [4/6] Building TodoMateWidget.exe ... (1-3 min)
.\venv\Scripts\pyinstaller.exe build.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)
echo       Done.
echo.

if not exist "dist\TodoMateWidget.exe" (
    echo [ERROR] dist\TodoMateWidget.exe not found!
    pause
    exit /b 1
)
echo [5/6] exe build OK
echo.

echo [6/6] Building installer...
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if defined ISCC (
    "%ISCC%" installer.iss
) else (
    echo [SKIP] Inno Setup not installed. Only portable exe created.
    echo        To install: winget install -e --id JRSoftware.InnoSetup
)
echo.

echo ============================================
echo   BUILD COMPLETE
echo ============================================
echo.
if exist "dist\TodoMateWidget.exe" echo   [Portable]  dist\TodoMateWidget.exe
if exist "installer_output\TodoMateWidget_Setup_1.0.0.exe" echo   [Installer] installer_output\TodoMateWidget_Setup_1.0.0.exe
echo.
pause
