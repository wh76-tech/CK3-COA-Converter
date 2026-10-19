@echo off
title CK3 Coat of Arms Converter
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    start "" "venv\Scripts\python.exe" main.py
) else (
    start "" python main.py
)
