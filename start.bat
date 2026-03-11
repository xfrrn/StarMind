@echo off
echo ==============================================
echo        Starting StarMind with Docker
echo ==============================================
echo.

:: Check if .env exists in the root (for docker-compose), if not, try to copy from backend
if not exist ".env" (
    if exist "backend\.env" (
        echo Copying backend\.env to root for docker-compose...
        copy "backend\.env" ".env" > nul
    ) else (
        echo [WARNING] No .env file found! Please create one in the root directory.
        echo You can copy backend\.env.example to .env and fill in your keys.
        echo.
    )
)

echo Building and starting containers in detached mode...
docker compose up -d --build

echo.
echo ==============================================
echo StarMind should be available shortly at:
echo Frontend UI : http://localhost:5173
echo Backend API : http://localhost:8000/docs
echo Database    : localhost:5432 (starmind / starmind_password)
echo ==============================================
echo.
pause
