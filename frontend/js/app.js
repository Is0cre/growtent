// Main application JavaScript
const API_BASE = window.location.origin;

// Utility functions
const api = {
    async get(endpoint) {
        const response = await fetch(`${API_BASE}${endpoint}`);
        return response.json();
    },
    
    async post(endpoint, data) {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    async put(endpoint, data) {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    async delete(endpoint) {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'DELETE'
        });
        return response.json();
    }
};

// Navigation
document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const page = link.dataset.page;
        showPage(page);
        
        // Update active state
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        
        // Update page title
        document.getElementById('pageTitle').textContent = link.querySelector('span').textContent;
        
        // Close sidebar on mobile
        if (window.innerWidth <= 768) {
            document.getElementById('sidebar').classList.remove('open');
        }
    });
});

function showPage(pageName) {
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.getElementById(`page-${pageName}`).classList.add('active');
    
    // Load page content
    switch(pageName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'projects':
            loadProjects();
            break;
        case 'data-logs':
            loadDataLogs();
            break;
        case 'diary':
            loadDiary();
            break;
        case 'settings':
            loadSettings();
            break;
        case 'timelapse':
            loadTimelapse();
            break;
        case 'plant-health':
            loadPlantHealth();
            break;
        case 'camera':
            loadCamera();
            break;
    }
}

// Menu toggle for mobile
document.getElementById('menuToggle').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
});

// Modal functions
function showModal(content) {
    const modal = document.getElementById('modal');
    document.getElementById('modalBody').innerHTML = content;
    modal.classList.add('show');
}

function hideModal() {
    document.getElementById('modal').classList.remove('show');
}

document.querySelector('.close').addEventListener('click', hideModal);
window.addEventListener('click', (e) => {
    const modal = document.getElementById('modal');
    if (e.target === modal) {
        hideModal();
    }
});

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Format number
function formatNumber(num, decimals = 1) {
    return parseFloat(num).toFixed(decimals);
}

// Show notification
function showNotification(message, type = 'success') {
    // Simple alert for now - could be enhanced with a toast library
    console.log(`${type.toUpperCase()}: ${message}`);
    alert(message);
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    
    // Refresh camera feed periodically
    setInterval(() => {
        const liveCamera = document.getElementById('liveCamera');
        if (liveCamera && liveCamera.offsetParent !== null) {
            liveCamera.src = `/api/camera/live?t=${Date.now()}`;
        }
        
        const mainCamera = document.getElementById('mainCamera');
        if (mainCamera && mainCamera.offsetParent !== null) {
            mainCamera.src = `/api/camera/live?t=${Date.now()}`;
        }
    }, 2000);
});



// Helper function to adjust numeric input values (for +/- spinners)
function adjustValue(inputId, delta) {
    const input = document.getElementById(inputId);
    if (input) {
        const min = parseInt(input.min) || -Infinity;
        const max = parseInt(input.max) || Infinity;
        const newValue = Math.min(max, Math.max(min, parseInt(input.value || 0) + delta));
        input.value = newValue;
    }
}
