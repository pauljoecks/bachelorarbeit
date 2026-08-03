@echo off
cd /d "%~dp0"

set "CONDA_ENV=bachelorarbeit"

for /f "delims=" %%i in ('conda info --base') do set "CONDA_BASE=%%i"
if not exist "%CONDA_BASE%\Scripts\activate.bat" (
    echo Conda not found. Please install Anaconda.
    pause
    exit /b 1
)

call "%CONDA_BASE%\Scripts\activate.bat" "%CONDA_BASE%"

conda env list | findstr /B /C:"%CONDA_ENV% " >nul 2>&1
if errorlevel 1 (
    echo Creating conda environment %CONDA_ENV%...
    conda env create -f environment.yml
    if errorlevel 1 (
        echo Failed to create conda environment.
        pause
        exit /b 1
    )
)

call conda activate %CONDA_ENV%
if errorlevel 1 (
    echo Failed to activate conda environment.
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo Setup complete.
pause
