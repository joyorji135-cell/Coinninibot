import os
import tempfile
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
import requests
import logging

app = Flask(__name__)

# Configuration
GOTENBERG_URL = os.environ.get('GOTENBERG_URL', 'http://localhost:3000')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/convert', methods=['POST'])
def convert_image_to_pdf():
    """Convert uploaded image(s) to PDF"""
    
    # Check if files were uploaded
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'Empty file list'}), 400
    
    # Prepare files for Gotenberg
    gotenberg_files = []
    for file in files:
        if allowed_file(file.filename):
            # Secure filename and create temp file
            filename = secure_filename(file.filename)
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            file.save(temp_path)
            
            # Open for Gotenberg
            gotenberg_files.append(
                ('files', (filename, open(temp_path, 'rb'), 'image/jpeg'))
            )
        else:
            return jsonify({'error': f'Unsupported file type: {file.filename}'}), 400
    
    try:
        # Send to Gotenberg for conversion
        response = requests.post(
            f"{GOTENBERG_URL}/forms/libreoffice/convert",
            files=gotenberg_files,
            timeout=60
        )
        
        # Clean up temp files
        for _, (_, file_obj) in gotenberg_files:
            file_obj.close()
        
        if response.status_code == 200:
            # Return the PDF
            return send_file(
                response.raw,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='converted.pdf'
            )
        else:
            return jsonify({'error': f'Conversion failed: {response.text}'}), 500
            
    except Exception as e:
        logger.error(f"Conversion error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'image-to-pdf-bot'}), 200

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'service': 'Image to PDF Converter Bot',
        'endpoints': {
            '/convert': 'POST - Upload images to convert to PDF',
            '/health': 'GET - Health check'
        },
        'supported_formats': list(ALLOWED_EXTENSIONS)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
