"""
Database models for Semantix application
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat()
        }


class TrainingData(db.Model):
    """Training data for intent classifier - manually added examples"""
    __tablename__ = 'training_data'
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(20), default='manual')  # 'manual', 'seed', 'learned'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'intent': self.intent,
            'source': self.source,
            'created_at': self.created_at.isoformat()
        }


class LearnedData(db.Model):
    """Self-learned data from unknown queries"""
    __tablename__ = 'learned_data'
    
    id = db.Column(db.Integer, primary_key=True)
    user_query = db.Column(db.Text, nullable=False)
    inferred_intent = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    keywords = db.Column(db.Text, nullable=True)  # JSON array of extracted keywords
    abstract_ids = db.Column(db.Text, nullable=True)  # JSON array of OpenAlex IDs used
    verified = db.Column(db.Boolean, default=False)  # User-verified flag
    added_to_training = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'query': self.user_query,
            'inferred_intent': self.inferred_intent,
            'confidence': self.confidence,
            'keywords': self.keywords,
            'verified': self.verified,
            'added_to_training': self.added_to_training,
            'created_at': self.created_at.isoformat()
        }


class CachedArticle(db.Model):
    """Cached articles from OpenAlex for faster retrieval"""
    __tablename__ = 'cached_articles'
    
    id = db.Column(db.Integer, primary_key=True)
    openalex_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.Text, nullable=False)
    abstract = db.Column(db.Text, nullable=True)
    authors = db.Column(db.Text, nullable=True)  # JSON array
    publication_year = db.Column(db.Integer, nullable=True)
    doi = db.Column(db.String(200), nullable=True)
    url = db.Column(db.String(500), nullable=True)
    concepts = db.Column(db.Text, nullable=True)  # JSON array of concepts
    embedding = db.Column(db.LargeBinary, nullable=True)  # Numpy array as bytes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'openalex_id': self.openalex_id,
            'title': self.title,
            'abstract': self.abstract,
            'authors': json.loads(self.authors) if self.authors else [],
            'publication_year': self.publication_year,
            'doi': self.doi,
            'url': self.url,
            'concepts': json.loads(self.concepts) if self.concepts else [],
            'created_at': self.created_at.isoformat()
        }


class Concept(db.Model):
    """Extracted concepts/keywords for knowledge graph"""
    __tablename__ = 'concepts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=True)  # Intent category
    frequency = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'frequency': self.frequency
        }


class ConceptRelation(db.Model):
    """Relationships between concepts for knowledge graph"""
    __tablename__ = 'concept_relations'
    
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('concepts.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('concepts.id'), nullable=False)
    weight = db.Column(db.Float, default=1.0)  # Relationship strength
    relation_type = db.Column(db.String(50), default='related')
    
    source = db.relationship('Concept', foreign_keys=[source_id], backref='outgoing')
    target = db.relationship('Concept', foreign_keys=[target_id], backref='incoming')
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'weight': self.weight,
            'relation_type': self.relation_type
        }


class SearchHistory(db.Model):
    """Search history for analytics and learning"""
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    query = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    results_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='searches')
    
    def to_dict(self):
        return {
            'id': self.id,
            'query': self.query,
            'intent': self.intent,
            'confidence': self.confidence,
            'results_count': self.results_count,
            'created_at': self.created_at.isoformat()
        }
