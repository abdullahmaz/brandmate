@echo off
echo Starting Brandmate Development Environment...

echo.
echo Starting Backend (FastAPI)...
start "Backend" cmd /k "cd backend && python main.py"

echo.
echo Starting Frontend (React)...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
pause
