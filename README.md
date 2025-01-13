# Stamp Paper OCR Processing System

A Flask-based web application for automated processing and validation of stamp papers using OCR (Optical Character Recognition). The system supports both single image processing and batch PDF processing with real-time progress tracking.

## Key Features

- Single image and multi-page PDF processing
- Real-time processing progress tracking via WebSocket
- Automated extraction of:
  - Certificate numbers
  - Reference numbers
  - Denominations
  - State information
  - Stamp validation
- Excel report generation with processing results
- Advanced error handling and recovery mechanisms
- Multiple preprocessing techniques for improved OCR accuracy
- Support for multiple Indian languages using Tesseract OCR

## Technical Stack

- **Backend**: Flask, SocketIO
- **Image Processing**: OpenCV, Tesseract OCR
- **PDF Handling**: pdf2image, Poppler
- **Data Management**: Pandas, OpenPyXL
- **Frontend**: Bootstrap 5, JavaScript
- **Real-time Updates**: Socket.IO

## Requirements

- Python 3.6+
- Tesseract OCR
- Poppler (for PDF processing)
- Other dependencies listed in requirements.txt

## Installation

```bash
git clone <repository-url>
cd stamp-paper-ocr
pip install -r requirements.txt
```

Make sure to install Tesseract OCR and Poppler on your system:
- [Tesseract OCR Installation Guide](https://github.com/UB-Mannheim/tesseract/wiki)
- [Poppler Installation Guide](https://github.com/oschwartz10612/poppler-windows/releases/)

## Usage

1. Start the Flask server
2. Upload single stamp paper images or PDF files containing multiple stamp papers
3. Monitor real-time processing progress
4. View validation results and download Excel reports

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

Note: This project is designed for Indian stamp papers and includes specific validation rules and denomination checks according to Indian standards.
