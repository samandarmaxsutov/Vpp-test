from flask import Blueprint, jsonify
from vpp_connection import get_vpp_for_request
import logging
import psutil
import time
import re

# Initialize Flask Blueprint
dashboard_bp = Blueprint('dashboard', __name__)
logging.basicConfig(level=logging.INFO)

# --- Helper Function for VPP Memory Parsing (Required if 'memory_stats' API is unavailable) ---
def parse_size(size_str):
    """Helper to convert VPP memory strings (e.g., '1.2G', '500K') to bytes."""
    units = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    match = re.match(r"([\d\.]+)([KMGT]?)", size_str.upper())
    if match:
        val, unit = match.groups()
        return float(val) * units.get(unit, 1)
    return 0

def get_vpp_memory_usage_internal(v):
    """
    Attempts to get VPP internal memory stats via CLI command 'show memory'.
    Returns dictionary with sizes in bytes.
    """
    try:
        # Use CLI because the binary API 'memory_stats' is often missing or complex to link
        response = v.api.cli_inband(cmd='show memory main-heap')
        output = response.reply

        stats = {"total": 0, "used": 0, "free": 0}

        # Regex to find standard stats pattern (often highly allocator-dependent)
        total_match = re.search(r'total:\s*([\d\.]+[KMGT]?)', output, re.IGNORECASE)
        used_match = re.search(r'used:\s*([\d\.]+[KMGT]?)', output, re.IGNORECASE)
        free_match = re.search(r'free:\s*([\d\.]+[KMGT]?)', output, re.IGNORECASE)

        if total_match: stats['total'] = parse_size(total_match.group(1))
        if used_match: stats['used'] = parse_size(used_match.group(1))
        if free_match: stats['free'] = parse_size(free_match.group(1))

        return stats

    except Exception as e:
        logging.error(f"VPP Internal Memory stats error: {e}")
        return {}
    
# --- Main API Route ---

@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """
    Gathers system resources (CPU/RAM percentages) and VPP network statistics.
    """
    try:
        # --- 1. System Resources (Independent of VPP connection) ---
        
        # CPU: Get per-core usage list. We use interval=0.1 for a quick update.
        # This will return a list of percentages for each logical CPU/core.
        cpu_cores_list = psutil.cpu_percent(interval=0.1, percpu=True)
        # Calculate the aggregate average load from the core list
        cpu_aggregate = round(sum(cpu_cores_list) / len(cpu_cores_list))
        
        # RAM: System-wide memory usage
        mem = psutil.virtual_memory()
        mem_usage_percent = mem.percent
        mem_total_str = f"{mem.total / (1024**3):.1f} GB"

        # VPP Internal Memory (Optional, depends on how VPP is configured)
        # This is commented out to prioritize the System RAM percentage for the FortiGate style.
        # vpp_mem_internal = get_vpp_memory_usage_internal(v)

        # --- 2. VPP Network Stats (Requires connection) ---
        v = get_vpp_for_request()
        
        if not v:
            # If VPP is down, return System stats and zero network stats
            return jsonify({
                'cpu': {'aggregate': cpu_aggregate, 'cores': cpu_cores_list},
                'memory': mem_usage_percent,
                'memory_total': mem_total_str,
                'interfaces': {'total': 0, 'active': 0},
                'routes': 0,
                'acls': 0,
                'nat_sessions': 0,
                'uptime': "VPP Down"
            })

        # VPP operational data retrieval
        interfaces = v.api.sw_interface_dump()
        total_interfaces = len(interfaces)
        active_interfaces = sum(1 for iface in interfaces if iface.flags & 1)
        
        routes = v.api.ip_route_dump(table={'table_id': 0, 'is_ip6': 0})
        total_routes = len(routes)
        
        acls = v.api.acl_dump(acl_index=0xffffffff)
        total_acls = len(acls)

        # NAT Sessions (Attempt to retrieve, may fail if NAT plugin is not loaded)
        nat_sessions = 0
        try:
            users = list(v.api.nat44_user_dump())
            for user in users:
                sessions = list(v.api.nat44_user_session_dump(
                    ip_address=user.ip_address, 
                    vrf_id=user.vrf_id
                ))
                nat_sessions += len(sessions)
        except Exception:
            pass # Ignore error if NAT is disabled

        # VPP Uptime (Use simple check via 'show version' via CLI)
        uptime_str = "Active"
        try:
            v.api.cli_inband(cmd='show version')
        except:
            uptime_str = "Unknown"


        # --- 3. Final Consolidated Response ---
        return jsonify({
            # System Resources (Required for FortiGate-style percentages)
            'cpu': {'aggregate': cpu_aggregate, 'cores': cpu_cores_list},
            'memory': mem_usage_percent,
            'memory_total': mem_total_str,
            # VPP Network Statistics
            'interfaces': {'total': total_interfaces, 'active': active_interfaces},
            'routes': total_routes,
            'acls': total_acls,
            'nat_sessions': nat_sessions,
            'uptime': uptime_str
        })

    except Exception as e:
        logging.error(f"Dashboard stats error: {e}")
        return jsonify({'error': str(e)}), 500

# The `get_system_uptime()` function is replaced by the simplified check within the main route.

def get_system_uptime(v=None):
    """Get VPP uptime"""
    try:
        local_v = v if v else get_vpp_for_request()
        if local_v:
            result = local_v.api.show_version()
            # Note: show_version in some APIs implies uptime info, 
            # but usually just returns version string. 
            # If explicit uptime is needed, parse cli_inband('show version verbose')
            return "Active" 
        return "Disconnected"
    except Exception as e:
        return "Unknown"