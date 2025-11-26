from flask import Blueprint, jsonify, request
from vpp_connection import get_vpp_for_request
import traceback
import logging
import ipaddress

interfaces_bp = Blueprint('interfaces', __name__)

# -------- Get interface list --------
@interfaces_bp.route('/api/interfaces', methods=['GET'])
def get_interfaces():
    """Get all interfaces with their configuration"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        interfaces = v.api.sw_interface_dump()
        result = []

        for iface in interfaces:
            # Get IP addresses
            ip_addrs = []
            try:
                addrs = v.api.ip_address_dump(sw_if_index=iface.sw_if_index)
                for addr in addrs:
                    # prefix.address.af == 0 → IPv4
                    if hasattr(addr, "prefix") and hasattr(addr.prefix, "address"):
                        prefix = addr.prefix
                        if prefix.address.af == 0:  # IPv4
                            ip = ipaddress.IPv4Address(prefix.address.un.ip4)
                            ip_addrs.append(f"{ip}/{prefix.len}")
                    else:
                        # fallback string
                        try:
                            ip_addrs.append(str(addr.prefix))
                        except:
                            pass
            except Exception as e:
                print(f"Error getting IPs for interface {iface.sw_if_index}: {e}")

            result.append({
                'sw_if_index': iface.sw_if_index,
                'name': iface.interface_name,
                'status': 'up' if iface.flags & 1 else 'down',
                'mtu': iface.mtu[0] if hasattr(iface, 'mtu') and iface.mtu else 0,
                'ip_addresses': ip_addrs
            })

        return jsonify(result)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in get_interfaces: {e}")
        print(error_trace)
        return jsonify({'error': str(e), 'trace': error_trace}), 500



@interfaces_bp.route('/api/interface/<int:sw_if_index>/status', methods=['POST'])
def set_interface_status(sw_if_index):
    """Set interface up/down"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json
        flags = 1 if data.get('up', True) else 0

        v.api.sw_interface_set_flags(sw_if_index=sw_if_index, flags=flags)
        return jsonify({'success': True, 'status': 'up' if flags else 'down'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@interfaces_bp.route('/api/interface/<int:sw_if_index>/ip', methods=['POST', 'DELETE'])
def manage_interface_ip(sw_if_index):
    """Add or remove IP address from interface"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json
        ip_addr = data.get('ip')
        prefix_len = int(data.get('prefix_len', 24))

        ip_packed = ipaddress.IPv4Address(ip_addr).packed
        is_add = 1 if request.method == 'POST' else 0

        v.api.sw_interface_add_del_address(
            sw_if_index=sw_if_index,
            is_add=is_add,
            prefix={
                "address": {"af": 0, "un": {"ip4": ip_packed}},
                "len": prefix_len
            },
            del_all=0
        )

        action = 'added' if is_add else 'removed'
        return jsonify({'success': True, 'message': f'IP {action}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@interfaces_bp.route("/api/interfaces/stats", methods=["GET"])
def get_interface_stats_binary():
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({"error": "Not connected to VPP"}), 500

        # --- fetch available counters (try/except to avoid KeyError) ---
        try:
            stats_names = v.vpp_stats.get_counter("/if/names")
        except Exception:
            stats_names = []

        def safe_get(path):
            try:
                return v.vpp_stats.get_counter(path)
            except Exception:
                print(f"counter {path} not available")
                return None

        stats_rx = safe_get("/if/rx")
        stats_tx = safe_get("/if/tx")
        stats_drops = safe_get("/if/drops")

        interfaces = []
        n = len(stats_names) if stats_names else 0

        for i in range(n):
            rx_bytes = 0
            rx_packets = 0
            tx_bytes = 0
            tx_packets = 0
            drops_total = 0

            for th in stats_rx or []:
                rx_bytes += th[i]["bytes"]
                rx_packets += th[i]["packets"]
            for th in stats_tx or []:
                tx_bytes += th[i]["bytes"]
                tx_packets += th[i]["packets"]
            for th in stats_drops or []:
                drops_total += th[i]

            interfaces.append({
                "name": stats_names[i],
                "rx_bytes": int(rx_bytes),
                "tx_bytes": int(tx_bytes),
                "rx_packets": int(rx_packets),
                "tx_packets": int(tx_packets),
                "drops": int(drops_total)
            })

        return jsonify(interfaces)

    except Exception as e:
        print("Exception occurred in get_interface_stats_binary:")
        traceback.print_exc()
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
