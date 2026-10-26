"""
Vercel Serverless WSGI Entrypoint for PDM (Predictive Maintenance Telemetry Console)
"""
import os
import sys

# Ensure project root directory is on sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from app import create_app
    app = create_app()
except Exception as boot_exc:
    import traceback
    boot_traceback = traceback.format_exc()
    from flask import Flask, Response
    app = Flask('pdm_fallback')
    
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return Response(
            f"PDM Serverless Boot Exception:\n\n{boot_traceback}",
            mimetype='text/plain; charset=utf-8',
            status=500
        )
