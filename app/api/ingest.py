"""
Ingestion API for real-time industrial sensor telemetry.
Supports REST edge gateways, Python edge daemons, Modbus/MQTT bridges, and pilot onboarding.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.sensor_data import SensorData, MachineState, EventLog
from app.models.configuration import Asset, AssetSensor
from app.config.machine_config import SENSOR_CONFIG
import logging

logger = logging.getLogger(__name__)

ingest_bp = Blueprint('ingest', __name__)

def validate_ingest_token(api_key: str, machine_id: str = None) -> bool:
    """
    Validate ingest token against global server API_KEY, per-machine live token,
    or asset serial number.
    """
    if not api_key:
        return False
        
    expected_global = current_app.config.get('API_KEY', 'dev-api-key')
    if api_key == expected_global:
        return True
        
    if machine_id:
        # Machine-specific live token
        if api_key == f"pdm_live_{machine_id}":
            return True
            
        asset = Asset.query.filter_by(name=machine_id).first()
        if asset:
            if asset.serial_number and api_key == f"pdm_tok_{asset.serial_number}":
                return True
            if api_key == f"pdm_sec_{asset.id}":
                return True

    return False

@ingest_bp.route('/ping', methods=['GET', 'POST'])
@ingest_bp.route('/ingest/ping', methods=['GET', 'POST'])
def ping_gateway():
    """
    Edge device handshake and latency verification endpoint.
    Used by edge daemons before initiating continuous telemetry streaming.
    """
    api_key = request.headers.get('X-API-Key') or request.args.get('key')
    machine_id = request.args.get('machine_id')
    
    if request.is_json:
        data = request.get_json() or {}
        machine_id = data.get('machine_id', machine_id)
        if not api_key:
            api_key = data.get('api_key')

    is_valid = validate_ingest_token(api_key, machine_id) if api_key else False

    return jsonify({
        "status": "online",
        "service": "PDM Industrial Ingestion Bridge",
        "server_time_utc": datetime.utcnow().isoformat(),
        "authenticated": is_valid,
        "machine_id": machine_id
    }), 200

@ingest_bp.route('/connection-info', methods=['GET'])
@ingest_bp.route('/ingest/connection-info', methods=['GET'])
def get_connection_info():
    """
    Generate device connection instructions, channel mapping schemas,
    and copyable edge gateway commands for a specific asset.
    """
    machine_id = request.args.get('machine_id')
    if not machine_id:
        return jsonify({"error": "machine_id query parameter is required"}), 400

    asset = Asset.query.filter_by(name=machine_id).first()
    if not asset:
        return jsonify({"error": f"Asset '{machine_id}' not found in registry"}), 404

    machine_type = asset.template.name if asset.template else "FILLING"
    host_url = request.host_url.rstrip('/')
    ingest_endpoint = f"{host_url}/api/ingest"
    device_token = f"pdm_live_{machine_id}"

    # Extract configured sensor channels
    channels = []
    sample_readings = {}
    if asset.sensors:
        for s in asset.sensors:
            s_name = s.sensor_template.name if s.sensor_template else s.channel_id
            unit = s.sensor_template.unit if s.sensor_template else "units"
            warn_val = s.config_overrides.get('warn') if s.config_overrides else None
            crit_val = s.config_overrides.get('crit') if s.config_overrides else None
            channels.append({
                "channel_id": s.channel_id,
                "name": s_name,
                "unit": unit,
                "threshold_warn": warn_val,
                "threshold_crit": crit_val
            })
            sample_readings[s_name] = 50.0

    # Fallback to template if no sensors configured
    if not channels and machine_type in SENSOR_CONFIG:
        for s_name, s_cfg in SENSOR_CONFIG[machine_type].items():
            channels.append({
                "channel_id": f"{machine_id}_{s_name}",
                "name": s_name,
                "unit": s_cfg.get('unit', 'units'),
                "threshold_warn": s_cfg.get('warn'),
                "threshold_crit": s_cfg.get('crit')
            })
            sample_readings[s_name] = s_cfg.get('mean', 50.0)

    sample_payload = {
        "machine_id": machine_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sensors": sample_readings
    }

    import json
    curl_command = (
        f'curl -X POST "{ingest_endpoint}" \\\n'
        f'  -H "Content-Type: application/json" \\\n'
        f'  -H "X-API-Key: {device_token}" \\\n'
        f"  -d '{json.dumps(sample_payload, indent=2)}'"
    )

    python_snippet = (
        f'import requests, time\n'
        f'payload = {json.dumps(sample_payload, indent=4)}\n'
        f'res = requests.post("{ingest_endpoint}", headers={{"X-API-Key": "{device_token}"}}, json=payload)\n'
        f'print(res.status_code, res.json())'
    )

    edge_agent_cmd = f"python scripts/edge/pdm_edge_agent.py --host {host_url} --machine-id {machine_id} --key {device_token}"

    return jsonify({
        "machine_id": machine_id,
        "asset_name": asset.name,
        "machine_type": machine_type,
        "location": asset.location.name if asset.location else "Main Floor",
        "ingest_url": ingest_endpoint,
        "device_token": device_token,
        "status": asset.status,
        "is_live": asset.status in ['Live', 'Hardware', 'LIVE_HARDWARE'],
        "channels": channels,
        "sample_payload": sample_payload,
        "curl_command": curl_command,
        "python_snippet": python_snippet,
        "edge_agent_command": edge_agent_cmd
    }), 200

@ingest_bp.route('/toggle-mode', methods=['POST'])
@ingest_bp.route('/ingest/toggle-mode', methods=['POST'])
def toggle_asset_mode():
    """
    Switch an asset between 'Live' (hardware feed) and 'Active' (simulated).
    """
    try:
        data = request.get_json() or {}
        machine_id = data.get('machine_id')
        mode = data.get('mode') # 'Live' or 'Active'

        if not machine_id:
            return jsonify({"error": "machine_id is required"}), 400

        asset = Asset.query.filter_by(name=machine_id).first()
        if not asset:
            return jsonify({"error": f"Asset '{machine_id}' not found"}), 404

        target_status = 'Live' if mode in ['Live', 'hardware', 'live'] else 'Active'
        asset.status = target_status
        db.session.commit()

        # Log mode transition
        log = EventLog(
            timestamp=datetime.utcnow(),
            machine_id=machine_id,
            event_type='Info',
            details=f"Asset {machine_id} ingestion mode set to {target_status} (Feed: {'Real Hardware Edge' if target_status == 'Live' else 'Physics Simulator'})."
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            "status": "success",
            "machine_id": machine_id,
            "mode": target_status,
            "is_live": target_status == 'Live'
        }), 200

    except Exception as e:
        logger.error(f"Error toggling mode: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@ingest_bp.route('/ingest', methods=['POST'])
def ingest_data():
    """
    Ingest sensor telemetry from edge daemons, PLCs, or IoT gateways.
    Supports single packets or batch timeseries lists.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        # Handle batch or single
        packets = data if isinstance(data, list) else [data]
        if not packets:
            return jsonify({"error": "Empty telemetry payload"}), 400

        first_packet = packets[0]
        machine_id = first_packet.get('machine_id')
        if not machine_id:
            return jsonify({"error": "Missing machine_id in telemetry packet"}), 400

        # 1. Validate API Key
        api_key = request.headers.get('X-API-Key')
        if not validate_ingest_token(api_key, machine_id):
            logger.warning(f"Unauthorized telemetry attempt for machine '{machine_id}' with key: {api_key}")
            return jsonify({"error": "Unauthorized: Invalid X-API-Key"}), 401

        # 2. Validate Asset Identity
        asset = Asset.query.filter_by(name=machine_id).first()
        machine_type = asset.template.name if asset and asset.template else machine_id.split('_')[0]

        valid_channel_ids = set()
        if asset and asset.sensors:
            for s in asset.sensors:
                valid_channel_ids.add(s.channel_id)
                if s.sensor_template:
                    valid_channel_ids.add(s.sensor_template.name)

        if not valid_channel_ids:
            if machine_type in SENSOR_CONFIG:
                for s_name in SENSOR_CONFIG[machine_type].keys():
                    valid_channel_ids.add(s_name)
                    valid_channel_ids.add(f"{machine_id}_{s_name}")

        new_readings = []
        latest_ts = datetime.utcnow()

        for pkt in packets:
            pkt_machine_id = pkt.get('machine_id', machine_id)
            ts_str = pkt.get('timestamp')
            if ts_str:
                try:
                    if ts_str.endswith('Z'):
                        ts_str = ts_str[:-1]
                    timestamp = datetime.fromisoformat(ts_str)
                except ValueError:
                    timestamp = datetime.utcnow()
            else:
                timestamp = datetime.utcnow()

            latest_ts = max(latest_ts, timestamp)
            sensors = pkt.get('sensors') or pkt.get('readings') or {}

            for sensor_name, value in sensors.items():
                if valid_channel_ids and sensor_name not in valid_channel_ids and f"{pkt_machine_id}_{sensor_name}" not in valid_channel_ids:
                    continue

                sensor_id = sensor_name if sensor_name.startswith(f"{pkt_machine_id}_") else f"{pkt_machine_id}_{sensor_name}"
                try:
                    float_val = float(value)
                except (ValueError, TypeError):
                    continue

                reading = SensorData(
                    timestamp=timestamp,
                    sensor_id=sensor_id,
                    value=float_val
                )
                new_readings.append(reading)

        if not new_readings:
            return jsonify({"error": "No valid sensor readings extracted from payload"}), 400

        db.session.bulk_save_objects(new_readings)

        # Update Asset status & MachineState
        if asset and asset.status not in ['Live', 'Maintenance']:
            asset.status = 'Live' # Auto-promote asset to live hardware feed

        state = MachineState.query.filter_by(machine_id=machine_id).first()
        if state:
            state.last_updated = latest_ts

        db.session.commit()

        return jsonify({
            "status": "success",
            "machine_id": machine_id,
            "readings_ingested": len(new_readings),
            "timestamp": latest_ts.isoformat(),
            "asset_mode": asset.status if asset else "Unknown"
        }), 200

    except Exception as e:
        logger.error(f"Ingest error: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
