"""
Graph Routes
Handles graph generation and manipulation endpoints
"""

from flask import Blueprint, request, jsonify

from config import Config
from services.graph_service import GraphService
from services.openalex_service import OpenAlexService
from services.embedding_service import EmbeddingService
from services.classifier_service import ClassifierService

graph_bp = Blueprint('graph', __name__)

# Initialize services
graph_service = GraphService()
openalex_service = OpenAlexService()
embedding_service = EmbeddingService()
classifier = ClassifierService()


@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
    Build a similarity graph for a query
    Returns Cytoscape.js compatible graph data
    """
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    max_related = data.get('max_related', Config.RELATED_ARTICLES)
    similarity_threshold = data.get('threshold', Config.SIMILARITY_THRESHOLD)
    
    # Classify and search
    intent, confidence = classifier.predict(query)
    
    top_results, _ = openalex_service.search_with_reranking(
        query=query,
        intent=intent,
        embedding_service=embedding_service,
        top_k=Config.TOP_RESULTS,
        fetch_count=30
    )
    
    if not top_results:
        return jsonify({
            'query': query,
            'error': 'No results found',
            'graph': {'nodes': [], 'edges': [], 'related_rankings': []}
        })
    
    # Build graph
    graph_data = graph_service.build_similarity_graph(
        primary_results=top_results,
        query=query,
        include_related=True,
        max_related=max_related,
        similarity_threshold=similarity_threshold
    )
    
    return jsonify({
        'query': query,
        'intent': intent,
        'confidence': confidence,
        'primary_results': top_results,
        'graph': graph_data
    })


@graph_bp.route('/related/<openalex_id>', methods=['GET'])
def get_related(openalex_id):
    """Get related articles for a specific paper"""
    limit = request.args.get('limit', Config.RELATED_ARTICLES, type=int)
    
    related = openalex_service.get_related_works(openalex_id, limit=limit)
    
    return jsonify({
        'openalex_id': openalex_id,
        'related': related,
        'count': len(related)
    })


@graph_bp.route('/article/<openalex_id>', methods=['GET'])
def get_article(openalex_id):
    """Get details for a specific article"""
    article = openalex_service.get_work_by_id(openalex_id)
    
    if not article:
        return jsonify({'error': 'Article not found'}), 404
    
    return jsonify(article)


@graph_bp.route('/filter', methods=['POST'])
def filter_graph():
    """
    Filter existing graph edges by similarity threshold
    Useful for dynamic UI filtering
    """
    data = request.get_json()
    graph_data = data.get('graph')
    new_threshold = data.get('threshold', Config.SIMILARITY_THRESHOLD)
    
    if not graph_data:
        return jsonify({'error': 'Graph data is required'}), 400
    
    filtered = graph_service.update_threshold(graph_data, new_threshold)
    
    return jsonify(filtered)


@graph_bp.route('/expand', methods=['POST'])
def expand_node():
    """
    Expand a node in the graph by fetching its related works
    """
    data = request.get_json()
    openalex_id = data.get('openalex_id')
    query = data.get('query', '')
    existing_ids = data.get('existing_ids', [])
    limit = data.get('limit', 5)
    
    if not openalex_id:
        return jsonify({'error': 'openalex_id is required'}), 400
    
    # Fetch related works
    related = openalex_service.get_related_works(openalex_id, limit=limit * 2)
    
    # Filter out existing nodes
    new_articles = [
        r for r in related 
        if r['openalex_id'] not in existing_ids
    ][:limit]
    
    if not new_articles:
        return jsonify({
            'openalex_id': openalex_id,
            'new_nodes': [],
            'new_edges': []
        })
    
    # Generate embeddings for similarity calculation
    if query:
        query_embedding = embedding_service.embed_text(query)
        texts = [a.get('abstract') or a.get('title', '') for a in new_articles]
        embeddings = embedding_service.embed_texts(texts)
        
        for i, article in enumerate(new_articles):
            sim = embedding_service.compute_similarity(query_embedding, embeddings[i])
            article['similarity'] = float(sim)
    
    # Convert to nodes
    new_nodes = []
    for article in new_articles:
        new_nodes.append({
            'data': {
                'id': article['openalex_id'],
                'label': article['title'][:50] + '...' if len(article['title']) > 50 else article['title'],
                'title': article['title'],
                'abstract': article.get('abstract', ''),
                'authors': article.get('authors', []),
                'year': article.get('publication_year'),
                'url': article.get('url', ''),
                'similarity': article.get('similarity', 0.5),
                'is_primary': False
            },
            'classes': 'related expanded'
        })
    
    # Create edge to parent
    new_edges = [{
        'data': {
            'id': f'e_{openalex_id}_{article["openalex_id"]}',
            'source': openalex_id,
            'target': article['openalex_id'],
            'weight': 0.6,
            'label': 'related'
        }
    } for article in new_articles]
    
    return jsonify({
        'openalex_id': openalex_id,
        'new_nodes': new_nodes,
        'new_edges': new_edges
    })
