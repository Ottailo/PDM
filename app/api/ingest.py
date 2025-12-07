"""
Ingestion API for real-time sensor data.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.sensor_data import SensorData, MachineState
from app.config.machine_config import SENSOR_CONFIG
import logging

logger = logging.getLogger(__name__)

ingest_bp = Blueprint('ingest', __name__)

@ingest_bp.route('/ingest', methods=['POST'])
def ingest_data():
    """
    Ingest sensor data from external sources.
    
    Expected Payload:
    {
        "machine_id": "FILLING_001",
        "timestamp": "2024-01-01T12:00:00Z",  # Optional, defaults to now
        "sensors": {
            "Fill_Volume_Sensor": 98.5,
            "Nozzle_Pressure": 2.1
        }
    }
    """
    # 1. Validate API Key
    api_key = request.headers.get('X-API-Key')
    expected_key = current_app.config.get('API_KEY')
    
    if not expected_key:
        logger.warning("API_KEY not configured in server. Rejecting ingest request.")
        return jsonify({"error": "Server configuration error"}), 500
        
    if not api_key or api_key != expected_key:
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400
            
        machine_id = data.get('machine_id')
        if not machine_id:
            return jsonify({"error": "Missing machine_id"}), 400
            
        # 2. Validate Machine ID (simple check against config for now, could check DB)
        machine_type = machine_id.split('_')[0]
        if machine_type not in SENSOR_CONFIG:
             return jsonify({"error": f"Unknown machine type for ID: {machine_id}"}), 400

        # 3. Parse Timestamp
        ts_str = data.get('timestamp')
        if ts_str:
            try:
                # Handle 'Z' for UTC
                if ts_str.endswith('Z'):
                    ts_str = ts_str[:-1]
                timestamp = datetime.fromisoformat(ts_str)
            except ValueError:
                return jsonify({"error": "Invalid timestamp format. Use ISO 8601."}), 400
        else:
            timestamp = datetime.utcnow()
            
        sensors = data.get('sensors', {})
        if not sensors:
             return jsonify({"error": "No sensor data provided"}), 400
             
        # 4. Write to DB
        new_readings = []
        valid_sensors = SENSOR_CONFIG.get(machine_type, {})
        
        for sensor_name, value in sensors.items():
            # Validate sensor name
            if sensor_name not in valid_sensors:
                logger.warning(f"Received unknown sensor '{sensor_name}' for machine '{machine_id}'. Skipping.")
                continue
                
            sensor_id = f"{machine_id}_{sensor_name}"
            
            reading = SensorData(
                timestamp=timestamp,
                sensor_id=sensor_id,
                value=float(value)
            )
            new_readings.append(reading)
            
        if not new_readings:
            return jsonify({"error": "No valid sensor readings found"}), 400
            
        db.session.bulk_save_objects(new_readings)
        
        # Update Machine State Last Updated
        state = MachineState.query.filter_by(machine_id=machine_id).first()
        if state:
            state.last_updated = timestamp
            # We could trigger anomaly detection here immediately, 
            # but for now we'll let the next poll/job handle it or keep it simple.
        
        db.session.commit()
        
        return jsonify({"status": "success", "count": len(new_readings)}), 200
        
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
