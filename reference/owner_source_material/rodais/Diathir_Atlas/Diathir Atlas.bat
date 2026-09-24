@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py atlas.py) || (python atlas.py)
if errorlevel 1 pause
