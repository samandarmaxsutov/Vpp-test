from flask import Blueprint, jsonify, request
from vpp_connection import get_vpp_for_request
import traceback

policers_bp = Blueprint('policers', __name__)

@policers_bp.route('/api/policers', methods=['GET'])
def list_policers():
    try:
        # Call the function to get the VPP instance
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        # Now we can call the API
        policers = v.api.policer_dump_v2(policer_index=0xFFFFFFFF)  # request all policers

        result = []
        for p in policers:
            result.append({
                'name': p.name.decode(errors='ignore').rstrip('\x00') if isinstance(p.name, bytes) else p.name,
                'cir': p.cir,
                'eir': p.eir,
                'cb': p.cb,
                'eb': p.eb,
                'rate_type': p.rate_type,
                'round_type': p.round_type,
                'type': p.type,
                'conform_action': p.conform_action,
                'exceed_action': p.exceed_action,
                'violate_action': p.violate_action,
                'single_rate': p.single_rate,
                'color_aware': p.color_aware,
                'scale': p.scale,
                'cir_tokens_per_period': p.cir_tokens_per_period,
                'pir_tokens_per_period': p.pir_tokens_per_period,
                'current_limit': p.current_limit,
                'current_bucket': p.current_bucket,
                'extended_limit': p.extended_limit,
                'extended_bucket': p.extended_bucket,
                'last_update_time': p.last_update_time
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()})




@policers_bp.route('/api/policer', methods=['POST'])
def create_policer():
    """Create a new policer"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        data = request.json

        name = data.get('name', 'default-policer')
        cir = int(data.get('cir', 1000000))     # committed rate bps
        cb = int(data.get('cb', 10000))         # committed burst
        eir = int(data.get('eir', 0))           # excess rate
        eb = int(data.get('eb', 0))             # excess burst
        rate_type = data.get('rate_type', 0)    # 0 = BPS, 1 = PPS
        round_type = data.get('round_type', 1)  # closest
        policer_type = data.get('type', 0)      # 0 = single rate

        # Actions
        conform_action = {'action_type': 0}  # 0 = transmit
        exceed_action = {'action_type': 1}   # 1 = drop

        resp = v.api.policer_add_del(
            is_add=1,
            name=name,
            cir=cir,
            cb=cb,
            eir=eir,
            eb=eb,
            rate_type=rate_type,
            round_type=round_type,
            type=policer_type,
            conform_action=conform_action,
            exceed_action=exceed_action
        )

        return jsonify({
            'success': True,
            'policer_index': int(resp.policer_index)
        })

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500



@policers_bp.route('/api/policer/<int:policer_index>', methods=['DELETE'])
def delete_policer(policer_index):
    """Delete policer"""
    try:
        v = get_vpp_for_request()
        if not v:
            return jsonify({'error': 'Not connected to VPP'}), 500

        v.api.policer_add_del(
            is_add=0,
            policer_index=policer_index
        )

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
