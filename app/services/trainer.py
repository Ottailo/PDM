"""
Model Training Service for Predictive Maintenance.
Trains Dual-Head GRU sequence models (Classification & RUL Regression)
and updates scalers and metrics.
"""
import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import joblib

logger = logging.getLogger(__name__)

# Ensure model directory exists
def get_model_base_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'models'))

def train_model_for_template(template_name, epochs=5, num_samples=5000, csv_path=None):
    """
    Train Dual-Head GRU model for an asset template.
    Returns (success: bool, metrics: dict, message: str)
    """
    try:
        from app.models.configuration import AssetTemplate
        template = AssetTemplate.query.filter_by(name=template_name).first()
        if not template:
            return False, {}, f"Asset template '{template_name}' not found."

        sensors = [s.sensor_template for s in template.sensors]
        num_sensors = len(sensors)
        if num_sensors == 0:
            return False, {}, f"No sensors configured for template '{template_name}'."

        import tensorflow as tf
        import keras
        from keras import layers

        window_size = 10
        batch_size = 32

        # 1. Dataset Generation or CSV Loading
        if csv_path and os.path.exists(csv_path):
            logger.info(f"Loading training data from CSV: {csv_path}")
            df = pd.read_csv(csv_path)
            # Find sensor columns matching template
            sensor_cols = [s.name for s in sensors if s.name in df.columns]
            if len(sensor_cols) < num_sensors:
                logger.warning(f"CSV missing some sensors. Using available: {sensor_cols}")
            
            raw_values = df[sensor_cols].ffill().bfill().fillna(0.0).values
            # Target generation from CSV if present
            if 'health_state' in df.columns:
                raw_labels = df['health_state'].values
            else:
                raw_labels = np.zeros(len(df), dtype=int)

            if 'rul_target' in df.columns:
                raw_rul = df['rul_target'].values
            elif 'ttf_hours' in df.columns:
                raw_rul = df['ttf_hours'].values
            else:
                raw_rul = np.full(len(df), 150.0)
        else:
            # Generate realistic synthetic degradation curves
            logger.info(f"Synthesizing {num_samples} degradation trajectory samples for {template_name}...")
            state_thresholds = {
                'NORMAL': int(num_samples * 0.50),
                'WARNING': int(num_samples * 0.75),
                'DEGRADING': int(num_samples * 0.90),
                'CRITICAL': int(num_samples * 1.00)
            }
            raw_values = []
            raw_labels = []
            raw_rul = []

            for i in range(num_samples):
                if i < state_thresholds['NORMAL']:
                    lbl = 0
                    base_mean = 0.5
                    noise = 0.05
                    ttf = np.random.randint(150, 200)
                elif i < state_thresholds['WARNING']:
                    lbl = 1
                    prog = (i - state_thresholds['NORMAL']) / (state_thresholds['WARNING'] - state_thresholds['NORMAL'])
                    base_mean = 0.5 + (prog * 0.1)
                    noise = 0.08
                    ttf = int(120 - prog * 40)
                elif i < state_thresholds['DEGRADING']:
                    lbl = 2
                    prog = (i - state_thresholds['WARNING']) / (state_thresholds['DEGRADING'] - state_thresholds['WARNING'])
                    base_mean = 0.6 + (prog * 0.15)
                    noise = 0.12
                    ttf = int(80 - prog * 60)
                else:
                    lbl = 3
                    prog = (i - state_thresholds['DEGRADING']) / (num_samples - state_thresholds['DEGRADING'])
                    base_mean = 0.75 + (prog * 0.2)
                    noise = 0.18
                    ttf = max(1, int(20 - prog * 19))

                sample_readings = []
                for s_idx in range(num_sensors):
                    val = base_mean + np.random.normal(0, noise)
                    sample_readings.append(np.clip(val, 0.0, 1.0))

                raw_values.append(sample_readings)
                raw_labels.append(lbl)
                raw_rul.append(ttf)

            raw_values = np.array(raw_values)
            raw_labels = np.array(raw_labels)
            raw_rul = np.array(raw_rul)

        # 2. Scalers Fitting
        feature_scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_features = feature_scaler.fit_transform(raw_values)

        rul_scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_rul = rul_scaler.fit_transform(raw_rul.reshape(-1, 1)).flatten()

        # 3. Create Windows
        X_seq = []
        y_cls = []
        y_reg = []
        for i in range(len(scaled_features) - window_size):
            X_seq.append(scaled_features[i:i+window_size])
            y_cls.append(raw_labels[i+window_size])
            y_reg.append(scaled_rul[i+window_size])

        X_seq = np.array(X_seq)
        y_cls = keras.utils.to_categorical(np.array(y_cls), num_classes=4)
        y_reg = np.array(y_reg)

        # 4. Build Architecture (Dual-Head GRU)
        inputs = layers.Input(shape=(window_size, num_sensors), name='sensor_sequence_input')
        x = layers.GRU(64, return_sequences=True)(inputs)
        x = layers.Dropout(0.2)(x)
        x = layers.GRU(32, return_sequences=False)(x)
        x = layers.Dropout(0.2)(x)
        features = layers.Dense(32, activation='relu')(x)

        # Head 1: Multi-class State Classification
        class_output = layers.Dense(4, activation='softmax', name='classification_head')(features)

        # Head 2: RUL Regression
        reg_dense = layers.Dense(16, activation='relu')(features)
        rul_output = layers.Dense(1, activation='linear', name='rul_regression_head')(reg_dense)

        model = keras.Model(inputs=inputs, outputs=[class_output, rul_output])
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss={
                'classification_head': 'categorical_crossentropy',
                'rul_regression_head': 'mean_squared_error'
            },
            loss_weights={'classification_head': 1.0, 'rul_regression_head': 0.5},
            metrics={'classification_head': 'accuracy', 'rul_regression_head': 'mae'}
        )

        # 5. Train Model
        logger.info(f"Fitting model for {template_name} over {epochs} epochs...")
        history = model.fit(
            X_seq,
            {'classification_head': y_cls, 'rul_regression_head': y_reg},
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2,
            verbose=0
        )

        final_acc = float(history.history['classification_head_accuracy'][-1])
        final_val_acc = float(history.history.get('val_classification_head_accuracy', [final_acc])[-1])
        final_mae = float(history.history['rul_regression_head_mae'][-1])

        # 6. Save Artifacts
        base_dir = get_model_base_dir()
        model_dir = os.path.join(base_dir, template_name)
        os.makedirs(model_dir, exist_ok=True)

        safe_type = template_name.lower().replace(" ", "_")
        model_path = os.path.join(model_dir, f"{safe_type}_recurrent_model.keras")
        scaler_path = os.path.join(model_dir, f"{safe_type}_scaler.joblib")
        rul_scaler_path = os.path.join(model_dir, f"{safe_type}_rul_scaler.joblib")
        metrics_path = os.path.join(model_dir, "evaluation_metrics.json")

        model.save(model_path)
        joblib.dump(feature_scaler, scaler_path)
        joblib.dump(rul_scaler, rul_scaler_path)

        metrics = {
            "template_name": template_name,
            "accuracy": round(final_val_acc * 100, 2),
            "training_accuracy": round(final_acc * 100, 2),
            "mae_hours": round(final_mae * 200, 1),
            "epochs": epochs,
            "window_size": window_size,
            "sensors": [s.name for s in sensors],
            "trained_at": pd.Timestamp.now().isoformat(),
            "model_path": model_path
        }

        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)

        # 7. Hot Reload in PredictiveService Cache
        try:
            from app.services.predictor import _MODEL_CACHE
            _MODEL_CACHE['models'][template_name] = model
            _MODEL_CACHE['scalers'][template_name] = feature_scaler
            _MODEL_CACHE['rul_scalers'][template_name] = rul_scaler
            _MODEL_CACHE['loaded'] = True
            logger.info(f"Hot-reloaded model cache for {template_name}")
        except Exception as cache_err:
            logger.warning(f"Could not hot-reload cache: {cache_err}")

        return True, metrics, f"Model for {template_name} trained successfully with {metrics['accuracy']}% validation accuracy."

    except Exception as e:
        logger.error(f"Error training model for {template_name}: {e}", exc_info=True)
        return False, {}, str(e)
