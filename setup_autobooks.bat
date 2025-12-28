@echo off
REM AutoBooks Environment Setup Script (Windows)
REM Run this to install all dependencies

echo ================================
echo AutoBooks Environment Setup
echo ================================
echo.

REM Check Python version
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Create virtual environment
echo.
echo [1/5] Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo.
echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo [3/5] Upgrading pip...
python -m pip install --upgrade pip

REM Install Python packages
echo.
echo [4/5] Installing Python packages...
pip install pathway==0.8.0 chromadb==0.4.22 sentence-transformers==2.2.2 pdf2image==1.16.3 pytesseract==0.3.10 pillow==10.1.0 openpyxl==3.1.2 pandas==2.1.4 numpy==1.26.2 pydantic==2.5.3 python-dotenv==1.0.0 pytest==7.4.3 watchdog==3.0.0

REM Check for Tesseract
echo.
echo [5/5] System Dependencies Check...
echo Checking for Tesseract OCR...
where tesseract >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Tesseract found!
    tesseract --version
) else (
    echo WARNING: Tesseract NOT found.
    echo Please download from: https://github.com/UB-Mannheim/tesseract/wiki
    echo After installation, add to PATH
)

REM Create project structure
echo.
echo Creating project structure...
if not exist "data\inbox" mkdir data\inbox
if not exist "data\archive" mkdir data\archive
if not exist "data\chroma_db" mkdir data\chroma_db
if not exist "src" mkdir src
if not exist "tests" mkdir tests
if not exist "config" mkdir config

REM Create .env file
if not exist ".env" (
    echo Creating .env file...
    (
        echo # AutoBooks Configuration
        echo INBOX_PATH=./data/inbox
        echo ARCHIVE_PATH=./data/archive
        echo CHROMA_DB_PATH=./data/chroma_db
        echo OUTPUT_EXCEL=./data/ledger.xlsx
        echo RULES_FILE=./config/rules.json
        echo.
        echo # Confidence Thresholds
        echo CONFIDENCE_THRESHOLD_HIGH=0.75
        echo CONFIDENCE_THRESHOLD_MEDIUM=0.50
        echo.
        echo # TDS Rates
        echo TDS_RATE_RENT=10.0
        echo TDS_RATE_SALARY=5.0
        echo TDS_RATE_CONSULTANCY=10.0
        echo TDS_RATE_CONTRACT=5.0
        echo.
        echo # Logging
        echo LOG_LEVEL=INFO
    ) > .env
)

REM Create placeholder files
type nul > data\inbox\.gitkeep
type nul > data\archive\.gitkeep

echo.
echo ================================
echo Setup Complete!
echo ================================
echo.
echo Next Steps:
echo 1. Activate environment: venv\Scripts\activate
echo 2. Install Tesseract if needed
echo 3. Run: python -c "import pathway; print('Pathway Ready!')"
echo 4. Start coding with the context files
echo.
pause