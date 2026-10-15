"""
Configuration Models for v2 Schema (Templates & Assets)
"""
from datetime import datetime
from app import db
from sqlalchemy.dialects.postgresql import JSONB

# 1. Location & Hierarchy
class Location(db.Model):
    """Physical location hierarchy (Site -> Area -> Line)."""
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False) # Site, Area, Line
    path = db.Column(db.String(500), index=True) # Materialized path e.g. "1/5/12"
    
    # Relationships
    children = db.relationship('Location', backref=db.backref('parent', remote_side=[id]))
    assets = db.relationship('Asset', backref='location', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'parent_id': self.parent_id,
            'name': self.name,
            'type': self.type,
            'path': self.path
        }

# 2. Templates
class AssetTemplate(db.Model):
    """Defines a type of machine (e.g., 'Boxing Machine v1')."""
    __tablename__ = 'asset_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    manufacturer = db.Column(db.String(100))
    version = db.Column(db.String(50))
    
    # Relationships
    sensors = db.relationship('AssetTemplateSensor', backref='asset_template', cascade='all, delete-orphan')
    failure_modes = db.relationship('FailureModeTemplate', backref='asset_template', cascade='all, delete-orphan')
    assets = db.relationship('Asset', backref='template', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'manufacturer': self.manufacturer,
            'version': self.version
        }

class SensorTemplate(db.Model):
    """Defines a type of sensor (e.g., 'Vibration Sensor 100Hz')."""
    __tablename__ = 'sensor_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    unit = db.Column(db.String(20))
    data_type = db.Column(db.String(20), default='float')
    min_range = db.Column(db.Float)
    max_range = db.Column(db.Float)
    sampling_rate_hz = db.Column(db.Float)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'unit': self.unit,
            'data_type': self.data_type,
            'min_range': self.min_range,
            'max_range': self.max_range,
            'sampling_rate_hz': self.sampling_rate_hz
        }

class AssetTemplateSensor(db.Model):
    """Link between AssetTemplate and SensorTemplate."""
    __tablename__ = 'asset_template_sensors'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_template_id = db.Column(db.Integer, db.ForeignKey('asset_templates.id'), nullable=False)
    sensor_template_id = db.Column(db.Integer, db.ForeignKey('sensor_templates.id'), nullable=False)
    
    # Default configuration for this sensor on this asset type
    default_threshold_min = db.Column(db.Float)
    default_threshold_max = db.Column(db.Float)
    
    sensor_template = db.relationship('SensorTemplate')

class FailureModeTemplate(db.Model):
    """Known failure modes for an asset type."""
    __tablename__ = 'failure_mode_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_template_id = db.Column(db.Integer, db.ForeignKey('asset_templates.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    severity = db.Column(db.Integer) # 1-10
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'severity': self.severity
        }

# 3. Instances
class Asset(db.Model):
    """A physical machine instance."""
    __tablename__ = 'assets'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_template_id = db.Column(db.Integer, db.ForeignKey('asset_templates.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False) # e.g. BOXING_001
    serial_number = db.Column(db.String(100))
    install_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Active')
    
    # Relationships
    sensors = db.relationship('AssetSensor', backref='asset', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'template_name': self.template.name,
            'location_name': self.location.name if self.location else None,
            'status': self.status,
            'install_date': self.install_date.isoformat() if self.install_date else None
        }

class AssetSensor(db.Model):
    """A specific sensor on a specific asset."""
    __tablename__ = 'asset_sensors'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    sensor_template_id = db.Column(db.Integer, db.ForeignKey('sensor_templates.id'), nullable=False)
    
    channel_id = db.Column(db.String(100), nullable=False) # ID used in ingestion
    config_overrides = db.Column(db.JSON) # Custom thresholds
    
    sensor_template = db.relationship('SensorTemplate')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.sensor_template.name,
            'channel_id': self.channel_id,
            'unit': self.sensor_template.unit,
            'config': self.config_overrides
        }
