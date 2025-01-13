import os
import logging
from datetime import datetime
from flask import render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from app import app, socketio
from .excel_handler import ExcelHandler
from .ocr_processor import StampPaperOCR
from .pdf_processor import BatchProcessor
from config import Config

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

excel_handler = ExcelHandler(Config.PROCESSED_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'})
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            
            # Ensure upload directory exists
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            
            file.save(filepath)
            
            if filename.lower().endswith('.pdf'):
                return process_pdf_file(filepath)
            else:
                return process_image_file(filepath)
        
        return jsonify({'error': 'Invalid file format'})
    
    except Exception as e:
        logger.error(f'Upload error: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)})

def process_pdf_file(pdf_path):
    try:
        processor = BatchProcessor(max_workers=Config.MAX_WORKERS)
        
        def progress_callback(processed, total):
            socketio.emit('processing_progress', {
                'processed': processed,
                'total': total,
                'percentage': (processed / total) * 100
            })
        
        # Check if PDF is readable
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        if not os.access(pdf_path, os.R_OK):
            raise PermissionError(f"Cannot read PDF file: {pdf_path}")
        
        results = processor.process_batch(pdf_path, callback=progress_callback)
        
        for result in results:
            try:
                excel_handler.update_excel(result)
            except Exception as e:
                logger.error(f'Excel update error for page {result.get("page_number")}: {str(e)}')
        
        if not Config.PRESERVE_UPLOADS:
            try:
                os.remove(pdf_path)
            except Exception as e:
                logger.warning(f'Failed to clean up PDF: {str(e)}')
        
        return jsonify({
            'total_pages': len(results),
            'successful': len([r for r in results if not r.get('validation_messages')]),
            'results': results
        })
        
    except Exception as e:
        logger.error(f'PDF processing error: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'error': 'PDF processing failed', 'details': str(e)})

def process_image_file(image_path):
    try:
        processor = StampPaperOCR()
        
        # Check if image is readable
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
            
        if not os.access(image_path, os.R_OK):
            raise PermissionError(f"Cannot read image file: {image_path}")
        
        results = processor.process_image(image_path)
        
        if results is None:
            return jsonify({'error': 'Failed to process the image'})
        
        excel_handler.update_excel(results)
        
        if not Config.PRESERVE_UPLOADS:
            try:
                os.remove(image_path)
            except Exception as e:
                logger.warning(f'Failed to clean up image: {str(e)}')
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f'Image processing error: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Image processing failed', 'details': str(e)})

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'})
            
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Invalid file format. Please upload a PDF file.'})
        
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            
            # Ensure upload directory exists
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            
            file.save(filepath)
            return process_pdf_file(filepath)
        
        return jsonify({'error': 'Invalid file'})
        
    except Exception as e:
        logger.error(f'PDF upload error: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'error': 'PDF processing failed', 'details': str(e)})

@app.route('/statistics')
def get_statistics():
    try:
        stats = excel_handler.get_statistics()
        return jsonify(stats) if stats else jsonify({'error': 'No statistics available'})
    except Exception as e:
        logger.error(f'Statistics error: {str(e)}')
        logger.error(traceback.format_exc())
        return jsonify({'error': 'Failed to get statistics'})

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')