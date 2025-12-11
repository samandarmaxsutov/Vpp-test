// ===================== ABF.JS - ABF Policy Management =====================

// -------- Load ABF Policies --------
async function loadAbfPolicies() {
    try {
        const response = await fetch(`${API_BASE}/abf/policy`);
        const data = await response.json();
        
        if (data.policies) {
            renderAbfPolicies(data.policies);
        }
    } catch (error) {
        console.error('Error loading ABF policies:', error);
        showAlert('alert-abf', 'Failed to load ABF policies', 'error');
    }
}

// -------- Render ABF Policies --------
function renderAbfPolicies(policies) {
    const tbody = document.getElementById('abf-policies-table');
    if (!tbody) return;

    if (policies.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">No ABF policies configured</td></tr>';
        return;
    }

    tbody.innerHTML = policies.map(policy => `
        <tr>
            <td><strong>Policy ${policy.policy_id}</strong></td>
            <td>ACL Index: ${policy.acl_index}</td>
            <td>
                ${policy.paths.map((path, idx) => `
                    <div style="margin-bottom: 5px; padding: 5px; background: #f9fafb; border-radius: 4px;">
                        <strong>Path ${idx + 1}:</strong><br>
                        Interface: ${path.sw_if_index} | 
                        Next Hop: ${path.next_hop} | 
                        Weight: ${path.weight}
                    </div>
                `).join('')}
            </td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="openEditAbfPolicyModal(${policy.policy_id})">
                    <i class="icon-edit"></i> Edit
                </button>
                <button class="btn btn-danger btn-sm" onclick="deleteAbfPolicy(${policy.policy_id})">
                    <i class="icon-trash"></i> Delete
                </button>
            </td>
        </tr>
    `).join('');
}

// -------- Load ABF Attachments --------
async function loadAbfAttachments() {
    try {
        const response = await fetch(`${API_BASE}/abf/attach`);
        const data = await response.json();
        
        if (data.attachments) {
            renderAbfAttachments(data.attachments);
        }
    } catch (error) {
        console.error('Error loading ABF attachments:', error);
        showAlert('alert-abf', 'Failed to load ABF attachments', 'error');
    }
}

// -------- Render ABF Attachments --------
function renderAbfAttachments(attachments) {
    const tbody = document.getElementById('abf-attachments-table');
    if (!tbody) return;

    if (attachments.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">No ABF policy attachments</td></tr>';
        return;
    }

    tbody.innerHTML = attachments.map(attach => `
        <tr>
            <td><strong>Policy ${attach.policy_id}</strong></td>
            <td>Interface ${attach.sw_if_index}</td>
            <td>${attach.priority}</td>
            <td><span class="badge ${attach.is_ipv6 ? 'badge-info' : 'badge-neutral'}">${attach.is_ipv6 ? 'IPv6' : 'IPv4'}</span></td>
            <td>
                <button class="btn btn-primary btn-sm" onclick="openEditAbfAttachmentModal(${attach.policy_id}, ${attach.sw_if_index})">
                    <i class="icon-edit"></i> Edit
                </button>
                <button class="btn btn-danger btn-sm" onclick="deleteAbfAttachment(${attach.policy_id}, ${attach.sw_if_index})">
                    <i class="icon-trash"></i> Detach
                </button>
            </td>
        </tr>
    `).join('');
}

// -------- Open Add ABF Policy Modal --------
function openAddAbfPolicyModal() {
    document.getElementById('abf-policy-modal').classList.add('active');
    document.getElementById('abf-policy-id').value = '';
    document.getElementById('abf-acl-index').value = '0';
    document.getElementById('abf-paths-container').innerHTML = '';
    addAbfPathRow(); // Add one default path
}

// -------- Add ABF Path Row --------
function addAbfPathRow() {
    const container = document.getElementById('abf-paths-container');
    const pathIndex = container.children.length;
    
    const pathRow = document.createElement('div');
    pathRow.className = 'abf-path-row';
    pathRow.style.cssText = 'display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 10px; margin-bottom: 10px; padding: 10px; background: #f9fafb; border-radius: 4px;';
    
    pathRow.innerHTML = `
        <div class="form-group">
            <label class="form-label">Interface Index</label>
            <input type="number" class="form-input path-sw-if" placeholder="e.g. 1">
        </div>
        <div class="form-group">
            <label class="form-label">Next Hop IP</label>
            <input type="text" class="form-input path-nexthop" placeholder="e.g. 192.168.1.1">
        </div>
        <div class="form-group">
            <label class="form-label">Weight</label>
            <input type="number" class="form-input path-weight" value="1" min="1">
        </div>
        <div class="form-group" style="display: flex; align-items: flex-end;">
            <button class="btn btn-danger btn-sm" onclick="this.closest('.abf-path-row').remove()">
                <i class="icon-trash"></i>
            </button>
        </div>
    `;
    
    container.appendChild(pathRow);
}

