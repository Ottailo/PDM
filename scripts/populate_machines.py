#!/usr/bin/env python3
"""
Script to populate the database with machines from the simulator configuration.
This ensures the machine management dropdowns are populated correctly.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.company import Company, Machine
from app.models.sensor_data import MachineState
from app.config.machine_config import MACHINES, SENSOR_CONFIG
from datetime import datetime

def populate_machines():
    """Populate the database with machines from the simulator configuration."""
    app = create_app()
    
    with app.app_context():
        try:
            # Ensure GDK Perfume company exists
            company = Company.query.filter_by(name="GDK Perfume").first()
            if not company:
                company = Company(
                    name="GDK Perfume",
                    industry="Manufacturing",
                    contact_email="admin@gdkperfume.com",
                    contact_phone="+1-555-0123",
                    address="123 Industrial Ave, Factory City, FC 12345"
                )
                db.session.add(company)
                db.session.commit()
                print(f"Created company: {company.name}")
            
            # Add all machines from MACHINES configuration
            machines_added = 0
            for machine_type, machine_ids in MACHINES.items():
                for machine_id in machine_ids:
                    # Check if machine already exists
                    existing_machine = Machine.query.filter_by(machine_id=machine_id).first()
                    if existing_machine:
                        print(f"Machine {machine_id} already exists, skipping...")
                        continue
                    
                    # Create sensor configuration for this machine type
                    sensor_config = {}
                    alert_thresholds = {}
                    
                    if machine_type in SENSOR_CONFIG:
                        for sensor_name, config in SENSOR_CONFIG[machine_type].items():
                            sensor_config[sensor_name] = {
                                "unit": config["unit"],
                                "min_value": config["mean"] - (3 * config["std_dev"]),
                                "max_value": config["mean"] + (3 * config["std_dev"])
                            }
                            alert_thresholds[sensor_name] = {
                                "warning": config["warn_threshold"],
                                "critical": config["crit_threshold"]
                            }
                    
                    # Create machine
                    machine = Machine(
                        machine_id=machine_id,
                        name=f"{machine_type.title()} Machine {machine_id.split('_')[1]}",
                        machine_type=machine_type,
                        manufacturer="Industrial Systems Inc.",
                        model=f"{machine_type}-2024",
                        serial_number=f"SN{machine_id.replace('_', '')}",
                        location="Production Floor A",
                        company_id=company.id,
                        sensor_config=sensor_config,
                        thresholds=alert_thresholds,
                        installation_date=datetime.utcnow()
                    )
                    
                    db.session.add(machine)
                    machines_added += 1
                    print(f"Added machine: {machine_id} ({machine_type})")
            
            # Commit all changes
            db.session.commit()
            print(f"\n✅ Successfully added {machines_added} machines to the database!")
            print(f"Company: {company.name} (ID: {company.id})")
            
            # Verify machines were added
            total_machines = Machine.query.count()
            print(f"Total machines in database: {total_machines}")
            
        except Exception as e:
            print(f"❌ Error populating machines: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    populate_machines()
