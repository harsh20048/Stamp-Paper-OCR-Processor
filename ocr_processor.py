import cv2
import numpy as np
import pytesseract
import re
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional, List

class StampPaperOCR:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        
        self.valid_denominations = ['20', '50', '100', '200', '500']
        self.states = [
            'ANDHRA PRADESH', 'ARUNACHAL PRADESH', 'ASSAM', 'BIHAR',
            'CHHATTISGARH',  'GUJARAT', 'HARYANA', 'HIMACHAL PRADESH',
            'JHARKHAND', 'KARNATAKA', 'KERALA', 'MADHYA PRADESH', 'MAHARASHTRA',
            'MANIPUR', 'MEGHALAYA', 'MIZORAM', 'NAGALAND', 'ODISHA', 'PUNJAB',
            'RAJASTHAN', 'SIKKIM', 'TAMIL NADU', 'TELANGANA', 'TRIPURA',
            'UTTAR PRADESH', 'UTTARAKHAND', 'WEST BENGAL'
        ]
        
        # Updated ROI map specifically for your stamp paper format
        self.default_roi_map = {
            'certificate_number': ((0.75625, 0.365), (0.99875, 0.44)),  # Adjusted for "34AB 670001" format
            'reference_number': ((0.25, 0.20), (0.35, 0.25)),    # Adjusted for अनुक्रमांक
            'denomination': ((0.0, 0.0), (1.0, 0.15)),           # Top portion for Rs. 100/500
            'state': ((0.005, 0.3725), (0.52375, 0.41375)),                # MAHARASHTRA text
            'stamp': ((0.7, 0.35), (0.95, 0.55))                # Stamp area
        }
        
        self.roi_map = self.default_roi_map.copy()
        
        # Special patterns for your stamp paper format
        self.state_patterns = {
            'MAHARASHTRA': [r'MAHARASHTRA', r'महाराष्ट्र'],
            'GUJARAT': [r'GUJARAT', r'गुजरात'],
            'KARNATAKA': [r'KARNATAKA', r'कर्नाटक'],  # Added missing comma
            'BIHAR': [r'BIHAR', r'बिहार']
        }

    def preprocess_image(self, image: np.ndarray) -> Optional[np.ndarray]:
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Enhanced CLAHE parameters
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            gray = clahe.apply(gray)
            
            # Stronger denoising
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # Binary thresholding instead of adaptive for clearer text
            _, thresh = cv2.threshold(denoised, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return thresh
        except Exception as e:
            logging.error(f"Preprocessing error: {str(e)}")
            return None

    def detect_text_regions(self, image: np.ndarray) -> Dict:
        height, width = image.shape[:2]
        config = '--oem 3 --psm 11 -l eng+mar'  # Added Marathi language
        data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
        
        regions = {
            'certificate_number': None,
            'reference_number': None,
            'denomination': None,
            'state': None,
            'stamp': self.default_roi_map['stamp']
        }
        
        for i in range(len(data['text'])):
            text = data['text'][i].upper().strip()
            if not text:
                continue
                
            conf = int(data['conf'][i])
            if conf < 50:  # Lowered confidence threshold
                continue
                
            x = data['left'][i] / width
            y = data['top'][i] / height
            w = data['width'][i] / width
            h = data['height'][i] / height
            
            # Updated patterns for certificate number
            if re.search(r'\d{2}[A-Z]{2}\s*\d{6}|\d{2}[A-Z]{2}\d{6}', text):
                regions['certificate_number'] = ((x-0.02, y-0.02), (x+w+0.02, y+h+0.02))
            
            # Updated pattern for reference number
            if re.search(r'\d{7}|\d{6}', text) and x < 0.5:
                regions['reference_number'] = ((x-0.02, y-0.02), (x+w+0.02, y+h+0.02))
            
            if any(state in text for state in self.states):
                regions['state'] = ((x-0.02, y-0.02), (x+w+0.02, y+h+0.02))
            
            # Enhanced denomination detection
            if any(d in text for d in self.valid_denominations) or 'RUPEES' in text or 'RS' in text:
                regions['denomination'] = ((0, 0), (1, y+h+0.1))

        return regions

    def detect_denomination(self, image: np.ndarray) -> Optional[str]:
        try:
            text = ""
            # Multiple OCR passes with different configurations
            configs = [
                '--oem 3 --psm 6 -l eng+mar',
                '--oem 3 --psm 7 -l eng+mar',
                '--oem 3 --psm 3 -l eng+mar'
            ]
            
            for config in configs:
                roi = self.extract_roi_text(image, self.roi_map['denomination'], config)
                text += " " + roi.upper()
            
            # Enhanced patterns for denomination
            denomination_patterns = {
                '500': [r'(?:RS\.?|₹|रु|रू)\s*500\b', r'\b500\s*(?:RUPEES)?\b', r'FIVE\s*HUNDRED', r'पाचशे'],
                '100': [r'(?:RS\.?|₹|रु|रू)\s*100\b', r'\b100\s*(?:RUPEES)?\b', r'ONE\s*HUNDRED', r'शंभर'],
                '50': [r'(?:RS\.?|₹|रु|रू)\s*50\b', r'\b50\s*(?:RUPEES)?\b', r'FIFTY'],
                '20': [r'(?:RS\.?|₹|रु|रू)\s*20\b', r'\b20\s*(?:RUPEES)?\b', r'TWENTY']
            }
            
            for denom, patterns in denomination_patterns.items():
                if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                    return denom
            
            return None
        except Exception as e:
            logging.error(f"Denomination detection error: {str(e)}")
            return None

    def extract_roi_text(self, image: np.ndarray, roi_coords: Tuple, config: str) -> str:
        try:
            height, width = image.shape[:2]
            (x1_ratio, y1_ratio), (x2_ratio, y2_ratio) = roi_coords
            
            x1 = int(x1_ratio * width)
            y1 = int(y1_ratio * height)
            x2 = int(x2_ratio * width)
            y2 = int(y2_ratio * height)
            
            roi = image[y1:y2, x1:x2]
            roi = cv2.resize(roi, None, fx=2.0, fy=2.0)  # Increased scaling factor
            
            return pytesseract.image_to_string(roi, config=config).strip()
            
        except Exception as e:
            logging.error(f"ROI extraction error: {str(e)}")
            return ""

    def extract_numbers(self, image: np.ndarray) -> Tuple[Optional[str], Optional[str]]:
        try:
            # Multiple OCR passes for certificate number
            cert_configs = [
                '--oem 3 --psm 6 -l eng',
                '--oem 3 --psm 7 -l eng',
                '--oem 3 --psm 8 -l eng'
            ]
            
            cert_text = ""
            for config in cert_configs:
                cert_text += " " + self.extract_roi_text(image, self.roi_map['certificate_number'], config)
            
            # Enhanced pattern for certificate number (e.g., "34AB 670001")
            cert_patterns = [
                r'(\d{2}[A-Z]{2}\s*\d{6})',
                r'([A-Z]{2}\s*\d{6})',
                r'(\d{2}\s*[A-Z]{2}\s*\d{6})'
            ]
            
            cert_num = None
            for pattern in cert_patterns:
                match = re.search(pattern, cert_text.upper())
                if match:
                    cert_num = match.group(1)
                    break
            
            # Extract reference number
            ref_text = self.extract_roi_text(image, self.roi_map['reference_number'], '--oem 3 --psm 6 -l eng')
            ref_match = re.search(r'(\d{6,7})', ref_text)
            ref_num = ref_match.group(1) if ref_match else None
            
            return cert_num, ref_num
        except Exception as e:
            logging.error(f"Number extraction error: {str(e)}")
            return None, None

    def detect_stamp(self, image: np.ndarray) -> bool:
        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Expanded color ranges for purple/blue stamps
            lower_purple = np.array([130, 30, 30])
            upper_purple = np.array([170, 255, 255])
            lower_blue = np.array([90, 30, 30])
            upper_blue = np.array([130, 255, 255])
            
            purple_mask = cv2.inRange(hsv, lower_purple, upper_purple)
            blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
            combined_mask = cv2.bitwise_or(purple_mask, blue_mask)
            
            # Get stamp region
            height, width = image.shape[:2]
            stamp_coords = self.roi_map['stamp']
            x1 = int(stamp_coords[0][0] * width)
            y1 = int(stamp_coords[0][1] * height)
            x2 = int(stamp_coords[1][0] * width)
            y2 = int(stamp_coords[1][1] * height)
            
            stamp_roi = combined_mask[y1:y2, x1:x2]
            
            # Calculate stamp presence
            total_pixels = stamp_roi.shape[0] * stamp_roi.shape[1]
            ink_pixels = cv2.countNonZero(stamp_roi)
            ink_percentage = (ink_pixels / total_pixels) * 100
            
            return ink_percentage > 1.0  # Lowered threshold
            
        except Exception as e:
            logging.error(f"Stamp detection error: {str(e)}")
            return False

    def process_image(self, image_path: str) -> Optional[Dict]:
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Failed to load image")
            
            processed = self.preprocess_image(image)
            if processed is None:
                raise ValueError("Failed to preprocess image")
            
            # Update ROI regions based on detected text
            detected_regions = self.detect_text_regions(processed)
            for key, value in detected_regions.items():
                if value:
                    self.roi_map[key] = value
                    
            state_text = self.extract_roi_text(processed, self.roi_map['state'], '--oem 3 --psm 6 -l eng+mar')
            state = 'MADHYA PRADESH' if 'MADHYA' in state_text.upper() or 'PRADESH' in state_text.upper() else "UNKNOWN"
            detected_state = None
            for state in self.states:
                if state in state_text.upper():
                    detected_state = state
                    break
            
            cert_num, ref_num = self.extract_numbers(processed)
            denomination = self.detect_denomination(processed)
            state = detected_state or "UNKNOWN"  
            has_stamp = self.detect_stamp(image)
            
            results = {
                'certificate_number': cert_num,
                'reference_number': ref_num,
                'denomination': denomination,
                'state': state,
                'has_valid_stamp': has_stamp,
                'processed_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_path': image_path
            }
            
            validation_messages = []
            if not denomination:
                validation_messages.append("Missing denomination")
            if not cert_num:
                validation_messages.append("Missing certificate number")
            if not ref_num:
                validation_messages.append("Missing reference number")
            if not has_stamp:
                validation_messages.append("Missing or invalid stamp")
            if state == "UNKNOWN":
                validation_messages.append("Could not detect state")
                
            results['validation_messages'] = validation_messages
            return results
            
        except Exception as e:
            logging.error(f"Processing error: {str(e)}")
            return None

def main():
    ocr = StampPaperOCR()
    image_path = "stamp_paper.jpg"
    results = ocr.process_image(image_path)
    
    if results:
        print("\nOCR Results:")
        for key, value in results.items():
            if key != 'validation_messages':
                print(f"{key}: {value}")
        
        if results['validation_messages']:
            print("\nValidation Messages:")
            for msg in results['validation_messages']:
                print(f"- {msg}")
    else:
        print("Processing failed")

if __name__ == "__main__":
    main()