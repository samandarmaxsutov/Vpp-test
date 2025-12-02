from flask import Blueprint, jsonify, request
from vpp_connection import get_vpp_for_request
import ipaddress
import traceback

dhcp_bp = Blueprint('dhcp', __name__)


# ============================================================================
# DHCP Plugin Status
# ============================================================================

@dhcp_bp.route('/api/dhcp/plugin', methods=['GET'])
def get_dhcp_plugin_status():
    """Get DHCP plugin version and status"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        version = v.api.dhcp_plugin_get_version()
        clients = list(v.api.dhcp_client_dump())

        return jsonify({
            'plugin_loaded': True,
            'version_major': int(version.major),
            'version_minor': int(version.minor),
            'clients_count': len(clients)
        })

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


# ============================================================================
# DHCP Client Configuration
# ============================================================================

@dhcp_bp.route('/api/dhcp/clients', methods=['GET'])
def get_dhcp_clients():
    """Get all DHCP client configurations"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        result = []
        for client_detail in v.api.dhcp_client_dump():
            client = client_detail.client
            lease = client_detail.lease

            # host address
            if isinstance(lease.host_address, bytes):
                host_addr = str(ipaddress.IPv4Address(lease.host_address))
            else:
                host_addr = str(lease.host_address)

            # router address
            if isinstance(lease.router_address, bytes):
                router_addr = str(ipaddress.IPv4Address(lease.router_address))
            else:
                router_addr = str(lease.router_address)

            result.append({
                'sw_if_index': int(client.sw_if_index),
                'hostname': client.hostname,
                'want_dhcp_event': bool(client.want_dhcp_event),
                'set_broadcast_flag': bool(client.set_broadcast_flag),
                'lease': {
                    'sw_if_index': int(lease.sw_if_index),
                    'state': int(lease.state),
                    'is_ipv6': bool(lease.is_ipv6),
                    'hostname': lease.hostname,
                    'mask_width': int(lease.mask_width),
                    'host_address': host_addr,
                    'router_address': router_addr
                }
            })

        return jsonify(result)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in get_dhcp_clients: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@dhcp_bp.route('/api/dhcp/client', methods=['POST'])
def add_dhcp_client():
    """Add a DHCP client configuration"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json
        sw_if_index = data.get('sw_if_index')
        hostname = data.get('hostname', '')
        want_dhcp_event = data.get('want_dhcp_event', False)
        set_broadcast_flag = data.get('set_broadcast_flag', False)

        if sw_if_index is None:
            return jsonify({'error': 'sw_if_index is required'}), 400

        print(f"Adding DHCP client: sw_if_index={sw_if_index}, hostname={hostname}")

        client_config = {
            'sw_if_index': int(sw_if_index),
            'hostname': hostname[:64] if hostname else '',
            'id': b'',
            'want_dhcp_event': want_dhcp_event,
            'set_broadcast_flag': set_broadcast_flag,
            'dscp': 0,
            'pid': 0
        }

        v.api.dhcp_client_config(
            is_add=True,
            client=client_config
        )

        return jsonify({
            'success': True,
            'message': 'DHCP client added successfully',
            'sw_if_index': sw_if_index
        })

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in add_dhcp_client: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@dhcp_bp.route('/api/dhcp/client/<int:sw_if_index>', methods=['DELETE'])
def remove_dhcp_client(sw_if_index):
    """Remove a DHCP client configuration"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        print(f"Removing DHCP client: sw_if_index={sw_if_index}")

        client_config = {
            'sw_if_index': int(sw_if_index),
            'hostname': '',
            'id': b'',
            'want_dhcp_event': False,
            'set_broadcast_flag': False,
            'dscp': 0,
            'pid': 0
        }

        v.api.dhcp_client_config(
            is_add=False,
            client=client_config
        )

        return jsonify({
            'success': True,
            'message': 'DHCP client removed successfully',
            'sw_if_index': sw_if_index
        })

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in remove_dhcp_client: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


