"""
Authentication routes.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from urllib.parse import urlparse

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))
            
        login_user(user, remember=remember)
        
        # Redirect to next page if it exists
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
            
        return redirect(next_page)
        
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# Simple setup route to create initial admin (remove in production or protect)
@auth_bp.route('/setup-admin', methods=['GET', 'POST'])
def setup_admin():
    try:
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            return "Admin already exists", 200
        
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        
        return "Admin created: admin / admin123", 200
    except Exception as e:
        db.session.rollback()
        return f"Error creating admin: {str(e)}", 500
