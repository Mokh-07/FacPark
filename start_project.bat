@echo off
echo ===================================================
echo      Demarrage de FacPark (Backend + Frontend)
echo ===================================================

:: 1. Activer l'environnement virtuel, Ingestion RAG, et lancer le Backend
:: CORRECTION: On reste à la racine du projet pour lancer les modules python
echo [BACKEND] Lancement dans une nouvelle fenetre...
start "FacPark Backend" cmd /k "backend\venv\Scripts\activate && set PYTHONPATH=. && echo [INFO] Ingestion des documents RAG... && python -m backend.scripts.ingest_docs && echo [INFO] Demarrage du serveur... && uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

:: 2. Lancer le Frontend
echo [FRONTEND] Lancement dans une nouvelle fenetre...
start "FacPark Frontend" cmd /k "cd frontend && echo [INFO] Demarrage du serveur de dev... && npm run dev"

echo.
echo ===================================================
echo [IMPORTANT] 
echo Si les serveurs ne demarrent pas immediatement,
echo attendez la fin de l'installation des dependances
echo puis relancez ce script.
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo ===================================================
pause
