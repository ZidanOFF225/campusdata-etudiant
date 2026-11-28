"""Les cas d'utilisation : chaque fonction reçoit une session et applique une règle métier."""
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Dataset, Ingestion, Measurement


class NotFound(Exception):
    """La ressource demandée n'existe pas (404)."""


class Conflict(Exception):
    """La demande viole une règle métier (409)."""


def _count_measurements(session: Session, dataset_id: uuid.UUID) -> int:
    return session.scalar(
        select(func.count()).select_from(Measurement).where(Measurement.dataset_id == dataset_id)
    )


def _dataset_read(session: Session, dataset: Dataset) -> dict:
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "owner": dataset.owner,
        "created_at": dataset.created_at,
        "measurement_count": _count_measurements(session, dataset.id),
    }


def create_dataset(session: Session, name: str, description: str | None, owner: str) -> dict:
    dataset = Dataset(name=name, description=description, owner=owner)
    session.add(dataset)
    try:
        session.commit()
    except IntegrityError:
        # La contrainte UNIQUE sur name a refusé l'insertion : nom déjà utilisé.
        session.rollback()
        raise Conflict("Dataset name already exists") from None
    return _dataset_read(session, dataset)


def list_datasets(session: Session) -> list[dict]:
    counts = (
        select(Measurement.dataset_id, func.count().label("n"))
        .group_by(Measurement.dataset_id)
        .subquery()
    )
    query = (
        select(Dataset, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.dataset_id == Dataset.id)
        .order_by(Dataset.created_at.desc(), Dataset.id)
    )
    return [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "owner": d.owner,
            "created_at": d.created_at,
            "measurement_count": n,
        }
        for d, n in session.execute(query)
    ]


def get_dataset(session: Session, dataset_id: uuid.UUID) -> dict:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise NotFound("Dataset not found")
    return _dataset_read(session, dataset)


def delete_dataset(session: Session, dataset_id: uuid.UUID) -> None:
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise NotFound("Dataset not found")
    session.delete(dataset)  # ON DELETE CASCADE supprime dépôts et mesures
    session.commit()


def create_ingestion(session: Session, dataset_id: uuid.UUID, filename: str, content: bytes) -> Ingestion:
    if session.get(Dataset, dataset_id) is None:
        raise NotFound("Dataset not found")
    # Le contenu est gardé tel quel ; c'est le worker qui le lira plus tard.
    ingestion = Ingestion(dataset_id=dataset_id, filename=filename, content=content)
    session.add(ingestion)
    session.commit()
    return ingestion


def list_ingestions(session: Session, dataset_id: uuid.UUID, status: str | None) -> list[Ingestion]:
    # TODO : 404 si le jeu n'existe pas ; filtrer par status s'il est fourni ;
    #        trier du plus récent au plus ancien (created_at décroissant).
    if session.get(Dataset, dataset_id) is None:
        raise NotFound("Dataset not found")
    query = select(Ingestion).where(Ingestion.dataset_id == dataset_id)
    if status is not None:
        query = query.where(Ingestion.status == status)
    return session.execute(query.order_by(Ingestion.created_at.desc())).scalars().all()


def get_ingestion(session: Session, ingestion_id: uuid.UUID) -> Ingestion:
    ingestion = session.get(Ingestion, ingestion_id)
    if ingestion is None:
        raise NotFound("Ingestion not found")
    return ingestion


def retry_ingestion(session: Session, ingestion_id: uuid.UUID) -> Ingestion:
    # TODO : charger le dépôt avec session.get(Ingestion, ingestion_id, with_for_update=True)
    #        404 s'il n'existe pas ; Conflict("Ingestion cannot be retried") s'il n'est pas failed ;
    #        sinon status = "pending", compteurs/error_message/dates à None, errors = [], commit.
    ingestion = session.get(Ingestion, ingestion_id, with_for_update=True)
    if ingestion is None:
        raise NotFound("Ingestion not found")
    if ingestion.status != "failed":
        raise Conflict("Ingestion cannot be retried")
    ingestion.status = "pending"
    ingestion.rows_total = None
    ingestion.rows_accepted = None
    ingestion.rows_rejected = None
    ingestion.rows_duplicate = None
    ingestion.error_message = None
    ingestion.started_at = None
    ingestion.finished_at = None
    ingestion.errors = []
    session.commit()
    return ingestion


def dataset_stats(
    session: Session,
    dataset_id: uuid.UUID,
    room: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> dict:
    # TODO : une requête select(...) avec func.count, func.avg, func.min, func.max,
    #        filtrée par dataset_id (puis room, from inclus, to exclu), group_by(room), order_by(room).
    #        Arrondir les moyennes à 1 décimale : func.round(func.avg(...), 1).
    # Renvoyer : {"dataset_id": ..., "room": ..., "from": ..., "to": ..., "rooms": [...]}
    query = select(
        Measurement.room,
        func.count().label("measurements"),
        func.round(func.avg(Measurement.co2), 1).label("co2_avg"),
        func.min(Measurement.co2).label("co2_min"),
        func.max(Measurement.co2).label("co2_max"),
        func.round(func.avg(Measurement.temperature), 1).label("temperature_avg"),
        func.round(func.avg(Measurement.humidity), 1).label("humidity_avg"),
        func.max(Measurement.measured_at).label("last_measured_at"),
    ).where(Measurement.dataset_id == dataset_id)
    if room is not None:
        query = query.where(Measurement.room == room)
    if date_from is not None:
        query = query.where(Measurement.measured_at >= date_from)
    if date_to is not None:
        query = query.where(Measurement.measured_at < date_to)
    query = query.group_by(Measurement.room).order_by(Measurement.room)
    return session.execute(query).fetchall()
