// ========== NAT ==========
async function loadNat() {
    await loadNatInterfaces();
    await loadNatAddresses();
    await loadNatSessions();
    await loadStaticNat();
    await loadNatStatus();
}
// Load current NAT plugin status
async function loadNatStatus() {
    try {
        const res = await fetch('/api/nat/plugin');
        const data = await res.json();
        const statusLabel = document.getElementById('nat-status');

        // Build status text
        let statusText = '';
        console.log(data.nat_active);
        // NAT active/inactive
        statusText += data.nat_active ? '🟢 Active' : '🔴 Inactive';

        // Plugin loaded
        statusText += ' | ';
        statusText += data.plugin_loaded ? '🟢 Plugin Loaded' : '🔴 Plugin Not Loaded';

        statusLabel.textContent = statusText;

        

    } catch (err) {
        console.error("Failed to load NAT status:", err);
        document.getElementById('nat-status').textContent = '⚠️ Error';
    }
}


// Enable NAT plugin
async function enableNat() {
    try {
        await fetch('/api/nat/plugin', {
            method: 'POST'
        });
        loadNat();
    } catch (err) {
        alert("Failed to enable NAT: " + err);
    }
}

// Disable NAT plugin
async function disableNat() {
    try {
        await fetch('/api/nat/plugin', {
            method: 'DELETE'
        });
        loadNat();
    } catch (err) {
        alert("Failed to disable NAT: " + err);
    }
}



async function loadNatInterfaces() {
    try {
        const res = await fetch(`${API_BASE}/nat/interfaces`);
        const data = await res.json();

        const tbody = document.getElementById('nat-interfaces-table');
        tbody.innerHTML = data.map(natIf => `
                    <tr>
                        <td>${natIf.sw_if_index}</td>
                        <td><span class="badge badge-${natIf.is_inside ? 'success' : 'info'}">
                            ${natIf.is_inside ? 'Inside (LAN)' : 'Outside (WAN)'}
                        </span></td>
                        <td>
                            <button class="btn btn-danger" onclick="removeNatInterface(${natIf.sw_if_index}, ${natIf.is_inside})">
                                Remove
                            </button>
                        </td>
                    </tr>
                `).join('');
    } catch (err) {
        console.error('Failed to load NAT interfaces:', err);
    }
}

async function loadNatAddresses() {
    try {
        const res = await fetch(`${API_BASE}/nat/addresses`);
        const data = await res.json();

        const tbody = document.getElementById('nat-addresses-table');
        tbody.innerHTML = data.map(addr => `
                    <tr>
                        <td><strong>${addr.ip_address}</strong></td>
                        <td>${addr.vrf_id}</td>
                        <td>
                            <button class="btn btn-danger" onclick="removeNatAddress('${addr.ip_address}')">
                                Remove
                            </button>
                        </td>
                    </tr>
                `).join('');
    } catch (err) {
        console.error('Failed to load NAT addresses:', err);
    }
}

async function loadNatSessions() {
    try {
        const res = await fetch(`${API_BASE}/nat/sessions`);
        const data = await res.json();

        const tbody = document.getElementById('nat-sessions-table');
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;"><em>No active sessions</em></td></tr>';
        } else {
            tbody.innerHTML = data.map(session => `
                        <tr>
                            <td>${session.inside_ip}:${session.inside_port}</td>
                            <td>${session.outside_ip}:${session.outside_port}</td>
                            <td>${session.protocol === 6 ? 'TCP' : session.protocol === 17 ? 'UDP' : session.protocol}</td>
                        </tr>
                    `).join('');
        }
    } catch (err) {
        console.error('Failed to load NAT sessions:', err);
    }
}

