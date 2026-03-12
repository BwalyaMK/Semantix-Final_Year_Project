"""
Semantix Intent Classifier - Simplified Test Suite
Appropriate for student project evaluation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collections import defaultdict
from app import app
from services.classifier_service import ClassifierService

# =============================================================================
# SIMPLIFIED TEST SET: 3 queries per category (45 total) + 5 ambiguous
# =============================================================================

TEST_QUERIES = {
    "software_engineering": [
        "How do I implement the observer design pattern?",
        "What is test-driven development?",
        "Explain the MVC architecture pattern",
    ],
    "cloud": [
        "How to deploy applications on AWS Lambda?",
        "What are the benefits of serverless architecture?",
        "Explain multi-region deployment strategies",
    ],
    "devops": [
        "How to create a CI/CD pipeline?",
        "What is the purpose of container orchestration?",
        "Explain blue-green deployment strategy",
    ],
    "ai_ml": [
        "How do neural networks learn?",
        "What is transfer learning?",
        "Explain the attention mechanism in transformers",
    ],
    "general": [
        "What programming language should beginners learn?",
        "How to prepare for a technical interview?",
        "What are the best resources for learning to code?",
    ],
    "cybersecurity": [
        "How to prevent SQL injection attacks?",
        "What is multi-factor authentication?",
        "What are the OWASP Top 10?",
    ],
    "database": [
        "What is database normalization?",
        "How to optimize SQL queries?",
        "What are ACID properties?",
    ],
    "networking": [
        "What is the difference between TCP and UDP?",
        "How does DNS resolution work?",
        "What are the OSI model layers?",
    ],
    "mobile_development": [
        "Native vs cross-platform mobile apps?",
        "How to implement push notifications?",
        "What is React Native?",
    ],
    "web_development": [
        "How to create responsive web designs?",
        "What is the virtual DOM in React?",
        "What are progressive web apps?",
    ],
    "data_science": [
        "How to perform exploratory data analysis?",
        "What are data visualization libraries?",
        "How to handle missing data?",
    ],
    "blockchain": [
        "How does Bitcoin consensus work?",
        "What are smart contracts?",
        "How to develop decentralized apps?",
    ],
    "emerging_tech": [
        "What are quantum computing applications?",
        "How to develop for VR platforms?",
        "What is edge computing?",
    ],
    "it_management": [
        "What is the difference between Agile and Waterfall?",
        "What are Scrum Master responsibilities?",
        "How to manage technical debt?",
    ],
    "systems": [
        "Difference between processes and threads?",
        "How does virtual memory work?",
        "What is the kernel's role in an OS?",
    ],
}

AMBIGUOUS_QUERIES = [
    ("How to deploy a machine learning model?", ["ai_ml", "devops", "cloud"]),
    ("Best practices for API security?", ["cybersecurity", "software_engineering", "web_development"]),
    ("How to set up a database in the cloud?", ["database", "cloud", "devops"]),
    ("How to secure a web application?", ["cybersecurity", "web_development"]),
    ("What skills for a DevOps engineer?", ["devops", "general", "cloud"]),
]


def run_tests():
    """Run simplified test suite"""
    results = {
        "test_info": {},
        "category_metrics": [],
        "ambiguous_results": [],
        "summary": {}
    }
    
    print("=" * 70)
    print("      SEMANTIX CLASSIFIER - SIMPLIFIED TEST RESULTS")
    print("=" * 70)
    print()
    
    with app.app_context():
        classifier = ClassifierService()
        
        total_queries = sum(len(q) for q in TEST_QUERIES.values())
        print(f"TEST CONFIGURATION")
        print("-" * 70)
        print(f"  Test queries: {total_queries} ({len(TEST_QUERIES)} categories x 3 each)")
        print(f"  Ambiguous queries: {len(AMBIGUOUS_QUERIES)}")
        print(f"  Total: {total_queries + len(AMBIGUOUS_QUERIES)} queries")
        print()
        
        results["test_info"] = {
            "standard_queries": total_queries,
            "ambiguous_queries": len(AMBIGUOUS_QUERIES),
            "categories": len(TEST_QUERIES)
        }
        
        # Test standard queries
        print("PER-CATEGORY RESULTS")
        print("-" * 70)
        
        all_true = []
        all_pred = []
        category_results = defaultdict(lambda: {"correct": 0, "total": 0, "predictions": []})
        
        for true_intent, queries in TEST_QUERIES.items():
            for query in queries:
                pred_intent, confidence = classifier.predict(query)
                all_true.append(true_intent)
                all_pred.append(pred_intent)
                
                is_correct = pred_intent == true_intent
                category_results[true_intent]["total"] += 1
                if is_correct:
                    category_results[true_intent]["correct"] += 1
                category_results[true_intent]["predictions"].append({
                    "query": query[:40],
                    "predicted": pred_intent,
                    "correct": is_correct
                })
        
        print(f"  {'Category':<22} {'Correct':>8} {'Accuracy':>10}")
        print(f"  {'-'*22} {'-'*8} {'-'*10}")
        
        for intent in sorted(TEST_QUERIES.keys()):
            correct = category_results[intent]["correct"]
            total = category_results[intent]["total"]
            accuracy = correct / total
            status = "PASS" if accuracy >= 0.67 else "FAIL"
            
            results["category_metrics"].append({
                "category": intent,
                "correct": correct,
                "total": total,
                "accuracy": accuracy
            })
            
            print(f"  {intent:<22} {correct}/{total:>5} {accuracy:>9.0%}  [{status}]")
        
        # Overall accuracy
        overall_correct = sum(1 for t, p in zip(all_true, all_pred) if t == p)
        overall_accuracy = overall_correct / len(all_true)
        
        print(f"  {'-'*22} {'-'*8} {'-'*10}")
        print(f"  {'OVERALL':<22} {overall_correct}/{len(all_true):>3} {overall_accuracy:>9.0%}")
        print()
        
        # Ambiguous query testing
        print("AMBIGUOUS QUERY ANALYSIS")
        print("-" * 70)
        
        for query, expected in AMBIGUOUS_QUERIES:
            probs = classifier.get_all_probabilities(query)
            top3 = sorted(probs.items(), key=lambda x: -x[1])[:3]
            top3_intents = [p[0] for p in top3]
            
            hits = sum(1 for e in expected if e in top3_intents)
            
            results["ambiguous_results"].append({
                "query": query,
                "expected": expected,
                "top3": [(i, round(c, 3)) for i, c in top3],
                "coverage": f"{hits}/{len(expected)}"
            })
            
            print(f"  Query: \"{query[:50]}\"")
            print(f"  Expected: {', '.join(expected)}")
            print(f"  Top-3: {', '.join([f'{i}({c:.2f})' for i, c in top3])}")
            print(f"  Coverage: {hits}/{len(expected)} expected in top-3")
            print()
        
        # Summary
        results["summary"] = {
            "overall_accuracy": overall_accuracy,
            "categories_passing": sum(1 for m in results["category_metrics"] if m["accuracy"] >= 0.67),
            "total_categories": len(TEST_QUERIES)
        }
        
        print("=" * 70)
        print("SUMMARY")
        print("-" * 70)
        print(f"  Overall Accuracy: {overall_accuracy:.1%}")
        print(f"  Categories Passing (>=67%): {results['summary']['categories_passing']}/{len(TEST_QUERIES)}")
        print(f"  Test Status: {'PASS' if overall_accuracy >= 0.70 else 'NEEDS IMPROVEMENT'}")
        print("=" * 70)
        
    return results


if __name__ == "__main__":
    run_tests()
