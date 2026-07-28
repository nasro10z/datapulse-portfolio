"""Schémas des couches de la base analytique.

`Base` est propre à la base analytique (distinct de `db/tables.Base`, qui régit
l'état applicatif) : `create_all(Base.metadata)` ne crée donc QUE les tables
bronze/silver/gold, dans le fichier analytique.

Importer les modules de tables ici garantit qu'ils sont enregistrés sur
`Base.metadata` avant tout `create_all`.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base déclarative de la base analytique (bronze/silver/gold)."""


# Enregistrement des tables sur Base.metadata (ordre sans importance).
from app.storage.schema import bronze, gold, silver  # noqa: E402,F401

__all__ = ["Base", "bronze", "silver", "gold"]
