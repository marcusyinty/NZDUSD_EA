@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"
set "PYTHON_DIR=.python_env"
set "REPO_URL=https://github.com/marcusyinty/NZDUSD_EA/archive/refs/heads/main.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.3/python-3.12.3-embed-amd64.zip"

echo ===================================================
echo NZDUSD_EA Launcher ^& Auto-Updater
echo ===================================================

:: 1. Check/Install Portable Python
if not exist "%PYTHON_DIR%\python.exe" (
    echo [INFO] Portable Python not found. Setting up...
    mkdir "%PYTHON_DIR%" 2>nul
    
    echo [INFO] Downloading Python 3.12.3 Embeddable...
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile 'python.zip'"
    
    echo [INFO] Extracting Python...
    powershell -Command "Expand-Archive -Path 'python.zip' -DestinationPath '%PYTHON_DIR%' -Force"
    del python.zip
    
    echo [INFO] Downloading get-pip.py...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'"
    
    echo [INFO] Configuring Python for pip and local modules...
    :: Uncomment "import site" in python312._pth
    powershell -Command "(Get-Content '%PYTHON_DIR%\python312._pth') -replace '#import site', 'import site' | Set-Content '%PYTHON_DIR%\python312._pth'"
    :: Add parent directory to sys.path so local scripts can be imported
    powershell -Command "Add-Content '%PYTHON_DIR%\python312._pth' '..'"
    
    echo [INFO] Installing pip...
    "%PYTHON_DIR%\python.exe" "%PYTHON_DIR%\get-pip.py"
    
    echo [INFO] Python setup complete.
) else (
    echo [INFO] Portable Python environment found.
)

:: 2. Download and Update Repository
echo [INFO] Checking for updates from GitHub...
powershell -Command "Invoke-WebRequest -Uri '%REPO_URL%' -OutFile 'main.zip'"
if exist "main.zip" (
    echo [INFO] Extracting updates...
    mkdir ".update_tmp" 2>nul
    powershell -Command "Expand-Archive -Path 'main.zip' -DestinationPath '.update_tmp' -Force"
    
    :: Copy files, overwriting old ones. This will NOT overwrite config.json because the repo only contains config.json.sample
    xcopy /Y /S /Q ".update_tmp\NZDUSD_EA-main\*" "."
    
    :: Cleanup
    rmdir /S /Q ".update_tmp"
    del main.zip
    echo [INFO] Update complete.
) else (
    echo [WARNING] Failed to download update. Proceeding with local files.
)

:: 3. Install Requirements
echo [INFO] Verifying dependencies...
"%PYTHON_DIR%\python.exe" -m pip install -r requirements.txt --upgrade

:: 4. Run the EA
echo ===================================================
echo [INFO] Starting NZDUSD_EA...
"%PYTHON_DIR%\python.exe" main.py

pause
