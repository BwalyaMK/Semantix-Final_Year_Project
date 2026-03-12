"""
Search Routes
Handles search requests with intent classification and re-ranking
"""

from flask import Blueprint, request, jsonify
from flask_login import current_user

from config import Config
from database.models import db, SearchHistory
from services.classifier_service import ClassifierService
from services.embedding_service import EmbeddingService
from services.openalex_service import OpenAlexService

search_bp = Blueprint('search', __name__)

# Initialize services
classifier = ClassifierService()
embedding_service = EmbeddingService()
openalex_service = OpenAlexService()


@search_bp.route('/', methods=['POST'])
def search():
    """
    Search for academic papers
    Classifies intent, searches OpenAlex, and re-ranks results
    """
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    page = data.get('page', 1)
    per_page = data.get('per_page', 25)
    use_reranking = data.get('rerank', True)
    
    # Classify intent
    intent, confidence = classifier.predict(query)
    
    # Search with or without re-ranking
    if use_reranking:
        results, rankings = openalex_service.search_with_reranking(
            query=query,
            intent=intent,
            embedding_service=embedding_service,
            top_k=per_page,
            fetch_count=max(per_page * 2, 50)
        )
    else:
        search_data = openalex_service.search(
            query=query,
            intent=intent,
            page=page,
            per_page=per_page
        )
        results = search_data.get('results', [])
        rankings = []
    
    # Log search history
    if current_user.is_authenticated:
        history = SearchHistory(
            user_id=current_user.id,
            query=query,
            intent=intent,
            confidence=confidence,
            results_count=len(results)
        )
    else:
        history = SearchHistory(
            query=query,
            intent=intent,
            confidence=confidence,
            results_count=len(results)
        )
    db.session.add(history)
    db.session.commit()
    
    return jsonify({
        'query': query,
        'intent': intent,
        'confidence': confidence,
        'results': results,
        'total': len(results),
        'page': page
    })


@search_bp.route('/simple', methods=['GET'])
def simple_search():
    """Simple GET-based search"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Classify intent
    intent, confidence = classifier.predict(query)
    
    # Search OpenAlex
    search_data = openalex_service.search(
        query=query,
        intent=intent,
        page=page,
        per_page=per_page
    )
    
    return jsonify({
        'query': query,
        'intent': intent,
        'confidence': confidence,
        'results': search_data.get('results', []),
        'meta': search_data.get('meta', {})
    })


@search_bp.route('/intents', methods=['GET'])
def get_intents():
    """Get available intent categories"""
    return jsonify({
        'intents': Config.INTENT_CATEGORIES,
        'classifier_status': classifier.get_model_info()
    })


@search_bp.route('/classify', methods=['POST'])
def classify_query():
    """Classify a query without searching"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    intent, confidence = classifier.predict(query)
    all_probs = classifier.get_all_probabilities(query)
    
    return jsonify({
        'query': query,
        'intent': intent,
        'confidence': confidence,
        'all_probabilities': all_probs,
        'is_confident': classifier.is_confident(confidence)
    })


@search_bp.route('/history', methods=['GET'])
def get_search_history():
    """Get search history (recent searches)"""
    limit = request.args.get('limit', 20, type=int)
    
    if current_user.is_authenticated:
        history = SearchHistory.query.filter_by(
            user_id=current_user.id
        ).order_by(
            SearchHistory.created_at.desc()
        ).limit(limit).all()
    else:
        history = SearchHistory.query.order_by(
            SearchHistory.created_at.desc()
        ).limit(limit).all()
    
    return jsonify({
        'history': [h.to_dict() for h in history]
    })
