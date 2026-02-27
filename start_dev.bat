@echo off
echo Starting backend...
start cmd /k "cd backend && uvicorn main:app --reload"
timeout /t 5 >nul
echo Starting frontend...
start cmd /k "cd frontend && npm run dev"
echo Both backend and frontend have been started.