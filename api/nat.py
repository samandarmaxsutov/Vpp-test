from flask import Blueprint, jsonify, request
from vpp_connection import get_vpp_connection
import ipaddress
import traceback

nat_bp = Blueprint('nat', __name__)



@nat_bp.route('/api/nat/plugin', methods=['GET'])
def get_nat_plugin_status():
    """Get NAT44ED plugin real runtime status"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        

        # Query actual runtime config
        cfg = v.api.nat44_show_running_config()
        interfaces = list(v.api.nat44_interface_dump()) 
        addresses = list(v.api.nat44_address_dump()) 
        nat_active = bool(interfaces or addresses)  # True if NAT is actively forwarding
        if cfg.sessions==0:
            plugin_loaded = False
        else:
            plugin_loaded =True
        return jsonify({
            'plugin_loaded': plugin_loaded,
            'nat_active': nat_active,
            'inside_vrf': cfg.inside_vrf,
            'outside_vrf': cfg.outside_vrf,
            'sessions': cfg.sessions,
            'flags': cfg.flags
        })

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500





@nat_bp.route('/api/nat/plugin', methods=['POST'])
def enable_nat():
    """Enable NAT44 plugin"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        # Enable NAT44
        v.api.nat44_ed_plugin_enable_disable(enable=True)

        return jsonify({
            'success': True,
            'message': 'NAT44 plugin enabled'
        })

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@nat_bp.route('/api/nat/plugin', methods=['DELETE'])
def disable_nat():
    """Disable NAT44 plugin"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        # Disable NAT44
        v.api.nat44_ed_plugin_enable_disable(enable=False)

        return jsonify({
            'success': True,
            'message': 'NAT44 plugin disabled'
        })

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@nat_bp.route('/api/nat/interfaces', methods=['GET'])
def get_nat_interfaces():
    """Get all NAT-configured interfaces"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        result = []
        for nat_if in v.api.nat44_interface_dump():
            result.append({
                'sw_if_index': int(nat_if.sw_if_index),
                'flags': int(nat_if.flags),
                'is_inside': bool(nat_if.flags & 32),
                'is_outside': bool(nat_if.flags & 16)
            })
                
        return jsonify(result)
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in get_nat_interfaces: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500


@nat_bp.route('/api/nat/interface/<int:sw_if_index>', methods=['POST', 'DELETE'])
def configure_nat_interface(sw_if_index):
    """Configure NAT on an interface (inside or outside)"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json or {}
        is_inside = bool(data.get('is_inside', True))
        is_add = 1 if request.method == 'POST' else 0

        # Determine flags manually
        flags = 0
        if is_inside:
            flags |= 0x20  # NAT44_EI_IF_INSIDE
        else:
            flags |= 0x10  # NAT44_EI_IF_OUTSIDE

        # Optional: additional features
        flags |= 0x02  # NAT44_EI_CONNECTION_TRACKING

        print(f"Configuring NAT: sw_if_index={sw_if_index}, is_inside={is_inside}, flags={flags}, is_add={is_add}")

        # Apply NAT configuration
        v.api.nat44_interface_add_del_feature(
            sw_if_index=sw_if_index,
            is_add=is_add,
            flags=flags
        )

        action = 'configured' if is_add else 'removed'
        direction = 'inside' if is_inside else 'outside'
        print(f"NAT interface {action}: sw_if_index={sw_if_index}, direction={direction}")

        # Verify the configuration
        verification = []
        for nat_if in v.api.nat44_interface_dump():
            if int(nat_if.sw_if_index) == sw_if_index:
                verification.append({
                    'sw_if_index': int(nat_if.sw_if_index),
                    'flags': int(nat_if.flags),
                    'is_inside': bool(nat_if.flags & 0x10),   # correct bitmask for inside
                    'is_outside': bool(nat_if.flags & 0x20)  # correct bitmask for outside
                })
        print(f"Verification: {verification}")

        return jsonify({
            'success': True,
            'message': f'NAT interface {action}',
            'sw_if_index': sw_if_index,
            'is_inside': is_inside,
            'action': action,
            'verification': verification
        })

    except Exception as e:
        print(f"Error in configure_nat_interface: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@nat_bp.route('/api/nat/addresses', methods=['GET'])
def get_nat_addresses():
    """Get all NAT address pool entries"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        result = []
        for addr in v.api.nat44_address_dump():
            if isinstance(addr.ip_address, bytes):
                ip_str = str(ipaddress.IPv4Address(addr.ip_address))
            else:
                ip_str = str(addr.ip_address)
            
            result.append({
                'ip_address': ip_str,
                'vrf_id': int(addr.vrf_id)
            })
        
        return jsonify(result)
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in get_nat_addresses: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500


@nat_bp.route('/api/nat/address', methods=['POST'])
def add_nat_address():
    """Add an IP address to the NAT address pool"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        data = request.json
        ip_address = data.get('ip_address')
        
        if not ip_address:
            return jsonify({'error': 'IP address is required'}), 400
        
        print(f"Adding NAT address: {ip_address}")
        
        ip_obj = ipaddress.IPv4Address(ip_address)
        
        v.api.nat44_add_del_address_range(
            first_ip_address=ip_obj,
            last_ip_address=ip_obj,
            vrf_id=0,
            is_add=1,
            flags=0
        )
        
        print(f"NAT address added successfully: {ip_address}")
        
        addresses = list(v.api.nat44_address_dump())
        print(f"Current NAT addresses: {len(addresses)}")
        
        return jsonify({
            'success': True,
            'message': 'NAT address added successfully',
            'ip_address': ip_address
        })
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in add_nat_address: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500


@nat_bp.route('/api/nat/address', methods=['DELETE'])
def remove_nat_address():
    """Remove an IP address from the NAT address pool"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        data = request.json
        ip_address = data.get('ip_address')
        
        if not ip_address:
            return jsonify({'error': 'IP address is required'}), 400
        
        print(f"Removing NAT address: {ip_address}")
        
        ip_obj = ipaddress.IPv4Address(ip_address)
        
        v.api.nat44_add_del_address_range(
            first_ip_address=ip_obj,
            last_ip_address=ip_obj,
            vrf_id=0,
            is_add=0,
            flags=0
        )
        
        print(f"NAT address removed successfully: {ip_address}")
        
        return jsonify({
            'success': True,
            'message': 'NAT address removed successfully',
            'ip_address': ip_address
        })
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in remove_nat_address: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500


