"""Les trois tables de CampusData et leurs contraintes."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    """Heure courante en UTC, calculée à chaque insertion (pas une seule fois)."""
    return datetime.now(timezone.utc)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(60), default="Équipe")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Ingestion(Base):
    __tablename__ = "ingestions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)
    # Octets bruts (BYTEA) : le worker décidera si le fichier est de l'UTF-8 valide.
    content: Mapped[bytes] = mapped_column(LargeBinary)
    rows_total: Mapped[int | None] = mapped_column(Integer)
    rows_accepted: Mapped[int | None] = mapped_column(Integer)
    rows_rejected: Mapped[int | None] = mapped_column(Integer)
    rows_duplicate: Mapped[int | None] = mapped_column(Integer)
    errors: Mapped[list] = mapped_column(JSONB, default=list)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')", name="ck_ingestion_status"
        ),
    )


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    ingestion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestions.id", ondelete="CASCADE"))
    room: Mapped[str] = mapped_column(String(30))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    co2_ppm: Mapped[int] = mapped_column(Integer)
    temperature_c: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    humidity_pct: Mapped[Decimal] = mapped_column(Numeric(4, 1))

    __table_args__ = (
        # Une mesure par salle et par instant dans un jeu : c'est ce qui évite les doublons.
        UniqueConstraint("dataset_id", "room", "measured_at", name="uq_measurement"),
        CheckConstraint("co2_ppm BETWEEN 250 AND 10000", name="ck_co2"),
        CheckConstraint("temperature_c BETWEEN -30 AND 60", name="ck_temperature"),
        CheckConstraint("humidity_pct BETWEEN 0 AND 100", name="ck_humidity"),
    )