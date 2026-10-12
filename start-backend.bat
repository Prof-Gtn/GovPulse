@echo off
cd /d C:\Users\Hp\GovPulse
call venv\Scripts\activate.bat
uvicorn api.main:app --reload --port 8000