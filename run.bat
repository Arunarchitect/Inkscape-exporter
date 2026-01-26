@echo off
chcp 65001 >nul
title SVG to PNG Converter & PDF Merger
color 0A

echo ========================================
echo    SVG to PNG Converter & PDF Merger
echo ========================================
echo.

:: Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.8+ from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Check Python version
python --version 2>nul
if %errorlevel% neq 0 (
    echo ❌ Cannot determine Python version.
    pause
    exit /b 1
)

:: Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "python_version=%%i"
echo ✅ Python %python_version% detected

:: Check for venv module
python -c "import venv" 2>nul
if %errorlevel% neq 0 (
    echo ❌ Python venv module not available.
    echo Please install Python with venv support.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ❌ Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created.
)

:: Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ Failed to activate virtual environment.
    pause
    exit /b 1
)
echo ✅ Virtual environment activated.

:: Check if pip is available
echo.
echo Checking for pip...

python -m pip --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo ✅ pip is already installed. Skipping installation.
) ELSE (
    echo ❌ pip not found. Installing latest pip...
    python -m ensurepip --upgrade >nul 2>&1

    :: Verify installation
    python -m pip --version >nul 2>&1
    IF %ERRORLEVEL% EQU 0 (
        echo ✅ pip installed successfully.
    ) ELSE (
        echo ⚠️ pip installation failed.
    )
)


:: Check requirements.txt exists, if not create it
if not exist "requirements.txt" (
    echo.
    echo Creating requirements.txt...
    (
        echo tkinter
        echo img2pdf^>=0.4.0
        echo Pillow^>=9.0.0
    ) > requirements.txt
    echo ✅ Created requirements.txt
)

:: Install dependencies
echo.
echo Installing dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Failed to install dependencies.
    echo Trying to install individually...
    
    :: Try installing packages individually
    python -m pip install img2pdf --quiet
    python -m pip install Pillow --quiet
    
    :: Check if packages installed successfully
    python -c "import img2pdf; import PIL" 2>nul
    if %errorlevel% neq 0 (
        echo ❌ Some packages failed to install.
        echo Please check your internet connection.
        pause
        exit /b 1
    )
    echo ✅ Dependencies installed.
) else (
    echo ✅ All dependencies installed.
)

:: Check if gui.py exists
if not exist "gui.py" (
    echo.
    echo ❌ gui.py not found!
    echo.
    echo Please make sure these files are in the same folder:
    echo - gui.py
    echo - converter_tab.py
    echo - settings_tab.py
    echo - pdf_merge_tab.py
    echo - png.py
    echo.
    pause
    exit /b 1
)

:: Check for all required Python files
set "missing_files=0"
for %%f in (converter_tab.py settings_tab.py pdf_merge_tab.py png.py) do (
    if not exist "%%f" (
        echo ❌ Missing file: %%f
        set /a missing_files+=1
    )
)

if %missing_files% gtr 0 (
    echo.
    echo ❌ Missing required Python files!
    pause
    exit /b 1
)

echo.
echo ✅ All files found.

:: Run the application
echo.
echo ========================================
echo    Starting Application...
echo ========================================
echo.

:: Set environment variable to avoid Tkinter issues on Windows 10/11
set "TK_SILENCE_DEPRECATION=1"

python gui.py

:: Check if application crashed
if %errorlevel% neq 0 (
    echo.
    echo ❌ Application exited with error code: %errorlevel%
    echo.
    echo Common solutions:
    echo 1. Make sure you have all required files
    echo 2. Try reinstalling dependencies: del venv /s /q ^&^& run this batch again
    echo 3. Check Python version (needs 3.8+)
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo ✅ Application closed successfully.
pause