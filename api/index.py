"""
Vercel Serverless WSGI Entrypoint for PDM (Predictive Maintenance Telemetry Console)
"""
import os
import sys

# Ensure project root directory is on sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import create_app

# Vercel's Python runtime directly discovers 'app' as a Flask WSGI application
app = create_app()
