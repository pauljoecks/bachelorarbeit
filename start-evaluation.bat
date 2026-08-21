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

set EVALUATION_PORT=5002

echo.
echo Evaluation-Modus:
echo   EVALUATION_PORT=%EVALUATION_PORT%
echo   http://localhost:%EVALUATION_PORT%
echo.

python evaluation\scripts\evaluation.py
if errorlevel 1 pause
