// ===================== SETTINGS TAB =====================
function loadSettings() {
    fetch(`${API_BASE}/settings/nat/`)
        .then(res => res.json())
        .then(data => {
            if(data.success && data.settings) {
                const t = data.settings.timeouts;
                const s = data.settings.sessions;

                document.getElementById('timeout-udp').value = t.udp;
                document.getElementById('timeout-tcp-established').value = t.tcp_established;
                document.getElementById('timeout-tcp-transitory').value = t.tcp_transitory;
                document.getElementById('timeout-icmp').value = t.icmp;

                document.getElementById('session-limit-vrf').value = data.settings.vrfs.inside_vrf || 0;
                document.getElementById('session-limit-value').value = s.sessions || 10000;
            } else {
                showAlert('alert-settings', 'Failed to load settings', 'error');
            }
        })
        .catch(err => showAlert('alert-settings', err.message, 'error'));
}

function saveSettings() {
    const payload = {
        timeouts: {
            udp: parseInt(document.getElementById('timeout-udp').value),
            tcp_established: parseInt(document.getElementById('timeout-tcp-established').value),
            tcp_transitory: parseInt(document.getElementById('timeout-tcp-transitory').value),
            icmp: parseInt(document.getElementById('timeout-icmp').value)
        },
        session_limit: {
            vrf_id: parseInt(document.getElementById('session-limit-vrf').value),
            limit: parseInt(document.getElementById('session-limit-value').value)
        }
    };

    fetch(`${API_BASE}/settings/nat/`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if(data.success) {
            showAlert('alert-settings', 'Settings updated successfully!', 'success');
            loadSettings(); // refresh inputs
        } else {
            showAlert('alert-settings', data.error || 'Failed to update settings', 'error');
        }
    })
    .catch(err => showAlert('alert-settings', err.message, 'error'));
}
