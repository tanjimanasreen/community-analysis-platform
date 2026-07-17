"""Read-only dashboard API over validated pipeline run artifacts."""

from src.api.app import app, create_app

__all__ = ["app", "create_app"]
