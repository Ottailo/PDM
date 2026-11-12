"""Fail-closed configuration and same-origin API/SPA serving."""
import logging
import os
import secrets
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit
from flask import Flask, g, jsonify, request, send_from_directory
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash
from cryptography.fernet import Fernet
from app import db, migrate
from app.pilot.security import APIError, csrf_check, rate_limit, request_guard

ROOT = Path(__file__).resolve().parents[2]
REVISION = 'pilot_0003'


def bool_env(name,default=False):
    return os.environ.get(name,str(default)).lower() in {'true','1','yes'}


def build_app(config=None):
    # Only the explicitly named, machine-local file is eligible; no legacy .env/default DB.
    overrides = dict(config) if config else {}
    if overrides.get('APP_ENV')=='development' or overrides.get('TESTING'):
        overrides.setdefault('SESSION_COOKIE_SECURE',False)
        overrides.setdefault('SMTP_STARTTLS',False)
    env_file = ROOT/'.env.pilot'
    requested_env = (config or {}).get('APP_ENV',os.environ.get('APP_ENV'))
    if overrides.get('LOAD_PILOT_ENV', True) and env_file.exists() and requested_env in {None,'development','test'}:
        from dotenv import load_dotenv
        load_dotenv(env_file,override=False)
    app = Flask(__name__,static_folder=None)
    app.config.update(
        APP_ENV=os.environ.get('APP_ENV','production'),
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={'pool_pre_ping':True},
        MFA_ENCRYPTION_KEY=os.environ.get('MFA_ENCRYPTION_KEY'),
        PRIVATE_STORAGE_DIR=os.environ.get('PRIVATE_STORAGE_DIR'),
        STORAGE_BACKEND=os.environ.get('STORAGE_BACKEND','local'),
        S3_BUCKET=os.environ.get('S3_BUCKET'),S3_ENDPOINT_URL=os.environ.get('S3_ENDPOINT_URL'),S3_REGION=os.environ.get('S3_REGION'),
        SMTP_HOST=os.environ.get('SMTP_HOST'),SMTP_PORT=int(os.environ.get('SMTP_PORT','587')),
        SMTP_FROM=os.environ.get('SMTP_FROM'),SMTP_USERNAME=os.environ.get('SMTP_USERNAME'),SMTP_PASSWORD=os.environ.get('SMTP_PASSWORD'),
        SMTP_STARTTLS=bool_env('SMTP_STARTTLS',os.environ.get('APP_ENV','production')!='development'),
        CLAMAV_HOST=os.environ.get('CLAMAV_HOST'),CLAMAV_PORT=int(os.environ.get('CLAMAV_PORT','3310')),
        APP_BASE_URL=os.environ.get('APP_BASE_URL'),
        SESSION_COOKIE_NAME='machivital_session',SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.environ.get('APP_ENV','production')!='development',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=11*1024*1024,PDF_MAX_BYTES=10*1024*1024,PDF_MAX_PAGES=200,PDF_MAX_TEXT=1000000,PDF_PARSE_TIMEOUT=25,
        AUTH_RATE_LIMIT=30,
        LOAD_PILOT_ENV=True,
        PM_PLAN_LIMIT=200, PM_OPEN_WORK_LIMIT=100, PM_PENDING_REMINDER_LIMIT=300,
        PM_TICK_LIMIT=50, PM_TENANT_TICK_LIMIT=5,
        WORKER_IDLE_SECONDS=2,
        PDF_PARSER_MODE=os.environ.get('PDF_PARSER_MODE','docker'),
        PDF_PARSER_IMAGE=os.environ.get('PDF_PARSER_IMAGE'),
        PDF_DOCKER_EXECUTABLE=os.environ.get('PDF_DOCKER_EXECUTABLE','docker'),
        PDF_RESTRICTED_RUNTIME_APPROVED=bool_env('PDF_RESTRICTED_RUNTIME_APPROVED'),
        DOCUMENT_QUOTA_BYTES=int(os.environ.get('DOCUMENT_QUOTA_BYTES',str(500*1024*1024))),
        DOCUMENT_QUOTA_FILES=int(os.environ.get('DOCUMENT_QUOTA_FILES','100')),
        DOCUMENT_PENDING_LIMIT=int(os.environ.get('DOCUMENT_PENDING_LIMIT','10')),
        DOCUMENT_UPLOAD_RATE_LIMIT=int(os.environ.get('DOCUMENT_UPLOAD_RATE_LIMIT','10')),
        DOCUMENT_UPLOAD_WINDOW_SECONDS=int(os.environ.get('DOCUMENT_UPLOAD_WINDOW_SECONDS','600')),
        DOCUMENT_STAGING_SECONDS=int(os.environ.get('DOCUMENT_STAGING_SECONDS','900')),
        DOCUMENT_RECONCILE_LIMIT=int(os.environ.get('DOCUMENT_RECONCILE_LIMIT','10')),
    )
    if config:
        app.config.update(overrides)
        if 'DATABASE_URL' in overrides and 'SQLALCHEMY_DATABASE_URI' not in overrides:
            app.config['SQLALCHEMY_DATABASE_URI'] = overrides['DATABASE_URL']
    if app.config['APP_ENV'] not in {'production','development','test'}:
        raise RuntimeError('APP_ENV must be production, development or test')
    required = ['SECRET_KEY','SQLALCHEMY_DATABASE_URI','MFA_ENCRYPTION_KEY','APP_BASE_URL']
    required += ['S3_BUCKET'] if app.config['STORAGE_BACKEND']=='s3' else ['PRIVATE_STORAGE_DIR']
    if not app.testing:
        required += ['SMTP_HOST','SMTP_FROM','CLAMAV_HOST']
    if any(not app.config.get(key) for key in required):
        raise RuntimeError('Missing required pilot configuration: '+', '.join(k for k in required if not app.config.get(k)))
    if len(app.config['SECRET_KEY'])<32:
        raise RuntimeError('SECRET_KEY must contain at least 32 characters')
    Fernet(app.config['MFA_ENCRYPTION_KEY'].encode())
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if uri.startswith('postgres://'):
        uri = 'postgresql+psycopg://'+uri[len('postgres://'):]
    elif uri.startswith('postgresql://'):
        uri = 'postgresql+psycopg://'+uri[len('postgresql://'):]
    if not uri.startswith('postgresql+psycopg://'):
        raise RuntimeError('Pilot requires an explicit new PostgreSQL database; legacy SQLite is forbidden')
    app.config['SQLALCHEMY_DATABASE_URI'] = uri
    base = urlsplit(app.config['APP_BASE_URL'])
    if base.scheme not in {'http','https'} or not base.netloc or base.username or base.password:
        raise RuntimeError('APP_BASE_URL must be an absolute HTTP(S) origin')
    origin = base.scheme+'://'+base.netloc
    app.config.setdefault('ALLOWED_ORIGINS',[origin])
    app.config.setdefault('TRUSTED_HOSTS',[base.hostname])
    if app.config['APP_ENV']=='production':
        if base.scheme!='https' or not app.config['SESSION_COOKIE_SECURE'] or not app.config['SMTP_STARTTLS']:
            raise RuntimeError('Production requires HTTPS, secure cookies and SMTP TLS')
    elif base.hostname in {'localhost','127.0.0.1'}:
        app.config['TRUSTED_HOSTS'] = ['localhost','127.0.0.1']
    if app.config.get('TEST_MAIL_ADAPTER') or app.config.get('TEST_SCANNER') or app.config.get('TEST_PARSER'):
        if not app.testing:
            raise RuntimeError('Test boundary adapters are forbidden outside TESTING')
    clock = app.config.get('TEST_CLOCK')
    if clock is not None and (not app.testing or not callable(clock)):
        raise RuntimeError('TEST_CLOCK requires explicit TESTING and a callable')
    for key in ('PM_PLAN_LIMIT','PM_OPEN_WORK_LIMIT','PM_PENDING_REMINDER_LIMIT','PM_TICK_LIMIT','PM_TENANT_TICK_LIMIT','WORKER_IDLE_SECONDS'):
        if type(app.config[key]) is not int or not 1 <= app.config[key] <= 10000:
            raise RuntimeError(f'{key} must be a positive bounded integer')
    import re
    for key in ('DOCUMENT_QUOTA_BYTES','DOCUMENT_QUOTA_FILES','DOCUMENT_PENDING_LIMIT','DOCUMENT_UPLOAD_RATE_LIMIT','DOCUMENT_UPLOAD_WINDOW_SECONDS','DOCUMENT_STAGING_SECONDS','DOCUMENT_RECONCILE_LIMIT'):
        if type(app.config[key]) is not int or not 1 <= app.config[key] <= (2**31-1):
            raise RuntimeError(f'{key} must be a positive bounded integer')
    mode = app.config['PDF_PARSER_MODE']
    if mode not in {'docker','development'}:
        raise RuntimeError('PDF_PARSER_MODE must be docker or development')
    if mode == 'development' and app.config['APP_ENV'] == 'production':
        raise RuntimeError('Production forbids the development PDF parser')
    image = app.config.get('PDF_PARSER_IMAGE')
    if image and not re.fullmatch(r'sha256:[a-f0-9]{64}',image):
        raise RuntimeError('PDF_PARSER_IMAGE must be a trusted immutable sha256 image ID')
    executable = app.config['PDF_DOCKER_EXECUTABLE']
    if not isinstance(executable,str) or not executable or '\x00' in executable or (executable != 'docker' and not Path(executable).is_absolute()):
        raise RuntimeError('PDF_DOCKER_EXECUTABLE must be docker or a fixed absolute path')
    if app.config['APP_ENV'] == 'production' and (mode != 'docker' or not image or app.config['PDF_RESTRICTED_RUNTIME_APPROVED'] is not True):
        raise RuntimeError('Production PDF parsing requires a pinned image and an approved restricted runtime')
    app.config['DUMMY_PASSWORD_HASH'] = generate_password_hash(secrets.token_urlsafe(32))
    db.init_app(app)
    from importlib import import_module
    import_module('app.models')  # Schema classes only; no simulator/predictor/LLM.
    import_module('app.pilot.models')
    migrate.init_app(app,db,directory=str(ROOT/'migrations_pilot'))
    from app.pilot.storage import LocalStorage,S3Storage
    if app.config['STORAGE_BACKEND']=='local':
        path = Path(app.config['PRIVATE_STORAGE_DIR'])
        if not path.is_absolute():
            path = ROOT/path
        path = path.resolve()
        forbidden = [ROOT/'app'/'static',ROOT/'frontend',ROOT/'instance']
        if path==ROOT or any(path==p or p in path.parents for p in forbidden):
            raise RuntimeError('Private storage must be outside public assets and legacy database directories')
        app.extensions['pilot_storage'] = LocalStorage(path)
    elif app.config['STORAGE_BACKEND']=='s3':
        app.extensions['pilot_storage'] = S3Storage(app.config)
    else:
        raise RuntimeError('STORAGE_BACKEND must be local or s3')
    from app.pilot import auth,registry,maintenance,documents,preventive
    for module in (auth,registry,maintenance,documents,preventive):
        app.register_blueprint(module.bp,url_prefix='/api/v1')

    @app.before_request
    def security_boundary():
        g.request_id = secrets.token_hex(12)
        if request.path.startswith('/api/v1/'):
            rate_limit()
            csrf_check()
            request_guard()

    @app.after_request
    def secure_headers(response):
        response.headers['Cache-Control'] = 'private, no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        response.headers['X-Request-ID'] = getattr(g,'request_id',secrets.token_hex(12))
        if app.config['APP_ENV']=='production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    def error_json(error):
        db.session.rollback()
        body = {'error':{'code':error.code,'message':error.message},'request_id':getattr(g,'request_id',secrets.token_hex(12))}
        if error.fields:
            body['error']['fields'] = error.fields
        return jsonify(body),error.status

    app.register_error_handler(APIError,error_json)

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        return error_json(APIError('conflict','A concurrent update conflicts with this request. Refresh and try again.',409))

    @app.errorhandler(HTTPException)
    def http_error(error):
        return error_json(APIError('http_'+str(error.code),error.description,error.code))

    @app.errorhandler(Exception)
    def internal_error(error):
        # Never log SQL parameters, passwords or token-bearing payloads.
        app.logger.error('Pilot request failed (%s), request_id=%s',type(error).__name__,getattr(g,'request_id','unknown'))
        return error_json(APIError('internal_error','The request could not be completed.',500))

    @app.teardown_request
    def rollback_unused(error):
        db.session.rollback()

    @app.get('/healthz')
    def health():
        return {'status':'ok'}

    @app.get('/readyz')
    def ready():
        try:
            revision = db.session.execute(text('SELECT version_num FROM alembic_version_pilot')).scalar_one()
            if revision!=REVISION:
                raise ValueError('Migration not current')
            db.session.execute(text('SELECT 1 FROM memberships LIMIT 1'))
            return {'status':'ready'}
        except (SQLAlchemyError,ValueError):
            db.session.rollback()
            return {'status':'not_ready'},503

    @app.route('/',defaults={'path':''},methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'])
    @app.route('/<path:path>',methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'])
    def spa(path):
        if path=='api' or path.startswith('api/'):
            status = 404 if path.startswith('api/v1/') else 410
            raise APIError('not_found' if status==404 else 'legacy_disabled','API endpoint not found.' if status==404 else 'Legacy API is disabled.',status)
        if path in {'admin','mobile','dashboard'} or path.startswith(('admin/','auth/','static/')):
            raise APIError('legacy_disabled','Legacy application is disabled.',410)
        if request.method not in {'GET','HEAD'}:
            raise APIError('method_not_allowed','Only GET is allowed for frontend routes.',405)
        dist = ROOT/'frontend'/'dist'
        if not (dist/'index.html').is_file():
            raise APIError('frontend_unavailable','Frontend build is not installed.',503)
        candidate = (dist/path).resolve()
        if dist.resolve() in candidate.parents and candidate.is_file():
            return send_from_directory(dist,path)
        if Path(path).suffix:
            raise APIError('not_found','File not found.',404)
        return send_from_directory(dist,'index.html')

    return app
