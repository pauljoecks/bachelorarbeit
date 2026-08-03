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
    echo Conda environment "%CONDA_ENV%" not found.
    echo Please run setup\setup-env.bat first.
    pause
    exit /b 1
)

call conda activate %CONDA_ENV%
if errorlevel 1 (
    echo Failed to activate conda environment.
    pause
    exit /b 1
)

set PREPARATION_PORT=5001

echo.
echo Preparation-Modus:
echo   PREPARATION_PORT=%PREPARATION_PORT%
echo   http://localhost:%PREPARATION_PORT%
echo.

python preparation\scripts\preparation.py
if errorlevel 1 pause
