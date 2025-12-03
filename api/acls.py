from flask import Blueprint, jsonify, request
from vpp_connection import get_vpp_for_request
import ipaddress
import traceback
# import logging

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

acls_bp = Blueprint('acls', __name__)


@acls_bp.route('/api/acl/<int:acl_index>/rule', methods=['POST'])
def add_acl_rule(acl_index):
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        print(dir(v.api))
        print(v.api.__dict__.keys())
        data = request.json
        # logger.debug(dir(v.api))
        # logger.debug(v.api.__dict__.keys())
        src_ip = data.get('src_ip', '0.0.0.0')
        dst_ip = data.get('dst_ip', '0.0.0.0')

        src_prefix_len = int(data.get('src_prefix_len', 0 if src_ip == '0.0.0.0' else 32))
        dst_prefix_len = int(data.get('dst_prefix_len', 0 if dst_ip == '0.0.0.0' else 32))

        # Load VPP rule class
        rule_cls = v.api._types['vl_api_acl_rule_t']

        # Create new ACL rule struct
        new_rule = rule_cls(
            is_permit = 1 if data.get('action') == 'permit' else 0,
            src_prefix = ipaddress.ip_network(f"{src_ip}/{src_prefix_len}", strict=False),
            dst_prefix = ipaddress.ip_network(f"{dst_ip}/{dst_prefix_len}", strict=False),
            proto = int(data.get('proto', 0)),
            srcport_or_icmptype_first = int(data.get('src_port_min', 0)),
            srcport_or_icmptype_last  = int(data.get('src_port_max', 65535)),
            dstport_or_icmpcode_first = int(data.get('dst_port_min', 0)),
            dstport_or_icmpcode_last  = int(data.get('dst_port_max', 65535)),
            tcp_flags_mask = 0,
            tcp_flags_value = 0
        )

 
        # Load existing ACL
        acl_dump = v.api.acl_dump(acl_index=acl_index)
        if not acl_dump:
            return jsonify({'error': 'ACL not found'}), 404

        # Copy existing rule structs
        existing_rules = list(acl_dump[0].r)

        # Append our new struct rule
        existing_rules.append(new_rule)

        rule_cls = v.api._msg_definitions['vl_api_acl_rule_t']
        print(dir(rule_cls))

        # Replace ACL with updated rule list
        resp = v.api.acl_add_replace(
            acl_index=acl_index,
            tag=acl_dump[0].tag,
            count=len(existing_rules),
            r=existing_rules
        )

        return jsonify({
            'success': True,
            'acl_index': acl_index,
            'rule_count': len(existing_rules)
        })

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500



@acls_bp.route('/api/acl/<int:acl_index>/rule/<int:rule_index>', methods=['DELETE'])
def delete_acl_rule(acl_index, rule_index):
    """Delete a specific rule from an ACL"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        acl_dump = v.api.acl_dump(acl_index=acl_index)
        if not acl_dump:
            return jsonify({'error': f'ACL {acl_index} not found'}), 404

        rules = list(acl_dump[0].r)
        if rule_index >= len(rules):
            return jsonify({'error': f'Rule index {rule_index} out of range'}), 400

        rules.pop(rule_index)

        # Replace ACL
        resp = v.api.acl_add_replace(
            acl_index=acl_index,
            tag=acl_dump[0].tag,
            count=len(rules),
            r=rules
        )

        return jsonify({'success': True, 'acl_index': acl_index, 'rule_count': len(rules)})

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@acls_bp.route('/api/acl/<int:acl_index>/rule/<int:rule_index>', methods=['PUT'])
def edit_acl_rule(acl_index, rule_index):
    """Edit a specific rule in an ACL"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json

        acl_dump = v.api.acl_dump(acl_index=acl_index)
        if not acl_dump:
            return jsonify({'error': f'ACL {acl_index} not found'}), 404

        rules = list(acl_dump[0].r)
        if rule_index >= len(rules):
            return jsonify({'error': f'Rule index {rule_index} out of range'}), 400

        # Build updated rule
        src_ip = data.get('src_ip', str(rules[rule_index].src_prefix.network_address))
        dst_ip = data.get('dst_ip', str(rules[rule_index].dst_prefix.network_address))
        src_prefix_len = int(data.get('src_prefix_len', rules[rule_index].src_prefix.prefixlen))
        dst_prefix_len = int(data.get('dst_prefix_len', rules[rule_index].dst_prefix.prefixlen))

        rules[rule_index] = {
            'is_permit': 1 if data.get('action', 'permit') == 'permit' else 0,
            'src_prefix': ipaddress.ip_network(f"{src_ip}/{src_prefix_len}", strict=False),
            'dst_prefix': ipaddress.ip_network(f"{dst_ip}/{dst_prefix_len}", strict=False),
            'proto': int(data.get('proto', rules[rule_index].proto)),
            'srcport_or_icmptype_first': int(data.get('src_port_min', rules[rule_index].srcport_or_icmptype_first)),
            'srcport_or_icmptype_last': int(data.get('src_port_max', rules[rule_index].srcport_or_icmptype_last)),
            'dstport_or_icmpcode_first': int(data.get('dst_port_min', rules[rule_index].dstport_or_icmpcode_first)),
            'dstport_or_icmpcode_last': int(data.get('dst_port_max', rules[rule_index].dstport_or_icmpcode_last)),
            'tcp_flags_mask': 0,
            'tcp_flags_value': 0
        }

        # Replace ACL
        resp = v.api.acl_add_replace(
            acl_index=acl_index,
            tag=acl_dump[0].tag,
            count=len(rules),
            r=rules
        )

        return jsonify({'success': True, 'acl_index': acl_index, 'rule_index': rule_index})

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


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

@acls_bp.route('/api/aclinterfaces', methods=['GET'])
def get_interface_acls():
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        res = []

        # Dump interfaces
        intfs = v.api.sw_interface_dump(sw_if_index=0xffffffff)

        for intf in intfs:
            swid = intf.sw_if_index
            name = intf.interface_name
            if isinstance(name, bytes):
                name = name.decode(errors='ignore')

            # Dump ACLs applied to this interface
            dump = v.api.acl_interface_list_dump(sw_if_index=swid)

            input_acls = []
            output_acls = []

            for rec in dump:
                if rec.sw_if_index != swid:
                    continue

                if rec.n_input > 0:
                    input_acls = list(rec.acls[:rec.n_input])

                if rec.count > rec.n_input:
                    output_acls = list(rec.acls[rec.n_input:rec.count])

            res.append({
                "sw_if_index": swid,
                "name": name,
                "input_acls": input_acls,
                "output_acls": output_acls
            })

        return jsonify(res)

    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500



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