// -------- Create ABF Policy --------
async function createAbfPolicy() {
    const policyId = parseInt(document.getElementById('abf-policy-id').value);
    const aclIndex = parseInt(document.getElementById('abf-acl-index').value);
    
    if (!policyId) {
        showAlert('alert-abf', 'Policy ID is required', 'error');
        return;
    }

    const pathRows = document.querySelectorAll('.abf-path-row');
    const paths = [];
    
    for (const row of pathRows) {
        const swIfIndex = parseInt(row.querySelector('.path-sw-if').value);
        const nextHop = row.querySelector('.path-nexthop').value;
        const weight = parseInt(row.querySelector('.path-weight').value) || 1;
        
        if (!swIfIndex || !nextHop) {
            showAlert('alert-abf', 'All path fields are required', 'error');
            return;
        }
        
        paths.push({
            sw_if_index: swIfIndex,
            next_hop: nextHop,
            weight: weight
        });
    }

    if (paths.length === 0) {
        showAlert('alert-abf', 'At least one path is required', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/abf/policy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                policy_id: policyId,
                acl_index: aclIndex,
                paths: paths
            })
        });

        const result = await response.json();
        
        if (response.ok) {
            showAlert('alert-abf', `ABF Policy ${policyId} created successfully`, 'success');
            closeModal('abf-policy-modal');
            loadAbfPolicies();
        } else {
            showAlert('alert-abf', `Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error creating ABF policy:', error);
        showAlert('alert-abf', 'Failed to create ABF policy', 'error');
    }
}

// -------- Open Edit ABF Policy Modal --------
async function openEditAbfPolicyModal(policyId) {
    try {
        const response = await fetch(`${API_BASE}/abf/policy`);
        const data = await response.json();
        const policy = data.policies.find(p => p.policy_id === policyId);
        
        if (!policy) {
            showAlert('alert-abf', 'Policy not found', 'error');
            return;
        }

        document.getElementById('edit-abf-policy-modal').classList.add('active');
        document.getElementById('edit-abf-policy-id').value = policy.policy_id;
        document.getElementById('edit-abf-policy-id').disabled = true;
        document.getElementById('edit-abf-acl-index').value = policy.acl_index;
        
        const container = document.getElementById('edit-abf-paths-container');
        container.innerHTML = '';
        
        policy.paths.forEach(path => {
            const pathRow = document.createElement('div');
            pathRow.className = 'abf-path-row';
            pathRow.style.cssText = 'display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 10px; margin-bottom: 10px; padding: 10px; background: #f9fafb; border-radius: 4px;';
            
            pathRow.innerHTML = `
                <div class="form-group">
                    <label class="form-label">Interface Index</label>
                    <input type="number" class="form-input path-sw-if" value="${path.sw_if_index}">
                </div>
                <div class="form-group">
                    <label class="form-label">Next Hop IP</label>
                    <input type="text" class="form-input path-nexthop" value="${path.next_hop}">
                </div>
                <div class="form-group">
                    <label class="form-label">Weight</label>
                    <input type="number" class="form-input path-weight" value="${path.weight}" min="1">
                </div>
                <div class="form-group" style="display: flex; align-items: flex-end;">
                    <button class="btn btn-danger btn-sm" onclick="this.closest('.abf-path-row').remove()">
                        <i class="icon-trash"></i>
                    </button>
                </div>
            `;
            container.appendChild(pathRow);
        });
        
    } catch (error) {
        console.error('Error loading policy for edit:', error);
        showAlert('alert-abf', 'Failed to load policy data', 'error');
    }
}

// -------- Update ABF Policy --------
async function updateAbfPolicy() {
    const policyId = parseInt(document.getElementById('edit-abf-policy-id').value);
    const aclIndex = parseInt(document.getElementById('edit-abf-acl-index').value);
    
    const pathRows = document.querySelectorAll('#edit-abf-paths-container .abf-path-row');
    const paths = [];
    
    for (const row of pathRows) {
        const swIfIndex = parseInt(row.querySelector('.path-sw-if').value);
        const nextHop = row.querySelector('.path-nexthop').value;
        const weight = parseInt(row.querySelector('.path-weight').value) || 1;
        
        if (!swIfIndex || !nextHop) {
            showAlert('alert-abf', 'All path fields are required', 'error');
            return;
        }
        
        paths.push({
            sw_if_index: swIfIndex,
            next_hop: nextHop,
            weight: weight
        });
    }

    if (paths.length === 0) {
        showAlert('alert-abf', 'At least one path is required', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/abf/policy/${policyId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                acl_index: aclIndex,
                paths: paths
            })
        });

        const result = await response.json();
        
        if (response.ok) {
            showAlert('alert-abf', `ABF Policy ${policyId} updated successfully`, 'success');
            closeModal('edit-abf-policy-modal');
            loadAbfPolicies();
        } else {
            showAlert('alert-abf', `Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error updating ABF policy:', error);
        showAlert('alert-abf', 'Failed to update ABF policy', 'error');
    }
}

