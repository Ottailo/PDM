#!/usr/bin/env python3
"""
Create basic ML models for the predictive maintenance system.
This script creates simple models that can be used for demonstration.
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import joblib
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import logging

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.machine_config import MACHINES, SENSOR_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_synthetic_data(machine_type, n_samples=1000):
    """Create synthetic training data for a machine type."""
    sensors = SENSOR_CONFIG.get(machine_type, {})
    if not sensors:
        return None
    
    # Create time series data
    timestamps = pd.date_range(start='2024-01-01', periods=n_samples, freq='5min')
    
    data = []
    for i, (sensor_name, config) in enumerate(sensors.items()):
        # Generate realistic sensor data with some degradation over time
        base_value = config['mean']
        std_dev = config['std_dev']
        
        # Add some degradation trend
        degradation = np.linspace(0, 0.1, n_samples) * np.random.normal(0, 0.05, n_samples)
        noise = np.random.normal(0, std_dev, n_samples)
        
        values = base_value + degradation + noise
        
        for j, (ts, val) in enumerate(zip(timestamps, values)):
            data.append({
                'timestamp': ts,
                'machine_id': f'{machine_type}_001',
                'sensor_id': f'{machine_type}_001_{sensor_name}',
                'value': val
            })
    
    return pd.DataFrame(data)

def create_lstm_model(input_shape, num_classes=2):
    """Create a simple LSTM model for classification and regression."""
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(25, activation='relu'),
        Dense(num_classes, activation='softmax')  # Classification output
    ])
    
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model

def create_rul_model(input_shape):
    """Create a simple model for RUL prediction."""
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(25, activation='relu'),
        Dense(1, activation='linear')  # Regression output
    ])
    
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='mse',
        metrics=['mae']
    )
    
    return model

def prepare_training_data(df, window_size=10):
    """Prepare training data for LSTM."""
    if df is None or df.empty:
        return None, None, None, None
    
    # Pivot data to get sensors as columns
    df_pivot = df.pivot(index='timestamp', columns='sensor_id', values='value')
    df_pivot = df_pivot.ffill().bfill().fillna(0)
    
    # Create sequences
    X, y_class, y_rul = [], [], []
    
    for i in range(window_size, len(df_pivot)):
        # Input sequence
        seq = df_pivot.iloc[i-window_size:i].values
        X.append(seq)
        
        # Classification target (degrading vs normal)
        # Simple heuristic: if any sensor is outside normal range
        is_degrading = 0
        machine_type = df_pivot.columns[0].split('_')[0]
        for col in df_pivot.columns:
            sensor_name = col.split('_')[-1]
            if sensor_name in SENSOR_CONFIG.get(machine_type, {}):
                config = SENSOR_CONFIG[machine_type][sensor_name]
                # Check if value is outside normal range (mean ± 2*std_dev)
                normal_min = config['mean'] - 2 * config['std_dev']
                normal_max = config['mean'] + 2 * config['std_dev']
                if seq[-1, df_pivot.columns.get_loc(col)] < normal_min or seq[-1, df_pivot.columns.get_loc(col)] > normal_max:
                    is_degrading = 1
                    break
        
        y_class.append(is_degrading)
        
        # RUL target (hours until failure)
        # Simple heuristic: more degradation = shorter RUL
        rul = max(1, 168 - (i * 0.1))  # 168 hours max, decreasing over time
        y_rul.append(rul)
    
    return np.array(X), np.array(y_class), np.array(y_rul), df_pivot.columns.tolist()

def main():
    """Create basic models for all machine types."""
    model_base_dir = 'models'
    os.makedirs(model_base_dir, exist_ok=True)
    
    for machine_type in MACHINES:
        logger.info(f"Creating models for {machine_type}")
        
        # Create model directory
        machine_dir = os.path.join(model_base_dir, machine_type)
        os.makedirs(machine_dir, exist_ok=True)
        
        # Generate synthetic data
        df = create_synthetic_data(machine_type)
        if df is None:
            logger.warning(f"No sensor config for {machine_type}, skipping")
            continue
        
        # Prepare training data
        X, y_class, y_rul, sensor_columns = prepare_training_data(df)
        if X is None or len(X) == 0:
            logger.warning(f"No training data for {machine_type}, skipping")
            continue
        
        # Create and train classification model
        class_model = create_lstm_model((X.shape[1], X.shape[2]))
        class_model.fit(X, y_class, epochs=10, batch_size=32, validation_split=0.2, verbose=0)
        
        # Create and train RUL model
        rul_model = create_rul_model((X.shape[1], X.shape[2]))
        rul_model.fit(X, y_rul, epochs=10, batch_size=32, validation_split=0.2, verbose=0)
        
        # Create scalers
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X.reshape(-1, X.shape[-1])).reshape(X.shape)
        
        rul_scaler = MinMaxScaler()
        y_rul_scaled = rul_scaler.fit_transform(y_rul.reshape(-1, 1))
        
        # Save models and scalers
        class_model.save(os.path.join(machine_dir, f"{machine_type.lower()}_recurrent_model.keras"))
        joblib.dump(scaler, os.path.join(machine_dir, f"{machine_type.lower()}_scaler.joblib"))
        joblib.dump(rul_scaler, os.path.join(machine_dir, f"{machine_type.lower()}_rul_scaler.joblib"))
        
        logger.info(f"Created models for {machine_type}")
    
    logger.info("Model creation completed!")

if __name__ == "__main__":
    main()
