"""Connexion à PostgreSQL : un engine pour toute l'application, une session par requête."""

#l'engine est la connexion (une seule pour toute l'application) ;
#  une session est ouverte pour une requête, puis fermée.

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# L'adresse de la base vient de l'environnement : jamais de mot de passe dans le code.
engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe mère de toutes les tables."""


def get_session():
    """Ouvrir une session pour une requête, puis la fermer quoi qu'il arrive."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()