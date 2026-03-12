"""
Semantix - Semantic Search and Knowledge Graph Application
Main Flask application entry point
"""

import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_login import LoginManager

from config import Config
from database.models import db, User

# Initialize Flask app
app = Flask(__name__, static_folder='public', static_url_path='')
app.config.from_object(Config)

# Initialize extensions
CORS(app)
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
from routes.auth import auth_bp
from routes.search import search_bp
from routes.chat import chat_bp
from routes.graph import graph_bp
from routes.train import train_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(search_bp, url_prefix='/api/search')
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(graph_bp, url_prefix='/api/graph')
app.register_blueprint(train_bp, url_prefix='/api/train')

# Serve static files
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# Create database tables and initialize services
def init_app():
    with app.app_context():
        # Create models directory if not exists
        os.makedirs(Config.MODEL_DIR, exist_ok=True)
        
        # Create database tables
        db.create_all()
        
        # Initialize classifier with seed data if not exists
        from services.training_service import TrainingService
        training_service = TrainingService()
        if not os.path.exists(Config.CLASSIFIER_PATH):
            print("Initializing classifier with seed data...")
            training_service.initialize_with_seed_data()
        
        print("✓ Application initialized successfully")

if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
