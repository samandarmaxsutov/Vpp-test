from flask import Blueprint, jsonify, request
from vpp_connection import get_vpp_for_request
import traceback

settings_bp = Blueprint('settings', __name__, url_prefix="/api/settings/nat")

# -----------------------------
# GET current NAT settings
# -----------------------------
@settings_bp.route("/", methods=["GET"])
def get_nat_settings():
    try:
        vpp = get_vpp_for_request()

        # Call NAT44 running config
        reply = vpp.api.nat44_show_running_config()

        if reply.retval != 0:
            return jsonify({"success": False, "error": f"VPP returned {reply.retval}"}), 400

        # Extract fields
        response = {
            "vrfs": {
                "inside_vrf": reply.inside_vrf,
                "outside_vrf": reply.outside_vrf
            },
            "sessions": {
                "users": reply.users,
                "sessions": reply.sessions,
                "user_sessions": reply.user_sessions,
                "user_buckets": reply.user_buckets,
                "translation_buckets": reply.translation_buckets
            },
            "timeouts": {
                "udp": reply.timeouts.udp,
                "tcp_established": reply.timeouts.tcp_established,
                "tcp_transitory": reply.timeouts.tcp_transitory,
                "icmp": reply.timeouts.icmp
            },
            "flags": {
                "forwarding_enabled": reply.forwarding_enabled,
                "ipfix_logging_enabled": reply.ipfix_logging_enabled,
                "endpoint_dependent": bool(reply.flags & 1)  # extract from enum
            },
            "log_level": reply.log_level.name
        }

        return jsonify({"success": True, "settings": response})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# -----------------------------
# POST update NAT settings
# -----------------------------
@settings_bp.route("/", methods=["POST"])
def set_nat_settings():
    """
    Update NAT session timeouts and/or NAT44 session limit.
    JSON payload examples:
    {
        "timeouts": {
            "udp": 300,
            "tcp_established": 7440,
            "tcp_transitory": 240,
            "icmp": 60
        },
        "session_limit": {
            "vrf_id": 0,
            "limit": 10000
        }
    }
    """
    try:
        data = request.get_json()
        vpp = get_vpp_for_request()


        # ------------------ Update timeouts ------------------
        if "timeouts" in data:
            t = data["timeouts"]
            reply = vpp.api.nat_set_timeouts(
                udp=t.get("udp", 300),
                tcp_established=t.get("tcp_established", 7440),
                tcp_transitory=t.get("tcp_transitory", 240),
                icmp=t.get("icmp", 60)
            )
            if reply.retval != 0:
                return jsonify({"success": False, "error": f"NAT timeout update failed ({reply.retval})"}), 400

        # ------------------ Update session limit ------------------
        if "session_limit" in data:
            s = data["session_limit"]
            vrf_id = s.get("vrf_id", 0)
            limit = s.get("limit", 10000)
            reply = vpp.api.nat44_set_session_limit(
                vrf_id=vrf_id,
                session_limit=limit
            )
            if reply.retval != 0:
                return jsonify({"success": False, "error": f"NAT44 session limit update failed ({reply.retval})"}), 400

        # Return updated settings
        return jsonify({"success": True, "message": "NAT settings updated"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
