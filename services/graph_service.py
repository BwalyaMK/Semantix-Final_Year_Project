"""
Graph Service
Builds similarity graphs from search results and related articles
for Cytoscape.js visualization
"""

from typing import List, Dict, Tuple, Optional
import numpy as np

from config import Config
from services.embedding_service import EmbeddingService
from services.openalex_service import OpenAlexService


class GraphService:
    """Service for building and managing similarity graphs"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.openalex_service = OpenAlexService()
    
    def build_similarity_graph(
        self,
        primary_results: List[Dict],
        query: str,
        include_related: bool = True,
        max_related: int = 10,
        similarity_threshold: float = None
    ) -> Dict:
        """
        Build a similarity graph from primary search results and their related works
        Returns Cytoscape.js compatible graph data
        """
        if similarity_threshold is None:
            similarity_threshold = Config.SIMILARITY_THRESHOLD
        
        all_articles = []
        article_ids = set()
        
        # Add primary results
        for article in primary_results:
            if article['openalex_id'] not in article_ids:
                article['is_primary'] = True
                all_articles.append(article)
                article_ids.add(article['openalex_id'])
        
        # Fetch related works for each primary result
        if include_related:
            for primary in primary_results[:3]:  # Limit to top 3 for performance
                related = self.openalex_service.get_related_works(
                    primary['openalex_id'],
                    limit=max_related
                )
                for article in related:
                    if article['openalex_id'] not in article_ids:
                        article['is_primary'] = False
                        article['related_to'] = primary['openalex_id']
                        all_articles.append(article)
                        article_ids.add(article['openalex_id'])
        
        # Calculate embeddings and similarities
        nodes, edges, rankings = self._compute_graph_structure(
            all_articles,
            query,
            similarity_threshold
        )
        
        return {
            'nodes': nodes,
            'edges': edges,
            'related_rankings': rankings[:max_related],  # Top 10 related
            'stats': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'primary_count': len(primary_results),
                'related_count': len(all_articles) - len(primary_results)
            }
        }
    
    def _compute_graph_structure(
        self,
        articles: List[Dict],
        query: str,
        threshold: float
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Compute graph nodes, edges, and rankings based on embeddings
        """
        if not articles:
            return [], [], []
        
        # Filter articles with abstracts for embedding
        articles_with_text = []
        for article in articles:
            text = article.get('abstract') or article.get('title', '')
            if text:
                article['_embed_text'] = text
                articles_with_text.append(article)
        
        if not articles_with_text:
            # Return basic nodes without similarity edges
            nodes = [self._article_to_node(a, 0.5) for a in articles]
            return nodes, [], []
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        # Generate article embeddings
        texts = [a['_embed_text'] for a in articles_with_text]
        embeddings = self.embedding_service.embed_texts(texts)
        
        # Compute similarities to query
        query_similarities = {}
        for i, article in enumerate(articles_with_text):
            sim = self.embedding_service.compute_similarity(query_embedding, embeddings[i])
            query_similarities[article['openalex_id']] = sim
            article['query_similarity'] = sim
        
        # Compute pairwise similarity matrix
        similarity_matrix = self.embedding_service.compute_similarity_matrix(embeddings)
        
        # Build nodes
        nodes = []
        for article in articles:
            sim = query_similarities.get(article['openalex_id'], 0.5)
            nodes.append(self._article_to_node(article, sim))
        
        # Build edges (only above threshold)
        edges = []
        edge_id = 0
        for i in range(len(articles_with_text)):
            for j in range(i + 1, len(articles_with_text)):
                sim = float(similarity_matrix[i][j])
                if sim >= threshold:
                    edges.append({
                        'data': {
                            'id': f'e{edge_id}',
                            'source': articles_with_text[i]['openalex_id'],
                            'target': articles_with_text[j]['openalex_id'],
                            'weight': sim,
                            'label': f'{sim:.2f}'
                        }
                    })
                    edge_id += 1
        
        # Rank articles by query similarity (for related articles list)
        rankings = sorted(
            [
                {
                    'openalex_id': a['openalex_id'],
                    'title': a['title'],
                    'authors': a.get('authors', []),
                    'url': a.get('url', ''),
                    'similarity': query_similarities.get(a['openalex_id'], 0),
                    'is_primary': a.get('is_primary', False)
                }
                for a in articles_with_text
            ],
            key=lambda x: x['similarity'],
            reverse=True
        )
        
        return nodes, edges, rankings
    
    def _article_to_node(self, article: Dict, similarity: float) -> Dict:
        """Convert article to Cytoscape.js node format"""
        return {
            'data': {
                'id': article['openalex_id'],
                'label': self._truncate(article.get('title', 'Untitled'), 50),
                'title': article.get('title', 'Untitled'),
                'abstract': article.get('abstract', ''),
                'authors': article.get('authors', []),
                'year': article.get('publication_year'),
                'url': article.get('url', ''),
                'doi': article.get('doi', ''),
                'concepts': article.get('concepts', []),
                'similarity': similarity,
                'is_primary': article.get('is_primary', False),
                'cited_by': article.get('cited_by_count', 0)
            },
            'classes': 'primary' if article.get('is_primary') else 'related'
        }
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + '...'
    
    def get_article_connections(self, openalex_id: str, graph_data: Dict) -> Dict:
        """Get all connections for a specific article in the graph"""
        connections = {
            'article_id': openalex_id,
            'connected_to': []
        }
        
        for edge in graph_data.get('edges', []):
            edge_data = edge.get('data', {})
            if edge_data.get('source') == openalex_id:
                connections['connected_to'].append({
                    'id': edge_data['target'],
                    'weight': edge_data['weight']
                })
            elif edge_data.get('target') == openalex_id:
                connections['connected_to'].append({
                    'id': edge_data['source'],
                    'weight': edge_data['weight']
                })
        
        return connections
    
    def update_threshold(self, graph_data: Dict, new_threshold: float) -> Dict:
        """
        Recalculate edges with a new similarity threshold
        Useful for dynamic filtering in the UI
        """
        # Filter edges by new threshold
        filtered_edges = [
            edge for edge in graph_data.get('edges', [])
            if edge['data']['weight'] >= new_threshold
        ]
        
        return {
            'nodes': graph_data['nodes'],
            'edges': filtered_edges,
            'related_rankings': graph_data.get('related_rankings', []),
            'stats': {
                **graph_data.get('stats', {}),
                'total_edges': len(filtered_edges),
                'threshold': new_threshold
            }
        }
