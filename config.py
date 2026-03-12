import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///semantix.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Model paths
    MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
    CLASSIFIER_PATH = os.path.join(MODEL_DIR, 'classifier.pkl')
    VECTORIZER_PATH = os.path.join(MODEL_DIR, 'vectorizer.pkl')
    FAISS_INDEX_PATH = os.path.join(MODEL_DIR, 'faiss.index')
    
    # Embedding model
    EMBEDDING_MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
    
    # OpenAlex API
    OPENALEX_BASE_URL = 'https://api.openalex.org'
    OPENALEX_EMAIL = os.getenv('OPENALEX_EMAIL', '')  # For polite pool
    
    # Intent classifier settings
    CONFIDENCE_THRESHOLD = 0.6  # Below this, trigger self-learning
    SELF_LEARNING_RETRAIN_THRESHOLD = 5  # Retrain after N new examples
    
    # Search settings
    TOP_RESULTS = 10
    RELATED_ARTICLES = 15
    SIMILARITY_THRESHOLD = 0.5  # Minimum similarity for graph edges
    
    # Intent categories
    INTENT_CATEGORIES = [
        'software_engineering',
        'cloud',
        'devops',
        'ai_ml',
        'general',
        'cybersecurity',
        'database',
        'networking',
        'mobile_development',
        'web_development',
        'data_science',
        'blockchain',
        'emerging_tech',
        'it_management',
        'systems'
    ]
