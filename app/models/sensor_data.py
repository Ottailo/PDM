"""
Database models for the Predictive Maintenance Platform.
"""
from datetime import datetime
from app import db
from sqlalchemy.dialects.sqlite import JSON as SqliteJSON

class SensorData(db.Model):
    """Sensor readings from machines."""
    __tablename__ = 'sensor_data'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sensor_id = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_sensor_time', 'sensor_id', 'timestamp'),
        db.Index('idx_timestamp', 'timestamp'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor_id,
            'value': self.value
        }

class EventLog(db.Model):
    """System events and state changes."""
    __tablename__ = 'event_log'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    machine_id = db.Column(db.String(100), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        db.Index('idx_event_time', 'timestamp'),
        db.Index('idx_machine_event', 'machine_id', 'event_type'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'machine_id': self.machine_id,
            'event_type': self.event_type,
            'details': self.details
        }

class MachineState(db.Model):
    """Current state of machines."""
    __tablename__ = 'machine_state'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Normal')
    health_factor = db.Column(db.Float, nullable=False, default=1.0)
    active_failure = db.Column(SqliteJSON, nullable=True)
    event_steps_left = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'status': self.status,
            'health_factor': self.health_factor,
            'active_failure': self.active_failure,
            'event_steps_left': self.event_steps_left,
            'last_updated': self.last_updated.isoformat()
        }

