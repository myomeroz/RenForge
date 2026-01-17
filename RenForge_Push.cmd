@echo off
REM RenForge 2-click Commit+Push (standalone v2)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\rfpush_gui.ps1"
exit /b %errorlevel%
