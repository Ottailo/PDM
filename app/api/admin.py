from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.models.user import User
from app import db
from functools import wraps
import time
try:
    import psutil
except ImportError:
    psutil = None

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        return render_template('errors/403.html'), 403
    return render_template('admin_dashboard.html')

@admin_bp.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'role': u.role,
        'created_at': u.created_at.isoformat() if u.created_at else None
    } for u in users])

@admin_bp.route('/api/admin/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    data = request.get_json()
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
        
    user = User(
        username=data['username'],
        email=data['email'],
        role=data.get('role', 'user')
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully', 'id': user.id}), 201

@admin_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
        
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': 'User deleted successfully'})

@admin_bp.route('/api/admin/system-stats', methods=['GET'])
@login_required
@admin_required
def system_stats():
    # Basic system stats using psutil
    try:
        cpu_percent = psutil.cpu_percent() if psutil else 0.0
    except Exception:
        cpu_percent = 0.0
    try:
        memory_percent = psutil.virtual_memory().percent if psutil else 0.0
    except Exception:
        memory_percent = 0.0
    
    # Database stats (simple check)
    try:
        db.session.execute('SELECT 1')
        db_status = 'Connected'
    except:
        db_status = 'Error'
        
    return jsonify({
        'cpu_usage': cpu_percent,
        'memory_usage': memory_percent,
        'db_status': db_status,
        'active_sessions': 1 # Placeholder for now
    })
