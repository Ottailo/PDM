"""
Application factory module for the Predictive Maintenance Platform.
"""
import os
from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO

# Initialize SQLAlchemy instance
db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO()

def create_app(config=None):
    """Create and configure the Flask application.
    
    Args:
        config: Configuration object or None to use default config
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Default configuration
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///maintenance.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MODEL_BASE_DIR=os.environ.get('MODEL_BASE_DIR', os.path.join(os.getcwd(), 'models')),
        SIMULATOR_UPDATE_INTERVAL=int(os.environ.get('SIMULATOR_UPDATE_INTERVAL', 1)),
        WINDOW_SIZE=int(os.environ.get('WINDOW_SIZE', 24)),
        ANOMALY_Z_SCORE_THRESHOLD=float(os.environ.get('ANOMALY_Z_SCORE_THRESHOLD', 4.0))
    )
    
    # Override with provided config if any
    if config:
        app.config.update(config)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Register blueprints
    from app.packages import api_bp
    from app.api.machine_management import machine_mgmt_bp
    
    # Import routes to register them with the blueprint
    from app.api import routes  # noqa: F401
    
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(machine_mgmt_bp, url_prefix='/api/machine-mgmt')
    
    # Dashboard route
    @app.route('/')
    def index():
        return render_template('dashboard.html')
    
    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')
    
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
