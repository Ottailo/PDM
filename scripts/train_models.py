"""
Train ML models for predictive maintenance in TensorFlow 2.x format.
This script generates synthetic training data and trains dual-output models
(classification + regression) for each asset template.
"""
import os
import sys
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure TensorFlow BEFORE import to suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import tensorflow as tf
# Set TF logger to ERROR only
tf.get_logger().setLevel('ERROR')

from tensorflow import keras
from tensorflow.keras import layers

# Suppress absl logging
import absl.logging
absl.logging.set_verbosity(absl.logging.ERROR)

# Set up app context
from app import create_app
from app.models.configuration import AssetTemplate

print("Starting model training...")

# Training parameters
WINDOW_SIZE = 10
EPOCHS = 50
BATCH_SIZE = 32
SAMPLES_PER_MACHINE = 5000

def generate_synthetic_data(template, num_samples=SAMPLES_PER_MACHINE):
    """Generate synthetic sensor data with degradation patterns."""
    print(f"\nGenerating {num_samples} samples for {template.name}...")
    
    # Get sensor configuration
    sensors = [s.sensor_template for s in template.sensors]
    num_sensors = len(sensors)
    
    if num_sensors == 0:
        raise ValueError(f"No sensors configured for template {template.name}")
    
    # Generate time series data
    X_data = []
    y_classification = []
    y_regression = []
    
    for i in range(num_samples):
        # Decide if this sample represents a failing machine
        is_degrading = i > num_samples * 0.7  # 30% degrading samples
        
        if is_degrading:
            # Generate degradation pattern
            degradation_progress = (i - num_samples * 0.7) / (num_samples * 0.3)
            ttf = int((1 - degradation_progress) * 100)  # Time to failure in hours
            
            # Create sensor readings with increasing variance and drift
            base_values = np.random.normal(0.5, 0.1 + degradation_progress * 0.3, (WINDOW_SIZE, num_sensors))
            drift = np.linspace(0, degradation_progress * 0.5, WINDOW_SIZE).reshape(-1, 1)
            sensor_window = base_values + drift
        else:
            # Generate normal operation pattern
            ttf = 200  # Arbitrary high value for healthy machines
            sensor_window = np.random.normal(0.5, 0.1, (WINDOW_SIZE, num_sensors))
        
        # Normalize to [0, 1] range
        sensor_window = np.clip(sensor_window, 0, 1)
        
        X_data.append(sensor_window)
        y_classification.append(1 if is_degrading else 0)
        y_regression.append(ttf)
    
    return np.array(X_data), np.array(y_classification), np.array(y_regression)

def create_model(input_shape, model_name):
    """Create a dual-output recurrent model (classification + regression)."""
    print(f"Creating model for {model_name}...")
    
    # Input layer
    inputs = keras.Input(shape=input_shape, name='sensor_input')
    
    # Shared LSTM layers
    x = layers.LSTM(64, return_sequences=True, name='lstm_1')(inputs)
    x = layers.Dropout(0.2)(x)
    x = layers.LSTM(32, name='lstm_2')(x)
    x = layers.Dropout(0.2)(x)
    
    # Classification head (degrading vs normal)
    class_output = layers.Dense(16, activation='relu', name='class_dense')(x)
    class_output = layers.Dense(1, activation='sigmoid', name='classification_output')(class_output)
    
    # Regression head (time to failure)
    reg_output = layers.Dense(16, activation='relu', name='reg_dense')(x)
    reg_output = layers.Dense(1, activation='linear', name='regression_output')(reg_output)
    
    # Create model with two outputs
    model = keras.Model(
        inputs=inputs,
        outputs=[class_output, reg_output],
        name=f'{model_name}_model'
    )
    
    # Compile with separate losses for each output
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss={
            'classification_output': 'binary_crossentropy',
            'regression_output': 'mse'
        },
        loss_weights={
            'classification_output': 1.0,
            'regression_output': 0.5
        },
        metrics={
            'classification_output': ['accuracy'],
            'regression_output': ['mae']
        }
    )
    
    return model

