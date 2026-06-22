@echo off
title Document Intelligence Platform

echo ============================================
echo   Document Intelligence Platform
echo ============================================
echo.

REM Check Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running.
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Create .env from example if it doesn't exist
if not exist ".env" (
    echo Creating .env from .env.example ...
    copy .env.example .env
    echo.
    echo *** IMPORTANT: Open .env and add your GEMINI_API_KEY before continuing ***
    echo.
    pause
)

echo Starting all services...
docker compose up --build -d

echo.
echo Waiting for services to be ready...
timeout /t 15 /nobreak >nul

echo.
echo ============================================
echo   App is running at: http://localhost
echo   (First startup may take 2-3 minutes)
echo ============================================
echo.
echo To stop: run stop.bat or "docker compose down"
echo To view logs: "docker compose logs -f"
echo.
pause
