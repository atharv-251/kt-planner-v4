@echo off
echo ======================================================================
echo Starting KT Planner Platform (Single Deployable Service)
echo Uvicorn + FastAPI + React UI + LangGraph + SQLite
echo ======================================================================

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload %*
pause

