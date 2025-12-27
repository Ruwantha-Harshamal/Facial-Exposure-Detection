// Privacy Exposure Checker - Main JavaScript

// DOM Elements
const uploadArea = document.getElementById('upload-area');
const photoInput = document.getElementById('photo-input');
const browseBtn = document.getElementById('browse-btn');
const uploadForm = document.getElementById('upload-form');
const previewArea = document.getElementById('preview-area');
const previewImage = document.getElementById('preview-image');
const loadingArea = document.getElementById('loading-area');
const resultsArea = document.getElementById('results-area');
const cancelBtn = document.getElementById('cancel-btn');

let selectedFile = null;

// Load stats on page load
window.addEventListener('DOMContentLoaded', loadStats);

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('stats-faces').textContent = 
                data.stats.total_faces.toLocaleString();
            document.getElementById('stats-websites').textContent = 
                data.stats.total_websites.toLocaleString();
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Browse button click
browseBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation(); // Prevent event from bubbling to upload area
    photoInput.click();
});

// Upload area click
uploadArea.addEventListener('click', (e) => {
    // Don't trigger if clicking the browse button or if it's a form element
    if (e.target === browseBtn || browseBtn.contains(e.target)) {
        return;
    }
    photoInput.click();
});

// File input change
photoInput.addEventListener('change', (e) => {
    handleFile(e.target.files[0]);
});

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    handleFile(e.dataTransfer.files[0]);
});

// Handle file selection
function handleFile(file) {
    if (!file) return;
    
    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
        alert('Please upload a JPG, JPEG, or PNG image');
        return;
    }
    
    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
        alert('File size must be less than 10MB');
        return;
    }
    
    selectedFile = file;
    
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        uploadArea.style.display = 'none';
        previewArea.style.display = 'block';
        resultsArea.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

// Cancel button
cancelBtn.addEventListener('click', () => {
    selectedFile = null;
    photoInput.value = '';
    uploadArea.style.display = 'block';
    previewArea.style.display = 'none';
    resultsArea.style.display = 'none';
});

// Form submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!selectedFile) {
        alert('Please select a photo first');
        return;
    }
    
    // Show loading
    previewArea.style.display = 'none';
    loadingArea.style.display = 'block';
    resultsArea.style.display = 'none';
    
    // Prepare form data
    const formData = new FormData();
    formData.append('photo', selectedFile);
    
    try {
        // Upload and search
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        // Hide loading
        loadingArea.style.display = 'none';
        
        if (data.success) {
            displayResults(data);
        } else {
            displayError(data.error || 'An error occurred');
        }
        
    } catch (error) {
        loadingArea.style.display = 'none';
        displayError('Network error: ' + error.message);
    }
});

// Display results
function displayResults(data) {
    resultsArea.style.display = 'block';
    
    if (data.status === 'safe') {
        // No matches found
        resultsArea.innerHTML = `
            <div class="alert alert-success result-safe">
                <h4>✅ Good News!</h4>
                <p class="mb-0">${data.message}</p>
                <small class="text-muted">
                    Searched ${data.total_searched.toLocaleString()} faces in our database.
                </small>
            </div>
            <button class="btn btn-primary w-100 mt-3" onclick="location.reload()">
                Check Another Photo
            </button>
        `;
    } else {
        // Matches found!
        let html = `
            <div class="alert alert-danger">
                <h4>⚠️ Privacy Alert</h4>
                <p class="mb-0">${data.message}</p>
            </div>
        `;
        
        // Display each match
        data.matches.forEach((match, index) => {
            const badgeClass = 
                match.similarity > 0.85 ? 'badge-high' :
                match.similarity > 0.70 ? 'badge-medium' : 'badge-low';
            
            html += `
                <div class="card result-card mb-3">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-auto">
                                <img src="/api/thumbnail/${match.face_id}" 
                                     class="thumbnail-preview"
                                     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22%3E%3Crect fill=%22%23ddd%22 width=%22100%22 height=%22100%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22%3ENo Image%3C/text%3E%3C/svg%3E'">
                            </div>
                            <div class="col">
                                <h5>
                                    Match ${index + 1}
                                    <span class="badge ${badgeClass} similarity-badge ms-2">
                                        ${match.percentage}
                                    </span>
                                </h5>
                                <p class="mb-1">
                                    <strong>Found on:</strong> 
                                    <a href="${match.website_url}" target="_blank" rel="noopener">
                                        ${match.website_name}
                                    </a>
                                </p>
                                <p class="mb-1">
                                    <strong>Image URL:</strong> 
                                    <a href="${match.image_url}" target="_blank" rel="noopener" class="text-truncate d-inline-block" style="max-width: 300px;">
                                        ${match.image_url}
                                    </a>
                                </p>
                                <small class="text-muted">
                                    Scraped: ${new Date(match.scraped_at).toLocaleDateString()}
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `
            <button class="btn btn-primary w-100 mt-3" onclick="location.reload()">
                Check Another Photo
            </button>
        `;
        
        resultsArea.innerHTML = html;
    }
}

// Display error
function displayError(message) {
    resultsArea.style.display = 'block';
    resultsArea.innerHTML = `
        <div class="alert alert-danger">
            <h4>❌ Error</h4>
            <p class="mb-0">${message}</p>
        </div>
        <button class="btn btn-secondary w-100 mt-3" onclick="location.reload()">
            Try Again
        </button>
    `;
}
