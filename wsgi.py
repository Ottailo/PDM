"""WSGI entrypoint for the explicitly configured Stage 1 pilot."""
from app import create_app

app = create_app()
