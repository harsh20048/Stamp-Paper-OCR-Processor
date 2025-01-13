import pdf2image
import tempfile
import os
import cv2
import numpy as np
import shutil
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
import logging
import subprocess
from pathlib import Path
from .ocr_processor import StampPaperOCR

class PDFProcessor:
    def __init__(self, dpi=300):
        self.dpi = dpi
        self.logger = logging.getLogger(__name__)
        
    def check_poppler_installation(self) -> bool:
        """Verify Poppler installation with enhanced path checking"""
        try:
            if os.name == 'nt':  # Windows
                # Check if pdftoppm is directly accessible
                poppler_path = shutil.which('pdftoppm')
                if poppler_path:
                    return True
                    
                # Check common Windows installation paths
                possible_paths = [
                    r'C:\Program Files\poppler\Library\bin',
                    r'C:\Program Files\poppler-xx\bin',
                    r'C:\Users\HARSH\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin',
                    r'C:\Program Files (x86)\poppler-xx\bin',
                    r'C:\poppler\Library\bin',
                    os.path.expanduser('~\\AppData\\Local\\poppler-xx\\bin')
                ]
                
                # Replace -xx with possible version numbers
                expanded_paths = []
                for path in possible_paths:
                    if '-xx' in path:
                        for i in range(0, 30):  # Check versions 0-29
                            expanded_paths.append(path.replace('-xx', f'-{i:02d}'))
                    expanded_paths.append(path)
                
                # Add paths to system PATH temporarily
                original_path = os.environ.get('PATH', '')
                for path in expanded_paths:
                    if os.path.exists(path):
                        os.environ['PATH'] = f"{path};{original_path}"
                        if shutil.which('pdftoppm'):
                            return True
                
                # Check if pdftoppm.exe exists in any of the paths
                for path in expanded_paths:
                    if os.path.exists(os.path.join(path, 'pdftoppm.exe')):
                        os.environ['PATH'] = f"{path};{original_path}"
                        return True
                        
                return False
            else:  # Linux/Mac
                result = subprocess.run(['which', 'pdftoppm'], 
                                     capture_output=True, 
                                     text=True)
                return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Error checking Poppler installation: {str(e)}")
            return False

    def convert_pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convert PDF pages to images with enhanced error handling"""
        temp_dir = None
        try:
            # Verify Poppler installation
            if not self.check_poppler_installation():
                raise RuntimeError(
                    "Poppler is not installed or not found in PATH. "
                    "Please install Poppler and ensure it's in your system PATH. "
                    "Installation instructions:\n"
                    "1. Download from https://github.com/oschwartz10612/poppler-windows/releases/\n"
                    "2. Extract to C:\\Program Files\\poppler\n"
                    "3. Add C:\\Program Files\\poppler\\Library\\bin to system PATH\n"
                    "4. Restart your application"
                )

            # Create temporary directory first
            temp_dir = tempfile.mkdtemp()
            self.logger.info(f"Created temporary directory: {temp_dir}")

            # Verify PDF exists and is readable
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            if not os.access(pdf_path, os.R_OK):
                raise PermissionError(f"Cannot read PDF file: {pdf_path}")

            # Convert PDF to images
            images = pdf2image.convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt='jpg',
                thread_count=4,
                poppler_path=self._get_poppler_path()
            )
            
            if not images:
                raise ValueError("No images were extracted from the PDF")

            image_paths = []
            for i, image in enumerate(images):
                image_path = os.path.join(temp_dir, f'page_{i+1}.jpg')
                image.save(image_path, 'JPEG', quality=95)
                image_paths.append(image_path)

            return image_paths
            
        except Exception as e:
            self.logger.error(f"PDF conversion error: {str(e)}")
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    self.logger.error(f"Failed to clean up temporary directory: {str(cleanup_error)}")
            raise
    
    def _get_poppler_path(self) -> Optional[str]:
        """Get the Poppler binary path"""
        if os.name == 'nt':  # Windows
            possible_paths = [
                r'C:\Program Files\poppler\Library\bin',
                r'C:\Program Files (x86)\poppler\Library\bin',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    return path
        return None

    def cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary files"""
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            self.logger.error(f"Failed to clean up temporary directory: {str(e)}")

class EnhancedStampPaperOCR(StampPaperOCR):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
    def enhance_image_quality(self, image: np.ndarray) -> np.ndarray:
        """Apply advanced image enhancement techniques"""
        try:
            # Convert to LAB color space
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            
            # Merge channels
            lab = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # Apply sharpening
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            enhanced = cv2.filter2D(enhanced, -1, kernel)
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Image enhancement error: {str(e)}")
            return image

    def process_image_enhanced(self, image_path: str) -> Optional[Dict]:
        """Enhanced image processing with improved accuracy"""
        try:
            # Verify image exists and is readable
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            if not os.access(image_path, os.R_OK):
                raise PermissionError(f"Cannot read image file: {image_path}")

            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Failed to load image")
                
            enhanced = self.enhance_image_quality(image)
            processed = self.preprocess_image(enhanced)
            
            if processed is None:
                raise ValueError("Failed to preprocess image")
            
            results_list = []
            preprocess_methods = [
                lambda img: cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
                lambda img: cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2),
                lambda img: processed
            ]
            
            for preprocess_method in preprocess_methods:
                processed_img = preprocess_method(cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY))
                result = self.process_image(image_path)
                if result:
                    results_list.append(result)
            
            if results_list:
                best_result = max(results_list, key=lambda x: len(x.get('validation_messages', [])) == 0)
                return best_result
                
            return None
            
        except Exception as e:
            self.logger.error(f"Enhanced processing error: {str(e)}")
            return None

class BatchProcessor:
    def __init__(self, max_workers=4):
        self.max_workers = max_workers
        self.pdf_processor = PDFProcessor()
        self.ocr_processor = EnhancedStampPaperOCR()
        self.logger = logging.getLogger(__name__)
        
    def process_batch(self, pdf_path: str, callback=None) -> List[Dict]:
        """Process multiple stamp papers from PDF"""
        temp_dir = None
        try:
            # Verify Poppler installation first
            if not self.pdf_processor.check_poppler_installation():
                raise RuntimeError(
                    "Poppler is not installed or not found in PATH. "
                    "Please install Poppler and ensure it's in your system PATH."
                )

            # Convert PDF to images
            image_paths = self.pdf_processor.convert_pdf_to_images(pdf_path)
            temp_dir = os.path.dirname(image_paths[0]) if image_paths else None
            results = []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_path = {
                    executor.submit(self.ocr_processor.process_image_enhanced, path): path 
                    for path in image_paths
                }
                
                for future in future_to_path:
                    path = future_to_path[future]
                    try:
                        result = future.result()
                        if result:
                            result['page_number'] = image_paths.index(path) + 1
                            results.append(result)
                            
                            if callback:
                                callback(len(results), len(image_paths))
                                
                    except Exception as e:
                        self.logger.error(f"Error processing page {path}: {str(e)}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch processing error: {str(e)}")
            raise
            
        finally:
            # Cleanup temporary directory in finally block
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    self.logger.error(f"Failed to cleanup temporary directory: {str(e)}")