# dashboard.py
from flask import Blueprint, jsonify, request
from vpp_connection import get_vpp_connection
import traceback
import logging
import ipaddress

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get overall system statistics for dashboard"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        # Get interface count and status
        interfaces = v.api.sw_interface_dump()
        total_interfaces = len(interfaces)
        active_interfaces = sum(1 for iface in interfaces if iface.flags & 1)
        
        # Get route count
        routes = v.api.ip_route_dump(table={'table_id': 0, 'is_ip6': 0})
        total_routes = len(routes)
        
        # Get ACL count
        acls = v.api.acl_dump(acl_index=0xffffffff)
        total_acls = len(acls)
        
        # Get NAT sessions count - improved error handling
        nat_sessions = 0
        try:
            # Try to get all users first
            users = list(v.api.nat44_user_dump())
            for user in users:
                sessions = list(v.api.nat44_user_session_dump(
                    ip_address=user.ip_address,
                    vrf_id=user.vrf_id
                ))
                nat_sessions += len(sessions)
                print(nat_sessions)
        except Exception as e:
            logging.debug(f"NAT session count failed: {e}")
            # NAT might not be configured
            pass
        
        return jsonify({
            'interfaces': {'total': total_interfaces, 'active': active_interfaces},
            'routes': total_routes,
            'acls': total_acls,
            'nat_sessions': nat_sessions,
            'uptime': get_system_uptime()
        })
    except Exception as e:
        logging.error(f"Dashboard stats error: {e}")
        return jsonify({'error': str(e)}), 500

def get_system_uptime():
    """Get VPP uptime"""
    try:
        v = get_vpp_connection()
        if v:
            result = v.api.show_version()
            # Try to parse uptime if available in result
            if hasattr(result, 'uptime'):
                return result.uptime
            return "Running"
        return "Disconnected"
    except Exception as e:
        logging.debug(f"Uptime check failed: {e}")
        return "Unknown"
