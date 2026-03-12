"""
Chat Routes
Handles chat/question answering with top abstracts as responses
Includes self-learning for unknown queries
"""

from flask import Blueprint, request, jsonify
from flask_login import current_user

from config import Config
from database.models import db, SearchHistory
from services.classifier_service import ClassifierService
from services.embedding_service import EmbeddingService
from services.openalex_service import OpenAlexService
from services.graph_service import GraphService
from services.learning_service import LearningService

chat_bp = Blueprint('chat', __name__)

# Initialize services
classifier = ClassifierService()
embedding_service = EmbeddingService()
openalex_service = OpenAlexService()
graph_service = GraphService()
learning_service = LearningService()


def generate_summary(question: str, results: list, intent: str) -> dict:
    """
    Generate a summary from the top search results.
    Extracts key sentences and synthesizes an answer.
    """
    if not results:
        return {
            'text': "No relevant papers found for your question.",
            'key_points': [],
            'sources_count': 0
        }
    
    # Intent-specific context
    intent_context = {
        'software_engineering': 'software development and engineering',
        'cloud': 'cloud computing and infrastructure',
        'devops': 'DevOps and continuous delivery',
        'ai_ml': 'artificial intelligence and machine learning',
        'general': 'technology'
    }
    
    context = intent_context.get(intent, 'technology')
    
    # Extract key information from top results
    key_points = []
    abstracts_text = []
    
    for i, result in enumerate(results[:5]):  # Use top 5 for summary
        abstract = result.get('abstract', '')
        title = result.get('title', '')
        
        if abstract:
            # Get first 2 sentences of each abstract
            sentences = abstract.replace('!', '.').replace('?', '.').split('.')
            sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
            
            if sentences:
                key_points.append({
                    'point': sentences[0] + '.',
                    'source': title[:80] + '...' if len(title) > 80 else title,
                    'rank': i + 1
                })
                abstracts_text.append(sentences[0])
    
    # Generate summary text
    if len(results) == 1:
        summary_intro = f"Based on 1 relevant paper in {context}"
    else:
        summary_intro = f"Based on {len(results)} relevant papers in {context}"
    
    # Create a synthesized summary
    if key_points:
        main_finding = key_points[0]['point']
        summary_text = f"{summary_intro}, here's what the research shows:\n\n{main_finding}"
        
        if len(key_points) > 1:
            summary_text += f"\n\nAdditionally, research indicates that {key_points[1]['point'].lower()}"
    else:
        summary_text = f"{summary_intro}. Review the papers below for detailed information."
    
    return {
        'text': summary_text,
        'key_points': key_points[:3],  # Top 3 key points
        'sources_count': len(results),
        'context': context
    }


@chat_bp.route('/ask', methods=['POST'])
def ask():
    """
    Answer a question with top 3 matching abstracts
    Also returns similarity graph data
    """
    data = request.get_json()
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    include_graph = data.get('include_graph', True)
    max_related = data.get('max_related', Config.RELATED_ARTICLES)
    
    # Classify intent
    intent, confidence = classifier.predict(question)
    
    # Search and re-rank
    top_results, all_rankings = openalex_service.search_with_reranking(
        query=question,
        intent=intent,
        embedding_service=embedding_service,
        top_k=Config.TOP_RESULTS,
        fetch_count=30
    )
    
    # Check if we should learn from this query
    learned_info = None
    if learning_service.should_learn(confidence) and top_results:
        learned_info = learning_service.learn_from_query(
            query=question,
            search_results=top_results,
            original_confidence=confidence
        )
    
    # Build similarity graph if requested
    graph_data = None
    if include_graph and top_results:
        graph_data = graph_service.build_similarity_graph(
            primary_results=top_results,
            query=question,
            include_related=True,
            max_related=max_related
        )
    
    # Log search
    history = SearchHistory(
        user_id=current_user.id if current_user.is_authenticated else None,
        query=question,
        intent=intent,
        confidence=confidence,
        results_count=len(top_results)
    )
    db.session.add(history)
    db.session.commit()
    
    # Generate summary from results
    summary = generate_summary(question, top_results, intent)
    
    return jsonify({
        'question': question,
        'intent': intent,
        'confidence': confidence,
        'is_confident': classifier.is_confident(confidence),
        'summary': summary,  # Summary of findings
        'answers': top_results,  # Top abstracts
        'graph': graph_data,
        'learned': learned_info
    })


@chat_bp.route('/quick', methods=['POST'])
def quick_answer():
    """
    Quick answer without graph generation
    Faster response for simple queries
    """
    data = request.get_json()
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({'error': 'Question is required'}), 400
    
    # Classify intent
    intent, confidence = classifier.predict(question)
    
    # Search and re-rank
    top_results, _ = openalex_service.search_with_reranking(
        query=question,
        intent=intent,
        embedding_service=embedding_service,
        top_k=Config.TOP_RESULTS,
        fetch_count=20
    )
    
    # Self-learn if low confidence
    if learning_service.should_learn(confidence) and top_results:
        learning_service.learn_from_query(
            query=question,
            search_results=top_results,
            original_confidence=confidence
        )
    
    return jsonify({
        'question': question,
        'intent': intent,
        'confidence': confidence,
        'answers': top_results
    })


@chat_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """
    Submit feedback on a learned query
    Allows users to correct or verify inferred intents
    """
    data = request.get_json()
    learned_id = data.get('learned_id')
    correct_intent = data.get('correct_intent')
    
    if not learned_id:
        return jsonify({'error': 'learned_id is required'}), 400
    
    result = learning_service.verify_learned_example(
        learned_id=learned_id,
        correct_intent=correct_intent
    )
    
    if result.get('success'):
        return jsonify(result)
    
    return jsonify(result), 400


@chat_bp.route('/stats', methods=['GET'])
def get_chat_stats():
    """Get chat/learning statistics"""
    classifier_info = classifier.get_model_info()
    learning_stats = learning_service.get_learning_stats()
    
    return jsonify({
        'classifier': classifier_info,
        'learning': learning_stats,
        'config': {
            'confidence_threshold': Config.CONFIDENCE_THRESHOLD,
            'top_results': Config.TOP_RESULTS,
            'related_articles': Config.RELATED_ARTICLES
        }
    })
