@echo off
:: bootstrap_sunday.bat (Resides on the 1TB HDD)

:: Get the current drive letter (e.g., E:)
set DRIVE_LETTER=%~d0

:: Set all AI paths to point strictly to the external drive
:: This ensures NO files leak onto the laptop's C:\ drive
set HF_HOME=%DRIVE_LETTER%\sunday_env\huggingface_cache
set OLLAMA_MODELS=%DRIVE_LETTER%\sunday_env\ollama_models
set SUNDAY_DB_PATH=%DRIVE_LETTER%\sunday_env\data\sunday.db
set SUNDAY_VECTOR_PATH=%DRIVE_LETTER%\sunday_env\data\vectors
set DOTENV_PATH=%DRIVE_LETTER%\Sunday\.env

:: Activate the virtual environment located on the drive
call %DRIVE_LETTER%\sunday_env\Scripts\activate.bat

:: Launch the Sunday Daemon with Insomnia (24/7) and Mobile Dashboard enabled
cd %DRIVE_LETTER%\Sunday
python -m sunday.daemon.pipeline --insomnia --dashboard --telegram
