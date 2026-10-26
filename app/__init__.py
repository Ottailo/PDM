"""
Application factory module for the Predictive Maintenance Platform.
"""
import os
from flask import Flask, render_template, redirect, url_for
from flask_login import login_required, LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO

from sqlalchemy import MetaData

# Define naming convention for Alembic/SQLite support
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)

# Initialize SQLAlchemy instance
db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
socketio = SocketIO()

def create_app(config=None):
    """Create and configure the Flask application.
    
    Args:
        config: Configuration object or None to use default config
        
    Returns:
        Flask application instance
    """
    application = Flask(__name__)
    
    # Compute absolute project-anchored database path for rock-solid SQLite resolution
    if os.environ.get('VERCEL'):
        default_db_path = '/tmp/maintenance.db'
        source_db = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'maintenance.db'))
        if os.path.exists(source_db) and not os.path.exists(default_db_path):
            import shutil
            try:
                shutil.copyfile(source_db, default_db_path)
            except Exception:
                pass
    else:
        default_db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'maintenance.db')).replace('\\', '/')

    # Default configuration
    application.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        # Use PostgreSQL if available, else SQLite with absolute path
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', f'sqlite:///{default_db_path}').replace('postgres://', 'postgresql://'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MODEL_BASE_DIR=os.environ.get('MODEL_BASE_DIR', os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models'))),
        SIMULATOR_UPDATE_INTERVAL=int(os.environ.get('SIMULATOR_UPDATE_INTERVAL', 1)),
        WINDOW_SIZE=int(os.environ.get('WINDOW_SIZE', 10)),
        ANOMALY_Z_SCORE_THRESHOLD=float(os.environ.get('ANOMALY_Z_SCORE_THRESHOLD', 4.0)),
        # New Configs
        API_KEY=os.environ.get('API_KEY', 'dev-api-key'),
        ENABLE_SIMULATOR=os.environ.get('ENABLE_SIMULATOR', 'False').lower() == 'true'
    )
    
    # Override with provided config if any
    if config:
        application.config.update(config)
    
    # Initialize extensions
    db.init_app(application)
    migrate.init_app(application, db)
    socketio.init_app(application, cors_allowed_origins="*")
    
    # Initialize LoginManager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(application)
    
    from app.models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.packages import api_bp
    from app.api.machine_management import machine_mgmt_bp
    
    # Register Ingest Blueprint
    from app.api.ingest import ingest_bp
    application.register_blueprint(ingest_bp, url_prefix='/api')
    
    # Register Auth Blueprint
    from app.api.auth import auth_bp
    application.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Register Admin Blueprint
    from app.api.admin import admin_bp
    application.register_blueprint(admin_bp)
    
    # Register Configuration Blueprint (v2)
    from app.api.configuration import config_bp
    application.register_blueprint(config_bp, url_prefix='/api/config')
    
    # Import routes to register them with the blueprint
    from app.api import routes  # noqa: F401
    
    application.register_blueprint(api_bp, url_prefix='/api')
    application.register_blueprint(machine_mgmt_bp, url_prefix='/api/machine-mgmt')
    
    # Dashboard route
    @application.route('/')
    @login_required
    def index():
        return render_template('dashboard.html')
    
    @application.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html')
    
    @application.route('/mobile')
    def mobile_surveillance():
        """Dedicated mobile remote surveillance view for plant engineers and floor technicians."""
        return render_template('mobile_dashboard.html')

    @application.route('/manifest.json')
    def manifest():
        """Web App Manifest for mobile PWA installation."""
        return application.send_static_file('manifest.json')
    
    
    # Create database tables
    with application.app_context():
        # Import models to ensure they are registered with SQLAlchemy
        import app.models
        
        # Enable WAL mode for SQLite concurrency
        from sqlalchemy import event
        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
            except Exception:
                pass

        try:
            db.create_all()
        except Exception:
            pass
    
    return application
