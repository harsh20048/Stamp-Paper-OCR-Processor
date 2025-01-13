# Stamp-Paper-OCR-Processor
A Flask-based web application for automated processing and validation of stamp papers using OCR (Optical Character Recognition). The system can process both single images and batch PDF files, extracting key information such as certificate numbers, reference numbers, denominations, state details, and stamp validations.
Key Features

Single image and multi-page PDF processing capabilities
Robust OCR processing with Tesseract
Advanced image preprocessing for improved accuracy
Real-time processing progress updates via WebSocket
Excel report generation with validation results
Support for multiple Indian states and languages
Error handling and automatic retries
Backup and recovery mechanisms
Multi-threaded batch processing
Web-based user interface with Bootstrap

Technical Stack

Flask & Flask-SocketIO for web server and real-time updates
OpenCV for image processing
Tesseract OCR for text extraction
pandas for data handling
pdf2image for PDF conversion
Poppler for PDF processing
Bootstrap for frontend styling

Core Functionalities

Image enhancement and preprocessing
Automatic ROI (Region of Interest) detection
Stamp validation using color detection
Multi-language support (English + Marathi)
Denomination validation
Certificate and reference number extraction
State detection
Detailed validation reporting
Excel-based result storage

This application is particularly useful for organizations that need to process and validate large volumes of stamp papers while maintaining accuracy and efficiency.
