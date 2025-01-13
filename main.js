/* static/js/main.js */
document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const singleUploadForm = document.getElementById('singleUploadForm');
    const pdfUploadForm = document.getElementById('pdfUploadForm');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const resultsDiv = document.getElementById('results');

    function displayResults(data, isBatch = false) {
        resultsDiv.style.display = 'block';
        
        if (data.error) {
            resultsDiv.innerHTML = `
                <div class="alert alert-danger">
                    <strong>Error:</strong> ${data.error}
                    ${data.details ? `<br><small>${data.details}</small>` : ''}
                </div>
            `;
            return;
        }

        if (isBatch) {
            // Display batch processing results
            let tableRows = data.results.map((result, index) => `
                <tr>
                    <td>${result.page_number}</td>
                    <td>${result.certificate_number || 'N/A'}</td>
                    <td>${result.reference_number || 'N/A'}</td>
                    <td>${result.denomination || 'N/A'}</td>
                    <td>${result.state || 'N/A'}</td>
                    <td>
                        <span class="badge rounded-pill ${result.has_valid_stamp ? 'bg-success' : 'warning-badge'}">
                            ${result.has_valid_stamp ? 'Valid' : 'Invalid/Missing'}
                        </span>
                    </td>
                    <td>
                        <span class="badge rounded-pill ${result.validation_messages.length === 0 ? 'bg-success' : 'warning-badge'}">
                            ${result.validation_messages.length === 0 ? 'Success' : 'Warning'}
                        </span>
                    </td>
                    <td>${result.validation_messages.join(', ') || 'None'}</td>
                </tr>
            `).join('');

            resultsDiv.innerHTML = `
                <div class="alert alert-info">
                    <h4>Batch Processing Summary:</h4>
                    <p>Total Pages: ${data.total_pages}</p>
                    <p>Successfully Processed: ${data.successful}</p>
                </div>
                <div class="table-responsive">
                    <table class="table results-table">
                        <thead>
                            <tr>
                                <th>Page</th>
                                <th>Certificate Number</th>
                                <th>Reference Number</th>
                                <th>Denomination</th>
                                <th>State</th>
                                <th>Stamp Status</th>
                                <th>Processing Status</th>
                                <th>Messages</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${tableRows}
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            // Display single image results
            resultsDiv.innerHTML = `
                <div class="alert ${data.validation_messages.length === 0 ? 'alert-success' : 'alert-warning'}">
                    <h4>OCR Results:</h4>
                    <div class="ocr-results">
                        <div class="result-item">
                            <span class="result-label">Certificate Number:</span>
                            <span class="result-value">${data.certificate_number || 'Not found'}</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Reference Number:</span>
                            <span class="result-value">${data.reference_number || 'Not found'}</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Denomination:</span>
                            <span class="result-value">${data.denomination || 'Not found'}</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">State:</span>
                            <span class="result-value">${data.state || 'Not found'}</span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Stamp Status:</span>
                            <span class="badge rounded-pill ${data.has_valid_stamp ? 'bg-success' : 'warning-badge'}">
                                ${data.has_valid_stamp ? 'Valid' : 'Invalid/Missing'}
                            </span>
                        </div>
                        <div class="result-item">
                            <span class="result-label">Processing Status:</span>
                            <span class="badge rounded-pill ${data.validation_messages.length === 0 ? 'bg-success' : 'warning-badge'}">
                                ${data.validation_messages.length === 0 ? 'Success' : 'Warning'}
                            </span>
                        </div>
                        ${data.validation_messages.length > 0 ? `
                        <div class="result-item">
                            <span class="result-label">Messages:</span>
                            <span class="result-value">${data.validation_messages.join(', ')}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }
    }

    function handleSubmit(form, url, isBatch = false) {
        const formData = new FormData(form);
        const submitButton = form.querySelector('button[type="submit"]');
        
        submitButton.disabled = true;
        submitButton.innerHTML = 'Processing...';
        
        if (isBatch) {
            progressContainer.style.display = 'block';
            progressBar.style.width = '0%';
            progressText.textContent = 'Starting processing...';
        }
        
        fetch(url, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            displayResults(data, isBatch);
        })
        .catch(error => {
            console.error('Error:', error);
            resultsDiv.style.display = 'block';
            resultsDiv.innerHTML = `
                <div class="alert alert-danger">
                    <strong>Error:</strong> An error occurred while processing the file.
                    <br><small>${error.message}</small>
                </div>
            `;
        })
        .finally(() => {
            submitButton.disabled = false;
            submitButton.innerHTML = isBatch ? 'Process PDF' : 'Process Image';
            if (isBatch) {
                progressContainer.style.display = 'none';
            }
        });
    }

    singleUploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        handleSubmit(this, '/upload', false);
    });

    pdfUploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        handleSubmit(this, '/upload-pdf', true);
    });

    socket.on('processing_progress', function(data) {
        progressBar.style.width = data.percentage + '%';
        progressText.textContent = `Processing: ${data.processed}/${data.total} pages`;
    });
});