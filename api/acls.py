from flask import Blueprint, jsonify, request
from vpp_connection import get_vpp_for_request
import ipaddress
import traceback

acls_bp = Blueprint('acls', __name__)


@acls_bp.route('/api/acls', methods=['GET'])
def get_acls():
    """Get all ACLs"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        acls = v.api.acl_dump(acl_index=0xffffffff)
        result = []

        for acl in acls:
            rules = []
            for rule in acl.r:
                try:
                    # Source prefix
                    if isinstance(rule.src_prefix, ipaddress._BaseNetwork):
                        src_prefix = str(rule.src_prefix)
                    else:
                        src_prefix = f"{rule.src_prefix.address}/{rule.src_prefix.len}"

                    # Destination prefix
                    if isinstance(rule.dst_prefix, ipaddress._BaseNetwork):
                        dst_prefix = str(rule.dst_prefix)
                    else:
                        dst_prefix = f"{rule.dst_prefix.address}/{rule.dst_prefix.len}"

                    rules.append({
                        'is_permit': int(rule.is_permit),
                        'src_prefix': src_prefix,
                        'dst_prefix': dst_prefix,
                        'proto': int(rule.proto),
                        'src_port_min': int(rule.srcport_or_icmptype_first),
                        'src_port_max': int(rule.srcport_or_icmptype_last),
                        'dst_port_min': int(rule.dstport_or_icmpcode_first),
                        'dst_port_max': int(rule.dstport_or_icmpcode_last)
                    })

                except Exception as e:
                    print(f"Error processing ACL rule: {e}")
                    continue

            result.append({
                'acl_index': int(acl.acl_index),
                'tag': acl.tag if isinstance(acl.tag, str) else acl.tag.decode(errors='ignore'),
                'count': int(getattr(acl, 'count', len(acl.r))),
                'rules': rules
            })

        return jsonify(result)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in get_acls: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500



@acls_bp.route('/api/acl', methods=['POST'])
def create_acl():
    """Create a new ACL"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json
        tag = data.get('tag', 'custom-acl')
        rules = data.get('rules', [])

        acl_rules = []
        for rule in rules:
            # IP + prefix length
            src_ip = rule.get('src_ip', '0.0.0.0')
            dst_ip = rule.get('dst_ip', '0.0.0.0')

            src_prefix_len = int(rule.get('src_prefix_len', 32 if src_ip != '0.0.0.0' else 0))
            dst_prefix_len = int(rule.get('dst_prefix_len', 32 if dst_ip != '0.0.0.0' else 0))

            src_network = ipaddress.ip_network(f"{src_ip}/{src_prefix_len}", strict=False)
            dst_network = ipaddress.ip_network(f"{dst_ip}/{dst_prefix_len}", strict=False)

            acl_rule = {
                'is_permit': 1 if rule.get('action', 'permit') == 'permit' else 0,
                'src_prefix': src_network,
                'dst_prefix': dst_network,
                'proto': int(rule.get('proto', 0)),
                'srcport_or_icmptype_first': int(rule.get('src_port_min', 0)),
                'srcport_or_icmptype_last': int(rule.get('src_port_max', 65535)),
                'dstport_or_icmpcode_first': int(rule.get('dst_port_min', 0)),
                'dstport_or_icmpcode_last': int(rule.get('dst_port_max', 65535)),
                'tcp_flags_mask': 0,
                'tcp_flags_value': 0
            }

            acl_rules.append(acl_rule)

        # ✔ KEEP LOGS
        print(f"Sending ACL '{tag}' with {len(acl_rules)} rule(s) to VPP:")
        for r in acl_rules:
            print(
                f"{'PERMIT' if r['is_permit'] else 'DENY'} "
                f"{r['src_prefix']} -> {r['dst_prefix']} "
                f"proto {r['proto']} "
                f"sports {r['srcport_or_icmptype_first']}-{r['srcport_or_icmptype_last']} "
                f"-> dports {r['dstport_or_icmpcode_first']}-{r['dstport_or_icmpcode_last']}"
            )

        resp = v.api.acl_add_replace(
            acl_index=0xFFFFFFFF,
            tag=tag,
            count=len(acl_rules),
            r=acl_rules
        )

        return jsonify({'success': True, 'acl_index': resp.acl_index})

    except Exception as e:
        error_trace = traceback.format_exc()
        print("Error in create_acl:", e)
        print(error_trace)
        return jsonify({'error': str(e), 'trace': error_trace}), 500



@acls_bp.route('/api/acl/<int:acl_index>', methods=['DELETE'])
def delete_acl(acl_index):
    """Delete an ACL by index"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        v.api.acl_del(acl_index=acl_index)

        return jsonify({'success': True, 'deleted_acl': acl_index})

    except Exception as e:
        print(f"Error deleting ACL: {e}")
        return jsonify({'error': str(e)}), 500



@acls_bp.route('/api/acl/<int:acl_index>/interface/<int:sw_if_index>', methods=['POST', 'DELETE'])
def apply_acl_to_interface(acl_index, sw_if_index):
    """Attach or detach an ACL to/from a specific interface"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.get_json(force=True)
        is_input = data.get('is_input', True)
        is_add = 1 if request.method == 'POST' else 0

        current = v.api.acl_interface_list_dump(sw_if_index=sw_if_index)

        current_input = []
        current_output = []

        for entry in current:
            current_input = list(entry.acls[:entry.n_input])
            current_output = list(entry.acls[entry.n_input:])

        # Modify ACL list based on action
        if is_input:
            if is_add and acl_index not in current_input:
                current_input.append(acl_index)
            elif not is_add and acl_index in current_input:
                current_input.remove(acl_index)
        else:
            if is_add and acl_index not in current_output:
                current_output.append(acl_index)
            elif not is_add and acl_index in current_output:
                current_output.remove(acl_index)

        updated_acls = current_input + current_output

        v.api.acl_interface_set_acl_list(
            sw_if_index=sw_if_index,
            count=len(updated_acls),
            n_input=len(current_input),
            acls=updated_acls
        )

        action = "attached" if is_add else "detached"

        return jsonify({
            'success': True,
            'interface': sw_if_index,
            'acl_index': acl_index,
            'action': action,
            'is_input': is_input,
            'input_acls': current_input,
            'output_acls': current_output
        })

    except Exception as e:
        print(f"Error applying/removing ACL: {e}")
        return jsonify({'error': str(e)}), 500
