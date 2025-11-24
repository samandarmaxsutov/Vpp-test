// ../static/js/utils.js
const API_BASE = 'http://localhost:5000/api';

// ===================== TAB MANAGEMENT =====================
function switchTab(tabName) {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    // Handle click from icon or text
    const clickedItem = event.target.closest('.nav-item');
    if(clickedItem) clickedItem.classList.add('active');

    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');

    // Load tab-specific content
    if (tabName === 'dashboard') loadDashboard();
    if (tabName === 'interfaces') loadInterfaces();
    if (tabName === 'routing') loadRoutes();
    if (tabName === 'acl') loadAcls();
    if (tabName === 'nat') loadNat();

    // --- TRAFFIC MONITOR LOGIC ---
    // If we enter the traffic tab, start the timer
    if (tabName === 'traffic') {
        // Call immediately once
        if (window.updateTrafficStats) window.updateTrafficStats(); 
        
        // Start interval if not running
        if (!window.trafficUpdateInterval) {
            console.log("Starting Traffic Monitor...");
            window.trafficUpdateInterval = setInterval(() => {
                if (window.updateTrafficStats) window.updateTrafficStats();
            }, 2000);
        }
    } else {
        // If we leave the traffic tab, stop the timer to save CPU
        if (window.trafficUpdateInterval) {
            console.log("Stopping Traffic Monitor...");
            clearInterval(window.trafficUpdateInterval);
            window.trafficUpdateInterval = null;
        }
    }
}

// ===================== ALERTS =====================
function showAlert(containerId, message, type = 'success') {
    const container = document.getElementById(containerId);
    if(container) {
        container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
        setTimeout(() => container.innerHTML = '', 4000);
    }
}

// ===================== MODALS =====================
function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}
function openModal(modalId) { // Helper if needed
    document.getElementById(modalId).classList.add('active');
}

// ===================== INITIALIZATION =====================
window.addEventListener('DOMContentLoaded', () => {
    // Load default tab
    loadDashboard();
    
    // Global Refresh for Dashboard widgets
    setInterval(loadDashboard, 5000);
});