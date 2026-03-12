"""
Learning Service
Handles self-learning when the classifier encounters unknown queries
Extracts concepts from search results to infer intent
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from config import Config
from database.models import db, LearnedData, TrainingData
from services.classifier_service import ClassifierService
from services.embedding_service import EmbeddingService
from services.openalex_service import OpenAlexService

# Optional: KeyBERT for keyword extraction
try:
    from keybert import KeyBERT
    KEYBERT_AVAILABLE = True
except ImportError:
    KEYBERT_AVAILABLE = False


class LearningService:
    """Service for self-learning from unknown queries"""
    
    def __init__(self):
        self.classifier = ClassifierService()
        self.embedding_service = EmbeddingService()
        self.openalex_service = OpenAlexService()
        
        # Initialize KeyBERT if available
        self._keybert = None
        if KEYBERT_AVAILABLE:
            try:
                self._keybert = KeyBERT(model=self.embedding_service._model)
            except Exception:
                pass
        
        # Intent keyword mappings for inference
        self.intent_keywords = {
            'software_engineering': [
                'software', 'programming', 'code', 'development', 'testing',
                'design pattern', 'architecture', 'api', 'algorithm', 'debugging',
                'refactoring', 'agile', 'scrum', 'version control', 'git'
            ],
            'cloud': [
                'cloud', 'aws', 'azure', 'gcp', 'serverless', 'iaas', 'paas',
                'saas', 'virtualization', 'container', 'kubernetes', 'docker',
                'scalability', 'elastic', 'cloud native'
            ],
            'devops': [
                'devops', 'ci/cd', 'continuous integration', 'deployment',
                'pipeline', 'automation', 'infrastructure', 'monitoring',
                'kubernetes', 'docker', 'terraform', 'ansible', 'jenkins'
            ],
            'ai_ml': [
                'machine learning', 'artificial intelligence', 'neural network',
                'deep learning', 'nlp', 'natural language', 'computer vision',
                'model', 'training', 'transformer', 'embedding', 'classification',
                'prediction', 'data science'
            ],
            'general': [
                'programming', 'learn', 'career', 'technology', 'computer',
                'developer', 'engineer', 'interview', 'skills'
            ],
            'cybersecurity': [
                'security', 'cybersecurity', 'encryption', 'hashing', 'malware',
                'vulnerability', 'penetration', 'firewall', 'authentication',
                'injection', 'breach', 'vpn', 'audit', 'ids', 'ips'
            ],
            'database': [
                'database', 'sql', 'nosql', 'schema', 'index', 'replication',
                'normalization', 'acid', 'transaction', 'query', 'optimization',
                'mongodb', 'postgresql', 'mysql', 'sharding', 'oltp', 'olap'
            ],
            'networking': [
                'network', 'tcp', 'udp', 'router', 'switch', 'osi',
                'dns', 'vlan', 'load balancing', 'subnet', 'routing',
                'protocol', 'lan', 'wan', 'connectivity', 'qos'
            ],
            'mobile_development': [
                'mobile', 'ios', 'android', 'app', 'swift', 'kotlin',
                'react native', 'flutter', 'notification', 'ui', 'ux',
                'cross-platform', 'progressive web', 'hybrid'
            ],
            'web_development': [
                'web', 'html', 'css', 'javascript', 'frontend', 'backend',
                'react', 'vue', 'angular', 'nodejs', 'responsive', 'seo',
                'webpack', 'websocket', 'spa', 'component'
            ],
            'data_science': [
                'data science', 'data analysis', 'mining', 'visualization',
                'big data', 'statistics', 'exploratory', 'pipeline',
                'time series', 'correlation', 'warehouse', 'testing',
                'pandas', 'numpy', 'dashboard', 'analytics'
            ],
            'blockchain': [
                'blockchain', 'bitcoin', 'ethereum', 'smart contract',
                'cryptocurrency', 'consensus', 'mining', 'decentralized',
                'dapp', 'nft', 'web3', 'solidity', 'ledger', 'crypto'
            ],
            'emerging_tech': [
                'virtual reality', 'augmented reality', 'vr', 'ar', 'iot',
                'internet of things', 'quantum', 'edge computing',
                '5g', 'computer vision', 'digital twin', 'voice',
                'robotics', 'wearable', 'sensor'
            ],
            'it_management': [
                'project management', 'agile', 'scrum', 'waterfall', 'sprint',
                'governance', 'itil', 'service management', 'kpi',
                'technical debt', 'scrum master', 'change management',
                'compliance', 'documentation', 'product management'
            ],
            'systems': [
                'operating system', 'linux', 'windows', 'unix', 'process',
                'thread', 'virtualization', 'system administration', 'kernel',
                'system call', 'performance', 'monitoring',
                'containerization', 'recovery', 'os'
            ]
        }
    
    def should_learn(self, confidence: float) -> bool:
        """Check if the query confidence is below threshold for learning"""
        return confidence < Config.CONFIDENCE_THRESHOLD
    
    def learn_from_query(
        self,
        query: str,
        search_results: List[Dict],
        original_confidence: float
    ) -> Dict:
        """
        Learn from a query with low confidence
        Extracts keywords from results and infers intent
        """
        # Extract keywords from search results
        keywords = self._extract_keywords(query, search_results)
        
        # Infer intent from keywords
        inferred_intent, intent_confidence = self._infer_intent(keywords)
        
        # Store learned data
        abstract_ids = [r.get('openalex_id', '') for r in search_results[:3]]
        
        learned = LearnedData(
            user_query=query,
            inferred_intent=inferred_intent,
            confidence=intent_confidence,
            keywords=json.dumps(keywords),
            abstract_ids=json.dumps(abstract_ids),
            verified=False,
            added_to_training=False
        )
        db.session.add(learned)
        db.session.commit()
        
        # Check if we should trigger retraining
        self._check_retrain_threshold()
        
        return {
            'learned_id': learned.id,
            'query': query,
            'inferred_intent': inferred_intent,
            'confidence': intent_confidence,
            'keywords': keywords,
            'original_confidence': original_confidence
        }
    
    def _extract_keywords(self, query: str, results: List[Dict]) -> List[str]:
        """Extract keywords from query and search results"""
        keywords = []
        
        # Combine text from query and abstracts
        texts = [query]
        for result in results[:3]:
            if result.get('abstract'):
                texts.append(result['abstract'])
            if result.get('title'):
                texts.append(result['title'])
            # Add concepts from OpenAlex
            for concept in result.get('concepts', [])[:3]:
                if concept.get('name'):
                    keywords.append(concept['name'].lower())
        
        combined_text = ' '.join(texts)
        
        # Use KeyBERT if available
        if self._keybert:
            try:
                extracted = self._keybert.extract_keywords(
                    combined_text,
                    keyphrase_ngram_range=(1, 2),
                    stop_words='english',
                    top_n=10
                )
                keywords.extend([kw[0].lower() for kw in extracted])
            except Exception:
                pass
        
        # Fallback: simple word frequency extraction
        if not keywords:
            words = combined_text.lower().split()
            # Filter common words
            stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                         'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                         'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                         'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                         'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                         'through', 'during', 'before', 'after', 'above', 'below',
                         'between', 'under', 'again', 'further', 'then', 'once',
                         'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                         'neither', 'not', 'only', 'own', 'same', 'than', 'too',
                         'very', 'just', 'also', 'now', 'here', 'there', 'when',
                         'where', 'why', 'how', 'all', 'each', 'every', 'both',
                         'few', 'more', 'most', 'other', 'some', 'such', 'no',
                         'any', 'this', 'that', 'these', 'those', 'what', 'which'}
            
            word_freq = {}
            for word in words:
                if len(word) > 3 and word not in stop_words and word.isalpha():
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            keywords = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[:10]
        
        return list(set(keywords))[:15]
    
    def _infer_intent(self, keywords: List[str]) -> Tuple[str, float]:
        """Infer intent based on extracted keywords"""
        intent_scores = {intent: 0 for intent in Config.INTENT_CATEGORIES}
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for intent, intent_kws in self.intent_keywords.items():
                for intent_kw in intent_kws:
                    if intent_kw in keyword_lower or keyword_lower in intent_kw:
                        intent_scores[intent] += 1
                        break
        
        # Find best matching intent
        max_score = max(intent_scores.values())
        if max_score == 0:
            return ('general', 0.3)
        
        best_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x])
        
        # Calculate confidence based on score distribution
        total_score = sum(intent_scores.values())
        confidence = intent_scores[best_intent] / total_score if total_score > 0 else 0.3
        
        return (best_intent, min(confidence, 0.9))
    
    def _check_retrain_threshold(self):
        """Check if we have enough learned examples to trigger retraining"""
        pending_count = db.session.query(LearnedData).filter_by(added_to_training=False).count()
        
        if pending_count >= Config.SELF_LEARNING_RETRAIN_THRESHOLD:
            self._promote_learned_data()
    
    def _promote_learned_data(self):
        """Promote verified learned data to training data and retrain"""
        # Get verified or high-confidence learned examples
        learned = db.session.query(LearnedData).filter(
            LearnedData.added_to_training == False,
            (LearnedData.verified == True) | (LearnedData.confidence >= 0.7)
        ).all()
        
        if not learned:
            return
        
        # Add to training data
        for item in learned:
            training_example = TrainingData(
                question=item.user_query,
                intent=item.inferred_intent,
                source='learned'
            )
            db.session.add(training_example)
            item.added_to_training = True
        
        db.session.commit()
        
        # Retrain classifier
        from services.training_service import TrainingService
        training_service = TrainingService()
        training_service.retrain_classifier()
    
    def verify_learned_example(self, learned_id: int, correct_intent: Optional[str] = None) -> Dict:
        """Verify or correct a learned example"""
        learned = db.session.get(LearnedData, learned_id)
        if not learned:
            return {'success': False, 'error': 'Example not found'}
        
        if correct_intent:
            if correct_intent not in Config.INTENT_CATEGORIES:
                return {'success': False, 'error': f'Invalid intent: {correct_intent}'}
            learned.inferred_intent = correct_intent
        
        learned.verified = True
        db.session.commit()
        
        return {
            'success': True,
            'learned_id': learned_id,
            'intent': learned.inferred_intent,
            'verified': True
        }
    
    def get_pending_learned_data(self, page: int = 1, per_page: int = 20) -> Dict:
        """Get learned data pending verification"""
        pagination = db.session.query(LearnedData).filter_by(
            added_to_training=False
        ).order_by(
            LearnedData.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'examples': [e.to_dict() for e in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }
    
    def get_learning_stats(self) -> Dict:
        """Get self-learning statistics"""
        total = db.session.query(LearnedData).count()
        verified = db.session.query(LearnedData).filter_by(verified=True).count()
        promoted = db.session.query(LearnedData).filter_by(added_to_training=True).count()
        pending = total - promoted
        
        # Count by inferred intent
        by_intent = {}
        for intent in Config.INTENT_CATEGORIES:
            count = db.session.query(LearnedData).filter_by(inferred_intent=intent).count()
            by_intent[intent] = count
        
        return {
            'total_learned': total,
            'verified': verified,
            'promoted_to_training': promoted,
            'pending': pending,
            'by_intent': by_intent,
            'retrain_threshold': Config.SELF_LEARNING_RETRAIN_THRESHOLD
        }
    
    def force_retrain(self) -> Dict:
        """Force promotion of learned data and retraining"""
        self._promote_learned_data()
        
        from services.training_service import TrainingService
        training_service = TrainingService()
        return training_service.retrain_classifier()
