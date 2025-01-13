import pandas as pd
import os
import logging
import traceback
from datetime import datetime
import time
from pathlib import Path
import tempfile
import shutil

class ExcelHandler:
    def __init__(self, processed_folder, excel_filename="stamp_paper_results.xlsx"):
        self.processed_folder = processed_folder
        self.excel_filename = excel_filename
        self.temp_dir = None
        self.excel_path = None
        self.retries = 3
        self.retry_delay = 0.5
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Initialize paths
        self._initialize_paths()

    def _initialize_paths(self):
        """Initialize all possible paths for Excel file storage"""
        possible_paths = [
            # Primary location
            os.path.join(self.processed_folder, self.excel_filename),
            # User's Documents folder
            os.path.join(os.path.expanduser('~'), 'Documents', self.excel_filename),
            # Temp directory
            os.path.join(tempfile.gettempdir(), self.excel_filename),
            # Current working directory
            os.path.join(os.getcwd(), self.excel_filename)
        ]

        # Try each path until we find one we can write to
        for path in possible_paths:
            if self._test_path(path):
                self.excel_path = path
                self.logger.info(f"Successfully initialized Excel path: {path}")
                return

        # If no paths work, create a temporary directory as last resort
        self.temp_dir = tempfile.mkdtemp()
        self.excel_path = os.path.join(self.temp_dir, self.excel_filename)
        self.logger.warning(f"Using temporary directory for Excel file: {self.temp_dir}")

    def _test_path(self, path):
        """Test if we can write to the given path"""
        try:
            directory = os.path.dirname(path)
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            # Test file creation
            test_path = os.path.join(directory, '.test_write')
            try:
                with open(test_path, 'w') as f:
                    f.write('test')
                os.remove(test_path)
                return True
            except Exception:
                return False

        except Exception:
            return False

    def _create_backup(self):
        """Create backup of existing Excel file"""
        if os.path.exists(self.excel_path):
            try:
                backup_path = f"{self.excel_path}.bak"
                shutil.copy2(self.excel_path, backup_path)
                self.logger.info(f"Created backup at: {backup_path}")
            except Exception as e:
                self.logger.warning(f"Failed to create backup: {str(e)}")

    def _write_with_retry(self, df, max_retries=None, delay=None):
        """Write DataFrame to Excel with retry mechanism"""
        retries = max_retries or self.retries
        delay = delay or self.retry_delay
        last_error = None
        
        for attempt in range(retries):
            try:
                # Create backup before writing
                self._create_backup()
                
                # Try writing to temporary file first
                temp_file = f"{self.excel_path}.tmp"
                df.to_excel(temp_file, index=False, engine='openpyxl')
                
                # If successful, rename to actual file
                if os.path.exists(self.excel_path):
                    os.remove(self.excel_path)
                os.rename(temp_file, self.excel_path)
                return True
                
            except PermissionError as e:
                last_error = e
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
            except Exception as e:
                self.logger.error(f"Write error on attempt {attempt + 1}: {str(e)}")
                last_error = e
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                
        if last_error:
            # If all retries failed, try writing to alternate location
            try:
                alt_path = os.path.join(tempfile.gettempdir(), f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.excel_filename}")
                df.to_excel(alt_path, index=False, engine='openpyxl')
                self.logger.warning(f"Wrote to alternate location: {alt_path}")
                self.excel_path = alt_path
                return True
            except Exception as e:
                raise Exception(f"Failed to write to alternate location: {str(e)}") from last_error

    def read_excel(self):
        """Read Excel with corruption handling"""
        try:
            if os.path.exists(self.excel_path):
                try:
                    return pd.read_excel(self.excel_path, engine='openpyxl')
                except Exception as e:
                    self.logger.warning(f"Error reading Excel file: {str(e)}")
                    # Try reading from backup
                    backup_path = f"{self.excel_path}.bak"
                    if os.path.exists(backup_path):
                        try:
                            return pd.read_excel(backup_path, engine='openpyxl')
                        except Exception:
                            pass
            
            # If no existing file or backup, return empty DataFrame
            return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"Error reading Excel: {str(e)}")
            return pd.DataFrame()

    def update_excel(self, results):
        """Update Excel with new results"""
        try:
            if not isinstance(results, dict):
                raise ValueError("Results must be a dictionary")

            # Read existing data
            existing_df = self.read_excel()
            
            # Prepare results
            results_copy = results.copy()
            
            # Convert validation messages to string
            if 'validation_messages' in results_copy:
                if isinstance(results_copy['validation_messages'], list):
                    results_copy['validation_messages'] = '; '.join(results_copy['validation_messages'])
            
            # Add metadata
            results_copy.update({
                'processing_status': 'Success' if not results_copy.get('validation_messages') else 'Warning',
                'upload_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Update DataFrame
            new_row = pd.DataFrame([results_copy])
            updated_df = pd.concat([existing_df, new_row], ignore_index=True)
            
            # Write with retry mechanism
            success = self._write_with_retry(updated_df)
            
            if success:
                self.logger.info("Successfully updated Excel file")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to update Excel: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise

    def __del__(self):
        """Cleanup temporary directory if it exists"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                self.logger.error(f"Failed to cleanup temporary directory: {str(e)}")