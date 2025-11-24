// ========== DASHBOARD ==========

// Global variables for the chart
let dashboardChart = null;
let lastDashTime = Date.now();
let lastTotalRx = 0;
let lastTotalTx = 0;
const MAX_DASH_POINTS = 30; // Keep 60 seconds of history

// Colors
const DASH_COLOR_RX = 'rgba(16, 185, 129, 0.2)'; // Green background
const DASH_BORDER_RX = '#10b981';
const DASH_COLOR_TX = 'rgba(59, 130, 246, 0.2)'; // Blue background
const DASH_BORDER_TX = '#3b82f6';

async function loadDashboard() {
    try {
        // 1. Fetch General Stats (Cards)
        const res = await fetch(`${API_BASE}/dashboard/stats`);
        // Handle 404 or errors gracefully if endpoint doesn't exist yet
        if(res.ok) {
            const data = await res.json();
            document.getElementById('dash-interfaces').textContent = `${data.interfaces.active}/${data.interfaces.total}`;
            document.getElementById('dash-routes').textContent = data.routes;
            document.getElementById('dash-acls').textContent = data.acls;
            document.getElementById('dash-nat').textContent = data.nat_sessions;
        }

        // 2. Trigger Traffic Update
        updateTrafficChart();

    } catch (err) {
        console.error('Failed to load dashboard stats:', err);
    }
}

function initDashboardChart() {
    const ctx = document.getElementById('dashboardChart');
    if (!ctx) return; // Safety check

    dashboardChart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Total Download (RX)',
                    data: [],
                    borderColor: DASH_BORDER_RX,
                    backgroundColor: DASH_COLOR_RX,
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                },
                {
                    label: 'Total Upload (TX)',
                    data: [],
                    borderColor: DASH_BORDER_TX,
                    backgroundColor: DASH_COLOR_TX,
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + ' Mbps';
                        }
                    }
                }
            },
            scales: {
                x: { display: false }, // Hide X axis labels for cleaner look
                y: { 
                    beginAtZero: true, 
                    title: { display: true, text: 'Mbps' },
                    grid: { color: 'rgba(0,0,0,0.05)' }
                }
            },
            animation: { duration: 0 },
            elements: { point: { radius: 0 } } // Hide points for smooth wave look
        }
    });
}

async function updateTrafficChart() {
    // Initialize chart if it doesn't exist
    if (!dashboardChart) {
        initDashboardChart();
    }
    // Safety: If HTML is missing (e.g. user switched tabs), stop
    if (!dashboardChart) return;

    try {
        const res = await fetch(`${API_BASE}/interfaces/stats`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // 1. Aggregate Totals
        let currentTotalRx = 0;
        let currentTotalTx = 0;

        if (Array.isArray(data)) {
            data.forEach(iface => {
                currentTotalRx += iface.rx_bytes;
                currentTotalTx += iface.tx_bytes;
            });
        }

        // 2. Calculate Rates (Mbps)
        const now = Date.now();
        const timeDiff = (now - lastDashTime) / 1000; // seconds
        
        // Avoid division by zero or huge spikes on first load
        if (timeDiff > 0 && lastTotalRx > 0) {
            const deltaRx = currentTotalRx - lastTotalRx;
            const deltaTx = currentTotalTx - lastTotalTx;

            // (Bytes * 8) / (Time * 1M) = Mbps
            const rxMbps = Math.max(0, (deltaRx * 8) / (timeDiff * 1000000));
            const txMbps = Math.max(0, (deltaTx * 8) / (timeDiff * 1000000));

            addDataToChart(rxMbps, txMbps);
            updateStatsText(data.length, currentTotalRx, currentTotalTx, rxMbps, txMbps);
        }

        // 3. Update State
        lastDashTime = now;
        lastTotalRx = currentTotalRx;
        lastTotalTx = currentTotalTx;

    } catch (err) {
        console.error("Failed to update dashboard traffic:", err);
    }
}

function addDataToChart(rx, tx) {
    const nowStr = new Date().toLocaleTimeString();

    // Add new data
    dashboardChart.data.labels.push(nowStr);
    dashboardChart.data.datasets[0].data.push(rx);
    dashboardChart.data.datasets[1].data.push(tx);

    // Remove old data to keep chart moving
    if (dashboardChart.data.labels.length > MAX_DASH_POINTS) {
        dashboardChart.data.labels.shift();
        dashboardChart.data.datasets[0].data.shift();
        dashboardChart.data.datasets[1].data.shift();
    }

    dashboardChart.update();
}

function updateStatsText(ifaceCount, totalRx, totalTx, rxSpeed, txSpeed) {
    const el = document.getElementById("dashboardTrafficStats");
    if (el) {
        // Convert Total Bytes to readable format (GB/MB)
        const formatBytes = (bytes) => {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        };

        el.innerHTML = `
            <div><b>Active Interfaces:</b> ${ifaceCount}</div>
            <div style="color: #10b981"><b>Download:</b> ${rxSpeed.toFixed(2)} Mbps</div>
            <div style="color: #3b82f6"><b>Upload:</b> ${txSpeed.toFixed(2)} Mbps</div>
            <div style="opacity: 0.6; font-size: 0.8em; padding-top:3px">Total Processed: ${formatBytes(totalRx + totalTx)}</div>
        `;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // The Utils.js loop usually handles periodic calls, 
    // but we can ensure the dashboard loads initially here.
    loadDashboard();
});