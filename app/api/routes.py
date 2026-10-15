"""
API routes for the Predictive Maintenance Platform.
"""
from datetime import datetime, timedelta
from flask import jsonify, request, current_app
from flask_login import login_required
from sqlalchemy import func
from app.packages import api_bp
from app.models.sensor_data import SensorData, EventLog, MachineState
from app.models.company import Company # Keep Company for now if needed, but Machine is replaced
from app.models.configuration import Asset
from app.services.predictor import PredictiveService
from app.services.simulator import DataSimulator
from app.api.auth import auth_bp
from app.api.ingest import ingest_bp
from app.api.machine_management import machine_mgmt_bp
from app.api.admin import admin_bp

def register_routes(app):
    app.register_blueprint(api_bp) # Register the existing api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(ingest_bp)
    app.register_blueprint(machine_mgmt_bp)
    app.register_blueprint(admin_bp)

# Services will be initialized per request to avoid context issues

@api_bp.route('/latest-states', methods=['GET'])
# @login_required - Public dashboard access
def get_latest_machine_states():
    """Get current state of all machines with predictions."""
    try:
        # For now, get all machines (we'll add company filtering later)
        # Using Asset model instead of legacy Machine model
        company_machines = Asset.query.filter_by(company_id=1).all()  # GDK Perfume
        machine_ids = [asset.name for asset in company_machines]
        
        predictor = PredictiveService()
        simulator = DataSimulator()
        
        if not machine_ids:
            return jsonify({
                "is_operational": False,
                "predictions": {},
                "kpis": {
                    "machines_online": 0,
                    "total_machines": 0,
                    "active_alerts": 0
                },
                "event_log": [],
                "last_prediction_run_time_utc": datetime.utcnow().isoformat()
            }), 200
        
        # Get predictions for company's machines only
        predictions = predictor.get_predictions_for_machines(machine_ids)
        kpis = predictor.calculate_kpis_for_company(1)  # GDK Perfume company ID
        
        # Get recent events for company's machines
        events = (EventLog.query
                 .filter(EventLog.machine_id.in_(machine_ids))
                 .order_by(EventLog.timestamp.desc())
                 .limit(50)
                 .all())
        
        event_log = [event.to_dict() for event in events]
        
        # Check if factory is operational
        current_time = datetime.utcnow()
        is_operational = simulator.is_operational(current_time)
        
        return jsonify({
            "is_operational": is_operational,
            "predictions": predictions,
            "kpis": kpis,
            "event_log": event_log,
            "last_prediction_run_time_utc": current_time.isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"API Error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/history')
# @login_required - Public dashboard access
def get_history():
    """Get historical sensor data for a specific machine."""
    machine_id = request.args.get('machine_id')
    time_range = request.args.get('range', '1h')
    
    if not machine_id:
        return jsonify({"error": "machine_id parameter is required"}), 400
    
    # Calculate start time based on range
    hours = {"1h": 1, "6h": 6, "24h": 24}.get(time_range, 1)
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    try:
        predictor = PredictiveService()
        history_data = predictor.get_machine_history(machine_id, start_time)
        return jsonify(history_data), 200
        
    except Exception as e:
        current_app.logger.error(f"History API Error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route('/perform-maintenance', methods=['POST'])
# @login_required - Public dashboard access
def perform_maintenance():
    """Request maintenance for a specific machine."""
    try:
        data = request.get_json()
        machine_id = data.get('machine_id')
        
        if not machine_id:
            return jsonify({"error": "machine_id is required"}), 400
        
        simulator = DataSimulator()
        success = simulator.request_maintenance(machine_id)
        
        if success:
            return jsonify({"status": "success", "message": f"Maintenance requested for {machine_id}"}), 200
        else:
            return jsonify({"error": "Failed to request maintenance"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Maintenance API Error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        predictor = PredictiveService()
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "models_loaded": predictor.models_loaded
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 500
