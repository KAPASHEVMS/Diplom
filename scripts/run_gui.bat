@echo off
REM Запуск Tkinter-GUI локально (БД должна быть поднята в docker compose)
cd /d "%~dp0.."
if not exist .env (
    copy .env.example .env
)
python -m venv .venv 2>nul
call .venv\Scripts\activate
pip install -q -r requirements.txt
python -m app
