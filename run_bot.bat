@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title Board2Audio - KIUT University AI Bot
echo ==============================================
echo   Board2Audio: Doskadan Podkastga va Konspekt
echo ==============================================
call venv\Scripts\activate.bat
python main.py
pause
