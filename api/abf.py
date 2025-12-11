# abf.py
from flask import Blueprint, jsonify, request
from vpp_connection import get_vpp_for_request
import traceback
import time

abf_bp = Blueprint('abf', __name__, url_prefix='/api/abf')

# -------- Get ABF policy --------
@abf_bp.route('/policy', methods=['GET'])
def get_abf_policy():
    """Get all ABF policies"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        result = v.api.abf_policy_dump()

        policies = []

        for item in result:
            policy = item.policy
            
            # Paths listini parse qilish
            paths = []
            for p in policy.paths:
                # IP manzil IP4 yoki IP6 bo'lishi mumkin
                nh_ip = None
                if p.nh.address.ip4:
                    nh_ip = str(p.nh.address.ip4)
                elif p.nh.address.ip6:
                    nh_ip = str(p.nh.address.ip6)

                paths.append({
                    "sw_if_index": p.sw_if_index,
                    "table_id": p.table_id,
                    "weight": p.weight,
                    "preference": p.preference,
                    "type": p.type.name,
                    "proto": p.proto.name,
                    "next_hop": nh_ip
                })

            policies.append({
                "policy_id": policy.policy_id,
                "acl_index": policy.acl_index,
                "n_paths": policy.n_paths,
                "paths": paths
            })

        return jsonify({"policies": policies})

    except Exception as e:
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500

# -------- Add ABF Policy --------
@abf_bp.route('/policy', methods=['POST'])
def add_abf_policy():
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        data = request.json

        policy_id = data.get("policy_id")
        acl_index = data.get("acl_index")
        paths_data = data.get("paths", [])

        if policy_id is None or acl_index is None or not paths_data:
            return jsonify({'error': 'policy_id, acl_index, and paths are required'}), 400

        # Prepare paths for VPP
        paths = []
        for p in paths_data:
            paths.append({
                "sw_if_index": p["sw_if_index"],
                "table_id": p.get("table_id", 0),
                "type": 0,  # NORMAL
                "weight": p.get("weight", 1),
                "preference": p.get("preference", 0),
                "proto": 0,  # IPv4
                "nh": {
                    "address": {
                        "ip4": p["next_hop"]
                    }
                },
                "label_stack": [0]*16
            })

        # Call VPP API to add ABF policy
        reply = v.api.abf_policy_add_del(
            is_add=True,
            policy={
                "policy_id": policy_id,
                "acl_index": acl_index,
                "n_paths": len(paths),
                "paths": paths
            }
        )
        print(f"ABF Policy added: {reply}")

        return jsonify({
            "status": "success",
            "vpp_reply": reply
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


# -------- Delete ABF Policy --------
@abf_bp.route('/policy/<int:policy_id>', methods=['DELETE'])
def delete_abf_policy(policy_id):
    """Delete ABF policy by ID in URL"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        # 1️⃣ Find the policy with its current paths
        dump = v.api.abf_policy_dump()
        acl_index = None
        current_paths = []
        policy_found = False
        
        for item in dump:
            if item.policy.policy_id == policy_id:
                acl_index = item.policy.acl_index
                # Convert VPP path objects to dictionaries
                for p in item.policy.paths:
                    path_dict = {
                        "sw_if_index": p.sw_if_index,
                        "table_id": p.table_id,
                        "rpf_id": p.rpf_id,
                        "weight": p.weight,
                        "preference": p.preference,
                        "type": int(p.type),
                        "flags": int(p.flags),
                        "proto": int(p.proto),
                        "nh": {
                            "address": {
                                "ip4": str(p.nh.address.ip4) if p.proto == 0 else "0.0.0.0",
                                "ip6": str(p.nh.address.ip6) if p.proto == 1 else "::"
                            },
                            "via_label": p.nh.via_label,
                            "obj_id": p.nh.obj_id,
                            "classify_table_index": p.nh.classify_table_index
                        },
                        "n_labels": p.n_labels,
                        "label_stack": [{"is_uniform": 0, "label": 0, "ttl": 0, "exp": 0} for _ in range(16)]
                    }
                    current_paths.append(path_dict)
                policy_found = True
                break

        if not policy_found:
            return jsonify({"error": f"Policy {policy_id} not found"}), 404

        # 2️⃣ Detach policy from all interfaces first
        attaches = v.api.abf_itf_attach_dump()
        detached_count = 0
        for a in attaches:
            if a.attach.policy_id == policy_id:
                v.api.abf_itf_attach_add_del(
                    is_add=False,
                    attach={
                        "policy_id": policy_id,
                        "priority": a.attach.priority,
                        "sw_if_index": a.attach.sw_if_index
                    }
                )
                detached_count += 1

        # Small delay to ensure detachment completes
        time.sleep(0.1)

        # 3️⃣ Delete the policy WITH its current paths (VPP requirement)
        # VPP expects the paths to be provided when deleting
        reply = v.api.abf_policy_add_del(
            is_add=False,
            policy={
                "policy_id": policy_id,
                "acl_index": acl_index,
                "n_paths": len(current_paths),
                "paths": current_paths
            }
        )

        # Verify deletion
        time.sleep(0.1)
        verify_dump = v.api.abf_policy_dump()
        still_exists = any(item.policy.policy_id == policy_id for item in verify_dump)
        
        if still_exists:
            return jsonify({
                "status": "warning",
                "message": f"Policy {policy_id} detached from {detached_count} interface(s), but deletion may have failed",
                "vpp_reply": reply,
                "note": "Policy still appears in dump. VPP may require additional steps."
            }), 200

        return jsonify({
            "status": "success",
            "message": f"Policy {policy_id} detached from {detached_count} interface(s) and deleted successfully",
            "vpp_reply": reply
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

# -------- Update ABF Policy --------
@abf_bp.route('/policy/<int:policy_id>', methods=['PUT'])
def update_abf_policy(policy_id):
    """Update an existing ABF policy"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        data = request.json
        acl_index = data.get("acl_index")
        paths_data = data.get("paths", [])

        if acl_index is None or not paths_data:
            return jsonify({'error': 'acl_index and paths are required'}), 400

        # 1️⃣ Check if policy exists
        dump = v.api.abf_policy_dump()
        policy_exists = any(item.policy.policy_id == policy_id for item in dump)
        
        if not policy_exists:
            return jsonify({'error': f'Policy {policy_id} not found'}), 404

        # 2️⃣ Prepare new paths
        paths = []
        for p in paths_data:
            paths.append({
                "sw_if_index": p["sw_if_index"],
                "table_id": p.get("table_id", 0),
                "rpf_id": 0,
                "weight": p.get("weight", 1),
                "preference": p.get("preference", 0),
                "type": 0,  # NORMAL
                "flags": 0,  # NONE
                "proto": 0,  # IPv4
                "nh": {
                    "address": {
                        "ip4": p["next_hop"],
                        "ip6": "::"
                    },
                    "via_label": 0,
                    "obj_id": 0,
                    "classify_table_index": 0
                },
                "n_labels": 0,
                "label_stack": [{"is_uniform": 0, "label": 0, "ttl": 0, "exp": 0} for _ in range(16)]
            })

        # 3️⃣ Update the policy (is_add=True updates existing policy)
        reply = v.api.abf_policy_add_del(
            is_add=True,  # True means add/update
            policy={
                "policy_id": policy_id,
                "acl_index": acl_index,
                "n_paths": len(paths),
                "paths": paths
            }
        )

        return jsonify({
            "status": "success",
            "message": f"Policy {policy_id} updated successfully",
            "vpp_reply": reply
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

# -------- Get ABF Interface Attachments --------
@abf_bp.route('/attach', methods=['GET'])
def get_abf_attachments():
    """Get all ABF policy attachments to interfaces"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        result = v.api.abf_itf_attach_dump()

        attachments = []
        for item in result:
            attach = item.attach
            attachments.append({
                "policy_id": attach.policy_id,
                "sw_if_index": attach.sw_if_index,
                "priority": attach.priority,
                "is_ipv6": attach.is_ipv6
            })

        return jsonify({"attachments": attachments}), 200

    except Exception as e:
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500


# -------- Get ABF Attachments for Specific Interface --------
@abf_bp.route('/attach/interface/<int:sw_if_index>', methods=['GET'])
def get_abf_attachments_by_interface(sw_if_index):
    """Get all ABF policy attachments for a specific interface"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        result = v.api.abf_itf_attach_dump()

        attachments = []
        for item in result:
            attach = item.attach
            if attach.sw_if_index == sw_if_index:
                attachments.append({
                    "policy_id": attach.policy_id,
                    "sw_if_index": attach.sw_if_index,
                    "priority": attach.priority,
                    "is_ipv6": attach.is_ipv6
                })

        return jsonify({
            "sw_if_index": sw_if_index,
            "attachments": attachments
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500


# -------- Get ABF Attachments for Specific Policy --------
@abf_bp.route('/attach/policy/<int:policy_id>', methods=['GET'])
def get_abf_attachments_by_policy(policy_id):
    """Get all interface attachments for a specific ABF policy"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        result = v.api.abf_itf_attach_dump()

        attachments = []
        for item in result:
            attach = item.attach
            if attach.policy_id == policy_id:
                attachments.append({
                    "policy_id": attach.policy_id,
                    "sw_if_index": attach.sw_if_index,
                    "priority": attach.priority,
                    "is_ipv6": attach.is_ipv6
                })

        return jsonify({
            "policy_id": policy_id,
            "attachments": attachments
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500


# -------- Add ABF Interface Attachment --------
@abf_bp.route('/attach', methods=['POST'])
def add_abf_attachment():
    """Attach an ABF policy to an interface"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        data = request.json

        policy_id = data.get("policy_id")
        sw_if_index = data.get("sw_if_index")
        priority = data.get("priority", 0)
        is_ipv6 = data.get("is_ipv6", False)

        if policy_id is None or sw_if_index is None:
            return jsonify({'error': 'policy_id and sw_if_index are required'}), 400

        # Check if policy exists
        policies = v.api.abf_policy_dump()
        policy_exists = any(item.policy.policy_id == policy_id for item in policies)
        
        if not policy_exists:
            return jsonify({'error': f'Policy {policy_id} does not exist'}), 404

        # Attach policy to interface
        reply = v.api.abf_itf_attach_add_del(
            is_add=True,
            attach={
                "policy_id": policy_id,
                "sw_if_index": sw_if_index,
                "priority": priority,
                "is_ipv6": is_ipv6
            }
        )

        return jsonify({
            "status": "success",
            "message": f"Policy {policy_id} attached to interface {sw_if_index}",
            "vpp_reply": reply
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


# -------- Update ABF Interface Attachment --------
@abf_bp.route('/attach/<int:policy_id>/<int:sw_if_index>', methods=['PUT'])
def update_abf_attachment(policy_id, sw_if_index):
    """Update an ABF policy attachment (change priority or IPv6 setting)"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        data = request.json
        priority = data.get("priority")
        is_ipv6 = data.get("is_ipv6")

        if priority is None and is_ipv6 is None:
            return jsonify({'error': 'priority or is_ipv6 is required'}), 400

        # Check if attachment exists
        attachments = v.api.abf_itf_attach_dump()
        attachment_exists = False
        current_priority = 0
        current_is_ipv6 = False
        
        for item in attachments:
            if item.attach.policy_id == policy_id and item.attach.sw_if_index == sw_if_index:
                attachment_exists = True
                current_priority = item.attach.priority
                current_is_ipv6 = item.attach.is_ipv6
                break

        if not attachment_exists:
            return jsonify({
                'error': f'Attachment not found for policy {policy_id} on interface {sw_if_index}'
            }), 404

        # Use provided values or keep current ones
        new_priority = priority if priority is not None else current_priority
        new_is_ipv6 = is_ipv6 if is_ipv6 is not None else current_is_ipv6

        # Update attachment (is_add=True updates existing attachment)
        reply = v.api.abf_itf_attach_add_del(
            is_add=True,
            attach={
                "policy_id": policy_id,
                "sw_if_index": sw_if_index,
                "priority": new_priority,
                "is_ipv6": new_is_ipv6
            }
        )

        return jsonify({
            "status": "success",
            "message": f"Attachment updated for policy {policy_id} on interface {sw_if_index}",
            "vpp_reply": reply
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


# -------- Delete ABF Interface Attachment --------
@abf_bp.route('/attach/<int:policy_id>/<int:sw_if_index>', methods=['DELETE'])
def delete_abf_attachment(policy_id, sw_if_index):
    """Detach an ABF policy from an interface"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        # Find the attachment
        attachments = v.api.abf_itf_attach_dump()
        attachment_found = False
        priority = 0
        is_ipv6 = False
        
        for item in attachments:
            if item.attach.policy_id == policy_id and item.attach.sw_if_index == sw_if_index:
                attachment_found = True
                priority = item.attach.priority
                is_ipv6 = item.attach.is_ipv6
                break

        if not attachment_found:
            return jsonify({
                'error': f'Attachment not found for policy {policy_id} on interface {sw_if_index}'
            }), 404

        # Detach policy from interface
        reply = v.api.abf_itf_attach_add_del(
            is_add=False,
            attach={
                "policy_id": policy_id,
                "sw_if_index": sw_if_index,
                "priority": priority,
                "is_ipv6": is_ipv6
            }
        )

        return jsonify({
            "status": "success",
            "message": f"Policy {policy_id} detached from interface {sw_if_index}",
            "vpp_reply": reply
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


# -------- Delete All Attachments for a Policy --------
@abf_bp.route('/attach/policy/<int:policy_id>', methods=['DELETE'])
def delete_all_attachments_for_policy(policy_id):
    """Detach an ABF policy from all interfaces"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        # Find all attachments for this policy
        attachments = v.api.abf_itf_attach_dump()
        detached_count = 0
        
        for item in attachments:
            if item.attach.policy_id == policy_id:
                v.api.abf_itf_attach_add_del(
                    is_add=False,
                    attach={
                        "policy_id": item.attach.policy_id,
                        "sw_if_index": item.attach.sw_if_index,
                        "priority": item.attach.priority,
                        "is_ipv6": item.attach.is_ipv6
                    }
                )
                detached_count += 1

        if detached_count == 0:
            return jsonify({
                'message': f'No attachments found for policy {policy_id}'
            }), 200

        return jsonify({
            "status": "success",
            "message": f"Policy {policy_id} detached from {detached_count} interface(s)",
            "detached_count": detached_count
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500


# -------- Delete All Attachments for an Interface --------
@abf_bp.route('/attach/interface/<int:sw_if_index>', methods=['DELETE'])
def delete_all_attachments_for_interface(sw_if_index):
    """Detach all ABF policies from an interface"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        # Find all attachments for this interface
        attachments = v.api.abf_itf_attach_dump()
        detached_count = 0
        
        for item in attachments:
            if item.attach.sw_if_index == sw_if_index:
                v.api.abf_itf_attach_add_del(
                    is_add=False,
                    attach={
                        "policy_id": item.attach.policy_id,
                        "sw_if_index": item.attach.sw_if_index,
                        "priority": item.attach.priority,
                        "is_ipv6": item.attach.is_ipv6
                    }
                )
                detached_count += 1

        if detached_count == 0:
            return jsonify({
                'message': f'No attachments found for interface {sw_if_index}'
            }), 200

        return jsonify({
            "status": "success",
            "message": f"All policies detached from interface {sw_if_index}",
            "detached_count": detached_count
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500