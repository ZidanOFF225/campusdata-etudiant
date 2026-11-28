"""Créer les tables manquantes. Peut être lancé plusieurs fois sans rien effacer."""
from app import models  # noqa: F401  (importer les modèles pour que les tables soient connues)
from app.database import Base, engine


def main() -> None:
    Base.metadata.create_all(engine)
    print("Tables prêtes :", ", ".join(sorted(Base.metadata.tables)))


if __name__ == "__main__":
    main()