"""
User model for authentication.
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from datetime import datetime, timezone

class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    name = db.Column(db.String(100), nullable=False, default='')
    email_verified_at = db.Column(db.DateTime(timezone=True))
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    totp_secret = db.Column(db.Text)
    totp_last_counter = db.Column(db.BigInteger, nullable=False, default=-1)
    totp_pending_secret = db.Column(db.Text)
    totp_pending_until = db.Column(db.DateTime(timezone=True))
    recovery_hashes = db.Column(db.JSON, nullable=False, default=list)
    role = db.Column(db.String(20), default='viewer')  # admin, operator, viewer
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
        
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'company_id': self.company_id
        }
