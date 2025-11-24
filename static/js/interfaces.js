// ========== INTERFACES ==========
let dhcpClients = [];

async function loadInterfaces() {
    try {
        const resDhcp = await fetch(`${API_BASE}/dhcp/clients`);
        dhcpClients = await resDhcp.json();   // store DHCP interfaces

        const res = await fetch(`${API_BASE}/interfaces`);
        const data = await res.json();

        currentInterfaces = data;

        const tbody = document.getElementById('interfaces-table');
        tbody.innerHTML = data.map(iface => `
                    <tr>
                    
                        <td><strong>${iface.name}</strong></td>
                        <td><span class="badge badge-${iface.status === 'up' ? 'success' : 'danger'}">${iface.status.toUpperCase()}</span></td>
                      
                        <td>
                            ${iface.ip_addresses.length > 0
                                        ? iface.ip_addresses.map(ip => `
                                    <div>
                                        ${ip}
                                        <button class="btn btn-success btn-xs" onclick="openEditIpModal('${ip}', ${iface.sw_if_index})" title ="Edit">Edit</button>
                                        <button class="btn btn-danger btn-xs"  onclick="deleteIp('${ip}', ${iface.sw_if_index})" title= "Delete">Delete</button>

                                    </div>
                                `).join('')
                                        : '<em>No IP</em>'
                                    }
                        </td>
                        <td>
                            <button class="btn ${iface.status === 'up' ? 'btn-danger' : 'btn-success'}" 
                                onclick="toggleInterface(${iface.sw_if_index}, '${iface.status}')">
                                ${iface.status === 'up' ? 'Disable' : 'Enable'}
                            </button>
                            <button class="btn btn-primary" onclick="openIpModal(${iface.sw_if_index})">+ IP</button>
                            <button class="btn ${isDhcpEnabled(iface.sw_if_index) ? 'btn-success' : 'btn-danger'} btn-sm" 
                                    onclick="toggleDhcp(${iface.sw_if_index})">
                                ${isDhcpEnabled(iface.sw_if_index) ? 'DHCP: ON' : 'DHCP: OFF'}
                            </button>

                        </td>
                    </tr>
                `).join('');
    } catch (err) {
        showAlert('alert-interfaces', 'Failed to load interfaces: ' + err.message, 'error');
    }
}

function isDhcpEnabled(sw_if_index) {
    return dhcpClients.some(c => c.sw_if_index === sw_if_index);
}

async function toggleDhcp(sw_if_index) {
    const enabled = isDhcpEnabled(sw_if_index);

    try {
        if (!enabled) {
            // ENABLE DHCP
            await fetch(`${API_BASE}/dhcp/client`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    sw_if_index,
                    hostname: "vpp-client",
                    want_dhcp_event: true
                })
            });
            showAlert('alert-interfaces', 'DHCP Enabled');
        } else {
            // DISABLE DHCP
            await fetch(`${API_BASE}/dhcp/client/${sw_if_index}`, {
                method: 'DELETE'
            });
            showAlert('alert-interfaces', 'DHCP Disabled');
        }

        loadInterfaces();
    } catch(err) {
        showAlert('alert-interfaces', 'DHCP toggle failed: ' + err.message, 'error');
    }
}



function openEditIpModal(ipEntry, sw_if_index) {
    selectedInterface = sw_if_index;
    selectedIpEntry = ipEntry;

    const [ip, prefix] = ipEntry.split('/');
    document.getElementById('edit-ip-address').value = ip;
    document.getElementById('edit-ip-prefix').value = prefix;

    document.getElementById('edit-ip-modal').classList.add('active');
}
async function saveEditedIp() {
    const newIp = document.getElementById('edit-ip-address').value;
    const newPrefix = document.getElementById('edit-ip-prefix').value;

    const [oldIp, oldPrefix] = selectedIpEntry.split('/');

    try {
        // Remove old IP
        await fetch(`${API_BASE}/interface/${selectedInterface}/ip`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip: oldIp, prefix_len: oldPrefix })
        });

        // Add new IP
        await fetch(`${API_BASE}/interface/${selectedInterface}/ip`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip: newIp, prefix_len: newPrefix })
        });

        showAlert('alert-interfaces', 'IP updated successfully');
        closeModal('edit-ip-modal');
        loadInterfaces();

    } catch (err) {
        showAlert('alert-interfaces', 'Failed to update IP: ' + err.message, 'error');
    }
}

async function deleteIp(ipEntry, sw_if_index) {
    // ipEntry looks like "192.168.1.10/24"
    const [ip, prefix_len] = ipEntry.split('/');

    try {
        const res = await fetch(`${API_BASE}/interface/${sw_if_index}/ip`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip, prefix_len })
        });

        const data = await res.json();

        if (data.error) throw new Error(data.error);

        showAlert('alert-interfaces', 'IP removed successfully');
        loadInterfaces();

    } catch (err) {
        showAlert('alert-interfaces', 'Failed to delete IP: ' + err.message, 'error');
    }
}

async function toggleInterface(sw_if_index, currentStatus) {
    try {
        const res = await fetch(`${API_BASE}/interface/${sw_if_index}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                up: currentStatus !== 'up'
            })
        });
        const data = await res.json();
        showAlert('alert-interfaces', `Interface ${data.status === 'up' ? 'enabled' : 'disabled'}`);
        loadInterfaces();
    } catch (err) {
        showAlert('alert-interfaces', 'Failed to toggle interface: ' + err.message, 'error');
    }
}

function openIpModal(sw_if_index) {
    selectedInterface = sw_if_index;
    document.getElementById('ip-modal').classList.add('active');
}

async function addIpAddress() {
    const ip = document.getElementById('ip-address').value;
    const prefix = document.getElementById('ip-prefix').value;

    try {
        const res = await fetch(`${API_BASE}/interface/${selectedInterface}/ip`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ip,
                prefix_len: prefix
            })
        });
        await res.json();
        showAlert('alert-interfaces', 'IP address added successfully');
        closeModal('ip-modal');
        loadInterfaces();
    } catch (err) {
        showAlert('alert-interfaces', 'Failed to add IP: ' + err.message, 'error');
    }
}