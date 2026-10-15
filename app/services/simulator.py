"""
Data Simulator Service for generating realistic machine sensor data.
Implements a Physics-Lite engine for deterministic, concurrent failure simulation.
"""
import logging
import os
import random
import json
import numpy as np
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.sensor_data import SensorData, EventLog, MachineState
from app.models.configuration import Asset, AssetSensor, AssetTemplate

logger = logging.getLogger(__name__)

# --- Physics Engine Configuration ---
# Defines how specific failures affect specific sensors.
# Structure: { FailureMode: { SensorType: { type: 'offset'|'drift'|'noise', magnitude: float } } }
# magnitude: multiplier for the effect (e.g. 1.0 means full effect at 100% severity)
FAILURE_EFFECTS = {
    # FILLING Machine Failures
    "Nozzle Clog": {
        "Pressure": {"type": "offset", "magnitude": 2.5},   # Pressure rises significantly
        "Flow": {"type": "offset", "magnitude": -1.5},       # Flow decreases
        "Vibration": {"type": "noise", "magnitude": 2.0}     # Turbulence causes noise
    },
    "Pump Wear": {
        "Pressure": {"type": "offset", "magnitude": -1.5},  # Pressure drops
        "Vibration": {"type": "offset", "magnitude": 2.0},  # Vibration increases heavily
        "Flow": {"type": "noise", "magnitude": 1.5}          # Flow becomes erratic
    },
    "Seal Deterioration": {
         "Pressure": {"type": "drift", "magnitude": -1.0},   # Slow pressure leak
    },
    
    # BOXING Machine Failures
    "Conveyor Belt Stretch": {
        "Speed": {"type": "drift", "magnitude": -0.8},       # Speed slows down
        "Vibration": {"type": "noise", "magnitude": 1.5}     # Belt flap causes noise
    },
    "Pneumatic Seal Wear": {
        "Pressure": {"type": "drift", "magnitude": -1.2},    # Pressure leak
    },
    "Sensor Calibration Drift": {
        "ALL": {"type": "drift", "magnitude": 0.5}           # Generic sensor drift
    },

    # PACKAGING/SHRINK Failures
    "Heater Element Degradation": {
        "Temperature": {"type": "drift", "magnitude": -2.0}, # Temp drops
        "Power": {"type": "offset", "magnitude": 1.0}        # Power usage might spike (resistance change)
    },
    "Insulation Failure": {
        "Temperature": {"type": "noise", "magnitude": 3.0}   # Temp becomes unstable
    },
    
    # Generic
    "Component Wear Detected": {
         "Vibration": {"type": "drift", "magnitude": 0.5}
    }
}

