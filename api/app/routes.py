"""Les routes HTTP de CampusData.

Chaque route reçoit et valide les données HTTP, obtient une session via
Depends, délègue la règle métier à services, puis traduit ses erreurs en
réponses HTTP. Les schémas de réponse filtrent les données renvoyées au client.
"""
import uuid
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app import services
from app.database import get_session
from app.schemas import DatasetCreate, DatasetRead, IngestionRead, StatsRead

MAX_FILE_SIZE = 1_048_576  # 1 Mio

datasets = APIRouter(prefix="/api/datasets", tags=["datasets"])
ingestions = APIRouter(prefix="/api/ingestions", tags=["ingestions"])


class Status(str, Enum):
    """Valeurs de statut acceptées par le filtre des ingestions."""

    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


async def raw_body(request: Request) -> bytes:
    """Lire le corps brut de la requête (le fichier CSV)."""
    return await request.body()


@datasets.get("", response_model=list[DatasetRead])
def list_datasets(session: Session = Depends(get_session)):
    return services.list_datasets(session)


@datasets.post("", response_model=DatasetRead, status_code=201)
def create_dataset(data: DatasetCreate, session: Session = Depends(get_session)):
    """Créer un jeu à partir du JSON validé; convertir un nom en conflit en HTTP 409."""
    try:
        return services.create_dataset(session, data.name, data.description, data.owner)
    except services.Conflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@datasets.get("/{dataset_id}", response_model=DatasetRead)
def get_dataset(dataset_id: uuid.UUID, session: Session = Depends(get_session)):
    """Lire un jeu par UUID; un identifiant valide mais absent donne HTTP 404."""
    try:
        return services.get_dataset(session, dataset_id)
    except services.NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@datasets.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: uuid.UUID, session: Session = Depends(get_session)):
    """Supprimer un jeu; le service applique les cascades et la route répond sans corps."""
    try:
        services.delete_dataset(session, dataset_id)
    except services.NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return Response(status_code=204)


@datasets.post("/{dataset_id}/ingestions", response_model=IngestionRead, status_code=202)
def create_ingestion(
    dataset_id: uuid.UUID,
    request: Request,
    response: Response,
    filename: str = Query(min_length=1, max_length=255, pattern=r"^[^/\\]+$"),
    content: bytes = Depends(raw_body),
    session: Session = Depends(get_session),
):
    """Enregistrer un CSV puis répondre 202 avec son URL de suivi dans Location.

    Les contrôles HTTP sont faits dans l'ordre du contrat avant l'appel au service :
    type de contenu, taille, corps non vide, puis existence du jeu.
    """
    # Ordre du contrat : type (415), taille (413), corps vide (422), puis jeu existant (404).
    if not request.headers.get("content-type", "").startswith("text/csv"):
        raise HTTPException(status_code=415, detail="Expected text/csv")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    if not content:
        raise HTTPException(status_code=422, detail="Empty file")
    try:
        ingestion = services.create_ingestion(session, dataset_id, filename, content)
    except services.NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    response.headers["Location"] = f"/api/ingestions/{ingestion.id}"
    return ingestion


@datasets.get("/{dataset_id}/ingestions", response_model=list[IngestionRead])
def list_ingestions(
    dataset_id: uuid.UUID, status: Status | None = None, session: Session = Depends(get_session)
):
    try:
        return services.list_ingestions(session, dataset_id, status.value if status else None)
    except services.NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@datasets.get("/{dataset_id}/stats", response_model=StatsRead, response_model_by_alias=True)
def dataset_stats(
    dataset_id: uuid.UUID,
    room: str | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    session: Session = Depends(get_session),
):
    """Calculer les indicateurs, éventuellement limités à une salle et une période.

    La borne from est incluse et la borne to exclue par le service.
    """
    if date_from and date_to and date_from >= date_to:
        raise HTTPException(status_code=422, detail="from must be before to")
    try:
        return services.dataset_stats(session, dataset_id, room, date_from, date_to)
    except services.NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@ingestions.get("/{ingestion_id}", response_model=IngestionRead)
def get_ingestion(ingestion_id: uuid.UUID, session: Session = Depends(get_session)):
    """Consulter l'état et le bilan d'un fichier; le schéma n'expose pas son contenu brut."""
    try:
        return services.get_ingestion(session, ingestion_id)
    except services.NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@ingestions.post("/{ingestion_id}/retry", response_model=IngestionRead)
def retry_ingestion(ingestion_id: uuid.UUID, session: Session = Depends(get_session)):
    """Redemander le traitement d'un fichier échoué; traduire absence en 404 et refus en 409."""
    try:
        return services.retry_ingestion(session, ingestion_id)
    except services.NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except services.Conflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from None