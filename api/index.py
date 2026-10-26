"""
Vercel Serverless WSGI Entrypoint for PDM (Predictive Maintenance Telemetry Console)
"""
import os
import sys
import traceback

# Ensure project root directory is on sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Explicitly flag Vercel serverless environment before importing app modules
os.environ['VERCEL'] = '1'

boot_error = None
flask_app = None
try:
    from app import create_app
    flask_app = create_app()
except Exception:
    boot_error = traceback.format_exc()

def app(environ, start_response):
    if boot_error or flask_app is None:
        status = '500 Internal Server Error'
        response_headers = [('Content-Type', 'text/plain; charset=utf-8')]
        start_response(status, response_headers)
        return [f"PDM Vercel Boot Exception:\n\n{boot_error}".encode('utf-8')]
    
    # Path correction for Vercel rewrites:
    # When rewritten to /api/index, restore original user path from Vercel headers
    matched_path = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_URI') or environ.get('RAW_URI')
    if matched_path:
        clean_path = matched_path.split('?')[0]
        # Only rewrite if current path is pointing to the function handler itself
        if environ.get('PATH_INFO') in ['/api/index', '/api/index.py']:
            environ['PATH_INFO'] = clean_path
    
    try:
        return flask_app.wsgi_app(environ, start_response)
    except Exception:
        req_error = traceback.format_exc()
        status = '500 Internal Server Error'
        response_headers = [('Content-Type', 'text/plain; charset=utf-8')]
        start_response(status, response_headers)
        return [f"PDM Vercel Request Exception:\n\n{req_error}".encode('utf-8')]

# WSGI aliases
application = app
