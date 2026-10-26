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
    try:
        migrate.init_app(application, db)
    except Exception:
        pass
    if not os.environ.get('VERCEL') and not os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        try:
            socketio.init_app(application, cors_allowed_origins="*")
        except Exception:
            pass
    
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
    def index():
        from flask_login import current_user, login_user
        if not current_user.is_authenticated:
            try:
                from app.models.user import User
                admin_user = User.query.filter_by(username='admin').first()
                if admin_user:
                    login_user(admin_user)
            except Exception:
                pass
        return render_template('dashboard.html')
    
    @application.route('/dashboard')
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
        
        # Enable WAL mode for SQLite concurrency (local/VPS only; skip on serverless Lambda/Vercel)
        from sqlalchemy import event
        @event.listens_for(db.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
                return
            try:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
            except Exception:
                pass

        try:
            db.create_all()
            
            # Auto-seed initial fleet if empty (essential for Vercel serverless cold starts)
            from app.models.company import Company
            from app.models.user import User
            from app.models.configuration import Asset, AssetTemplate, Location, SensorTemplate, AssetSensor
            from app.models.sensor_data import MachineState
            from app.config.machine_config import MACHINES, SENSOR_CONFIG

            if Company.query.get(1) is None:
                company = Company(id=1, name="GDK Perfume", industry="Manufacturing", contact_email="admin@gdk.com")
                db.session.add(company)
                db.session.commit()

            if User.query.filter_by(username='admin').first() is None:
                admin_user = User(username='admin', email='admin@pdm.local', role='admin', company_id=1)
                admin_user.set_password('admin')
                db.session.add(admin_user)
                db.session.commit()

            if Location.query.first() is None:
                loc = Location(name="Factory Floor", type="Area", path="1")
                db.session.add(loc)
                db.session.commit()

            if Asset.query.count() == 0:
                loc = Location.query.first()
                for machine_type, machine_ids in MACHINES.items():
                    template = AssetTemplate.query.filter_by(name=machine_type).first()
                    if not template:
                        template = AssetTemplate(name=machine_type, description=f"{machine_type} Machine Line")
                        db.session.add(template)
                        db.session.commit()

                    for mid in machine_ids:
                        asset = Asset(
                            name=mid,
                            asset_template_id=template.id,
                            location_id=loc.id if loc else None,
                            company_id=1,
                            status='Active'
                        )
                        db.session.add(asset)
                        db.session.commit()

                        st_state = MachineState(machine_id=mid, status='Normal', health_factor=1.0)
                        db.session.add(st_state)

                        if machine_type in SENSOR_CONFIG:
                            for s_name, s_cfg in SENSOR_CONFIG[machine_type].items():
                                st = SensorTemplate.query.filter_by(name=s_name).first()
                                if not st:
                                    st = SensorTemplate(
                                        name=s_name,
                                        unit=s_cfg.get('unit', ''),
                                        min_range=s_cfg.get('range', [0, 100])[0],
                                        max_range=s_cfg.get('range', [0, 100])[1]
                                    )
                                    db.session.add(st)
                                    db.session.commit()
                                asensor = AssetSensor(
                                    asset_id=asset.id,
                                    sensor_template_id=st.id,
                                    channel_id=f"{mid}_{s_name}"
                                )
                                db.session.add(asensor)
                db.session.commit()
        except Exception as e:
            application.logger.warning(f"Auto-seed exception: {e}")
    
    return application