# ============================================================================
# DHCP Proxy Configuration
# ============================================================================

@dhcp_bp.route('/api/dhcp/proxy', methods=['GET'])
def get_dhcp_proxies():
    """Get all DHCP proxy configurations"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        result = []
        for proxy in v.api.dhcp_proxy_dump(is_ip6=False):
            if isinstance(proxy.dhcp_src_address, bytes):
                src_addr = str(ipaddress.IPv4Address(proxy.dhcp_src_address))
            else:
                src_addr = str(proxy.dhcp_src_address)

            servers = []
            for i in range(proxy.count):
                server = proxy.servers[i]
                if isinstance(server.dhcp_server, bytes):
                    srv_addr = str(ipaddress.IPv4Address(server.dhcp_server))
                else:
                    srv_addr = str(server.dhcp_server)

                servers.append({
                    'server_vrf_id': int(server.server_vrf_id),
                    'dhcp_server': srv_addr
                })

            result.append({
                'rx_vrf_id': int(proxy.rx_vrf_id),
                'vss_type': int(proxy.vss_type),
                'vss_vpn_ascii_id': proxy.vss_vpn_ascii_id,
                'vss_oui': int(proxy.vss_oui),
                'vss_fib_id': int(proxy.vss_fib_id),
                'is_ipv6': bool(proxy.is_ipv6),
                'dhcp_src_address': src_addr,
                'servers': servers
            })

        return jsonify(result)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in get_dhcp_proxies: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@dhcp_bp.route('/api/dhcp/proxy', methods=['POST'])
def add_dhcp_proxy():
    """Add a DHCP proxy configuration"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json
        rx_vrf_id = data.get('rx_vrf_id', 0)
        server_vrf_id = data.get('server_vrf_id', 0)
        dhcp_server = data.get('dhcp_server')
        dhcp_src_address = data.get('dhcp_src_address')

        if not dhcp_server or not dhcp_src_address:
            return jsonify({'error': 'dhcp_server and dhcp_src_address are required'}), 400

        v.api.dhcp_proxy_config(
            rx_vrf_id=int(rx_vrf_id),
            server_vrf_id=int(server_vrf_id),
            is_add=True,
            dhcp_server=ipaddress.IPv4Address(dhcp_server),
            dhcp_src_address=ipaddress.IPv4Address(dhcp_src_address)
        )

        print(f"DHCP proxy added successfully")

        return jsonify({'success': True, 'message': 'DHCP proxy added successfully'})

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in add_dhcp_proxy: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@dhcp_bp.route('/api/dhcp/proxy', methods=['DELETE'])
def remove_dhcp_proxy():
    """Remove a DHCP proxy configuration"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json
        rx_vrf_id = data.get('rx_vrf_id', 0)
        server_vrf_id = data.get('server_vrf_id', 0)
        dhcp_server = data.get('dhcp_server')
        dhcp_src_address = data.get('dhcp_src_address')

        if not dhcp_server or not dhcp_src_address:
            return jsonify({'error': 'dhcp_server and dhcp_src_address are required'}), 400

        print(f"Removing DHCP proxy: rx_vrf={rx_vrf_id}, server={dhcp_server}")


        v.api.dhcp_proxy_config(
            rx_vrf_id=int(rx_vrf_id),
            server_vrf_id=int(server_vrf_id),
            is_add=False,
            dhcp_server=ipaddress.IPv4Address(dhcp_server),
            dhcp_src_address=ipaddress.IPv4Address(dhcp_src_address)
        )

        return jsonify({'success': True, 'message': 'DHCP proxy removed successfully'})

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


# ============================================================================
# DHCP VSS (Virtual Subnet Selection)
# ============================================================================

@dhcp_bp.route('/api/dhcp/vss', methods=['POST'])
def set_dhcp_vss():
    """Set DHCP VSS configuration"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json
        tbl_id = data.get('tbl_id', 0)
        vss_type = data.get('vss_type', 255)
        vpn_ascii_id = data.get('vpn_ascii_id', '')
        oui = data.get('oui', 0)
        vpn_index = data.get('vpn_index', 0)
        is_ipv6 = data.get('is_ipv6', False)

        print(f"Setting DHCP VSS: tbl_id={tbl_id}, vss_type={vss_type}")

        v.api.dhcp_proxy_set_vss(
            tbl_id=int(tbl_id),
            vss_type=int(vss_type),
            vpn_ascii_id=vpn_ascii_id[:129] if vpn_ascii_id else '',
            oui=int(oui),
            vpn_index=int(vpn_index),
            is_ipv6=bool(is_ipv6),
            is_add=True
        )

        return jsonify({'success': True, 'message': 'DHCP VSS set successfully'})

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in set_dhcp_vss: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@dhcp_bp.route('/api/dhcp/vss', methods=['DELETE'])
def unset_dhcp_vss():
    """Unset DHCP VSS configuration"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json
        tbl_id = data.get('tbl_id', 0)
        is_ipv6 = data.get('is_ipv6', False)

        print(f"Unsetting DHCP VSS: tbl_id={tbl_id}")

        v.api.dhcp_proxy_set_vss(
            tbl_id=int(tbl_id),
            vss_type=255,
            vpn_ascii_id='',
            oui=0,
            vpn_index=0,
            is_ipv6=bool(is_ipv6),
            is_add=False
        )

        print(f"DHCP VSS unset successfully")

        return jsonify({'success': True, 'message': 'DHCP VSS unset successfully'})

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


# ============================================================================
# DHCPv6 Client Control
# ============================================================================

@dhcp_bp.route('/api/dhcp/v6/enable', methods=['POST'])
def enable_dhcpv6():
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        v.api.dhcp6_clients_enable_disable(enable=True)

        return jsonify({'success': True, 'message': 'DHCPv6 clients enabled'})

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in enable_dhcpv6: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@dhcp_bp.route('/api/dhcp/v6/disable', methods=['POST'])
def disable_dhcpv6():
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        v.api.dhcp6_clients_enable_disable(enable=False)

        return jsonify({'success': True, 'message': 'DHCPv6 clients disabled'})

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@dhcp_bp.route('/api/dhcp/v6/duid', methods=['POST'])
def set_dhcpv6_duid():
    """Set DHCPv6 DUID-LL (hardware identifier)"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json
        duid_ll = data.get('duid_ll')

        if not duid_ll:
            return jsonify({'error': 'duid_ll is required (10 bytes)'}), 400

        if isinstance(duid_ll, str):
            duid_ll = bytes.fromhex(duid_ll.replace(':', '').replace('-', ''))

        if len(duid_ll) != 10:
            return jsonify({'error': 'duid_ll must be exactly 10 bytes'}), 400

        v.api.dhcp6_duid_ll_set(duid_ll=duid_ll)

        return jsonify({'success': True, 'message': 'DHCPv6 DUID-LL set successfully'})

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


# ============================================================================
# DHCP Client Detection
# ============================================================================

@dhcp_bp.route('/api/dhcp/detect/<int:sw_if_index>', methods=['POST'])
def enable_dhcp_detect(sw_if_index):
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        v.api.dhcp_client_detect_enable_disable(
            sw_if_index=int(sw_if_index),
            enable=True
        )

        return jsonify({'success': True, 'message': 'DHCP detection enabled', 'sw_if_index': sw_if_index})

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@dhcp_bp.route('/api/dhcp/detect/<int:sw_if_index>', methods=['DELETE'])
def disable_dhcp_detect(sw_if_index):
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        v.api.dhcp_client_detect_enable_disable(
            sw_if_index=int(sw_if_index),
            enable=False
        )

        return jsonify({'success': True, 'message': 'DHCP detection disabled', 'sw_if_index': sw_if_index})

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in disable_dhcp_detect: {e}\n{error_trace}")
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500
