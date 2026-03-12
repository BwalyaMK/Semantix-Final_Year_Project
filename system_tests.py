"""
Semantix - Simplified System Tests
Covers: Re-ranking, Knowledge Graph, Self-Learning, Performance
Appropriate for student project evaluation
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from services.classifier_service import ClassifierService
from services.embedding_service import EmbeddingService
from services.openalex_service import OpenAlexService
from services.graph_service import GraphService
from services.learning_service import LearningService
from database.models import LearnedData

# Test queries for each component
RERANK_TEST_QUERIES = [
    "machine learning optimization techniques",
    "cloud computing security best practices",
    "software testing methodologies",
]

GRAPH_TEST_QUERY = "neural network deep learning"

SELF_LEARNING_QUERIES = [
    ("quantum machine learning applications", 0.3),  # Should trigger (< 0.6)
    ("blockchain IoT integration", 0.25),            # Should trigger
    ("software design patterns", 0.8),               # Should NOT trigger (> 0.6)
]


def test_reranking():
    """Test 1: Semantic Re-ranking Effectiveness"""
    print()
    print("=" * 70)
    print("TEST 1: SEMANTIC RE-RANKING EFFECTIVENESS")
    print("=" * 70)
    print()
    
    embedding_service = EmbeddingService()
    openalex_service = OpenAlexService()
    
    results = []
    
    for query in RERANK_TEST_QUERIES:
        print(f"Query: \"{query}\"")
        print("-" * 50)
        
        # Get baseline results (no reranking)
        baseline = openalex_service.search(query, intent=None, page=1, per_page=5)
        baseline_titles = [r.get('title', '')[:50] for r in baseline.get('results', [])]
        
        # Get reranked results (returns tuple: results, rankings)
        reranked_results, rankings = openalex_service.search_with_reranking(
            query=query,
            intent=None,
            embedding_service=embedding_service,
            top_k=5,
            fetch_count=20
        )
        reranked_titles = [r.get('title', '')[:50] for r in reranked_results]
        reranked_scores = [r.get('similarity_score', 0) for r in reranked_results]
        
        # Check if order changed (indicates reranking worked)
        order_changed = baseline_titles != reranked_titles
        avg_similarity = sum(reranked_scores) / len(reranked_scores) if reranked_scores else 0
        
        print(f"  Baseline top result: {baseline_titles[0] if baseline_titles else 'N/A'}...")
        print(f"  Reranked top result: {reranked_titles[0] if reranked_titles else 'N/A'}...")
        print(f"  Order changed: {'Yes' if order_changed else 'No'}")
        print(f"  Avg similarity score: {avg_similarity:.3f}")
        print()
        
        results.append({
            "query": query,
            "order_changed": order_changed,
            "avg_similarity": avg_similarity
        })
    
    # Summary
    queries_improved = sum(1 for r in results if r["order_changed"])
    avg_sim = sum(r["avg_similarity"] for r in results) / len(results)
    
    print("RESULT: Re-ranking Effectiveness")
    print(f"  Queries with order changes: {queries_improved}/{len(results)}")
    print(f"  Average similarity score: {avg_sim:.3f}")
    print(f"  Status: {'PASS' if queries_improved > 0 else 'CHECK'}")
    
    return results


def test_graph_construction():
    """Test 2: Knowledge Graph Construction"""
    print()
    print("=" * 70)
    print("TEST 2: KNOWLEDGE GRAPH CONSTRUCTION")
    print("=" * 70)
    print()
    
    classifier = ClassifierService()
    embedding_service = EmbeddingService()
    openalex_service = OpenAlexService()
    graph_service = GraphService()
    
    query = GRAPH_TEST_QUERY
    print(f"Query: \"{query}\"")
    print("-" * 50)
    
    # Get search results (returns tuple: results, rankings)
    intent, confidence = classifier.predict(query)
    search_results, _ = openalex_service.search_with_reranking(
        query=query,
        intent=intent,
        embedding_service=embedding_service,
        top_k=5
    )
    
    # Build graph
    start_time = time.time()
    graph = graph_service.build_similarity_graph(
        primary_results=search_results,
        query=query,
        include_related=True,
        max_related=3,
        similarity_threshold=0.5
    )
    build_time = time.time() - start_time
    
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    stats = graph.get('stats', {})
    
    primary_count = sum(1 for n in nodes if n.get('data', {}).get('is_primary'))
    related_count = len(nodes) - primary_count
    
    print(f"  Total nodes: {len(nodes)}")
    print(f"  Primary nodes: {primary_count}")
    print(f"  Related nodes: {related_count}")
    print(f"  Total edges: {len(edges)}")
    print(f"  Build time: {build_time:.2f}s")
    print()
    
    # Validate structure
    has_nodes = len(nodes) > 0
    has_edges = len(edges) > 0
    has_primaries = primary_count > 0
    valid_structure = all(
        'data' in n and 'id' in n.get('data', {})
        for n in nodes
    )
    
    print("RESULT: Graph Construction")
    print(f"  Has nodes: {'Yes' if has_nodes else 'No'}")
    print(f"  Has edges: {'Yes' if has_edges else 'No'}")
    print(f"  Has primary nodes: {'Yes' if has_primaries else 'No'}")
    print(f"  Valid structure: {'Yes' if valid_structure else 'No'}")
    print(f"  Status: {'PASS' if all([has_nodes, has_edges, valid_structure]) else 'FAIL'}")
    
    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "primary": primary_count,
        "related": related_count,
        "build_time": build_time,
        "valid": all([has_nodes, has_edges, valid_structure])
    }


def test_self_learning():
    """Test 3: Self-Learning Trigger Behavior"""
    print()
    print("=" * 70)
    print("TEST 3: SELF-LEARNING TRIGGER BEHAVIOR")
    print("=" * 70)
    print()
    
    learning_service = LearningService()
    
    results = []
    
    for query, simulated_conf in SELF_LEARNING_QUERIES:
        should_trigger = simulated_conf < 0.6
        actual_trigger = learning_service.should_learn(simulated_conf)
        
        correct = should_trigger == actual_trigger
        
        print(f"Query: \"{query}\"")
        print(f"  Confidence: {simulated_conf}")
        print(f"  Should trigger learning: {should_trigger}")
        print(f"  Actually triggers: {actual_trigger}")
        print(f"  Correct behavior: {'Yes' if correct else 'No'}")
        print()
        
        results.append({
            "query": query,
            "confidence": simulated_conf,
            "should_trigger": should_trigger,
            "did_trigger": actual_trigger,
            "correct": correct
        })
    
    all_correct = all(r["correct"] for r in results)
    
    print("RESULT: Self-Learning Triggers")
    print(f"  Correct behaviors: {sum(1 for r in results if r['correct'])}/{len(results)}")
    print(f"  Threshold: 0.60")
    print(f"  Status: {'PASS' if all_correct else 'FAIL'}")
    
    return results


def test_performance():
    """Test 4: Response Time Performance"""
    print()
    print("=" * 70)
    print("TEST 4: RESPONSE TIME PERFORMANCE")
    print("=" * 70)
    print()
    
    classifier = ClassifierService()
    embedding_service = EmbeddingService()
    openalex_service = OpenAlexService()
    
    test_query = "software engineering best practices"
    
    # Test 1: Classification time
    start = time.time()
    intent, conf = classifier.predict(test_query)
    classify_time = time.time() - start
    
    # Test 2: Embedding generation time
    start = time.time()
    embedding = embedding_service.embed_text(test_query)
    embed_time = time.time() - start
    
    # Test 3: Simple search time
    start = time.time()
    results = openalex_service.search(test_query, intent, page=1, per_page=10)
    search_time = time.time() - start
    
    # Test 4: Search with reranking time
    start = time.time()
    reranked, _ = openalex_service.search_with_reranking(
        query=test_query,
        intent=intent,
        embedding_service=embedding_service,
        top_k=10
    )
    rerank_time = time.time() - start
    
    print(f"Query: \"{test_query}\"")
    print("-" * 50)
    print()
    print("  Component Response Times:")
    print(f"    Classification:     {classify_time*1000:>8.1f} ms")
    print(f"    Embedding gen:      {embed_time*1000:>8.1f} ms")
    print(f"    Simple search:      {search_time*1000:>8.1f} ms")
    print(f"    Search + rerank:    {rerank_time*1000:>8.1f} ms")
    print()
    
    total_time = rerank_time  # Full pipeline time
    acceptable = total_time < 5.0  # Under 5 seconds is acceptable
    
    print("RESULT: Performance")
    print(f"  Total response time: {total_time:.2f}s")
    print(f"  Acceptable (< 5s): {'Yes' if acceptable else 'No'}")
    print(f"  Status: {'PASS' if acceptable else 'FAIL'}")
    
    return {
        "classify_ms": classify_time * 1000,
        "embed_ms": embed_time * 1000,
        "search_ms": search_time * 1000,
        "rerank_ms": rerank_time * 1000,
        "total_s": total_time,
        "acceptable": acceptable
    }


def run_all_tests():
    """Run all system tests"""
    print("=" * 70)
    print("         SEMANTIX - SYSTEM COMPONENT TESTS")
    print("=" * 70)
    
    with app.app_context():
        rerank_results = test_reranking()
        graph_results = test_graph_construction()
        learning_results = test_self_learning()
        perf_results = test_performance()
    
    # Final Summary
    print()
    print("=" * 70)
    print("                    TEST SUMMARY")
    print("=" * 70)
    print()
    print("  Test                          Status")
    print("  --------------------------    ------")
    
    rerank_pass = sum(1 for r in rerank_results if r["order_changed"]) > 0
    graph_pass = graph_results["valid"]
    learn_pass = all(r["correct"] for r in learning_results)
    perf_pass = perf_results["acceptable"]
    
    print(f"  1. Re-ranking Effectiveness   {'PASS' if rerank_pass else 'CHECK'}")
    print(f"  2. Graph Construction         {'PASS' if graph_pass else 'FAIL'}")
    print(f"  3. Self-Learning Triggers     {'PASS' if learn_pass else 'FAIL'}")
    print(f"  4. Performance                {'PASS' if perf_pass else 'FAIL'}")
    print()
    
    all_pass = all([rerank_pass, graph_pass, learn_pass, perf_pass])
    print(f"  OVERALL: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS NEED ATTENTION'}")
    print("=" * 70)
    
    return {
        "reranking": rerank_results,
        "graph": graph_results,
        "learning": learning_results,
        "performance": perf_results
    }


if __name__ == "__main__":
    run_all_tests()
