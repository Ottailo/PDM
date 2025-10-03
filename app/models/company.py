"""
Company and Machine Management Models
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from app import db

class Company(db.Model):
    """Company model for multi-tenant support."""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    industry = db.Column(db.String(50), nullable=False)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    machines = db.relationship('Machine', backref='company', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'industry': self.industry,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'address': self.address,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'machine_count': len(self.machines)
        }

class Machine(db.Model):
    """Machine model for storing machine configurations."""
    __tablename__ = 'machines'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    machine_type = db.Column(db.String(50), nullable=False)
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    installation_date = db.Column(db.DateTime)
    location = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Active')
    
    # Company relationship
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Configuration data
    sensor_config = db.Column(db.JSON)  # Custom sensor configuration
    thresholds = db.Column(db.JSON)    # Custom thresholds
    maintenance_schedule = db.Column(db.JSON)  # Maintenance schedule
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'name': self.name,
            'machine_type': self.machine_type,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'serial_number': self.serial_number,
            'installation_date': self.installation_date.isoformat() if self.installation_date else None,
            'location': self.location,
            'status': self.status,
            'company_id': self.company_id,
            'sensor_config': self.sensor_config,
            'thresholds': self.thresholds,
            'maintenance_schedule': self.maintenance_schedule,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by
        }


class MaintenanceRecord(db.Model):
    """Maintenance records for machines."""
    __tablename__ = 'maintenance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String(50), nullable=False)
    maintenance_type = db.Column(db.String(50), nullable=False)  # preventive, corrective, emergency
    description = db.Column(db.Text)
    performed_by = db.Column(db.String(100))
    duration_hours = db.Column(db.Float)
    cost = db.Column(db.Float)
    parts_replaced = db.Column(db.JSON)
    notes = db.Column(db.Text)
    
    # Timestamps
    scheduled_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Company relationship
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'maintenance_type': self.maintenance_type,
            'description': self.description,
            'performed_by': self.performed_by,
            'duration_hours': self.duration_hours,
            'cost': self.cost,
            'parts_replaced': self.parts_replaced,
            'notes': self.notes,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'created_at': self.created_at.isoformat(),
            'company_id': self.company_id
        }
