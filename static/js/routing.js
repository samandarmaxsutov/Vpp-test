// ========== ROUTING ==========
async function loadRoutes() {
    try {
        const res = await fetch(`${API_BASE}/routes`);
        const data = await res.json();

        const tbody = document.getElementById('routes-table');
        tbody.innerHTML = data.map(route => `
                    <tr>
                        <td><strong>${route.destination}</strong></td>
                        <td>${route.next_hop}</td>
                        <td>${route.interface}</td>
            
                        <td>
                            <button class="btn btn-danger" 
                                onclick="deleteRoute('${route.destination}', ${route.sw_if_index}, '${route.next_hop}')">
                                Delete
                            </button>
                        </td>
                    </tr>
                `).join('');
    } catch (err) {
        showAlert('alert-routing', 'Failed to load routes: ' + err.message, 'error');
    }
}

function openAddRouteModal() {
    const select = document.getElementById('route-interface');
    select.innerHTML = currentInterfaces.map(iface =>
        `<option value="${iface.sw_if_index}">${iface.name} (${iface.sw_if_index})</option>`
    ).join('');
    document.getElementById('route-modal').classList.add('active');
}

async function addRoute() {
    const dest = document.getElementById('route-dest').value;
    const prefix = document.getElementById('route-prefix').value;
    const ifIndex = document.getElementById('route-interface').value;
    const nextHop = document.getElementById('route-nexthop').value;

    try {
        await fetch(`${API_BASE}/route`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                destination: dest,
                prefix_len: prefix,
                sw_if_index: ifIndex,
                next_hop: nextHop
            })
        });
        showAlert('alert-routing', 'Route added successfully');
        closeModal('route-modal');
        loadRoutes();
    } catch (err) {
        showAlert('alert-routing', 'Failed to add route: ' + err.message, 'error');
    }
}

async function deleteRoute(dest, ifIndex, nextHop) {
    if (!confirm('Delete this route?')) return;

    const [ip, prefix] = dest.split('/');
    try {
        await fetch(`${API_BASE}/route`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                destination: ip,
                prefix_len: prefix,
                sw_if_index: ifIndex,
                next_hop: nextHop === 'direct' ? '0.0.0.0' : nextHop
            })
            
            
        });
        showAlert('alert-routing', 'Route deleted successfully');
        loadRoutes();
    } catch (err) {
        showAlert('alert-routing', 'Failed to delete route: ' + err.message, 'error');
    }
}