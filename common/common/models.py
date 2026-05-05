"""Shared SQLAlchemy models and declarative base."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models.

    All models should inherit from this base class.
    """

    pass
