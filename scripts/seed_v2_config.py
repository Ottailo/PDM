import sys
import os
sys.path.append(os.getcwd())

from app import create_app, db
from app.models.configuration import (
    Location, AssetTemplate, SensorTemplate, AssetTemplateSensor,
    FailureModeTemplate, Asset, AssetSensor
)
from app.models.company import Company
from app.config.machine_config import MACHINES, SENSOR_CONFIG, FAILURE_MODES

app = create_app()

def seed_v2_config():
    with app.app_context():
        print("Seeding v2 configuration...")
        
        # 1. Ensure Company exists
        company = Company.query.get(1)
        if not company:
            print("Creating default company...")
            company = Company(id=1, name="GDK Perfume", industry="Manufacturing", contact_email="admin@gdk.com")
            db.session.add(company)
            db.session.commit()
            
        # 2. Ensure Location exists
        location = Location.query.filter_by(name="Factory Floor").first()
        if not location:
            print("Creating default location...")
            location = Location(name="Factory Floor", type="Area", path="1")
            db.session.add(location)
            db.session.commit()
            
        # 3. Create Templates
        for machine_type, machine_ids in MACHINES.items():
            print(f"Processing template: {machine_type}")
            
            # AssetTemplate
            template = AssetTemplate.query.filter_by(name=machine_type).first()
            if not template:
                template = AssetTemplate(name=machine_type, description=f"{machine_type} Machine Type")
                db.session.add(template)
                db.session.commit()
            
            # FailureModeTemplate
            if machine_type in FAILURE_MODES:
                for fm_name, fm_data in FAILURE_MODES[machine_type].items():
                    fm = FailureModeTemplate.query.filter_by(asset_template_id=template.id, name=fm_name).first()
                    if not fm:
                        fm = FailureModeTemplate(
                            asset_template_id=template.id,
                            name=fm_name,
                            description=fm_data.get('recommendation', ''),
                            severity=5 # Default
                        )
                        db.session.add(fm)
                db.session.commit()

            # SensorTemplate & AssetTemplateSensor
            if machine_type in SENSOR_CONFIG:
                for sensor_name, sensor_data in SENSOR_CONFIG[machine_type].items():
                    # SensorTemplate (Global)
                    # We append machine type to name if needed to make it unique, or reuse if generic?
                    # The config has generic names like "Vibration" but specific params.
                    # Let's create specific templates for now to preserve params.
                    template_sensor_name = f"{machine_type}_{sensor_name}"
                    
                    st = SensorTemplate.query.filter_by(name=template_sensor_name).first()
                    if not st:
                        st = SensorTemplate(
                            name=template_sensor_name,
                            unit=sensor_data.get('unit', ''),
                            min_range=0.0, # Not in config
                            max_range=1000.0, # Not in config
                            sampling_rate_hz=1.0
                        )
                        db.session.add(st)
                        db.session.commit()
                    
                    # Link to AssetTemplate
                    ats = AssetTemplateSensor.query.filter_by(asset_template_id=template.id, sensor_template_id=st.id).first()
                    if not ats:
                        ats = AssetTemplateSensor(
                            asset_template_id=template.id,
                            sensor_template_id=st.id,
                            default_threshold_min=sensor_data.get('warn_threshold', 0) * 0.5, # Guess
                            default_threshold_max=sensor_data.get('crit_threshold', 100)
                        )
                        db.session.add(ats)
                        db.session.commit()

            # 4. Create Assets (Instances)
            for machine_id in machine_ids:
                asset = Asset.query.filter_by(name=machine_id).first()
                if not asset:
                    print(f"Creating asset: {machine_id}")
                    asset = Asset(
                        name=machine_id,
                        asset_template_id=template.id,
                        location_id=location.id,
                        company_id=company.id,
                        status="Active"
                    )
                    db.session.add(asset)
                    db.session.commit()
                
                # Create AssetSensors
                # We iterate through the template sensors we just created/found
                if machine_type in SENSOR_CONFIG:
                    for sensor_name, sensor_data in SENSOR_CONFIG[machine_type].items():
                         template_sensor_name = f"{machine_type}_{sensor_name}"
                         st = SensorTemplate.query.filter_by(name=template_sensor_name).first()
                         
                         # Channel ID logic: currently simulator uses "{machine_id}_{sensor_name}"
                         channel_id = f"{machine_id}_{sensor_name}"
                         
                         asensor = AssetSensor.query.filter_by(asset_id=asset.id, channel_id=channel_id).first()
                         if not asensor:
                             asensor = AssetSensor(
                                 asset_id=asset.id,
                                 sensor_template_id=st.id,
                                 channel_id=channel_id,
                                 config_overrides={
                                     "warn": sensor_data.get('warn_threshold'),
                                     "crit": sensor_data.get('crit_threshold')
                                 }
                             )
                             db.session.add(asensor)
                             db.session.commit()

        print("Seeding complete.")

if __name__ == "__main__":
    seed_v2_config()
