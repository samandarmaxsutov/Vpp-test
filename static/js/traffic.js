// Global Chart Objects
let bandwidthChart = null;
let packetsChart = null;
let previousStats = {}; 
const MAX_DATA_POINTS = 30; 

// Colors
const CHART_COLORS = [
    '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#6366f1', 
    '#ec4899', '#8b5cf6', '#14b8a6', '#f97316', '#06b6d4'
];

window.updateTrafficStats = async function() {
    // 1. Try to initialize charts if they don't exist
    if (!bandwidthChart) {
        initTrafficCharts();
    }

    // 2. CRITICAL FIX: If initialization failed (canvas not found), STOP HERE.
    if (!bandwidthChart || !packetsChart) {
        console.warn("Charts not initialized yet. Waiting for HTML elements...");
        return; 
    }

    try {
        const res = await fetch('/api/interfaces/stats');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const data = await res.json();
        
        if (!Array.isArray(data)) {
            console.error("Expected Array, got:", data);
            return;
        }

        // Update status badge
        const statusBadge = document.getElementById("traffic-status");
        if(statusBadge) {
            statusBadge.innerText = "Live ●";
            statusBadge.className = "badge badge-success";
        }

        processTrafficData(data);

    } catch (err) {
        console.error("Failed to load traffic data:", err);
        const statusBadge = document.getElementById("traffic-status");
        if(statusBadge) {
            statusBadge.innerText = "Error";
            statusBadge.className = "badge badge-danger";
        }
    }
};

function initTrafficCharts() {
    const ctxBw = document.getElementById('bandwidthChart');
    const ctxPk = document.getElementById('packetsChart');

    // If HTML elements are missing, exit gracefully
    if (!ctxBw || !ctxPk) return; 

    // 1. Bandwidth Line Chart
    bandwidthChart = new Chart(ctxBw.getContext('2d'), {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: { display: true },
                y: { display: true, beginAtZero: true, title: { display: true, text: 'Mbps' } }
            },
            animation: { duration: 0 },
            elements: { point: { radius: 0 } } // Remove dots for cleaner lines
        }
    });

    // 2. Packets Bar Chart
    packetsChart = new Chart(ctxPk.getContext('2d'), {
        type: 'bar',
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'Packets / Sec' } }
            },
            animation: { duration: 0 }
        }
    });
}

function processTrafficData(currentData) {
    // Double check charts exist before processing
    if (!bandwidthChart || !packetsChart) return;

    const now = new Date();
    const timeLabel = now.toLocaleTimeString('en-US', { hour12: false, hour: "numeric", minute: "numeric", second: "numeric" });

    // Update Time Axis
    if (bandwidthChart.data.labels.length >= MAX_DATA_POINTS) {
        bandwidthChart.data.labels.shift();
    }
    bandwidthChart.data.labels.push(timeLabel);

    const packetLabels = [];
    const rxPacketsData = [];
    const txPacketsData = [];
    const dropsData = [];

    currentData.forEach((iface, index) => {
        const name = iface.name;
        const prev = previousStats[name];
        
        let rxMbps = 0, txMbps = 0, rxPps = 0, txPps = 0, newDrops = 0;

        if (prev) {
            // Mbps Calculation (Bytes * 8 / 2s / 1M)
            const deltaRx = iface.rx_bytes - prev.rx_bytes;
            const deltaTx = iface.tx_bytes - prev.tx_bytes;
            
            if (deltaRx >= 0) rxMbps = (deltaRx * 8) / 2000000;
            if (deltaTx >= 0) txMbps = (deltaTx * 8) / 2000000;

            // PPS Calculation
            const deltaRxP = iface.rx_packets - prev.rx_packets;
            const deltaTxP = iface.tx_packets - prev.tx_packets;

            if (deltaRxP >= 0) rxPps = deltaRxP / 2;
            if (deltaTxP >= 0) txPps = deltaTxP / 2;
            
            newDrops = iface.drops - prev.drops;
        }

        // Update Bandwidth Chart
        if (iface.rx_bytes > 0 || iface.tx_bytes > 0) {
            updateDataset(bandwidthChart, `${name} RX`, rxMbps, CHART_COLORS[index % CHART_COLORS.length], false);
            updateDataset(bandwidthChart, `${name} TX`, txMbps, CHART_COLORS[index % CHART_COLORS.length], true);
        }

        // Update Packets Chart Data
        if (rxPps > 0 || txPps > 0 || iface.drops > 0) {
            packetLabels.push(name);
            rxPacketsData.push(rxPps);
            txPacketsData.push(txPps);
            dropsData.push(newDrops);
        }

        previousStats[name] = iface;
    });

    bandwidthChart.update();

    packetsChart.data.labels = packetLabels;
    packetsChart.data.datasets = [
        { label: 'RX PPS', data: rxPacketsData, backgroundColor: '#10b981' },
        { label: 'TX PPS', data: txPacketsData, backgroundColor: '#3b82f6' },
        { label: 'Drops', data: dropsData, backgroundColor: '#ef4444' }
    ];
    packetsChart.update();
}

function updateDataset(chart, label, value, color, isDashed) {
    let dataset = chart.data.datasets.find(ds => ds.label === label);
    if (!dataset) {
        dataset = {
            label: label,
            data: new Array(chart.data.labels.length - 1).fill(0),
            borderColor: color,
            backgroundColor: color,
            borderWidth: 2,
            tension: 0.3,
            fill: false,
            borderDash: isDashed ? [5, 5] : []
        };
        chart.data.datasets.push(dataset);
    }
    if (dataset.data.length >= MAX_DATA_POINTS) dataset.data.shift();
    dataset.data.push(value);
}