class DataSimulator:
    """Simulates sensor data and machine states using a physics-lite engine."""
    
    def __init__(self):
        self.noise_level = 0.02 # 2% base noise

    def ensure_initialized(self):
        """Ensure machine states are initialized."""
        try:
            assets = Asset.query.all()
            for asset in assets:
                state = MachineState.query.filter_by(machine_id=asset.name).first()
                if not state:
                    self._create_new_state(asset)
            
            # --- User Request: Add Extra Sensor to Box_001 ---
            box001 = None
            for a in assets:
                if a.name == 'BOXING_001':
                    box001 = a
                    break
            
            if box001:
                # Check if it has Aux Sensor (look for suffix)
                has_aux = any(s.channel_id.endswith('_Aux_Vibration') for s in box001.sensors)
                if not has_aux:
                    # Find Vibration template
                    from app.models.configuration import SensorTemplate
                    # Assuming we can access Config models
                    vib_temp = SensorTemplate.query.filter_by(name='Vibration').first()
                    if not vib_temp:
                         vib_temp = SensorTemplate.query.first() # Fallback
                    
                    if vib_temp:
                        new_sensor = AssetSensor(
                            asset_id=box001.id,
                            sensor_template_id=vib_temp.id,
                            channel_id=f"{box001.name}_Aux_Vibration"
                        )
                        db.session.add(new_sensor)
                        logger.info("Added Aux_Vibration to BOXING_001")

            db.session.commit()
            logger.info("Machine states initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing states: {str(e)}")
            db.session.rollback()

    def _create_new_state(self, asset):
        """Create a standard clean state for a new asset."""
        state = MachineState(
            machine_id=asset.name,
            status="Normal",
            health_factor=1.0,
            active_failure={} # JSON dict for active failures: {"Name": severity}
        )
        db.session.add(state)
        return state

    def is_operational(self, timestamp):
        return True # 24/7 operation

    def generate_sensor_data(self):
        """Main loop: Update states and generate sensor readings."""
        try:
            assets = Asset.query.all()
            current_time = datetime.utcnow()
            
            for asset in assets:
                state = MachineState.query.filter_by(machine_id=asset.name).first()
                if not state:
                    state = self._create_new_state(asset)
                    db.session.flush()

                # 1. Update Machine Physics/State (Degradation)
                self._update_machine_physics(state, asset)
                
                # 2. Generate Sensor Readings based on State
                for asset_sensor in asset.sensors:
                    value = self._calculate_sensor_value(asset, asset_sensor, state)
                    
                    # Store reading
                    reading = SensorData(
                        timestamp=current_time,
                        sensor_id=asset_sensor.channel_id,
                        value=value
                    )
                    db.session.add(reading)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error acting simulator step: {str(e)}", exc_info=True)
            db.session.rollback()

    def _update_machine_physics(self, state, asset):
        """Evolve the machine state: degrade components, trigger failures."""
        
        old_status = state.status

        # Ensure active_failure is a dict
        active_failures = state.active_failure or {}
        if isinstance(active_failures, list): # Legacy format handling
            active_failures = {} 
        
        # --- Logic 1: Randomly Start New Failures ---
        # 0.1% chance per tick to start a new failure (approx once per 1.5 hours per machine)
        if state.status == "Normal" and random.random() < 0.001: 
             possible_modes = asset.template.failure_modes
             if possible_modes:
                 mode = random.choice(possible_modes)
                 if mode.name not in active_failures:
                     active_failures[mode.name] = 0.05 # Start at 5% severity
                     logger.info(f"Feature: Started failure {mode.name} on {asset.name}")
                     
                     # Log Event for New Failure
                     event = EventLog(
                        timestamp=datetime.utcnow(),
                        machine_id=asset.name,
                        event_type="Warning",
                        details=f"Early detection: {mode.name} signature identified."
                     )
                     db.session.add(event)
        
        # --- Logic 2: Evolve Existing Failures ---
        max_severity = 0.0
        
        # We need to copy keys to iterate and modify
        for failure_name in list(active_failures.keys()):
            try:
                severity = float(active_failures[failure_name])
            except (ValueError, TypeError):
                severity = 0.0
            
            # Growth rate: random small increment
            growth = random.uniform(0.001, 0.005) 
            new_severity = min(1.0, severity + growth)
            active_failures[failure_name] = new_severity
            
            max_severity = max(max_severity, new_severity)
            
        # --- Logic 3: Update State & Health ---
        state.active_failure = active_failures
        state.health_factor = 1.0 - max_severity
        
        # Determine Status Label
        if max_severity > 0.8:
            state.status = "Critical Failure Imminent"
        elif max_severity > 0.4:
            state.status = "Degrading"
        elif max_severity > 0.1:
            state.status = "Warning" 
        elif len(active_failures) > 0:
            state.status = "Normal" # Underlying issue but not severe yet
        else:
            state.status = "Normal"

        # Log Status Change
        if state.status != old_status:
             event_type = "Info"
             if state.status in ["Warning", "Degrading"]: event_type = "Warning"
             if state.status == "Critical Failure Imminent": event_type = "Critical"
             
             event = EventLog(
                timestamp=datetime.utcnow(),
                machine_id=asset.name,
                event_type=event_type,
                details=f"Status changed to {state.status}"
             )
             db.session.add(event)

    def _calculate_sensor_value(self, asset, asset_sensor, state):
        """Calculate sensor value based on base template and active failure effects."""
        template = asset_sensor.sensor_template
        
        # 1. Base Value (from Template defaults)
        # Find the default ranges from AssetTemplate's sensor config
        # (This logic mimics the old one roughly)
        # Assuming asset.template.sensors has the ranges
        ts = next((s for s in asset.template.sensors if s.sensor_template_id == asset_sensor.sensor_template_id), None)
        
        if ts:
            base_min = ts.default_threshold_min
            base_max = ts.default_threshold_max
        else:
            base_min, base_max = 0, 100 # Fallback

        base_mean = (base_min + base_max) / 2
        base_range = (base_max - base_min)
        
        # 2. Apply Physics Effects from Active Failures
        total_offset = 0.0
        total_noise_mult = 1.0
        
        active_failures = state.active_failure or {}
        
        for failure_name, severity in active_failures.items():
            # Lookup effect
            effects = FAILURE_EFFECTS.get(failure_name, FAILURE_EFFECTS.get("Component Wear Detected", {}))
            
            # Check if this sensor type is affected
            # We match by string containment e.g. "Pressure" in "Box_Pressure_Sensor"
            sensor_name = template.name
            
            for key, effect_data in effects.items():
                if key == "ALL" or key in sensor_name:
                    # Apply effect
                    magnitude = effect_data['magnitude'] * severity * base_range
                    
                    if effect_data['type'] == 'offset':
                        total_offset += magnitude
                    elif effect_data['type'] == 'drift':
                        # Drift is like offset but maybe time based? 
                        # For now treat as offset that grows with severity (which already grows)
                        total_offset += magnitude
                    elif effect_data['type'] == 'noise':
                        # Increase noise variance
                        total_noise_mult += (magnitude * severity)

        # 3. Generate Final Value
        # Start with base mean
        val = base_mean + total_offset
        
        # Add random noise
        std_dev = (base_range / 10) * total_noise_mult
        val += np.random.normal(0, std_dev)
        
        return val

    def request_maintenance(self, machine_id):
        """Repair the machine."""
        try:
            state = MachineState.query.filter_by(machine_id=machine_id).first()
            if state:
                state.status = "Normal"
                state.health_factor = 1.0
                state.active_failure = {} # Clear all failures
                state.active_failure = {} 
                # Need to explicitly set it to empty dict for JSON
                
                # Log
                event = EventLog(
                    timestamp=datetime.utcnow(),
                    machine_id=machine_id,
                    event_type="Maintenance",
                    details="Full maintenance performed. All components repaired."
                )
                db.session.add(event)
                db.session.commit()
                return True
        except Exception:
            db.session.rollback()
        return False
