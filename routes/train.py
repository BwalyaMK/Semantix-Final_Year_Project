"""
Training Routes
Handles manual training and self-learning management
"""

from flask import Blueprint, request, jsonify
import json
import csv
from io import StringIO

from config import Config
from services.training_service import TrainingService
from services.learning_service import LearningService
from services.classifier_service import ClassifierService

train_bp = Blueprint('train', __name__)

# Initialize services
training_service = TrainingService()
learning_service = LearningService()
classifier = ClassifierService()


@train_bp.route('/add', methods=['POST'])
def add_training_example():
    """Add a single training example"""
    data = request.get_json()
    question = data.get('question', '').strip()
    intent = data.get('intent', '').strip()
    
    if not question or not intent:
        return jsonify({'error': 'Question and intent are required'}), 400
    
    result = training_service.add_training_example(question, intent)
    
    if result.get('success'):
        return jsonify(result)
    
    return jsonify(result), 400


@train_bp.route('/batch', methods=['POST'])
def add_batch_training():
    """
    Add multiple training examples
    Accepts JSON array or CSV format
    """
    content_type = request.content_type
    
    if 'application/json' in content_type:
        data = request.get_json()
        examples = data.get('examples', [])
    elif 'text/csv' in content_type:
        csv_data = request.data.decode('utf-8')
        reader = csv.DictReader(StringIO(csv_data))
        examples = list(reader)
    else:
        return jsonify({'error': 'Unsupported content type. Use application/json or text/csv'}), 400
    
    if not examples:
        return jsonify({'error': 'No examples provided'}), 400
    
    result = training_service.add_batch_training(examples)
    
    return jsonify(result)


@train_bp.route('/retrain', methods=['POST'])
def retrain_classifier():
    """Retrain the classifier with all training data"""
    result = training_service.retrain_classifier()
    
    if result.get('success'):
        return jsonify(result)
    
    return jsonify(result), 400


@train_bp.route('/data', methods=['GET'])
def get_training_data():
    """Get paginated training data"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    result = training_service.get_training_data(page, per_page)
    
    return jsonify(result)


@train_bp.route('/data/<int:example_id>', methods=['DELETE'])
def delete_training_example(example_id):
    """Delete a training example"""
    result = training_service.delete_training_example(example_id)
    
    if result.get('success'):
        return jsonify(result)
    
    return jsonify(result), 404


@train_bp.route('/export', methods=['GET'])
def export_training_data():
    """Export all training data as JSON"""
    format_type = request.args.get('format', 'json')
    
    data = training_service.export_training_data()
    
    if format_type == 'csv':
        output = StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=['question', 'intent', 'source', 'created_at'])
            writer.writeheader()
            for row in data:
                writer.writerow({
                    'question': row['question'],
                    'intent': row['intent'],
                    'source': row['source'],
                    'created_at': row['created_at']
                })
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=training_data.csv'
        }
    
    return jsonify({'examples': data})


@train_bp.route('/stats', methods=['GET'])
def get_training_stats():
    """Get training data and classifier statistics"""
    training_stats = training_service.get_training_stats()
    learning_stats = learning_service.get_learning_stats()
    
    return jsonify({
        'training': training_stats,
        'learning': learning_stats,
        'intents': Config.INTENT_CATEGORIES
    })


@train_bp.route('/learned', methods=['GET'])
def get_learned_data():
    """Get pending learned data for review"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    result = learning_service.get_pending_learned_data(page, per_page)
    
    return jsonify(result)


@train_bp.route('/learned/<int:learned_id>/verify', methods=['POST'])
def verify_learned(learned_id):
    """Verify or correct a learned example"""
    data = request.get_json()
    correct_intent = data.get('correct_intent')
    
    result = learning_service.verify_learned_example(learned_id, correct_intent)
    
    if result.get('success'):
        return jsonify(result)
    
    return jsonify(result), 400


@train_bp.route('/learned/promote', methods=['POST'])
def promote_learned():
    """Force promotion of learned data and retraining"""
    result = learning_service.force_retrain()
    
    return jsonify({
        'success': True,
        'retrain_result': result
    })


@train_bp.route('/reset', methods=['POST'])
def reset_model():
    """Reset the classifier (requires confirmation)"""
    data = request.get_json()
    confirm = data.get('confirm', False)
    
    if not confirm:
        return jsonify({
            'error': 'Confirmation required. Send {"confirm": true} to reset.'
        }), 400
    
    classifier.reset_model()
    
    # Optionally reseed
    if data.get('reseed', False):
        training_service.initialize_with_seed_data()
    
    return jsonify({
        'success': True,
        'message': 'Classifier reset successfully'
    })


@train_bp.route('/intents', methods=['GET'])
def get_intents():
    """Get available intent categories"""
    return jsonify({
        'intents': Config.INTENT_CATEGORIES
    })
