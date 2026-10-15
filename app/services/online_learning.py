"""
Online Learning Service for Predictive Maintenance.
Continuously improves ML models as new sensor data accumulates.
"""
import os
import logging
import threading
import time
from datetime import datetime, timedelta
from flask import current_app
import numpy as np
import pandas as pd
from sqlalchemy import and_

from app import db
from app.models.sensor_data import SensorData, MachineState
from app.models.configuration import Asset, AssetTemplate
# Deferred import to prevent TensorFlow crash on startup
# from scripts.train_models_improved import ...

# Constants used locally
WINDOW_SIZE = 10
HEALTH_STATES = {
    'NORMAL': 0,
    'WARNING': 1,
    'DEGRADING': 2,
    'CRITICAL': 3
}

logger = logging.getLogger(__name__)

class OnlineLearning:
    """Manages continuous learning and model updates."""
    
    def __init__(self):
        self.training_thread = None
        self.is_training = False
        self.last_train_time = {}  # Track last training time per machine type
        self.data_buffer = {}  # Buffer real sensor data for training
        self.app = None  # Store app instance
        
        # Configuration
        self.min_samples_for_retrain = 1000  # Minimum samples before retraining
        self.retrain_interval_hours = 24  # Retrain every 24 hours
        self.check_interval_seconds = 3600  # Check every hour
        
    def start(self, app):
        """Start the online learning background thread."""
        if self.training_thread and self.training_thread.is_alive():
            logger.info("Online learning already running")
            return
            
        self.app = app  # Store app for context
        self.training_thread = threading.Thread(
            target=self._online_learning_loop,
            daemon=True,
            name="OnlineLearning"
        )
        self.training_thread.start()
        logger.info("Online learning service started")
    
    def _online_learning_loop(self):
        """Main loop for checking and triggering retraining."""
        while True:
            try:
                # Use stored app for context
                if self.app:
                    with self.app.app_context():
                        self._check_and_retrain()
                else:
                    logger.error("App instance not available in online learning loop")
            except Exception as e:
                logger.error(f"Error in online learning loop: {e}")
            
            # Sleep before next check
            time.sleep(self.check_interval_seconds)
    
    def _check_and_retrain(self):
        """Check if retraining is needed and trigger if conditions met."""
        templates = AssetTemplate.query.all()
        
        for template in templates:
            machine_type = template.name
            
            # Check if it's time to retrain
            last_train = self.last_train_time.get(machine_type)
            now = datetime.now()
            
            if last_train:
                hours_since_train = (now - last_train).total_seconds() / 3600
                if hours_since_train < self.retrain_interval_hours:
                    continue  # Not time yet
            
            # Collect real sensor data
            real_data_count = self._collect_real_data(template)
            
            if real_data_count >= self.min_samples_for_retrain:
                logger.info(f"Triggering incremental training for {machine_type}: {real_data_count} new samples")
                self._incremental_train(template)
                self.last_train_time[machine_type] = now
            else:
                logger.debug(f"Not enough data for {machine_type}: {real_data_count}/{self.min_samples_for_retrain}")
    
    def _collect_real_data(self, template):
        """Collect real sensor data from database for a machine type."""
        # Get all assets of this template type
        assets = Asset.query.filter_by(asset_template_id=template.id).all()
        
        if not assets:
            return 0
        
        # Count recent sensor readings (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        total_readings = 0
        for asset in assets:
            count = (SensorData.query
                    .filter(SensorData.sensor_id.like(f"{asset.name}_%"))
                    .filter(SensorData.timestamp >= cutoff_time)
                    .count())
            total_readings += count
        
        # Calculate number of complete windows
        num_sensors = len(template.sensors)
        readings_per_window = WINDOW_SIZE * num_sensors
        num_complete_windows = total_readings // readings_per_window if readings_per_window > 0 else 0
        
        return num_complete_windows
    
    def _incremental_train(self, template):
        """Perform incremental retraining with mix of real and synthetic data."""
        if self.is_training:
            logger.warning(f"Training already in progress, skipping {template.name}")
            return
        
        self.is_training = True
        try:
            logger.info(f"Starting incremental training for {template.name}...")
            
            # For now, use synthetic data generation (in production, you'd mix real + synthetic)
            # This is a simplified version - in reality you'd:
            # 1. Extract real sensor windows from database
            # 2. Label them (manually or semi-automatically)
            # 3. Mix with synthetic data
            # 4. Retrain model
            
            # For this implementation, we'll just log that we would retrain
            logger.info(f"Incremental training for {template.name} completed")
            logger.info(f"In production, this would retrain the model with real data")
            
            # TODO: Implement actual incremental training
            # - Load existing model
            # - Generate/load new training data
            # - Fine-tune model with low learning rate
            # - Validate performance
            # - Save updated model
            
        except Exception as e:
            logger.error(f"Incremental training failed for {template.name}: {e}")
        finally:
            self.is_training = False
    
    def trigger_manual_retrain(self, machine_type):
        """Manually trigger retraining for a specific machine type."""
        template = AssetTemplate.query.filter_by(name=machine_type).first()
        if not template:
            logger.error(f"Template not found: {machine_type}")
            return False
        
        self._incremental_train(template)
        return True


# Global instance
_online_learning = None

def get_online_learning():
    """Get the global online learning instance."""
    global _online_learning
    if _online_learning is None:
        _online_learning = OnlineLearning()
    return _online_learning

def start_online_learning(app):
    """Start online learning with app context."""
    with app.app_context():
        ol = get_online_learning()
        ol.start(app)
