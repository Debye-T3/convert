@echo off
setlocal

set "PROJECT_DIR=D:\Projects\convert"
set "CONDA_EXE=%USERPROFILE%\anaconda3\Scripts\conda.exe"
set "ENV_NAME=convert-da30"
set "ENV_DIR=D:\Anaconda\envs\convert-da30"

cd /d "%PROJECT_DIR%"

if exist "build" rmdir /s /q "build"
if exist "dist\converter_app" rmdir /s /q "dist\converter_app"

if exist "%CONDA_EXE%" (
    "%CONDA_EXE%" run -n %ENV_NAME% pyinstaller --clean converter_app.spec
) else if exist "%ENV_DIR%\Scripts\pyinstaller.exe" (
    "%ENV_DIR%\Scripts\pyinstaller.exe" --clean converter_app.spec
) else (
    echo Could not find conda.exe or %ENV_DIR%\Scripts\pyinstaller.exe.
    pause
    exit /b 1
)

if errorlevel 1 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Build complete:
echo %PROJECT_DIR%\dist\converter_app\converter_app.exe
echo.
echo Distribute the entire dist\converter_app folder, not only converter_app.exe.
pause
