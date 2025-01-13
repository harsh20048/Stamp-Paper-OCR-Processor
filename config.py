import os
from pathlib import Path

class Config:
    # Secret key for session management and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Base directory of the application
    BASE_DIR = Path(__file__).resolve().parent
    
    # Upload configurations
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    PROCESSED_FOLDER = os.path.join(BASE_DIR, 'processed')
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    
    # OCR configurations
    TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe' if os.name == 'nt' else '/usr/bin/tesseract'
    
    # Processing configurations
    MAX_WORKERS = 4  # Maximum number of parallel processing workers
    PDF_DPI = 300   # DPI for PDF conversion
    
    # Database configurations
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Logging configuration
    LOG_FILE = os.path.join(BASE_DIR, 'app.log')
    LOG_LEVEL = 'DEBUG'
    
    # Application settings
    DEBUG = True
    TESTING = False
    
    # File processing settings
    PRESERVE_UPLOADS = True
    EXCEL_PREFIX = 'stamp_paper_results_'

    @staticmethod
    def init_app(app):
        """Initialize application configuration"""
        directories = {
            'static': os.path.join(app.root_path, 'static'),
            'css': os.path.join(app.root_path, 'static', 'css'),
            'js': os.path.join(app.root_path, 'static', 'js'),
            'uploads': Config.UPLOAD_FOLDER,
            'processed': Config.PROCESSED_FOLDER
        }
        
        for dir_name, dir_path in directories.items():
            try:
                os.makedirs(dir_path, exist_ok=True)
                test_file = os.path.join(dir_path, '.write_test')
                try:
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                except Exception as e:
                    print(f"Warning: Directory {dir_name} is not writable: {e}")
                    if dir_name in ['uploads', 'processed']:
                        raise
            except Exception as e:
                print(f"Error setting up {dir_name} directory: {e}")
                if dir_name in ['uploads', 'processed']:
                    raise

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    
class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    UPLOAD_FOLDER = os.path.join(Config.BASE_DIR, 'test_uploads')
    PROCESSED_FOLDER = os.path.join(Config.BASE_DIR, 'test_processed')
    
class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    PRESERVE_UPLOADS = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}