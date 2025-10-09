@echo off
echo Starting h-dcn frontend Processor...
echo.

start "Frontend" cmd /k "cd frontend && npm start"

echo.
echo Server is starting...
echo Frontend: http://localhost:3000
echo.
echo Press any key to exit this window...
pause > nul