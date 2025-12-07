"""
Machine Management API Routes
"""
from flask import Blueprint, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models.company import Company, Machine, MaintenanceRecord
from app.models.sensor_data import MachineState
from app.services.simulator import DataSimulator
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Create blueprint for machine management
machine_mgmt_bp = Blueprint('machine_mgmt', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

@machine_mgmt_bp.before_request
@login_required
def before_request():
    pass

@machine_mgmt_bp.route('/companies', methods=['GET'])
def get_companies():
    """Get all companies."""
    try:
        companies = Company.query.filter_by(is_active=True).all()
        return jsonify([company.to_dict() for company in companies]), 200
    except Exception as e:
        logger.error(f"Error fetching companies: {str(e)}")
        return jsonify({"error": "Failed to fetch companies"}), 500

@machine_mgmt_bp.route('/companies', methods=['POST'])
def create_company():
    """Create a new company."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'industry', 'contact_email']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create company
        company = Company(
            name=data['name'],
            industry=data['industry'],
            contact_email=data['contact_email'],
            contact_phone=data.get('contact_phone'),
            address=data.get('address')
        )
        
        db.session.add(company)
        db.session.commit()
        
        logger.info(f"Created company: {company.name}")
        return jsonify(company.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Error creating company: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to create company"}), 500

@machine_mgmt_bp.route('/companies/<int:company_id>/machines', methods=['GET'])
def get_company_machines(company_id):
    """Get all machines for a specific company."""
    try:
        company = Company.query.get_or_404(company_id)
        machines = Machine.query.filter_by(company_id=company_id).all()
        return jsonify([machine.to_dict() for machine in machines]), 200
    except Exception as e:
        logger.error(f"Error fetching machines for company {company_id}: {str(e)}")
        return jsonify({"error": "Failed to fetch machines"}), 500

# Removed duplicate create_machine function - using the one below instead

# Removed first duplicate update_machine function - using the one below instead


@machine_mgmt_bp.route('/machines/<string:machine_id>/maintenance', methods=['POST'])
def add_maintenance_record(machine_id):
    """Add a maintenance record for a machine."""
    try:
        machine = Machine.query.filter_by(machine_id=machine_id).first_or_404()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['maintenance_type', 'description']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create maintenance record
        maintenance_record = MaintenanceRecord(
            machine_id=machine_id,
            maintenance_type=data['maintenance_type'],
            description=data['description'],
            performed_by=data.get('performed_by'),
            duration_hours=data.get('duration_hours'),
            cost=data.get('cost'),
            parts_replaced=data.get('parts_replaced', []),
            notes=data.get('notes'),
            scheduled_date=datetime.fromisoformat(data['scheduled_date']) if data.get('scheduled_date') else None,
            completed_date=datetime.fromisoformat(data['completed_date']) if data.get('completed_date') else None,
            company_id=machine.company_id
        )
        
        db.session.add(maintenance_record)
        db.session.commit()
        
        logger.info(f"Added maintenance record for machine: {machine_id}")
        return jsonify(maintenance_record.to_dict()), 201
        
    except Exception as e:
        logger.error(f"Error adding maintenance record for machine {machine_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to add maintenance record"}), 500

@machine_mgmt_bp.route('/machines/<string:machine_id>/maintenance', methods=['GET'])
def get_maintenance_records(machine_id):
    """Get maintenance records for a machine."""
    try:
        machine = Machine.query.filter_by(machine_id=machine_id).first_or_404()
        records = MaintenanceRecord.query.filter_by(machine_id=machine_id).order_by(MaintenanceRecord.created_at.desc()).all()
        return jsonify([record.to_dict() for record in records]), 200
    except Exception as e:
        logger.error(f"Error fetching maintenance records for machine {machine_id}: {str(e)}")
        return jsonify({"error": "Failed to fetch maintenance records"}), 500

@machine_mgmt_bp.route('/machine-types', methods=['GET'])
def get_machine_types():
    """Get available machine types and their configurations."""
    try:
        from app.config.machine_config import MACHINES, SENSOR_CONFIG
        
        machine_types = {}
        for machine_type in MACHINES.keys():
            machine_types[machine_type] = {
                'name': machine_type,
                'sensor_config': SENSOR_CONFIG.get(machine_type, {}),
                'sample_machines': MACHINES[machine_type][:3]  # Show first 3 as examples
            }
        
        return jsonify(machine_types), 200
    except Exception as e:
        logger.error(f"Error fetching machine types: {str(e)}")
        return jsonify({"error": "Failed to fetch machine types"}), 500

@machine_mgmt_bp.route('/companies/<int:company_id>/dashboard', methods=['GET'])
def get_company_dashboard(company_id):
    """Get dashboard data for a specific company."""
    try:
        company = Company.query.get_or_404(company_id)
        machines = Machine.query.filter_by(company_id=company_id).all()
        
        # Get machine states
        machine_ids = [machine.machine_id for machine in machines]
        machine_states = MachineState.query.filter(MachineState.machine_id.in_(machine_ids)).all()
        
        # Calculate KPIs
        total_machines = len(machines)
        machines_online = len([state for state in machine_states if state.status == "Normal"])
        active_alerts = len([state for state in machine_states if state.status in ["Degrading", "Operator Error"]])
        
        # Calculate OEE (simplified)
        oee = machines_online / total_machines if total_machines > 0 else 0
        
        dashboard_data = {
            'company': company.to_dict(),
            'kpis': {
                'total_machines': total_machines,
                'machines_online': machines_online,
                'active_alerts': active_alerts,
                'oee': oee
            },
            'machines': [machine.to_dict() for machine in machines],
            'machine_states': [state.to_dict() for state in machine_states]
        }
        
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        logger.error(f"Error fetching dashboard for company {company_id}: {str(e)}")
        return jsonify({"error": "Failed to fetch dashboard data"}), 500

@machine_mgmt_bp.route('/machines', methods=['POST'])
@admin_required
def create_machine():
    """Create a new machine with dynamic sensor configuration."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['machine_id', 'name', 'machine_type', 'company_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Check if machine already exists
        existing_machine = Machine.query.filter_by(machine_id=data['machine_id']).first()
        if existing_machine:
            return jsonify({"error": "Machine with this ID already exists"}), 400
        
        # Create machine with dynamic sensor configuration
        machine = Machine(
            machine_id=data['machine_id'],
            name=data['name'],
            machine_type=data['machine_type'],
            manufacturer=data.get('manufacturer'),
            model=data.get('model'),
            location=data.get('location'),
            company_id=data['company_id'],
            sensor_config=data.get('sensor_config', {}),
            thresholds=data.get('alert_thresholds', {}),
            installation_date=datetime.utcnow()
        )
        
        db.session.add(machine)
        
        # Create initial machine state
        machine_state = MachineState(
            machine_id=data['machine_id'],
            status='Normal',
            last_updated=datetime.utcnow()
        )
        
        db.session.add(machine_state)
        db.session.commit()
        
        # Initialize simulator for new machine
        try:
            simulator = DataSimulator()
            # Add the machine to the simulator's machine list
            if hasattr(simulator, 'machines'):
                simulator.machines.append(data['machine_id'])
        except Exception as e:
            logger.warning(f"Could not initialize simulator for machine {data['machine_id']}: {e}")
        
        return jsonify({
            "message": "Machine created successfully",
            "machine": machine.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating machine: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({"error": f"Failed to create machine: {str(e)}"}), 500

@machine_mgmt_bp.route('/machines/<machine_id>/sensors', methods=['POST'])
def add_sensor_config():
    """Add or update sensor configuration for a machine."""
    try:
        data = request.get_json()
        machine_id = request.view_args['machine_id']
        
        # Find machine
        machine = Machine.query.filter_by(machine_id=machine_id).first()
        if not machine:
            return jsonify({"error": "Machine not found"}), 404
        
        # Update sensor configuration
        if 'sensor_config' in data:
            machine.sensor_config = data['sensor_config']
        
        if 'alert_thresholds' in data:
            machine.alert_thresholds = data['alert_thresholds']
        
        machine.last_updated = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "message": "Sensor configuration updated successfully",
            "machine": machine.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating sensor config: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to update sensor configuration"}), 500

@machine_mgmt_bp.route('/machines/<machine_id>', methods=['DELETE'])
@admin_required
def delete_machine(machine_id):
    """Delete a machine."""
    try:
        # Find machine
        machine = Machine.query.filter_by(machine_id=machine_id).first()
        if not machine:
            return jsonify({"error": "Machine not found"}), 404
        
        # Delete related data
        MachineState.query.filter_by(machine_id=machine_id).delete()
        MaintenanceRecord.query.filter_by(machine_id=machine_id).delete()
        
        # Delete machine
        db.session.delete(machine)
        db.session.commit()
        
        return jsonify({
            "message": "Machine deleted successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting machine: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to delete machine"}), 500

@machine_mgmt_bp.route('/machines/<string:machine_id>', methods=['PUT'])
def update_machine(machine_id):
    """Update an existing machine."""
    try:
        data = request.get_json()
        
        # Find machine
        machine = Machine.query.filter_by(machine_id=machine_id).first()
        if not machine:
            return jsonify({"error": "Machine not found"}), 404
        
        # Update machine fields
        if 'name' in data:
            machine.name = data['name']
        if 'machine_type' in data:
            machine.machine_type = data['machine_type']
        if 'manufacturer' in data:
            machine.manufacturer = data['manufacturer']
        if 'model' in data:
            machine.model = data['model']
        if 'serial_number' in data:
            machine.serial_number = data['serial_number']
        if 'location' in data:
            machine.location = data['location']
        if 'installation_date' in data:
            machine.installation_date = datetime.fromisoformat(data['installation_date'].replace('Z', '+00:00'))
        if 'sensor_config' in data:
            machine.sensor_config = data['sensor_config']
        if 'thresholds' in data:
            machine.thresholds = data['thresholds']
        
        machine.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "message": "Machine updated successfully",
            "machine": machine.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating machine: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to update machine"}), 500
