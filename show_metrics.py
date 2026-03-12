"""
Classifier Training Metrics Display Script
Shows cross-validation scores, training examples, and class distribution
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from database.models import TrainingData, LearnedData
from services.classifier_service import ClassifierService
from services.training_service import TrainingService
from collections import Counter

def display_metrics():
    print("=" * 70)
    print("           SEMANTIX - CLASSIFIER TRAINING METRICS")
    print("=" * 70)
    print()
    
    with app.app_context():
        # Get training data statistics
        training_examples = TrainingData.query.all()
        total_examples = len(training_examples)
        
        print("1. TRAINING DATA SUMMARY")
        print("-" * 70)
        print(f"   Total Training Examples: {total_examples}")
        print()
        
        # Class distribution
        intent_counts = Counter([ex.intent for ex in training_examples])
        source_counts = Counter([ex.source for ex in training_examples])
        
        print("2. CLASS DISTRIBUTION (by Intent)")
        print("-" * 70)
        print(f"   {'Intent Category':<25} {'Count':>8} {'Percentage':>12}")
        print(f"   {'-'*25} {'-'*8} {'-'*12}")
        
        for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
            pct = (count / total_examples) * 100
            print(f"   {intent:<25} {count:>8} {pct:>11.1f}%")
        
        print(f"   {'-'*25} {'-'*8} {'-'*12}")
        print(f"   {'TOTAL':<25} {total_examples:>8} {'100.0%':>12}")
        print()
        
        print("3. SOURCE DISTRIBUTION")
        print("-" * 70)
        print(f"   {'Source':<25} {'Count':>8} {'Percentage':>12}")
        print(f"   {'-'*25} {'-'*8} {'-'*12}")
        
        for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            pct = (count / total_examples) * 100
            print(f"   {source:<25} {count:>8} {pct:>11.1f}%")
        
        print()
        
        # Get classifier service and check if trained
        classifier = ClassifierService()
        
        print("4. CLASSIFIER STATUS")
        print("-" * 70)
        print(f"   Model Loaded: {classifier.is_trained}")
        print(f"   Model Path: models/classifier.pkl")
        
        if classifier.is_trained and hasattr(classifier, 'pipeline') and classifier.pipeline is not None:
            print(f"   Number of Classes: {len(classifier.pipeline.classes_)}")
            print(f"   Classes: {list(classifier.pipeline.classes_)}")
        print()
        
        # Retrain and show cross-validation metrics
        print("5. RETRAINING CLASSIFIER (with Cross-Validation)")
        print("-" * 70)
        print("   Training in progress...")
        print()
        
        training_service = TrainingService()
        result = training_service.retrain_classifier()
        
        if result.get('success'):
            print(f"   ✓ Training Successful!")
            print()
            print(f"   Training Samples Used: {result.get('training_samples', 'N/A')}")
            print(f"   Number of Classes: {result.get('num_classes', len(result.get('classes', [])))}")
            print(f"   Cross-Validation Score: {result.get('cv_score', 'N/A'):.4f}")
            print(f"   Cross-Validation Accuracy: {result.get('cv_score', 0) * 100:.2f}%")
            print()
            print("   Classes Trained:")
            for i, cls in enumerate(result.get('classes', []), 1):
                print(f"      {i:2}. {cls}")
        else:
            print(f"   ✗ Training Failed: {result.get('error', 'Unknown error')}")
        
        print()
        
        # Learned data statistics
        learned_data = LearnedData.query.all()
        verified_count = sum(1 for ld in learned_data if ld.verified)
        promoted_count = sum(1 for ld in learned_data if ld.added_to_training)
        
        print("6. SELF-LEARNING STATISTICS")
        print("-" * 70)
        print(f"   Total Learned Examples: {len(learned_data)}")
        print(f"   Verified Examples: {verified_count}")
        print(f"   Promoted to Training: {promoted_count}")
        print(f"   Pending Review: {len(learned_data) - verified_count}")
        print()
        
        print("=" * 70)
        print("                    END OF METRICS REPORT")
        print("=" * 70)

if __name__ == "__main__":
    display_metrics()
