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
    
    # Default configuration
    application.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        # Use PostgreSQL if available, else SQLite
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///maintenance.db').replace('postgres://', 'postgresql://'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MODEL_BASE_DIR=os.environ.get('MODEL_BASE_DIR', os.path.join(os.getcwd(), 'models')),
        SIMULATOR_UPDATE_INTERVAL=int(os.environ.get('SIMULATOR_UPDATE_INTERVAL', 1)),
        WINDOW_SIZE=int(os.environ.get('WINDOW_SIZE', 10)),
        ANOMALY_Z_SCORE_THRESHOLD=float(os.environ.get('ANOMALY_Z_SCORE_THRESHOLD', 4.0)),
        # New Configs
        API_KEY=os.environ.get('API_KEY', 'dev-api-key'),
        ENABLE_SIMULATOR=os.environ.get('ENABLE_SIMULATOR', 'True').lower() == 'true'
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
    
    
    # Create database tables
    with application.app_context():
        # Import models to ensure they are registered with SQLAlchemy
        import app.models
        
        # Enable WAL mode for SQLite concurrency
        from sqlalchemy import event
        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        db.create_all()
    
    return application
