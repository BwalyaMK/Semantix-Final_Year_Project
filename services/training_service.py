"""
Training Service
Handles manual training of the intent classifier
with batch and single-example support
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime

from config import Config
from database.models import db, TrainingData
from services.classifier_service import ClassifierService


class TrainingService:
    """Service for training and managing the intent classifier"""
    
    def __init__(self):
        self.classifier = ClassifierService()
    
    def add_training_example(
        self,
        question: str,
        intent: str,
        source: str = 'manual'
    ) -> Dict:
        """Add a single training example to the database"""
        if intent not in Config.INTENT_CATEGORIES:
            return {
                'success': False,
                'error': f'Invalid intent. Must be one of: {Config.INTENT_CATEGORIES}'
            }
        
        # Check for duplicate
        existing = TrainingData.query.filter_by(question=question).first()
        if existing:
            # Update intent if different
            if existing.intent != intent:
                existing.intent = intent
                existing.source = source
                db.session.commit()
                return {'success': True, 'action': 'updated', 'id': existing.id}
            return {'success': True, 'action': 'exists', 'id': existing.id}
        
        # Add new example
        example = TrainingData(
            question=question,
            intent=intent,
            source=source
        )
        db.session.add(example)
        db.session.commit()
        
        return {'success': True, 'action': 'added', 'id': example.id}
    
    def add_batch_training(self, examples: List[Dict]) -> Dict:
        """
        Add multiple training examples
        Each example should have 'question' and 'intent' keys
        """
        added = 0
        updated = 0
        errors = []
        
        for i, example in enumerate(examples):
            question = example.get('question', '').strip()
            intent = example.get('intent', '').strip()
            
            if not question or not intent:
                errors.append(f"Row {i}: Missing question or intent")
                continue
            
            result = self.add_training_example(question, intent, source='batch')
            
            if result.get('success'):
                if result['action'] == 'added':
                    added += 1
                elif result['action'] == 'updated':
                    updated += 1
            else:
                errors.append(f"Row {i}: {result.get('error')}")
        
        return {
            'success': True,
            'added': added,
            'updated': updated,
            'errors': errors
        }
    
    def retrain_classifier(self) -> Dict:
        """Retrain the classifier using all training data"""
        # Fetch all training data
        examples = TrainingData.query.all()
        
        if len(examples) < 2:
            return {
                'success': False,
                'error': 'Need at least 2 training examples to train'
            }
        
        texts = [e.question for e in examples]
        labels = [e.intent for e in examples]
        
        # Train the classifier
        result = self.classifier.train(texts, labels)
        
        if result.get('success'):
            return {
                'success': True,
                'training_samples': len(examples),
                'classes': list(set(labels)),
                'cv_score': result.get('cv_score')
            }
        
        return result
    
    def get_training_data(self, page: int = 1, per_page: int = 50) -> Dict:
        """Get paginated training data"""
        pagination = TrainingData.query.order_by(
            TrainingData.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'examples': [e.to_dict() for e in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }
    
    def get_training_stats(self) -> Dict:
        """Get training data statistics"""
        total = TrainingData.query.count()
        
        # Count by intent
        by_intent = {}
        for intent in Config.INTENT_CATEGORIES:
            count = TrainingData.query.filter_by(intent=intent).count()
            by_intent[intent] = count
        
        # Count by source
        by_source = {
            'manual': TrainingData.query.filter_by(source='manual').count(),
            'seed': TrainingData.query.filter_by(source='seed').count(),
            'learned': TrainingData.query.filter_by(source='learned').count(),
            'batch': TrainingData.query.filter_by(source='batch').count()
        }
        
        return {
            'total': total,
            'by_intent': by_intent,
            'by_source': by_source,
            'classifier': self.classifier.get_model_info()
        }
    
    def delete_training_example(self, example_id: int) -> Dict:
        """Delete a training example"""
        example = TrainingData.query.get(example_id)
        if not example:
            return {'success': False, 'error': 'Example not found'}
        
        db.session.delete(example)
        db.session.commit()
        
        return {'success': True, 'deleted_id': example_id}
    
    def export_training_data(self) -> List[Dict]:
        """Export all training data as list of dicts"""
        examples = TrainingData.query.all()
        return [e.to_dict() for e in examples]
    
    def initialize_with_seed_data(self) -> Dict:
        """Initialize classifier with seed training data"""
        seed_data = self._get_seed_data()
        
        # Add to database
        for example in seed_data:
            self.add_training_example(
                example['question'],
                example['intent'],
                source='seed'
            )
        
        # Train classifier
        result = self.retrain_classifier()
        
        return {
            'success': True,
            'seeded_examples': len(seed_data),
            'training_result': result
        }
    
    def _get_seed_data(self) -> List[Dict]:
        """Get seed training data for initial classifier training"""
        return [
            # Software Engineering (25 examples)
            {"question": "What are design patterns in software engineering?", "intent": "software_engineering"},
            {"question": "How do I implement the singleton pattern?", "intent": "software_engineering"},
            {"question": "What is test-driven development?", "intent": "software_engineering"},
            {"question": "Explain SOLID principles", "intent": "software_engineering"},
            {"question": "What is agile methodology?", "intent": "software_engineering"},
            {"question": "How does version control work?", "intent": "software_engineering"},
            {"question": "What is code refactoring?", "intent": "software_engineering"},
            {"question": "Explain microservices architecture", "intent": "software_engineering"},
            {"question": "What is clean code?", "intent": "software_engineering"},
            {"question": "How to do code review effectively?", "intent": "software_engineering"},
            {"question": "What is software testing?", "intent": "software_engineering"},
            {"question": "Explain object-oriented programming", "intent": "software_engineering"},
            {"question": "What is the software development lifecycle?", "intent": "software_engineering"},
            {"question": "How to handle technical debt?", "intent": "software_engineering"},
            {"question": "What is API design best practices?", "intent": "software_engineering"},
            {"question": "How to write unit tests?", "intent": "software_engineering"},
            {"question": "What is the factory design pattern?", "intent": "software_engineering"},
            {"question": "Explain dependency injection", "intent": "software_engineering"},
            {"question": "What is domain-driven design?", "intent": "software_engineering"},
            {"question": "How to implement event-driven architecture?", "intent": "software_engineering"},
            {"question": "What is behavior-driven development BDD?", "intent": "software_engineering"},
            {"question": "Explain hexagonal architecture", "intent": "software_engineering"},
            {"question": "What is functional programming?", "intent": "software_engineering"},
            {"question": "How to design RESTful APIs?", "intent": "software_engineering"},
            {"question": "What is continuous integration testing?", "intent": "software_engineering"},
            
            # Cloud (25 examples)
            {"question": "What is cloud computing?", "intent": "cloud"},
            {"question": "Explain AWS services", "intent": "cloud"},
            {"question": "What is Azure?", "intent": "cloud"},
            {"question": "How does Google Cloud Platform work?", "intent": "cloud"},
            {"question": "What is serverless computing?", "intent": "cloud"},
            {"question": "Explain IaaS, PaaS, and SaaS", "intent": "cloud"},
            {"question": "What is cloud migration?", "intent": "cloud"},
            {"question": "How to secure cloud infrastructure?", "intent": "cloud"},
            {"question": "What is cloud native development?", "intent": "cloud"},
            {"question": "Explain cloud storage solutions", "intent": "cloud"},
            {"question": "What is multi-cloud strategy?", "intent": "cloud"},
            {"question": "How does cloud load balancing work?", "intent": "cloud"},
            {"question": "What is cloud cost optimization?", "intent": "cloud"},
            {"question": "Explain virtual machines in cloud", "intent": "cloud"},
            {"question": "What is cloud orchestration?", "intent": "cloud"},
            {"question": "How does AWS Lambda work?", "intent": "cloud"},
            {"question": "What is Azure Functions?", "intent": "cloud"},
            {"question": "Explain Amazon S3 storage", "intent": "cloud"},
            {"question": "What is cloud auto-scaling?", "intent": "cloud"},
            {"question": "How to deploy applications to AWS?", "intent": "cloud"},
            {"question": "What is Azure DevOps?", "intent": "cloud"},
            {"question": "Explain cloud networking VPC", "intent": "cloud"},
            {"question": "What is AWS EC2?", "intent": "cloud"},
            {"question": "How to use Google Cloud Run?", "intent": "cloud"},
            {"question": "What is cloud disaster recovery?", "intent": "cloud"},
            
            # DevOps (25 examples)
            {"question": "What is DevOps?", "intent": "devops"},
            {"question": "Explain CI/CD pipelines", "intent": "devops"},
            {"question": "How does Docker work?", "intent": "devops"},
            {"question": "What is Kubernetes?", "intent": "devops"},
            {"question": "Explain infrastructure as code", "intent": "devops"},
            {"question": "What is Jenkins?", "intent": "devops"},
            {"question": "How to implement continuous deployment?", "intent": "devops"},
            {"question": "What is GitOps?", "intent": "devops"},
            {"question": "Explain container orchestration", "intent": "devops"},
            {"question": "What is monitoring and observability?", "intent": "devops"},
            {"question": "How to use Terraform?", "intent": "devops"},
            {"question": "What is Ansible?", "intent": "devops"},
            {"question": "Explain DevSecOps", "intent": "devops"},
            {"question": "What is site reliability engineering?", "intent": "devops"},
            {"question": "How to automate deployments?", "intent": "devops"},
            {"question": "What is Docker Compose?", "intent": "devops"},
            {"question": "How to write Dockerfiles?", "intent": "devops"},
            {"question": "What is Helm for Kubernetes?", "intent": "devops"},
            {"question": "Explain GitHub Actions", "intent": "devops"},
            {"question": "What is ArgoCD?", "intent": "devops"},
            {"question": "How to set up monitoring with Prometheus?", "intent": "devops"},
            {"question": "What is Grafana used for?", "intent": "devops"},
            {"question": "Explain log aggregation with ELK stack", "intent": "devops"},
            {"question": "What is blue-green deployment?", "intent": "devops"},
            {"question": "How to implement canary releases?", "intent": "devops"},
            
            # AI/ML (25 examples)
            {"question": "What is machine learning?", "intent": "ai_ml"},
            {"question": "Explain neural networks", "intent": "ai_ml"},
            {"question": "What is deep learning?", "intent": "ai_ml"},
            {"question": "How do transformers work?", "intent": "ai_ml"},
            {"question": "What is natural language processing?", "intent": "ai_ml"},
            {"question": "Explain computer vision", "intent": "ai_ml"},
            {"question": "What is reinforcement learning?", "intent": "ai_ml"},
            {"question": "How to train a machine learning model?", "intent": "ai_ml"},
            {"question": "What are embeddings?", "intent": "ai_ml"},
            {"question": "Explain GPT and large language models", "intent": "ai_ml"},
            {"question": "What is transfer learning?", "intent": "ai_ml"},
            {"question": "How does BERT work?", "intent": "ai_ml"},
            {"question": "What is data preprocessing for ML?", "intent": "ai_ml"},
            {"question": "Explain supervised vs unsupervised learning", "intent": "ai_ml"},
            {"question": "What is model fine-tuning?", "intent": "ai_ml"},
            {"question": "How to use TensorFlow?", "intent": "ai_ml"},
            {"question": "What is PyTorch?", "intent": "ai_ml"},
            {"question": "Explain convolutional neural networks CNN", "intent": "ai_ml"},
            {"question": "What is recurrent neural network RNN?", "intent": "ai_ml"},
            {"question": "How to build a recommendation system?", "intent": "ai_ml"},
            {"question": "What is sentiment analysis?", "intent": "ai_ml"},
            {"question": "Explain attention mechanism in transformers", "intent": "ai_ml"},
            {"question": "What is feature engineering?", "intent": "ai_ml"},
            {"question": "How to evaluate ML model performance?", "intent": "ai_ml"},
            {"question": "What is MLOps?", "intent": "ai_ml"},
            
            # General (20 examples)
            {"question": "How to learn programming?", "intent": "general"},
            {"question": "What programming language should I learn?", "intent": "general"},
            {"question": "How to become a software developer?", "intent": "general"},
            {"question": "What is computer science?", "intent": "general"},
            {"question": "How to prepare for technical interviews?", "intent": "general"},
            {"question": "What are good coding practices?", "intent": "general"},
            {"question": "How to build a portfolio?", "intent": "general"},
            {"question": "What is open source?", "intent": "general"},
            {"question": "How to contribute to open source?", "intent": "general"},
            {"question": "What is GitHub?", "intent": "general"},
            {"question": "How to debug code effectively?", "intent": "general"},
            {"question": "What is the best IDE for programming?", "intent": "general"},
            {"question": "How to read technical documentation?", "intent": "general"},
            {"question": "What is stack overflow?", "intent": "general"},
            {"question": "How to write better code comments?", "intent": "general"},
            {"question": "What is pair programming?", "intent": "general"},
            {"question": "How to stay updated with technology?", "intent": "general"},
            {"question": "What are coding bootcamps?", "intent": "general"},
            {"question": "How to manage coding projects?", "intent": "general"},
            {"question": "What is technical blogging?", "intent": "general"},
        ]
