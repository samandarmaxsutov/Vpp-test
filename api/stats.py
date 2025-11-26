from flask import Blueprint, jsonify
from vpp_connection import get_vpp_for_request

stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/api/interfaces/cli-stats')
def get_interface_stats():
    """Fetch raw interface stats via CLI."""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({"error": "Not connected to VPP"}), 500

        result = v.api.cli_inband(cmd="show interface")
        return jsonify({"output": result.reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
