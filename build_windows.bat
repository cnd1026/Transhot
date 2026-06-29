@echo off
setlocal

cd /d "%~dp0"

echo Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

set "ADD_DATA=--add-data config\settings.example.json;config"
if exist fonts (
    set "ADD_DATA=%ADD_DATA% --add-data fonts;fonts"
)

echo Building Transhot with PyInstaller...
python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --windowed ^
    --name Transhot ^
    --paths src ^
    %ADD_DATA% ^
    main.py

if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo.
echo Build completed successfully.
echo Executable: dist\Transhot\Transhot.exe

endlocal
