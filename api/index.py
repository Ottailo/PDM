"""Optional WSGI adapter. No serverless SQLite, seeding or traceback exposure."""
import logging
from urllib.parse import parse_qs, urlencode
from app import create_app

logger = logging.getLogger(__name__)
try:
    flask_app = create_app()
except Exception as error:
    logger.error('Machivital startup configuration failed (%s)', type(error).__name__)
    flask_app = None


def app(environ, start_response):
    if flask_app is None:
        start_response('503 Service Unavailable', [('Content-Type', 'application/json'), ('Cache-Control', 'no-store')])
        return [b'{"error":{"code":"startup_unavailable","message":"The application is not configured for this deployment."}}']
    params = parse_qs(environ.get('QUERY_STRING', ''), keep_blank_values=True)
    if '__pdm_path__' in params:
        path = params.pop('__pdm_path__', [''])[0]
        environ['PATH_INFO'] = '/' + path.lstrip('/')
        environ['QUERY_STRING'] = urlencode(params, doseq=True)
    elif environ.get('PATH_INFO') in {'/api/index', '/api/index.py'}:
        environ['PATH_INFO'] = '/'
    return flask_app.wsgi_app(environ, start_response)


application = app