def train_and_save_model(template, model_dir):
    """Train and save a model for a specific template."""
    print(f"\n{'='*60}")
    print(f"Training model for: {template.name}")
    print(f"{'='*60}")
    
    # Generate training data
    X, y_class, y_reg = generate_synthetic_data(template)
    
    # Split data
    split_idx = int(0.8 * len(X))
    X_train, X_val = X[:split_idx], X[split_idx:]
    y_class_train, y_class_val = y_class[:split_idx], y_class[split_idx:]
    y_reg_train, y_reg_val = y_reg[:split_idx], y_reg[split_idx:]
    
    # Create and fit feature scaler
    scaler = MinMaxScaler()
    X_train_reshaped = X_train.reshape(-1, X_train.shape[-1])
    scaler.fit(X_train_reshaped)
    
    # Scale data
    X_train_scaled = scaler.transform(X_train_reshaped).reshape(X_train.shape)
    X_val_scaled = scaler.transform(X_val.reshape(-1, X_val.shape[-1])).reshape(X_val.shape)
    
    # Create and fit RUL scaler (for regression output)
    rul_scaler = MinMaxScaler()
    y_reg_train_scaled = rul_scaler.fit_transform(y_reg_train.reshape(-1, 1))
    y_reg_val_scaled = rul_scaler.transform(y_reg_val.reshape(-1, 1))
    
    # Create model
    model_name = template.name.lower().replace(' ', '_')
    model = create_model((WINDOW_SIZE, X_train.shape[-1]), model_name)
    
    print(model.summary())
    
    # Train model
    print(f"\nTraining...")
    history = model.fit(
        X_train_scaled,
        {
            'classification_output': y_class_train,
            'regression_output': y_reg_train_scaled
        },
        validation_data=(
            X_val_scaled,
            {
                'classification_output': y_class_val,
                'regression_output': y_reg_val_scaled
            }
        ),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        verbose=1,
        callbacks=[
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True
            )
        ]
    )
    
    # Create output directory
    os.makedirs(model_dir, exist_ok=True)
    
    # Save model in TF2 format
    model_path = os.path.join(model_dir, f'{model_name}_recurrent_model.keras')
    model.save(model_path, save_format='keras')
    print(f"Model saved to: {model_path}")
    
    # Save scalers
    scaler_path = os.path.join(model_dir, f'{model_name}_scaler.joblib')
    joblib.dump(scaler, scaler_path)
    print(f"Feature scaler saved to: {scaler_path}")
    
    rul_scaler_path = os.path.join(model_dir, f'{model_name}_rul_scaler.joblib')
    joblib.dump(rul_scaler, rul_scaler_path)
    print(f"RUL scaler saved to: {rul_scaler_path}")
    
    # Print final metrics
    val_class_acc = history.history['val_classification_output_accuracy'][-1]
    val_reg_mae = history.history['val_regression_output_mae'][-1]
    print(f"\nFinal Validation Metrics:")
    print(f"  Classification Accuracy: {val_class_acc:.4f}")
    print(f"  Regression MAE: {val_reg_mae:.4f}")
    
    return model

def main():
    """Main training function."""
    app = create_app()
    
    with app.app_context():
        # Get all asset templates
        templates = AssetTemplate.query.all()
        
        if not templates:
            print("No asset templates found in database!")
            return
        
        print(f"Found {len(templates)} asset templates to train models for:")
        for t in templates:
            print(f"  - {t.name}")
        
        # Base model directory
        base_model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        
        # Train model for each template
        for template in templates:
            # Create model directory name (use template name in uppercase)
            model_dir_name = template.name.upper().replace(' ', '_')
            model_dir = os.path.join(base_model_dir, model_dir_name)
            
            try:
                train_and_save_model(template, model_dir)
                print(f"\n✓ Successfully trained model for {template.name}")
            except Exception as e:
                print(f"\n✗ Error training model for {template.name}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*60}")
        print("Training complete!")
        print(f"{'='*60}")

if __name__ == '__main__':
    main()
