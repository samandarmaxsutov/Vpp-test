from vpp_papi.vpp_papi import VPPApiClient
from vpp_papi.vpp_stats import VPPStats
import logging

vpp = None
vpp_stats = None

def get_vpp_client():
    v = VPPApiClient(server_address="/run/vpp/api.sock")
    try:
        v.connect("vpp-gui")
    except Exception:
        return None
    return v

def get_vpp_connection():
    """Get or reconnect to VPP API and stats"""
    global vpp, vpp_stats
    # print(vpp, vpp_stats)
    try:
        if vpp is None:
            vpp = VPPApiClient(server_address="/run/vpp/api.sock",read_timeout=5)
            vpp.connect("vpp-firewall-gui")
            logging.info("✓ Connected to VPP API")

        if vpp_stats is None:
            vpp_stats = VPPStats(socketname="/dev/shm/vpp/stats.sock")
            logging.info("✓ Connected to VPP stats segment")

        # ✅ Attach under a safe name (not 'stats')
        vpp.vpp_stats = vpp_stats

        return vpp

    except Exception as e:
        logging.error(f"❌ Failed to connect to VPP: {e}")
        vpp = None
        vpp_stats = None
        return None
