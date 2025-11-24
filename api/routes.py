from flask import Blueprint, jsonify, request
from vpp_connection import get_vpp_connection
import ipaddress
import traceback
import socket

routes_bp = Blueprint('routes', __name__)

@routes_bp.route('/api/routes', methods=['GET'])
def get_routes():
    """List all IPv4 routes."""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        # Map sw_if_index → interface name
        interfaces = v.api.sw_interface_dump()
        if_names = {iface.sw_if_index: iface.interface_name for iface in interfaces}

        # Dump all IPv4 routes
        routes = v.api.ip_route_dump(table={'table_id': 0, 'is_ip6': 0})
      
        result = []
        for route in routes:
            prefix = route.route.prefix

            # Build readable destination prefix
            dst_str = str(prefix)

            # Extract each path (next-hop + interface)
            for path in route.route.paths:
                # Some routes have empty next-hop (direct)
                if hasattr(path.nh, "address") and hasattr(path.nh.address, "ip4"):
                    nh_ip = ipaddress.IPv4Address(path.nh.address.ip4)
                    nh_str = str(nh_ip)
                else:
                    nh_str = "direct"

                result.append({
                    "destination": dst_str,
                    "next_hop": nh_str,
                    "interface": if_names.get(path.sw_if_index, f"if{path.sw_if_index}"),
                    "sw_if_index": path.sw_if_index
                })

        return jsonify(result)

    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

@routes_bp.route('/api/route', methods=['POST', 'DELETE'])
def manage_route():
    """
    Add or delete an IPv4 route in VPP.
    Uses ip_route_add_del_v2 when available (VPP ≥24.06),
    falls back to ip_route_add_del for older versions.
    """

    try:
        # Parse input JSON
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON payload"}), 400

        dst = data.get("destination", "0.0.0.0")
        prefix_len = int(data.get("prefix_len", 0))
        sw_if_index = int(data.get("sw_if_index", 0))
        next_hop = data.get("next_hop", "0.0.0.0")

        if not dst:
            return jsonify({"error": "Missing destination"}), 400

        v = get_vpp_connection()
        if not v:
            return jsonify({"error": "VPP connection failed"}), 500

        # Convert IPs to binary
        dst_bin = socket.inet_pton(socket.AF_INET, dst)
        nh_bin = socket.inet_pton(socket.AF_INET, next_hop)

        # Choose proper API call
        use_v2 = hasattr(v.api, "ip_route_add_del_v2")
        api_call = v.api.ip_route_add_del_v2 if use_v2 else v.api.ip_route_add_del

        # Define the path entry
        path_entry = {
            "sw_if_index": sw_if_index,
            "weight": 1,
            "preference": 0,
            "proto": 0,  # IPv4
        }

        # Add next-hop and additional fields depending on API version
        if use_v2:
            # Create empty label stack with 16 elements (fixed size requirement)
            empty_label = {"label": 0, "ttl": 0, "exp": 0, "is_uniform": 0}
            label_stack = [empty_label] * 16
            
            path_entry.update({
                "nh": {"ip4": nh_bin},
                "n_labels": 0,
                "label_stack": label_stack  # Must be exactly 16 elements
            })
        else:
            path_entry.update({
                "table_id": 0,
                "type": 0,
                "flags": 0,
                "n_labels": 0,
                "nh": {"address": {"af": 0, "un": {"ip4": nh_bin}}}
            })

        # Wrap route object
        if use_v2:
            route_data = {
                "table_id": 0,
                "prefix": {
                    "af": 0,  # IPv4
                    "address": {"ip4": dst_bin},
                    "len": prefix_len
                },
                "n_paths": 1,
                "paths": [path_entry]
            }
        else:
            route_data = {
                "prefix": {
                    "address": {"af": 0, "un": {"ip4": dst_bin}},
                    "len": prefix_len
                },
                "table_id": 0,
                "n_paths": 1,
                "paths": [path_entry]
            }

        # Perform add or delete
        api_call(
            is_add=1 if request.method == "POST" else 0,
            is_multipath=False,
            route=route_data
        )

        action = "added" if request.method == "POST" else "deleted"
        return jsonify({"status": f"Route {action} successfully"}), 200

    except Exception as e:
        print("❌ Route management error:")
        print(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500