"""
Vercel Serverless WSGI Entrypoint for PDM (Predictive Maintenance Telemetry Console)
"""
import os
import sys
import traceback
from urllib.parse import parse_qs, urlencode

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
    query_string = environ.get('QUERY_STRING', '')
    if '__pdm_path__' in query_string:
        params = parse_qs(query_string, keep_blank_values=True)
        raw_paths = params.pop('__pdm_path__', [''])
        resolved_path = raw_paths[0] if raw_paths else ''
        environ['PATH_INFO'] = '/' + resolved_path.lstrip('/')
        environ['QUERY_STRING'] = urlencode(params, doseq=True)
    elif environ.get('PATH_INFO') in ['/api/index', '/api/index.py']:
        environ['PATH_INFO'] = '/'
    
    try:
        return flask_app.wsgi_app(environ, start_response)
    except Exception:
        req_error = traceback.format_exc()
        status = '500 Internal Server Error'
        response_headers = [('Content-Type', 'text/plain; charset=utf-8')]
        start_response(status, response_headers)
        return [f"PDM Vercel Request Exception:\n\n{req_error}".encode('utf-8')]

# WSGI alias
application = app