async function loadStaticNat() {
    const table = document.getElementById("static-nat-table");
    table.innerHTML = "";

    try {
        const response = await fetch("/api/nat/static");
        const data = await response.json();

        data.forEach(mapping => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${mapping.local_ip}:${mapping.local_port ?? '-'}</td>
                <td>${mapping.external_ip}:${mapping.external_port ?? '-'}</td>
                <td>${mapping.protocol === 6 ? 'TCP' : mapping.protocol === 17 ? 'UDP' : mapping.protocol}</td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="deleteStaticNat('${mapping.local_ip}', '${mapping.external_ip}', ${mapping.local_port}, ${mapping.external_port}, ${mapping.protocol})">Delete</button>
                </td>
            `;
            table.appendChild(row);
        });
    } catch (err) {
        console.error("Failed to load static NATs:", err);
        table.innerHTML = `<tr><td colspan="4">Error loading NAT mappings</td></tr>`;
    }
}

function openStaticNatModal() {
    document.getElementById("static-nat-modal").classList.add("active");
}

function closeStaticNatModal() {
    document.getElementById("static-nat-modal").classList.remove("active");
}


async function addStaticNat() {
    const local_ip = document.getElementById("localIp").value.trim();
    const external_ip = document.getElementById("externalIp").value.trim();
    const local_port = document.getElementById("localPort").value;
    const external_port = document.getElementById("externalPort").value;
    const protocol = document.getElementById("protocol").value;

    if (!local_ip || !external_ip) {
        alert("Please provide both Local IP and External IP.");
        return;
    }

    try {
        const response = await fetch("/api/nat/static", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                local_ip,
                external_ip,
                local_port,
                external_port,
                protocol
            })
        });

        const result = await response.json();
        alert(result.message || "Static NAT mapping added successfully.");
        closeStaticNatModal();
        loadStaticNat(); // Refresh the table
    } catch (err) {
        console.error("Error adding static NAT mapping:", err);
        alert("Failed to add mapping. Check console for details.");
    }
}

async function deleteStaticNat(local_ip, external_ip, local_port, external_port, protocol) {
    if (!confirm("Are you sure you want to remove this NAT mapping?")) return;

    try {
        const response = await fetch("/api/nat/static", {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                local_ip,
                external_ip,
                local_port,
                external_port,
                protocol
            })
        });

        const result = await response.json();
        alert(result.message || "Static NAT mapping removed successfully.");
        loadStaticNat(); // Refresh the table
    } catch (err) {
        console.error("Error deleting static NAT mapping:", err);
        alert("Failed to delete mapping. Check console for details.");
    }
}


function openNatAddressModal() {
    document.getElementById('nat-address-modal').classList.add('active');
}

async function addNatAddress() {
    const ip = document.getElementById('nat-ip').value;

    try {
        await fetch(`${API_BASE}/nat/address`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ip_address: ip
            })
        });
        showAlert('alert-nat', 'NAT address added successfully');
        closeModal('nat-address-modal');
        loadNatAddresses();
    } catch (err) {
        showAlert('alert-nat', 'Failed to add NAT address: ' + err.message, 'error');
    }
}

async function removeNatAddress(ip) {
    if (!confirm('Remove this NAT address?')) return;

    try {
        await fetch(`${API_BASE}/nat/address`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ip_address: ip
            })
        });
        showAlert('alert-nat', 'NAT address removed successfully');
        loadNatAddresses();
    } catch (err) {
        showAlert('alert-nat', 'Failed to remove NAT address: ' + err.message, 'error');
    }
}

function openNatInterfaceModal() {
    const select = document.getElementById('nat-if-index');
    select.innerHTML = currentInterfaces.map(iface =>
        `<option value="${iface.sw_if_index}">${iface.name} (${iface.sw_if_index})</option>`
    ).join('');
    document.getElementById('nat-interface-modal').classList.add('active');
}

async function configureNatInterface() {
    const sw_if_index = parseInt(document.getElementById('nat-if-index').value);
    const is_inside = document.getElementById('nat-if-type').value === 'true';

    try {
        await fetch(`${API_BASE}/nat/interface/${sw_if_index}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                is_inside
            })
        });
        showAlert('alert-nat', 'NAT interface configured successfully');
        closeModal('nat-interface-modal');
        loadNatInterfaces();
    } catch (err) {
        showAlert('alert-nat', 'Failed to configure NAT interface: ' + err.message, 'error');
    }
}

async function removeNatInterface(sw_if_index, is_inside) {
    if (!confirm('Remove NAT configuration from this interface?')) return;

    try {
        await fetch(`${API_BASE}/nat/interface/${sw_if_index}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                is_inside
            })
        });
        showAlert('alert-nat', 'NAT interface removed successfully');
        loadNatInterfaces();
    } catch (err) {
        showAlert('alert-nat', 'Failed to remove NAT interface: ' + err.message, 'error');
    }
}