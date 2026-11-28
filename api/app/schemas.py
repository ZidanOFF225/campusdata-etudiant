"""Le JSON accepté et renvoyé par l'API."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DatasetCreate(BaseModel):
    # extra="forbid" : un champ inconnu (ex. "id") est refusé avec une erreur 422.
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    owner: str = Field(default="Équipe", min_length=2, max_length=60)

    @field_validator("name", "owner", mode="before")
    @classmethod
    def strip_spaces(cls, value):
        # Retirer les espaces AVANT de vérifier la longueur : "  ab  " devient "ab" (trop court).
        return value.strip() if isinstance(value, str) else value


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    owner: str
    created_at: datetime
    measurement_count: int


class LineError(BaseModel):
    line: int
    reason: str


class IngestionRead(BaseModel):
    # Le champ content n'est pas déclaré : il n'est jamais renvoyé au client.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    filename: str
    status: str
    rows_total: int | None
    rows_accepted: int | None
    rows_rejected: int | None
    rows_duplicate: int | None
    errors: list[LineError]
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RoomStats(BaseModel):
    room: str
    measurements: int
    co2_avg: float
    co2_min: int
    co2_max: int
    temperature_avg: float
    humidity_avg: float
    last_measured_at: datetime


class StatsRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dataset_id: uuid.UUID
    room: str | None
    from_: datetime | None = Field(alias="from")
    to: datetime | None
    rooms: list[RoomStats]