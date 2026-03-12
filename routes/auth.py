"""
Authentication Routes
Handles user registration, login, and logout
"""

from flask import Blueprint, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user

from database.models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    
    # Validation
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    # Check if user exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Create user
    user = User(email=email, name=name)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    # Log in the user
    login_user(user)
    
    return jsonify({
        'success': True,
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Log in a user"""
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    login_user(user, remember=data.get('remember', False))
    
    return jsonify({
        'success': True,
        'user': user.to_dict()
    })


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Log out the current user"""
    logout_user()
    return jsonify({'success': True})


@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user info"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': current_user.to_dict()
        })
    return jsonify({
        'authenticated': False,
        'user': None
    })


@auth_bp.route('/update', methods=['PUT'])
@login_required
def update_profile():
    """Update user profile"""
    data = request.get_json()
    
    if 'name' in data:
        current_user.name = data['name'].strip()
    
    if 'password' in data and data['password']:
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        current_user.set_password(data['password'])
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': current_user.to_dict()
    })
