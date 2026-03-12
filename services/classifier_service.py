"""
Intent Classifier Service
Scikit-learn based TF-IDF + LogisticRegression classifier
for categorizing user queries into domains
"""

import os
import joblib
from typing import Tuple, List, Dict, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
import numpy as np

from config import Config


class ClassifierService:
    """Service for intent classification using scikit-learn"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._pipeline = None
        self._classes = Config.INTENT_CATEGORIES
        self._load_or_create_model()
        self._initialized = True
    
    def _load_or_create_model(self):
        """Load existing model or create new pipeline"""
        if os.path.exists(Config.CLASSIFIER_PATH):
            try:
                self._pipeline = joblib.load(Config.CLASSIFIER_PATH)
                print("✓ Loaded intent classifier")
            except Exception as e:
                print(f"Error loading classifier: {e}")
                self._create_new_pipeline()
        else:
            self._create_new_pipeline()
    
    def _create_new_pipeline(self):
        """Create a new classification pipeline"""
        self._pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words='english',
                lowercase=True,
                min_df=1,
                max_df=0.95
            )),
            ('classifier', LogisticRegression(
                max_iter=1000,
                solver='lbfgs',
                class_weight='balanced'
            ))
        ])
        print("✓ Created new classifier pipeline")
    
    def train(self, texts: List[str], labels: List[str]) -> Dict:
        """
        Train the classifier on provided data
        Returns training metrics
        """
        if len(texts) < 2:
            return {'error': 'Need at least 2 training examples'}
        
        # Ensure all labels are valid
        valid_labels = [l for l in labels if l in self._classes]
        if len(valid_labels) != len(labels):
            invalid = set(labels) - set(self._classes)
            return {'error': f'Invalid labels: {invalid}'}
        
        # Train the pipeline
        self._pipeline.fit(texts, labels)
        
        # Calculate cross-validation score if enough data
        cv_score = None
        if len(texts) >= 5:
            try:
                scores = cross_val_score(self._pipeline, texts, labels, cv=min(5, len(texts)))
                cv_score = float(np.mean(scores))
            except Exception:
                pass
        
        # Save model
        self.save_model()
        
        return {
            'success': True,
            'training_samples': len(texts),
            'classes': list(set(labels)),
            'cv_score': cv_score
        }
    
    def predict(self, text: str) -> Tuple[str, float]:
        """
        Predict intent for a single text
        Returns (predicted_intent, confidence_score)
        """
        if self._pipeline is None or not hasattr(self._pipeline, 'classes_'):
            return ('general', 0.0)
        
        try:
            # Get prediction and probabilities
            prediction = self._pipeline.predict([text])[0]
            probabilities = self._pipeline.predict_proba([text])[0]
            confidence = float(max(probabilities))
            
            return (prediction, confidence)
        except Exception as e:
            print(f"Prediction error: {e}")
            return ('general', 0.0)
    
    def predict_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """
        Predict intents for multiple texts
        Returns list of (predicted_intent, confidence_score) tuples
        """
        if self._pipeline is None or not hasattr(self._pipeline, 'classes_'):
            return [('general', 0.0) for _ in texts]
        
        try:
            predictions = self._pipeline.predict(texts)
            probabilities = self._pipeline.predict_proba(texts)
            confidences = [float(max(p)) for p in probabilities]
            
            return list(zip(predictions, confidences))
        except Exception as e:
            print(f"Batch prediction error: {e}")
            return [('general', 0.0) for _ in texts]
    
    def get_all_probabilities(self, text: str) -> Dict[str, float]:
        """
        Get probability scores for all intent classes
        Returns dict of {intent: probability}
        """
        if self._pipeline is None or not hasattr(self._pipeline, 'classes_'):
            return {c: 0.0 for c in self._classes}
        
        try:
            probabilities = self._pipeline.predict_proba([text])[0]
            classes = self._pipeline.classes_
            return {c: float(p) for c, p in zip(classes, probabilities)}
        except Exception:
            return {c: 0.0 for c in self._classes}
    
    def is_confident(self, confidence: float) -> bool:
        """Check if prediction confidence meets threshold"""
        return confidence >= Config.CONFIDENCE_THRESHOLD
    
    def save_model(self):
        """Save the trained model to disk"""
        os.makedirs(os.path.dirname(Config.CLASSIFIER_PATH), exist_ok=True)
        joblib.dump(self._pipeline, Config.CLASSIFIER_PATH)
        print("✓ Saved classifier model")
    
    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        if self._pipeline is None or not hasattr(self._pipeline, 'classes_'):
            return {
                'trained': False,
                'classes': self._classes
            }
        
        return {
            'trained': True,
            'classes': list(self._pipeline.classes_),
            'feature_count': len(self._pipeline.named_steps['tfidf'].vocabulary_) if hasattr(self._pipeline.named_steps['tfidf'], 'vocabulary_') else 0
        }
    
    def reset_model(self):
        """Reset the model to untrained state"""
        self._create_new_pipeline()
        if os.path.exists(Config.CLASSIFIER_PATH):
            os.remove(Config.CLASSIFIER_PATH)
    
    @property
    def is_trained(self) -> bool:
        """Check if model has been trained"""
        return self._pipeline is not None and hasattr(self._pipeline, 'classes_')
    
    @property
    def classes(self) -> List[str]:
        """Get available intent classes"""
        return self._classes
