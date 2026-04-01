@echo off
chcp 65001 > nul
title DataProtect Senegal

echo.
echo  ================================================
echo   DataProtect Senegal - Serveur local
echo  ================================================
echo.

python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo  ERREUR : Python n'est pas installe.
    echo  Allez sur : https://www.python.org/downloads/
    echo  Cochez "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)

echo  Python detecte. OK
echo.

if not exist ".deps_ok" (
    echo  Installation des dependances...
    python -m pip install fastapi uvicorn pydantic python-multipart --quiet
    if %errorlevel% equ 0 (
        echo. > .deps_ok
        echo  Dependances installees. OK
    ) else (
        echo  ERREUR installation. Essayez :
        echo  pip install fastapi uvicorn pydantic python-multipart
        pause
        exit /b 1
    )
) else (
    echo  Dependances deja installees. OK
)

echo.
echo  Demarrage du serveur...
echo.
echo  Site web  : http://localhost:8080
echo  Admin     : http://localhost:8080/admin.html
echo  Mot passe : dataprotect2025
echo.
echo  CTRL+C pour arreter.
echo  ================================================
echo.

start /b cmd /c "timeout /t 3 > nul && start http://localhost:8080"

echo Arret des anciens processus sur le port 8080...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8080 2^>nul') do taskkill /PID %%a /F > nul 2>&1

python server.py

pause
