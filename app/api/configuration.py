"""
Configuration API Routes (v2)
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models.configuration import (
    AssetTemplate, SensorTemplate, AssetTemplateSensor,
    FailureModeTemplate, Asset, AssetSensor, Location
)
from app.models.company import Company
from functools import wraps

config_bp = Blueprint('config', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- Templates ---

@config_bp.route('/templates', methods=['GET'])
@login_required
def get_templates():
    """Get all asset templates."""
    templates = AssetTemplate.query.all()
    return jsonify([t.to_dict() for t in templates]), 200

@config_bp.route('/templates', methods=['POST'])
@login_required
@admin_required
def create_template():
    """Create a new asset template."""
    data = request.get_json()
    if not data.get('name'):
        return jsonify({"error": "Name is required"}), 400
        
    if AssetTemplate.query.filter_by(name=data['name']).first():
        return jsonify({"error": "Template with this name already exists"}), 400
        
    template = AssetTemplate(
        name=data['name'],
        description=data.get('description'),
        manufacturer=data.get('manufacturer'),
        version=data.get('version')
    )
    db.session.add(template)
    db.session.commit()
    return jsonify(template.to_dict()), 201

@config_bp.route('/templates/<int:id>', methods=['GET'])
@login_required
def get_template(id):
    """Get a specific asset template with details."""
    template = AssetTemplate.query.get_or_404(id)
    result = template.to_dict()
    
    # Include sensors and failure modes
    result['sensors'] = [{
        'id': s.sensor_template.id,
        'name': s.sensor_template.name,
        'unit': s.sensor_template.unit,
        'default_min': s.default_threshold_min,
        'default_max': s.default_threshold_max
    } for s in template.sensors]
    
    result['failure_modes'] = [fm.to_dict() for fm in template.failure_modes]
    
    return jsonify(result), 200

@config_bp.route('/templates/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_template(id):
    """Delete an asset template."""
    template = AssetTemplate.query.get_or_404(id)
    db.session.delete(template)
    db.session.commit()
    return jsonify({"message": "Template deleted successfully"}), 200

@config_bp.route('/templates/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_template(id):
    """Update an asset template."""
    template = AssetTemplate.query.get_or_404(id)
    data = request.get_json()
    
    if 'name' in data:
        existing = AssetTemplate.query.filter_by(name=data['name']).first()
        if existing and existing.id != id:
            return jsonify({"error": "Template with this name already exists"}), 400
        template.name = data['name']
        
    if 'description' in data:
        template.description = data['description']
    if 'manufacturer' in data:
        template.manufacturer = data['manufacturer']
    if 'version' in data:
        template.version = data['version']
        
    db.session.commit()
    return jsonify(template.to_dict()), 200

# --- Assets ---

@config_bp.route('/assets', methods=['GET'])
@login_required
def get_assets():
    """Get all assets."""
    assets = Asset.query.all()
    return jsonify([a.to_dict() for a in assets]), 200

@config_bp.route('/assets', methods=['POST'])
@login_required
@admin_required
def create_asset():
    """Create a new asset instance."""
    data = request.get_json()
    required = ['name', 'asset_template_id', 'company_id']
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
            
    asset = Asset(
        name=data['name'],
        asset_template_id=data['asset_template_id'],
        company_id=data['company_id'],
        location_id=data.get('location_id'),
        serial_number=data.get('serial_number'),
        status=data.get('status', 'Active')
    )
    db.session.add(asset)
    db.session.commit()
    
    # Auto-create sensors from template? 
    # For now, let's assume a separate step or auto-creation logic if needed.
    # But usually, we want to instantiate sensors based on the template.
    template = AssetTemplate.query.get(data['asset_template_id'])
    if template:
        for ts in template.sensors:
            # Create AssetSensor
            # Channel ID generation strategy? For now, use name.
            channel_id = f"{asset.name}_{ts.sensor_template.name.split('_')[-1]}" 
            
            asset_sensor = AssetSensor(
                asset_id=asset.id,
                sensor_template_id=ts.sensor_template_id,
                channel_id=channel_id,
                config_overrides={
                    "warn": ts.default_threshold_min, # Mapping logic might need refinement
                    "crit": ts.default_threshold_max
                }
            )
            db.session.add(asset_sensor)
        db.session.commit()
    
    return jsonify(asset.to_dict()), 201

@config_bp.route('/assets/<int:id>', methods=['GET'])
@login_required
def get_asset(id):
    """Get asset details."""
    asset = Asset.query.get_or_404(id)
    result = asset.to_dict()
    result['sensors'] = [s.to_dict() for s in asset.sensors]
    return jsonify(result), 200

@config_bp.route('/assets/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def delete_asset(id):
    """Delete an asset."""
    asset = Asset.query.get_or_404(id)
    db.session.delete(asset)
    db.session.commit()
    return jsonify({"message": "Asset deleted successfully"}), 200

@config_bp.route('/assets/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_asset(id):
    """Update an asset."""
    asset = Asset.query.get_or_404(id)
    data = request.get_json()
    
    if 'name' in data:
        # Check uniqueness if needed, though Asset name isn't strictly unique in model but should be
        asset.name = data['name']
        
    if 'location_id' in data:
        asset.location_id = data['location_id']
    if 'serial_number' in data:
        asset.serial_number = data['serial_number']
    if 'status' in data:
        asset.status = data['status']
        
    db.session.commit()
    return jsonify(asset.to_dict()), 200

# --- Locations ---

@config_bp.route('/locations', methods=['GET'])
@login_required
def get_locations():
    """Get location hierarchy."""
    locations = Location.query.all()
    return jsonify([l.to_dict() for l in locations]), 200
