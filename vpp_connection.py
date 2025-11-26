from flask import g
from vpp_papi.vpp_papi import VPPApiClient
from vpp_papi.vpp_stats import VPPStats
import logging

VPP_API_SOCKET = "/run/vpp/api.sock"
VPP_STATS_SOCKET = "/dev/shm/vpp/stats.sock"


def get_vpp_for_request():
    """
    Provides a fresh VPP connection for the current Flask request.
    Connection is closed automatically in teardown_appcontext.
    """
    # If already created during this request -- use it
    if hasattr(g, "vpp") and g.vpp is not None:
        return g.vpp

    try:
        # Create API client
        v = VPPApiClient(server_address=VPP_API_SOCKET, read_timeout=5)
        v.connect("vpp-gui-request")
        logging.info("✓ Connected to VPP API (per-request)")

        # Try connecting stats
        try:
            stats = VPPStats(socketname=VPP_STATS_SOCKET)
            v.vpp_stats = stats
            g.vpp_stats = stats
        except Exception as e:
            logging.warning(f"⚠ Could not connect to VPP stats: {e}")
            g.vpp_stats = None

        # store in flask.g so route handlers can reuse within same request
        g.vpp = v
        return v

    except Exception as e:
        logging.error(f"❌ Failed to connect to VPP API: {e}")
        g.vpp = None
        g.vpp_stats = None
        return None


def close_vpp_connection(response_or_exc):
    """
    This function will be called automatically after each request.
    It cleans up VPP API & stats connections.
    """
    v = g.pop("vpp", None)
    stats = g.pop("vpp_stats", None)

    # Close VPP API connection
    if v:
        try:
            v.disconnect()
            logging.info("✓ VPP API disconnected (per-request)")
        except Exception:
            logging.exception("Error disconnecting VPP API")

    # Close stats connection if possible
    if stats and hasattr(stats, "close"):
        try:
            stats.close()
        except Exception:
            logging.exception("Error closing VPP stats")

    return response_or_exc


def init_vpp_teardown(app):
    """
    Call this from create_app() to register automatic cleanup.
    """
    app.teardown_appcontext(close_vpp_connection)
