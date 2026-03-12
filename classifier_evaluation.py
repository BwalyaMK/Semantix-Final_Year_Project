"""
Semantix Intent Classifier - Systematic Evaluation Script
Generates per-category metrics, ambiguous query analysis, and confidence histogram
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for saving files

from app import app
from services.classifier_service import ClassifierService

# =============================================================================
# TEST DATASET: 7 queries per category (105 total) + 15 ambiguous queries
# =============================================================================

TEST_QUERIES = {
    "software_engineering": [
        "How do I implement the observer design pattern?",
        "What is the difference between composition and inheritance?",
        "Best practices for writing clean code",
        "How to perform code review effectively",
        "What is test-driven development methodology?",
        "Explain the MVC architecture pattern",
        "How to refactor legacy code safely",
    ],
    "cloud": [
        "How to deploy applications on AWS Lambda?",
        "What is the difference between EC2 and ECS?",
        "How to set up auto-scaling in Azure?",
        "What are the benefits of serverless architecture?",
        "How to optimize cloud storage costs?",
        "Explain multi-region deployment strategies",
        "What is infrastructure as a service?",
    ],
    "devops": [
        "How to create a CI/CD pipeline with GitHub Actions?",
        "What is the purpose of container orchestration?",
        "How to write effective Dockerfiles?",
        "Explain blue-green deployment strategy",
        "How to implement infrastructure as code with Terraform?",
        "What are the key DevOps metrics to track?",
        "How to set up monitoring with Prometheus?",
    ],
    "ai_ml": [
        "How do convolutional neural networks work?",
        "What is the difference between classification and regression?",
        "How to prevent overfitting in deep learning models?",
        "Explain the attention mechanism in transformers",
        "What is transfer learning and when to use it?",
        "How to evaluate model performance with cross-validation?",
        "What are word embeddings in NLP?",
    ],
    "general": [
        "What programming language should beginners learn?",
        "How to prepare for a software engineering interview?",
        "What are the best resources for learning to code?",
        "How to build a portfolio as a developer?",
        "What certifications are valuable in tech?",
        "How to transition into a tech career?",
        "What is the difference between frontend and backend?",
    ],
    "cybersecurity": [
        "How to prevent SQL injection attacks?",
        "What is the difference between symmetric and asymmetric encryption?",
        "How to implement multi-factor authentication?",
        "What are the OWASP Top 10 vulnerabilities?",
        "How to conduct a security penetration test?",
        "What is zero trust security architecture?",
        "How to secure API endpoints?",
    ],
    "database": [
        "What is database normalization and why is it important?",
        "How to optimize slow SQL queries?",
        "What is the difference between OLTP and OLAP?",
        "How to implement database sharding?",
        "What are the ACID properties in databases?",
        "How to design a scalable database schema?",
        "What is the CAP theorem?",
    ],
    "networking": [
        "What is the difference between TCP and UDP protocols?",
        "How does DNS resolution work?",
        "What are the layers of the OSI model?",
        "How to configure a load balancer?",
        "What is the purpose of subnetting?",
        "How does HTTPS encryption work?",
        "What is the difference between LAN and WAN?",
    ],
    "mobile_development": [
        "What is the difference between native and cross-platform apps?",
        "How to implement push notifications in mobile apps?",
        "What are the best practices for mobile UI design?",
        "How to optimize battery usage in mobile applications?",
        "What is React Native and how does it work?",
        "How to handle offline functionality in mobile apps?",
        "What is the app store submission process?",
    ],
    "web_development": [
        "How to create responsive web designs with CSS?",
        "What is the virtual DOM in React?",
        "How to implement authentication in web applications?",
        "What are progressive web apps?",
        "How to optimize website loading performance?",
        "What is the difference between REST and GraphQL?",
        "How to handle cross-browser compatibility?",
    ],
    "data_science": [
        "How to perform exploratory data analysis?",
        "What are the best data visualization libraries?",
        "How to handle missing values in datasets?",
        "What is the difference between correlation and causation?",
        "How to build interactive dashboards?",
        "What is A/B testing methodology?",
        "How to work with time series data?",
    ],
    "blockchain": [
        "How does the Bitcoin consensus mechanism work?",
        "What are smart contracts and how do they execute?",
        "How to develop decentralized applications?",
        "What is the difference between public and private blockchains?",
        "How to audit smart contracts for vulnerabilities?",
        "What are NFTs and how are they created?",
        "How does proof of stake differ from proof of work?",
    ],
    "emerging_tech": [
        "What are the applications of quantum computing?",
        "How to develop for virtual reality platforms?",
        "What is edge computing and its benefits?",
        "How to build IoT device applications?",
        "What is the difference between AR and VR?",
        "How do digital twins work in industry?",
        "What is 5G technology and its impact?",
    ],
    "it_management": [
        "What is the difference between Agile and Waterfall?",
        "How to estimate software project timelines?",
        "What are the responsibilities of a Scrum Master?",
        "How to manage technical debt effectively?",
        "What is IT governance and why is it important?",
        "How to conduct effective sprint retrospectives?",
        "What are key performance indicators for IT teams?",
    ],
    "systems": [
        "What is the difference between processes and threads?",
        "How does virtual memory management work?",
        "What are the components of an operating system?",
        "How to optimize system performance?",
        "What is the role of the kernel in an OS?",
        "How do file systems organize data?",
        "What is containerization at the OS level?",
    ],
}

# Ambiguous queries that could belong to multiple categories
AMBIGUOUS_QUERIES = [
    ("How to deploy a machine learning model to production?", ["ai_ml", "devops", "cloud"]),
    ("What are best practices for API security?", ["cybersecurity", "software_engineering", "web_development"]),
    ("How to set up a database in the cloud?", ["database", "cloud", "devops"]),
    ("How to automate testing in a CI/CD pipeline?", ["devops", "software_engineering", "ai_ml"]),
    ("What is containerization and how does Docker work?", ["devops", "systems", "cloud"]),
    ("How to build a mobile app backend?", ["mobile_development", "software_engineering", "cloud"]),
    ("What programming skills are needed for data science?", ["data_science", "general", "ai_ml"]),
    ("How to secure a web application from attacks?", ["cybersecurity", "web_development", "software_engineering"]),
    ("How to optimize network performance in cloud?", ["networking", "cloud", "devops"]),
    ("What is the future of AI in software development?", ["ai_ml", "software_engineering", "emerging_tech"]),
    ("How to manage a remote development team?", ["it_management", "general", "software_engineering"]),
    ("How to build a blockchain-based application?", ["blockchain", "software_engineering", "web_development"]),
    ("What skills do I need to become a DevOps engineer?", ["devops", "general", "cloud"]),
    ("How to implement real-time features in web apps?", ["web_development", "networking", "software_engineering"]),
    ("How to analyze system performance metrics?", ["systems", "data_science", "devops"]),
]


def evaluate_classifier():
    """Main evaluation function"""
    print("=" * 78)
    print("         SEMANTIX INTENT CLASSIFIER - SYSTEMATIC EVALUATION")
    print("=" * 78)
    print()
    
    with app.app_context():
        classifier = ClassifierService()
        
        if not classifier.is_trained:
            print("ERROR: Classifier not trained!")
            return
        
        # =====================================================================
        # SECTION 1: Per-Category Metrics (Precision, Recall, F1)
        # =====================================================================
        print("1. HELD-OUT TEST SET EVALUATION")
        print("-" * 78)
        print(f"   Test Set: {sum(len(q) for q in TEST_QUERIES.values())} queries across 15 categories")
        print(f"   Queries per category: 7")
        print()
        
        # Collect predictions
        all_true = []
        all_pred = []
        all_confidences = []
        category_results = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "confidences": []})
        
        for true_intent, queries in TEST_QUERIES.items():
            for query in queries:
                pred_intent, confidence = classifier.predict(query)
                all_true.append(true_intent)
                all_pred.append(pred_intent)
                all_confidences.append(confidence)
                
                category_results[true_intent]["confidences"].append(confidence)
                
                if pred_intent == true_intent:
                    category_results[true_intent]["tp"] += 1
                else:
                    category_results[true_intent]["fn"] += 1
                    category_results[pred_intent]["fp"] += 1
        
        # Calculate metrics per category
        print("   PER-CATEGORY METRICS:")
        print()
        print(f"   {'Category':<22} {'Precision':>10} {'Recall':>10} {'F1-Score':>10} {'Support':>8}")
        print(f"   {'-'*22} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
        
        total_precision = 0
        total_recall = 0
        total_f1 = 0
        total_support = 0
        
        category_metrics = []
        for intent in sorted(TEST_QUERIES.keys()):
            tp = category_results[intent]["tp"]
            fp = category_results[intent]["fp"]
            fn = category_results[intent]["fn"]
            support = tp + fn  # actual positives
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            category_metrics.append({
                "intent": intent,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": support
            })
            
            print(f"   {intent:<22} {precision:>10.3f} {recall:>10.3f} {f1:>10.3f} {support:>8}")
            
            total_precision += precision * support
            total_recall += recall * support
            total_f1 += f1 * support
            total_support += support
        
        # Weighted averages
        avg_precision = total_precision / total_support
        avg_recall = total_recall / total_support
        avg_f1 = total_f1 / total_support
        
        print(f"   {'-'*22} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
        print(f"   {'WEIGHTED AVERAGE':<22} {avg_precision:>10.3f} {avg_recall:>10.3f} {avg_f1:>10.3f} {total_support:>8}")
        print()
        
        # Overall accuracy
        correct = sum(1 for t, p in zip(all_true, all_pred) if t == p)
        accuracy = correct / len(all_true)
        print(f"   OVERALL ACCURACY: {accuracy:.3f} ({correct}/{len(all_true)} correct)")
        print()
        
        # =====================================================================
        # SECTION 2: Ambiguous Query Analysis
        # =====================================================================
        print()
        print("2. AMBIGUOUS QUERY ANALYSIS (Top-3 Confidence Scores)")
        print("-" * 78)
        print(f"   Testing {len(AMBIGUOUS_QUERIES)} queries with multiple valid interpretations")
        print()
        
        for i, (query, expected_intents) in enumerate(AMBIGUOUS_QUERIES, 1):
            probs = classifier.get_all_probabilities(query)
            sorted_probs = sorted(probs.items(), key=lambda x: -x[1])[:3]
            
            print(f"   Query {i}: \"{query[:60]}{'...' if len(query) > 60 else ''}\"")
            print(f"   Expected categories: {', '.join(expected_intents)}")
            print(f"   Top-3 predictions:")
            
            for rank, (intent, conf) in enumerate(sorted_probs, 1):
                match = "***" if intent in expected_intents else "   "
                bar = "#" * int(conf * 20)
                print(f"      {rank}. {intent:<22} {conf:.3f} [{bar:<20}] {match}")
            
            # Check if any expected intent is in top 3
            top3_intents = [p[0] for p in sorted_probs]
            hits = sum(1 for e in expected_intents if e in top3_intents)
            print(f"   Coverage: {hits}/3 expected intents in top-3")
            print()
        
        # =====================================================================
        # SECTION 3: Confidence Score Distribution
        # =====================================================================
        print()
        print("3. CONFIDENCE SCORE DISTRIBUTION")
        print("-" * 78)
        
        # Add more queries to get better distribution
        extra_queries = [
            "programming tutorials for beginners",
            "how to fix bugs in code",
            "best laptop for developers",
            "python vs javascript",
            "learn coding online free",
        ] * 3  # 15 extra general queries
        
        for q in extra_queries:
            _, conf = classifier.predict(q)
            all_confidences.append(conf)
        
        confidences = np.array(all_confidences)
        
        print(f"   Total queries analyzed: {len(confidences)}")
        print(f"   Confidence threshold: 0.60")
        print()
        print(f"   Distribution Statistics:")
        print(f"      Mean confidence:   {np.mean(confidences):.3f}")
        print(f"      Median confidence: {np.median(confidences):.3f}")
        print(f"      Std deviation:     {np.std(confidences):.3f}")
        print(f"      Min confidence:    {np.min(confidences):.3f}")
        print(f"      Max confidence:    {np.max(confidences):.3f}")
        print()
        
        # Count above/below threshold
        above_threshold = np.sum(confidences >= 0.60)
        below_threshold = np.sum(confidences < 0.60)
        print(f"   Threshold Analysis (0.60):")
        print(f"      Above threshold (confident):     {above_threshold} ({above_threshold/len(confidences)*100:.1f}%)")
        print(f"      Below threshold (self-learning): {below_threshold} ({below_threshold/len(confidences)*100:.1f}%)")
        print()
        
        # Confidence buckets
        print(f"   Confidence Buckets:")
        buckets = [(0.0, 0.3, "Low"), (0.3, 0.5, "Medium-Low"), (0.5, 0.7, "Medium"), 
                   (0.7, 0.85, "High"), (0.85, 1.0, "Very High")]
        for low, high, label in buckets:
            count = np.sum((confidences >= low) & (confidences < high))
            pct = count / len(confidences) * 100
            bar = "#" * int(pct / 2)
            marker = " <-- threshold" if low <= 0.60 < high else ""
            print(f"      {low:.2f}-{high:.2f} ({label:<11}): {count:>3} ({pct:>5.1f}%) [{bar:<25}]{marker}")
        
        # =====================================================================
        # SECTION 4: Generate Histogram
        # =====================================================================
        print()
        print("4. GENERATING CONFIDENCE HISTOGRAM")
        print("-" * 78)
        
        plt.figure(figsize=(10, 6))
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # Create histogram
        n, bins, patches = plt.hist(confidences, bins=20, range=(0, 1), 
                                     edgecolor='black', alpha=0.7, color='steelblue')
        
        # Color bars based on threshold
        for i, patch in enumerate(patches):
            if bins[i] < 0.60:
                patch.set_facecolor('#ff6b6b')  # Red for below threshold
            else:
                patch.set_facecolor('#4ecdc4')  # Teal for above threshold
        
        # Add threshold line
        plt.axvline(x=0.60, color='red', linestyle='--', linewidth=2, label='Threshold (0.60)')
        
        # Labels and title
        plt.xlabel('Confidence Score', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.title('Intent Classifier Confidence Score Distribution\n(Test Set: 120 Queries)', fontsize=14)
        plt.legend(loc='upper left')
        
        # Add annotations
        plt.annotate(f'Below threshold\n{below_threshold} queries\n({below_threshold/len(confidences)*100:.1f}%)', 
                     xy=(0.3, max(n)*0.8), fontsize=10, ha='center',
                     bbox=dict(boxstyle='round', facecolor='#ff6b6b', alpha=0.3))
        plt.annotate(f'Above threshold\n{above_threshold} queries\n({above_threshold/len(confidences)*100:.1f}%)', 
                     xy=(0.8, max(n)*0.8), fontsize=10, ha='center',
                     bbox=dict(boxstyle='round', facecolor='#4ecdc4', alpha=0.3))
        
        plt.tight_layout()
        
        # Save figure
        output_path = os.path.join(os.path.dirname(__file__), 'confidence_histogram.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"   Histogram saved to: {output_path}")
        
        plt.close()
        
        print()
        print("=" * 78)
        print("                      EVALUATION COMPLETE")
        print("=" * 78)
        print()
        print("   Summary:")
        print(f"   - Overall Accuracy: {accuracy:.1%}")
        print(f"   - Weighted F1-Score: {avg_f1:.3f}")
        print(f"   - Mean Confidence: {np.mean(confidences):.3f}")
        print(f"   - Queries triggering self-learning: {below_threshold/len(confidences)*100:.1f}%")
        print()


if __name__ == "__main__":
    evaluate_classifier()
