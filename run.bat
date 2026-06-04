@echo off
cd /d "D:\Projects\convert"
set "CONDA_EXE=%USERPROFILE%\anaconda3\Scripts\conda.exe"
set "ENV_DIR=D:\Anaconda\envs\convert-da30"

if exist "%CONDA_EXE%" (
    "%CONDA_EXE%" run -n convert-da30 python converter_app.py
) else if exist "%ENV_DIR%\python.exe" (
    "%ENV_DIR%\python.exe" converter_app.py
) else (
    echo Could not find conda.exe or %ENV_DIR%\python.exe.
)
pause
