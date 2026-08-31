from flask import Blueprint, request, jsonify
import os
from werkzeug.utils import secure_filename
from pathlib import Path
from image_handler import BlogImageOrchestrator
from dotenv import load_dotenv

load_dotenv()

images_bp = Blueprint('images', __name__, url_prefix='/api/images')

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE_MB', 50)) * 1024 * 1024

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.getenv('TEMP_IMAGE_DIR', './temp_images'), exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def check_file_size(file):
    """Check if file size is within limits"""
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    return file_size <= MAX_UPLOAD_SIZE


@images_bp.route('/upload', methods=['POST'])
def upload_images():
    """
    Upload images for blog post
    Expects multipart/form-data with:
    - featured_image: single image file (optional)
    - article_images: multiple image files (optional)
    - topic: blog topic (required)
    - products: product keywords (optional)
    """
    try:
        # Get form data
        topic = request.form.get('topic', '')
        products = request.form.get('products', '').split(',') if request.form.get('products') else []

        if not topic:
            return jsonify({'status': 'error', 'message': 'Blog topic is required'}), 400

        uploaded_files = []
        orchestrator = BlogImageOrchestrator()

        # Handle featured image
        if 'featured_image' in request.files:
            file = request.files['featured_image']
            if file and allowed_file(file.filename) and check_file_size(file):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                uploaded_files.append(filepath)
            elif file and not allowed_file(file.filename):
                return jsonify({'status': 'error', 'message': 'Featured image type not allowed'}), 400
            elif file and not check_file_size(file):
                return jsonify({'status': 'error', 'message': f'Featured image exceeds {os.getenv("MAX_UPLOAD_SIZE_MB", 50)}MB limit'}), 400

        # Handle article images
        if 'article_images' in request.files:
            files = request.files.getlist('article_images')
            for file in files:
                if file and allowed_file(file.filename) and check_file_size(file):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    uploaded_files.append(filepath)
                elif file and not allowed_file(file.filename):
                    return jsonify({'status': 'error', 'message': f'Image {file.filename} type not allowed'}), 400
                elif file and not check_file_size(file):
                    return jsonify({'status': 'error', 'message': f'Image {file.filename} exceeds {os.getenv("MAX_UPLOAD_SIZE_MB", 50)}MB limit'}), 400

        # Process images with orchestrator
        result = orchestrator.process_blog_images(
            uploaded_files,
            topic,
            products
        )

        # Clean up uploaded files
        for filepath in uploaded_files:
            try:
                os.remove(filepath)
            except:
                pass

        return jsonify({
            'status': 'success',
            'message': 'Images processed successfully',
            'data': result
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@images_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        orchestrator = BlogImageOrchestrator()
        
        # Check Shopify
        shopify_ok = orchestrator.shopify_handler.store_url is not None
        
        # Check Figma
        figma_ok = orchestrator.figma_generator.api_token is not None
        
        return jsonify({
            'status': 'healthy' if (shopify_ok and figma_ok) else 'degraded',
            'shopify': 'connected' if shopify_ok else 'missing_credentials',
            'figma': 'connected' if figma_ok else 'missing_credentials'
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@images_bp.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up temporary image directory"""
    try:
        temp_dir = os.getenv('TEMP_IMAGE_DIR', './temp_images')
        
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                filepath = os.path.join(temp_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        
        return jsonify({
            'status': 'success',
            'message': 'Temporary files cleaned up'
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