// -------- Delete ABF Policy --------
async function deleteAbfPolicy(policyId) {
    if (!confirm(`Are you sure you want to delete ABF Policy ${policyId}?`)) return;

    try {
        const response = await fetch(`${API_BASE}/abf/policy/${policyId}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        
        if (response.ok) {
            showAlert('alert-abf', `ABF Policy ${policyId} deleted successfully`, 'success');
            loadAbfPolicies();
        } else {
            showAlert('alert-abf', `Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting ABF policy:', error);
        showAlert('alert-abf', 'Failed to delete ABF policy', 'error');
    }
}

// -------- Open Add ABF Attachment Modal --------
function openAddAbfAttachmentModal() {
    document.getElementById('abf-attachment-modal').classList.add('active');
    loadInterfacesForSelect('abf-attach-interface');
}

// -------- Create ABF Attachment --------
async function createAbfAttachment() {
    const policyId = parseInt(document.getElementById('abf-attach-policy-id').value);
    const swIfIndex = parseInt(document.getElementById('abf-attach-interface').value);
    const priority = parseInt(document.getElementById('abf-attach-priority').value);
    const isIpv6 = document.getElementById('abf-attach-ipv6').checked;

    if (!policyId || !swIfIndex) {
        showAlert('alert-abf', 'Policy ID and Interface are required', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/abf/attach`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                policy_id: policyId,
                sw_if_index: swIfIndex,
                priority: priority,
                is_ipv6: isIpv6
            })
        });

        const result = await response.json();
        
        if (response.ok) {
            showAlert('alert-abf', 'ABF attachment created successfully', 'success');
            closeModal('abf-attachment-modal');
            loadAbfAttachments();
        } else {
            showAlert('alert-abf', `Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error creating ABF attachment:', error);
        showAlert('alert-abf', 'Failed to create ABF attachment', 'error');
    }
}

// -------- Delete ABF Attachment --------
async function deleteAbfAttachment(policyId, swIfIndex) {
    if (!confirm(`Detach Policy ${policyId} from Interface ${swIfIndex}?`)) return;

    try {
        const response = await fetch(`${API_BASE}/abf/attach/${policyId}/${swIfIndex}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        
        if (response.ok) {
            showAlert('alert-abf', 'ABF attachment deleted successfully', 'success');
            loadAbfAttachments();
        } else {
            showAlert('alert-abf', `Error: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error deleting ABF attachment:', error);
        showAlert('alert-abf', 'Failed to delete ABF attachment', 'error');
    }
}

// -------- Helper: Load Interfaces for Select --------
async function loadInterfacesForSelect(selectId) {
    try {
        const response = await fetch(`${API_BASE}/interfaces`);
        const data = await response.json();
        const select = document.getElementById(selectId);
        
        // Handle both array response and object with interfaces property
        const interfaces = Array.isArray(data) ? data : (data.interfaces || []);
        
        if (interfaces.length === 0) {
            select.innerHTML = '<option value="">No interfaces available</option>';
            return;
        }
        
        select.innerHTML = interfaces.map(iface => 
            `<option value="${iface.sw_if_index}">${iface.name || iface.interface_name} (Index: ${iface.sw_if_index})</option>`
        ).join('');
    } catch (error) {
        console.error('Error loading interfaces:', error);
        const select = document.getElementById(selectId);
        if (select) {
            select.innerHTML = '<option value="">Error loading interfaces</option>';
        }
    }
}

// -------- Load ABF Tab --------
function loadAbf() {
    loadAbfPolicies();
    loadAbfAttachments();
}