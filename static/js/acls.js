// ========== ACL/FIREWALL ==========
function openAddAclModal() {
    document.getElementById('acl-rules-container').innerHTML = '';
    aclRuleCount = 0;
    addAclRule();
    document.getElementById('acl-modal').classList.add('active');
}

function addAclRule() {
    const container = document.getElementById('acl-rules-container');
    const ruleId = aclRuleCount++;
    const ruleHtml = `
                <div class="rule-item" id="rule-${ruleId}">
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Action</label>
                            <select id="action-${ruleId}" class="form-select">
                                <option value="permit">Permit</option>
                                <option value="deny">Deny</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Protocol</label>
                            <select id="proto-${ruleId}" class="form-select">
                                <option value="0">Any</option>
                                <option value="1">ICMP</option>
                                <option value="6">TCP</option>
                                <option value="17">UDP</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Source IP/Prefix</label>
                            <input type="text" id="src-ip-${ruleId}" class="form-input" placeholder="0.0.0.0/0">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Destination IP/Prefix</label>
                            <input type="text" id="dst-ip-${ruleId}" class="form-input" placeholder="0.0.0.0/0">
                        </div>
                    </div>
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">Source Port Range</label>
                            <div style="display: flex; gap: 10px;">
                                <input type="number" id="src-port-min-${ruleId}" class="form-input" placeholder="0" min="0" max="65535">
                                <input type="number" id="src-port-max-${ruleId}" class="form-input" placeholder="65535" min="0" max="65535">
                            </div>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Destination Port Range</label>
                            <div style="display: flex; gap: 10px;">
                                <input type="number" id="dst-port-min-${ruleId}" class="form-input" placeholder="0" min="0" max="65535">
                                <input type="number" id="dst-port-max-${ruleId}" class="form-input" placeholder="65535" min="0" max="65535">
                            </div>
                        </div>
                    </div>
                    <button class="btn btn-danger" onclick="document.getElementById('rule-${ruleId}').remove()">Remove Rule</button>
                </div>
            `;
    container.insertAdjacentHTML('beforeend', ruleHtml);
}

async function createAcl() {
    const tag = document.getElementById('acl-tag').value.trim();
    if (!tag) {
        showAlert('alert-acl', 'Please enter an ACL tag/name', 'error');
        return;
    }

    const rules = [];
    for (let i = 0; i < aclRuleCount; i++) {
        const ruleEl = document.getElementById(`rule-${i}`);
        if (!ruleEl) continue;

        const srcIpFull = document.getElementById(`src-ip-${i}`).value || '0.0.0.0/0';
        const dstIpFull = document.getElementById(`dst-ip-${i}`).value || '0.0.0.0/0';
        const [srcIp, srcPrefix] = srcIpFull.split('/');
        const [dstIp, dstPrefix] = dstIpFull.split('/');

        rules.push({
            action: document.getElementById(`action-${i}`).value,
            proto: parseInt(document.getElementById(`proto-${i}`).value),
            src_ip: srcIp,
            src_prefix_len: parseInt(srcPrefix || 0),
            dst_ip: dstIp,
            dst_prefix_len: parseInt(dstPrefix || 0),
            src_port_min: parseInt(document.getElementById(`src-port-min-${i}`).value || 0),
            src_port_max: parseInt(document.getElementById(`src-port-max-${i}`).value || 65535),
            dst_port_min: parseInt(document.getElementById(`dst-port-min-${i}`).value || 0),
            dst_port_max: parseInt(document.getElementById(`dst-port-max-${i}`).value || 65535)
        });
    }

    // Add default permit rule
    rules.push({
        action: 'permit',
        proto: 0,
        src_ip: '0.0.0.0',
        src_prefix_len: 0,
        dst_ip: '0.0.0.0',
        dst_prefix_len: 0,
        src_port_min: 0,
        src_port_max: 65535,
        dst_port_min: 0,
        dst_port_max: 65535
    });

    try {
        const res = await fetch(`${API_BASE}/acl`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tag,
                rules
            })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        showAlert('alert-acl', `ACL "${tag}" created successfully (index ${data.acl_index})`);
        closeModal('acl-modal');
        loadAcls();
    } catch (err) {
        showAlert('alert-acl', 'Failed to create ACL: ' + err.message, 'error');
    }
}

async function loadAcls() {
    try {
        const res = await fetch(`${API_BASE}/acls`);
        const data = await res.json();

        const container = document.getElementById('acl-list');
        container.innerHTML = data.map(acl => `
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">ACL ${acl.acl_index}: ${acl.tag}</h3>
                            <span class="badge badge-info">${acl.count} rule(s)</span>
                        </div>
                        <table>
                            <thead>
                                <tr>
                                    <th>Action</th>
                                    <th>Protocol</th>
                                    <th>Source</th>
                                    <th>Destination</th>
                                    <th>Ports</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${acl.rules.map(rule => `
                                    <tr>
                                        <td><span class="badge badge-${rule.is_permit ? 'success' : 'danger'}">
                                            ${rule.is_permit ? 'PERMIT' : 'DENY'}
                                        </span></td>
                                        <td>${rule.proto === 0 ? 'ANY' : rule.proto === 1 ? 'ICMP' : rule.proto === 6 ? 'TCP' : rule.proto === 17 ? 'UDP' : rule.proto}</td>
                                        <td>${rule.src_prefix}</td>
                                        <td>${rule.dst_prefix}</td>
                                        <td>${rule.src_port_min}-${rule.src_port_max} → ${rule.dst_port_min}-${rule.dst_port_max}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                        <div style="margin-top: 15px; display: flex; align-items: center; gap: 10px;">
                            <select id="iface-select-${acl.acl_index}" class="form-select" style="width: 200px;">
                                ${currentInterfaces.map(i => `<option value="${i.sw_if_index}">${i.name}</option>`).join('')}
                            </select>
                            <select id="direction-${acl.acl_index}" class="form-select" style="width: 150px;">
                                <option value="true">Input</option>
                                <option value="false">Output</option>
                            </select>
                            <button class="btn btn-success" onclick="applyAcl(${acl.acl_index}, true)">Apply to Interface</button>
                            <button class="btn btn-danger" onclick="applyAcl(${acl.acl_index}, false)">Remove from Interface</button>
                            <button class="btn btn-danger" onclick="deleteAcl(${acl.acl_index})" style="margin-left: auto;">Delete ACL</button>
                        </div>
                    </div>
                `).join('');
    } catch (err) {
        showAlert('alert-acl', 'Failed to load ACLs: ' + err.message, 'error');
    }
}

async function deleteAcl(aclIndex) {
    if (!confirm('Delete this ACL?')) return;

    try {
        await fetch(`${API_BASE}/acl/${aclIndex}`, {
            method: 'DELETE'
        });
        showAlert('alert-acl', 'ACL deleted successfully');
        loadAcls();
    } catch (err) {
        showAlert('alert-acl', 'Failed to delete ACL: ' + err.message, 'error');
    }
}

async function applyAcl(aclIndex, isApply) {
    const sw_if_index = parseInt(document.getElementById(`iface-select-${aclIndex}`).value);
    const is_input = document.getElementById(`direction-${aclIndex}`).value === "true";

    try {
        await fetch(`${API_BASE}/acl/${aclIndex}/interface/${sw_if_index}`, {
            method: isApply ? 'POST' : 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                is_input
            })
        });

        showAlert('alert-acl', `ACL ${isApply ? 'applied to' : 'removed from'} interface ${sw_if_index}`, 'success');
    } catch (err) {
        showAlert('alert-acl', 'Failed to modify ACL: ' + err.message, 'error');
    }
}