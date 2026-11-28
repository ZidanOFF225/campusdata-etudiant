# CONTEXTE ÉTUDIANT : S1-S2 | point d’entrée Uvicorn app.main:app
# À PRÉPARER / ADAPTER : Charger DATABASE_URL avant le lancement. Compléter les TODO selon le contrat.
# CONTRÔLE ATTENDU : Contrôler live/ready/version, puis les routes métier après votre réalisation.
#
"""Point d'entrée du socle CampusData, à compléter pendant la séance 2.

Le starter expose uniquement la santé du processus, l'accès DB et la version.
Il ne contient ni tables (datasets, ingestions, measurements), ni routes
métier, ni lecture CSV, ni worker d'ingestion.
En S2, déplacer la connexion vers database.py et inclure le routeur métier.
Garder une seule source de configuration pour les probes et les services.
"""
"""Point d'entrée de l'API CampusData."""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.database import engine
from app.routes import datasets, ingestions

app = FastAPI(title="CampusData", version="0.1.0")
app.include_router(datasets)
app.include_router(ingestions)


@app.exception_handler(OperationalError)
def database_unavailable(request: Request, error: OperationalError):
    """Base injoignable pendant une requête métier : 503 avec un message générique."""
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


@app.get("/health/live")
def live():
    """Le processus répond, sans dépendre de PostgreSQL."""
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    """La base répond ET les trois tables existent (vides, elles sont acceptées)."""
    try:
        with engine.connect() as connection:
            for table in ("datasets", "ingestions", "measurements"):
                connection.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ready"}


@app.get("/api/version")
def version():
    version_file = Path(__file__).with_name("VERSION")
    value = version_file.read_text().strip() if version_file.exists() else "dev"
    return {"version": value}