@nat_bp.route('/api/nat/sessions', methods=['GET'])
def get_nat_sessions():
    """Get all active NAT sessions"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        result = []
        
        try:
            for user in v.api.nat44_user_dump():
                for session in v.api.nat44_user_session_dump(
                    ip_address=user.ip_address,
                    vrf_id=user.vrf_id
                ):
                    if isinstance(session.inside_ip_address, bytes):
                        inside_ip = str(ipaddress.IPv4Address(session.inside_ip_address))
                    else:
                        inside_ip = str(session.inside_ip_address)
                    
                    if isinstance(session.outside_ip_address, bytes):
                        outside_ip = str(ipaddress.IPv4Address(session.outside_ip_address))
                    else:
                        outside_ip = str(session.outside_ip_address)
                    
                    result.append({
                        'inside_ip': inside_ip,
                        'inside_port': int(session.inside_port),
                        'outside_ip': outside_ip,
                        'outside_port': int(session.outside_port),
                        'protocol': int(session.protocol)
                    })
        except:
            pass
        
        return jsonify(result)
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in get_nat_sessions: {e}\n{error_trace}")
        return jsonify([])


@nat_bp.route('/api/nat/static', methods=['GET'])
def get_static_mappings():
    """Get all static NAT mappings"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        result = []
        for mapping in v.api.nat44_static_mapping_dump():
            if isinstance(mapping.local_ip_address, bytes):
                local_ip = str(ipaddress.IPv4Address(mapping.local_ip_address))
            else:
                local_ip = str(mapping.local_ip_address)
            
            if isinstance(mapping.external_ip_address, bytes):
                external_ip = str(ipaddress.IPv4Address(mapping.external_ip_address))
            else:
                external_ip = str(mapping.external_ip_address)
            
            result.append({
                'local_ip': local_ip,
                'local_port': int(mapping.local_port) if hasattr(mapping, 'local_port') and mapping.local_port else None,
                'external_ip': external_ip,
                'external_port': int(mapping.external_port) if hasattr(mapping, 'external_port') and mapping.external_port else None,
                'protocol': int(mapping.protocol) if hasattr(mapping, 'protocol') and mapping.protocol else None,
                'vrf_id': int(mapping.vrf_id)
            })
        
        return jsonify(result)
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in get_static_mappings: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500


@nat_bp.route('/api/nat/static', methods=['POST'])
def add_static_mapping():
    """Add a static NAT mapping"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        data = request.json
        local_ip = data.get('local_ip')
        external_ip = data.get('external_ip')
        local_port = data.get('local_port')
        external_port = data.get('external_port')
        protocol = data.get('protocol', 6)
        
        if not local_ip or not external_ip:
            return jsonify({'error': 'Local and external IPs are required'}), 400
        
        print(f"Adding static NAT mapping: {local_ip}:{local_port} -> {external_ip}:{external_port}")
        
        v.api.nat44_add_del_static_mapping(
            is_add=1,
            local_ip_address=ipaddress.IPv4Address(local_ip),
            external_ip_address=ipaddress.IPv4Address(external_ip),
            local_port=int(local_port) if local_port else 0,
            external_port=int(external_port) if external_port else 0,
            protocol=int(protocol),
            vrf_id=0,
            external_sw_if_index=0xFFFFFFFF,
            flags=0
        )
        
        print(f"Static NAT mapping added successfully")
        
        return jsonify({
            'success': True,
            'message': 'Static NAT mapping added successfully'
        })
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in add_static_mapping: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500


@nat_bp.route('/api/nat/static', methods=['DELETE'])
def remove_static_mapping():
    """Remove a static NAT mapping"""
    try:
        v = get_vpp_connection()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500
        
        data = request.json
        local_ip = data.get('local_ip')
        external_ip = data.get('external_ip')
        local_port = data.get('local_port')
        external_port = data.get('external_port')
        protocol = data.get('protocol', 6)
        
        if not local_ip or not external_ip:
            return jsonify({'error': 'Local and external IPs are required'}), 400
        
        print(f"Removing static NAT mapping: {local_ip}:{local_port} -> {external_ip}:{external_port}")
        
        v.api.nat44_add_del_static_mapping(
            is_add=0,
            local_ip_address=ipaddress.IPv4Address(local_ip),
            external_ip_address=ipaddress.IPv4Address(external_ip),
            local_port=int(local_port) if local_port else 0,
            external_port=int(external_port) if external_port else 0,
            protocol=int(protocol),
            vrf_id=0,
            external_sw_if_index=0xFFFFFFFF,
            flags=0
        )
        
        print(f"Static NAT mapping removed successfully")
        
        return jsonify({
            'success': True,
            'message': 'Static NAT mapping removed successfully'
        })
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in remove_static_mapping: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': error_trace}), 500