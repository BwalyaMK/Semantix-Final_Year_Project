"""
OpenAlex Service
Handles API interactions with OpenAlex for academic paper search
with local re-ranking using embeddings
"""

import requests
from typing import List, Dict, Optional, Tuple
import json

from config import Config


class OpenAlexService:
    """Service for searching and fetching papers from OpenAlex API"""
    
    def __init__(self):
        self.base_url = Config.OPENALEX_BASE_URL
        self.email = Config.OPENALEX_EMAIL
        
        # Domain-specific search filters for intent enhancement
        self.intent_filters = {
            'software_engineering': {
                'keywords': ['software engineering', 'software development', 'programming', 
                           'software architecture', 'design patterns', 'testing', 'debugging',
                           'agile', 'scrum', 'version control', 'code review'],
                'concepts': ['C41018263', 'C121332964']  # OpenAlex concept IDs
            },
            'cloud': {
                'keywords': ['cloud computing', 'aws', 'azure', 'google cloud', 'kubernetes',
                           'microservices', 'serverless', 'iaas', 'paas', 'saas', 'containers'],
                'concepts': ['C2522767166']
            },
            'devops': {
                'keywords': ['devops', 'continuous integration', 'continuous deployment', 
                           'ci/cd', 'infrastructure as code', 'docker', 'kubernetes',
                           'monitoring', 'automation', 'jenkins', 'gitlab'],
                'concepts': []
            },
            'ai_ml': {
                'keywords': ['artificial intelligence', 'machine learning', 'deep learning',
                           'neural networks', 'natural language processing', 'computer vision',
                           'transformers', 'reinforcement learning', 'data science'],
                'concepts': ['C154945302', 'C119857082']
            },
            'general': {
                'keywords': [],
                'concepts': []
            },
            'cybersecurity': {
                'keywords': ['cybersecurity', 'security', 'encryption', 'hashing', 'malware',
                           'vulnerability', 'penetration testing', 'firewall', 'authentication',
                           'sql injection', 'zero trust', 'data breach', 'vpn', 'ids', 'ips'],
                'concepts': []
            },
            'database': {
                'keywords': ['database', 'sql', 'nosql', 'schema', 'indexing', 'replication',
                           'normalization', 'acid', 'transaction', 'query optimization',
                           'mongodb', 'postgresql', 'mysql', 'sharding', 'oltp', 'olap'],
                'concepts': []
            },
            'networking': {
                'keywords': ['networking', 'network', 'tcp', 'udp', 'router', 'switch',
                           'osi model', 'dns', 'vlan', 'load balancing', 'subnet',
                           'routing', 'protocol', 'lan', 'wan', 'qos'],
                'concepts': []
            },
            'mobile_development': {
                'keywords': ['mobile', 'ios', 'android', 'mobile app', 'swift', 'kotlin',
                           'react native', 'flutter', 'push notification', 'mobile ui',
                           'cross-platform', 'progressive web app', 'app store'],
                'concepts': []
            },
            'web_development': {
                'keywords': ['web development', 'html', 'css', 'javascript', 'frontend',
                           'backend', 'react', 'vue', 'angular', 'nodejs', 'responsive',
                           'seo', 'webpack', 'websocket', 'spa', 'web component'],
                'concepts': []
            },
            'data_science': {
                'keywords': ['data science', 'data analysis', 'data mining', 'visualization',
                           'big data', 'statistics', 'exploratory analysis', 'data pipeline',
                           'time series', 'correlation', 'data warehouse', 'a/b testing',
                           'pandas', 'numpy', 'dashboard'],
                'concepts': []
            },
            'blockchain': {
                'keywords': ['blockchain', 'bitcoin', 'ethereum', 'smart contract',
                           'cryptocurrency', 'consensus', 'mining', 'decentralized',
                           'dapp', 'nft', 'web3', 'solidity', 'distributed ledger'],
                'concepts': []
            },
            'emerging_tech': {
                'keywords': ['virtual reality', 'augmented reality', 'vr', 'ar', 'iot',
                           'internet of things', 'quantum computing', 'edge computing',
                           '5g', 'computer vision', 'digital twin', 'voice assistant',
                           'robotics', 'wearable'],
                'concepts': []
            },
            'it_management': {
                'keywords': ['project management', 'agile', 'scrum', 'waterfall', 'sprint',
                           'it governance', 'itil', 'service management', 'kpi',
                           'technical debt', 'scrum master', 'change management',
                           'compliance', 'documentation', 'product management'],
                'concepts': []
            },
            'systems': {
                'keywords': ['operating system', 'linux', 'windows', 'unix', 'process',
                           'thread', 'virtualization', 'system administration', 'kernel',
                           'system call', 'performance tuning', 'system monitoring',
                           'containerization', 'system security', 'system recovery'],
                'concepts': []
            }
        }
    
    def _build_headers(self) -> Dict:
        """Build request headers with polite pool email"""
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Semantix/1.0'
        }
        if self.email:
            headers['mailto'] = self.email
        return headers
    
    def search(
        self,
        query: str,
        intent: Optional[str] = None,
        page: int = 1,
        per_page: int = 25
    ) -> Dict:
        """
        Search OpenAlex for papers matching query
        Optionally enhances search with intent-specific filters
        """
        # Build search query
        search_query = query
        
        # Enhance with intent keywords if provided
        if intent and intent in self.intent_filters:
            intent_keywords = self.intent_filters[intent]['keywords']
            if intent_keywords:
                # Add top 2 relevant keywords to query
                search_query = f"{query} {' '.join(intent_keywords[:2])}"
        
        # Build API URL
        params = {
            'search': search_query,
            'page': page,
            'per_page': per_page,
            'select': 'id,title,abstract_inverted_index,authorships,publication_year,doi,open_access,concepts,cited_by_count,related_works'
        }
        
        if self.email:
            params['mailto'] = self.email
        
        try:
            response = requests.get(
                f"{self.base_url}/works",
                params=params,
                headers=self._build_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Process results
            results = []
            for work in data.get('results', []):
                article = self._process_work(work)
                if article:
                    results.append(article)
            
            return {
                'results': results,
                'meta': data.get('meta', {}),
                'query': search_query,
                'intent': intent
            }
        
        except requests.exceptions.RequestException as e:
            print(f"OpenAlex API error: {e}")
            return {
                'results': [],
                'error': str(e),
                'query': search_query
            }
    
    def get_work_by_id(self, openalex_id: str) -> Optional[Dict]:
        """Fetch a specific work by its OpenAlex ID"""
        try:
            # Clean ID format
            if not openalex_id.startswith('https://'):
                openalex_id = f"https://openalex.org/{openalex_id}"
            
            response = requests.get(
                openalex_id,
                headers=self._build_headers(),
                timeout=30
            )
            response.raise_for_status()
            work = response.json()
            
            return self._process_work(work)
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching work {openalex_id}: {e}")
            return None
    
    def get_related_works(self, openalex_id: str, limit: int = 10) -> List[Dict]:
        """Fetch related works for a given paper"""
        # First get the work to find related_works IDs
        try:
            if not openalex_id.startswith('https://'):
                openalex_id = f"https://openalex.org/{openalex_id}"
            
            response = requests.get(
                openalex_id,
                headers=self._build_headers(),
                timeout=30
            )
            response.raise_for_status()
            work = response.json()
            
            related_ids = work.get('related_works', [])[:limit]
            
            if not related_ids:
                return []
            
            # Fetch related works using filter
            # Extract just the IDs
            clean_ids = [rid.split('/')[-1] for rid in related_ids]
            filter_str = '|'.join(clean_ids)
            
            params = {
                'filter': f'openalex_id:{filter_str}',
                'per_page': limit,
                'select': 'id,title,abstract_inverted_index,authorships,publication_year,doi,concepts,cited_by_count'
            }
            
            if self.email:
                params['mailto'] = self.email
            
            response = requests.get(
                f"{self.base_url}/works",
                params=params,
                headers=self._build_headers(),
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for w in data.get('results', []):
                article = self._process_work(w)
                if article:
                    results.append(article)
            
            return results
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching related works: {e}")
            return []
    
    def _process_work(self, work: Dict) -> Optional[Dict]:
        """Process a work from OpenAlex into our standard format"""
        if not work:
            return None
        
        # Reconstruct abstract from inverted index
        abstract = self._reconstruct_abstract(work.get('abstract_inverted_index'))
        
        # Extract authors
        authors = []
        for authorship in work.get('authorships', [])[:5]:  # Limit to first 5 authors
            author = authorship.get('author', {})
            if author.get('display_name'):
                authors.append(author['display_name'])
        
        # Extract concepts
        concepts = []
        for concept in work.get('concepts', [])[:10]:
            if concept.get('display_name'):
                concepts.append({
                    'name': concept['display_name'],
                    'score': concept.get('score', 0)
                })
        
        # Get OpenAlex ID
        openalex_id = work.get('id', '').split('/')[-1]
        
        # Build URL
        doi = work.get('doi')
        url = doi if doi else work.get('id', '')
        
        # Open access URL
        oa = work.get('open_access', {})
        if oa.get('oa_url'):
            url = oa['oa_url']
        
        return {
            'openalex_id': openalex_id,
            'title': work.get('title', 'Untitled'),
            'abstract': abstract,
            'authors': authors,
            'publication_year': work.get('publication_year'),
            'doi': doi,
            'url': url,
            'concepts': concepts,
            'cited_by_count': work.get('cited_by_count', 0),
            'related_works': work.get('related_works', [])
        }
    
    def _reconstruct_abstract(self, inverted_index: Optional[Dict]) -> str:
        """Reconstruct abstract from OpenAlex inverted index format"""
        if not inverted_index:
            return ""
        
        try:
            # Inverted index: {"word": [positions], ...}
            words = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    words.append((pos, word))
            
            # Sort by position and join
            words.sort(key=lambda x: x[0])
            return ' '.join(word for _, word in words)
        except Exception:
            return ""
    
    def search_with_reranking(
        self,
        query: str,
        intent: Optional[str],
        embedding_service,
        top_k: int = 3,
        fetch_count: int = 25
    ) -> Tuple[List[Dict], List[Tuple[str, float]]]:
        """
        Search OpenAlex and re-rank results using embedding similarity
        Returns (top_k results, all_rankings)
        """
        # Search OpenAlex
        search_results = self.search(query, intent, per_page=fetch_count)
        results = search_results.get('results', [])
        
        if not results:
            return [], []
        
        # Filter results with abstracts
        results_with_abstracts = [r for r in results if r.get('abstract')]
        
        if not results_with_abstracts:
            # Fall back to results without re-ranking
            return results[:top_k], [(r['openalex_id'], 1.0) for r in results[:top_k]]
        
        # Generate query embedding
        query_embedding = embedding_service.embed_text(query)
        
        # Generate embeddings for abstracts
        abstracts = [r['abstract'] for r in results_with_abstracts]
        abstract_embeddings = embedding_service.embed_texts(abstracts)
        
        # Rank by similarity
        rankings = embedding_service.rank_by_similarity(
            query_embedding,
            abstract_embeddings,
            [r['openalex_id'] for r in results_with_abstracts]
        )
        
        # Map rankings back to full results
        id_to_result = {r['openalex_id']: r for r in results_with_abstracts}
        ranked_results = []
        
        for openalex_id, score in rankings:
            result = id_to_result.get(openalex_id)
            if result:
                result['similarity_score'] = score
                ranked_results.append(result)
        
        return ranked_results[:top_k], rankings
