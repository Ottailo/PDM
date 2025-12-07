"""
Data Simulator Service for generating realistic machine sensor data.
"""
import logging
import os
import random
import numpy as np
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.sensor_data import SensorData, EventLog, MachineState
from app.config.machine_config import (
    MACHINES, SENSOR_CONFIG, OPERATIONAL_DAYS, OPERATIONAL_HOURS,
    PROB_DEGRADE_START, PROB_OPERATOR_ERROR, PROB_SCHED_MAINTENANCE,
    FAILURE_MODES
)

logger = logging.getLogger(__name__)

class DataSimulator:
    """Simulates sensor data and machine states for testing and development."""
    
    def __init__(self):
        """Initialize the simulator."""
        pass
        
    def ensure_initialized(self):
        """Ensure machine states are initialized."""
        self.initialize_states()
        
    def initialize_states(self):
        """Initialize or load machine states."""
        try:
            # Create states for machines that don't have them
            for machine_type, instances in MACHINES.items():
                for machine_id in instances:
                    state = MachineState.query.filter_by(machine_id=machine_id).first()
                    if not state:
                        state = MachineState(
                            machine_id=machine_id,
                            status="Normal",
                            health_factor=1.0 - (random.random() * 0.4)
                        )
                        db.session.add(state)
            
            db.session.commit()
            logger.info("Machine states initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing states: {str(e)}")
            db.session.rollback()
            raise
            
    def is_operational(self, timestamp):
        """Check if the factory is operational at the given timestamp."""
        # Factory now operates 24/7 for continuous monitoring
        return True
                
    def apply_drift(self, current_means):
        """Apply random drift to sensor means."""
        DRIFT_FACTOR = 0.00005 / 3600.0
        
        for sensor_id, mean_val in current_means.items():
            parts = sensor_id.split('_')
            if len(parts) > 2:
                machine_type = parts[0]
                sensor_base_name = '_'.join(parts[2:])
                if (machine_type in SENSOR_CONFIG and 
                    sensor_base_name in SENSOR_CONFIG[machine_type]):
                    base_mean = SENSOR_CONFIG[machine_type][sensor_base_name]['mean']
                    current_means[sensor_id] += np.random.normal(0, base_mean * DRIFT_FACTOR)
                    
        return current_means
        
    def generate_sensor_reading(self, machine_id, sensor_name, mean_value, state):
        """Generate a single sensor reading based on machine state."""
        machine_type = machine_id.split('_')[0]
        
        # Check if machine type exists in SENSOR_CONFIG
        if machine_type not in SENSOR_CONFIG:
            logger.warning(f"Machine type {machine_type} not found in SENSOR_CONFIG, skipping")
            return 0.0
            
        if sensor_name not in SENSOR_CONFIG[machine_type]:
            logger.warning(f"Sensor {sensor_name} not found for machine type {machine_type}, skipping")
            return 0.0
            
        sensor_config = SENSOR_CONFIG[machine_type][sensor_name]
        
        if state.status in ["Maintenance", "Off", "Scheduled Maintenance"]:
            return 0.0
            
        if state.status == "Operator Error":
            return np.random.normal(sensor_config['mean'], sensor_config['std_dev'] * 5)
            
        value = np.random.normal(mean_value, sensor_config['std_dev'])
        
        # Apply degradation effects if active failure
        if state.status == "Degrading" and state.active_failure:
            progress = state.active_failure.get('progress', 0)
            failure_type = state.active_failure.get('type')
            
            if failure_type in FAILURE_MODES.get(machine_type, {}):
                failure_config = FAILURE_MODES[machine_type][failure_type]
                if sensor_name in failure_config.get('trends', {}):
                    trend = failure_config['trends'][sensor_name]
                    effect = progress ** 2  # Exponential degradation
                    if trend == "increase":
                        value *= (1 + effect)
                    else:
                        value *= (1 - effect)
                        
        return max(0, value)
        
    def request_maintenance(self, machine_id):
        """Request maintenance for a specific machine."""
        try:
            state = MachineState.query.filter_by(machine_id=machine_id).first()
            if not state:
                raise ValueError(f"No state found for machine {machine_id}")
                
            state.status = "Maintenance"
            state.event_steps_left = 180  # 3 hours
            state.active_failure = None
            
            # Log the event
            event = EventLog(
                timestamp=datetime.utcnow(),
                machine_id=machine_id,
                event_type="Maintenance",
                details=f"Maintenance requested for {machine_id}"
            )
            db.session.add(event)
            db.session.commit()
            
            logger.info(f"Maintenance requested for {machine_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error requesting maintenance: {str(e)}")
            db.session.rollback()
            return False
            
    def update_machine_state(self, state):
        """Update the state of a single machine."""
        old_status = state.status
        
        # Handle active events
        if state.event_steps_left > 0:
            state.event_steps_left -= 1
            if state.event_steps_left == 0:
                self.reset_machine_state(state)
                
        # Generate new events for normal machines
        elif state.status == "Normal":
            if random.random() < PROB_OPERATOR_ERROR:
                state.status = "Operator Error"
                state.event_steps_left = random.randint(30, 90)
            elif random.random() < PROB_SCHED_MAINTENANCE:
                state.status = "Scheduled Maintenance"
                state.event_steps_left = random.randint(3600, 7200)
            elif random.random() < (PROB_DEGRADE_START / state.health_factor):
                self.start_degradation(state)
                
        # Update degradation progress
        elif state.status == "Degrading" and state.active_failure:
            progress = state.active_failure.get('progress', 0)
            state.active_failure['progress'] = min(1.0, progress + (0.001 / state.health_factor))
            
        # Log state changes
        if old_status != state.status:
            event = EventLog(
                timestamp=datetime.utcnow(),
                machine_id=state.machine_id,
                event_type=state.status,
                details=f"{state.machine_id} changed from {old_status} to {state.status}"
            )
            db.session.add(event)
            
    def reset_machine_state(self, state):
        """Reset a machine to normal operation."""
        state.status = "Normal"
        state.active_failure = None
        state.event_steps_left = 0
        logger.info(f"Reset {state.machine_id} to Normal state")
        
    def start_degradation(self, state):
        """Start a degradation process for a machine."""
        machine_type = state.machine_id.split('_')[0]
        failure_modes = FAILURE_MODES.get(machine_type, {})
        
        if not failure_modes:
            return
            
        # Select a random failure mode
        failure_type = random.choice(list(failure_modes.keys()))
        
        state.status = "Degrading"
        state.active_failure = {
            'type': failure_type,
            'progress': 0.0
        }
        
        logger.info(f"Started degradation on {state.machine_id}: {failure_type}")
        
    def generate_sensor_data(self):
        """Generate a new set of sensor readings for all machines."""
        current_time = datetime.utcnow()
        
        if not self.is_operational(current_time):
            return
            
        try:
            # Update all machine states
            states = MachineState.query.all()
            for state in states:
                self.update_machine_state(state)
                
            # Generate sensor readings
            readings = []
            for state in states:
                machine_type = state.machine_id.split('_')[0]
                
                # Skip if machine type doesn't exist in SENSOR_CONFIG
                if machine_type not in SENSOR_CONFIG:
                    logger.warning(f"Skipping machine {state.machine_id} - type {machine_type} not in SENSOR_CONFIG")
                    continue
                    
                for sensor_name, config in SENSOR_CONFIG[machine_type].items():
                    sensor_id = f"{state.machine_id}_{sensor_name}"
                    mean_value = config['mean']
                    
                    value = self.generate_sensor_reading(
                        state.machine_id, sensor_name, mean_value, state
                    )
                    
                    readings.append(SensorData(
                        timestamp=current_time,
                        sensor_id=sensor_id,
                        value=value
                    ))
                    
            # Save all changes
            db.session.bulk_save_objects(readings)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error generating sensor data: {str(e)}")
            db.session.rollback()
            raise
