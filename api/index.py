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
    
    # Instant Diagnostic probe for Vercel routing
    if 'diag' in environ.get('QUERY_STRING', '') or environ.get('PATH_INFO') == '/diag':
        status = '200 OK'
        headers = [('Content-Type', 'application/json')]
        start_response(status, headers)
        import json
        diag_info = {
            'PATH_INFO': environ.get('PATH_INFO'),
            'SCRIPT_NAME': environ.get('SCRIPT_NAME'),
            'RAW_URI': environ.get('RAW_URI'),
            'REQUEST_URI': environ.get('REQUEST_URI'),
            'HTTP_X_MATCHED_PATH': environ.get('HTTP_X_MATCHED_PATH'),
            'HTTP_X_FORWARDED_URI': environ.get('HTTP_X_FORWARDED_URI'),
            'QUERY_STRING': environ.get('QUERY_STRING'),
            'ALL_MATCH_KEYS': {k: str(v) for k, v in environ.items() if any(x in k.upper() for x in ['PATH', 'URI', 'MATCH', 'VERCEL', 'ROUTE'])}
        }
        return [json.dumps(diag_info, indent=2).encode('utf-8')]
    
    # Path correction for Vercel rewrites:
    matched_path = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_URI') or environ.get('RAW_URI')
    if matched_path:
        clean_path = matched_path.split('?')[0]
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
