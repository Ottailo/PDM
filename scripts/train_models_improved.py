"""
Train ML models for predictive maintenance with realistic degradation patterns.
This improved version generates multi-state health classifications and accurate TTF estimates.
"""
import os
import sys
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import joblib

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure TensorFlow BEFORE import
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import tensorflow as tf
tf.get_logger().setLevel('ERROR')

import keras
from keras import layers

# Suppress absl logging
import absl.logging
absl.logging.set_verbosity(absl.logging.ERROR)

from app import create_app
from app.models.configuration import AssetTemplate

print("Starting improved model training with realistic degradation patterns...")

# Training parameters
WINDOW_SIZE = 10
EPOCHS = 5  # Reduced for faster regeneration
BATCH_SIZE = 32
SAMPLES_PER_MACHINE = 10000  # More samples for better distribution

# Health states (multi-class)
HEALTH_STATES = {
    'NORMAL': 0,
    'WARNING': 1,
    'DEGRADING': 2,
    'CRITICAL': 3
}

def generate_realistic_degradation_data(template, num_samples=SAMPLES_PER_MACHINE):
    """Generate realistic sensor data with gradual degradation patterns."""
    print(f"\nGenerating {num_samples} realistic samples for {template.name}...")
    
    sensors = [s.sensor_template for s in template.sensors]
    num_sensors = len(sensors)
    
    if num_sensors == 0:
        raise ValueError(f"No sensors configured for template {template.name}")
    
    X_data = []
    y_classification = []
    y_regression = []
    
    # Distribution: 50% Normal, 25% Warning, 15% Degrading, 10% Critical
    state_thresholds = {
        'NORMAL': int(num_samples * 0.50),
        'WARNING': int(num_samples * 0.75),
        'DEGRADING': int(num_samples * 0.90),
        'CRITICAL': int(num_samples * 1.00)
    }
    
    for i in range(num_samples):
        # Determine health state based on sample index
        if i < state_thresholds['NORMAL']:
            state = 'NORMAL'
            # Normal operation: centered around 50% with low variance
            base_mean = 0.5
            noise_level = 0.05
            drift = 0.0
            ttf = np.random.randint(150, 200)  # High TTF
            
        elif i < state_thresholds['WARNING']:
            state = 'WARNING'
            # Warning: slight drift, increased variance
            progress = (i - state_thresholds['NORMAL']) / (state_thresholds['WARNING'] - state_thresholds['NORMAL'])
            base_mean = 0.5 + (progress * 0.1)  # Slight upward drift
            noise_level = 0.08
            drift = progress * 0.05
            ttf = int(120 - progress * 40)  # TTF: 120 → 80 hours
            
        elif i < state_thresholds['DEGRADING']:
            state = 'DEGRADING'
            # Degrading: noticeable drift, higher variance
            progress = (i - state_thresholds['WARNING']) / (state_thresholds['DEGRADING'] - state_thresholds['WARNING'])
            base_mean = 0.6 + (progress * 0.15)
            noise_level = 0.12
            drift = 0.05 + (progress * 0.1)
            ttf = int(80 - progress * 60)  # TTF: 80 → 20 hours
            
        else:  # CRITICAL
            state = 'CRITICAL'
            # Critical: severe drift, very high variance
            progress = (i - state_thresholds['DEGRADING']) / (num_samples - state_thresholds['DEGRADING'])
            base_mean = 0.75 + (progress * 0.2)
            noise_level = 0.18
            drift = 0.15 + (progress * 0.15)
            ttf = int(20 - progress * 19)  # TTF: 20 → 1 hours
        
        # Generate sensor window with realistic patterns
        sensor_window = np.zeros((WINDOW_SIZE, num_sensors))
        
        for t in range(WINDOW_SIZE):
            # Add temporal progression within the window
            time_factor = t / WINDOW_SIZE
            
            # Generate readings with increasing drift over time
            for s in range(num_sensors):
                # Base value with state-dependent characteristics
                value = np.random.normal(base_mean + (time_factor * drift), noise_level)
                
                # Add sensor-specific patterns (some sensors drift faster)
                sensor_drift = drift * (0.5 + s * 0.3)
                value += time_factor * sensor_drift
                
                # Clip to valid range [0, 1]
                sensor_window[t, s] = np.clip(value, 0, 1)
        
        X_data.append(sensor_window)
        y_classification.append(HEALTH_STATES[state])
        y_regression.append(ttf)
    
    # Shuffle data to avoid sequential bias
    indices = np.random.permutation(num_samples)
    X_data = np.array(X_data)[indices]
    y_classification = np.array(y_classification)[indices]
    y_regression = np.array(y_regression)[indices]
    
    # Print distribution stats
    unique, counts = np.unique(y_classification, return_counts=True)
    print(f"  Sample distribution:")
    for state_val, count in zip(unique, counts):
        state_name = [k for k, v in HEALTH_STATES.items() if v == state_val][0]
        print(f"    {state_name}: {count} ({count/num_samples*100:.1f}%)")
    
    print(f"  TTF range: {y_regression.min():.1f} - {y_regression.max():.1f} hours")
    print(f"  Mean TTF: {y_regression.mean():.1f} hours")
    
    return X_data, y_classification, y_regression

def create_improved_model(input_shape, model_name, num_classes=4):
    """Create an improved dual-output model with multi-class classification."""
    print(f"Creating improved model for {model_name}...")
    
    inputs = keras.Input(shape=input_shape, name='sensor_input')
    
    # Enhanced LSTM architecture
    x = layers.LSTM(128, return_sequences=True, name='lstm_1')(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    
    x = layers.LSTM(64, return_sequences=True, name='lstm_2')(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    
    x = layers.LSTM(32, name='lstm_3')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.2)(x)
    
    # Multi-class classification head (4 states)
    class_dense = layers.Dense(64, activation='relu', name='class_dense_1')(x)
    class_dense = layers.Dropout(0.2)(class_dense)
    class_dense = layers.Dense(32, activation='relu', name='class_dense_2')(class_dense)
    class_output = layers.Dense(num_classes, activation='softmax', name='classification_output')(class_dense)
    
    # Regression head (TTF)
    reg_dense = layers.Dense(64, activation='relu', name='reg_dense_1')(x)
    reg_dense = layers.Dropout(0.2)(reg_dense)
    reg_dense = layers.Dense(32, activation='relu', name='reg_dense_2')(reg_dense)
    reg_output = layers.Dense(1, activation='linear', name='regression_output')(reg_dense)
    
    model = keras.Model(
        inputs=inputs,
        outputs=[class_output, reg_output],
        name=f'{model_name}_model'
    )
    
    # Compile with appropriate losses
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0005),  # Lower LR for stability
        loss={
            'classification_output': 'sparse_categorical_crossentropy',
            'regression_output': 'huber'  # Robust to outliers
        },
        loss_weights={
            'classification_output': 1.0,
            'regression_output': 0.3  # Lower weight to prevent regression dominance
        },
        metrics={
            'classification_output': ['accuracy'],
            'regression_output': ['mae', 'mse']
        }
    )
    
    return model

def train_and_save_improved_model(template, model_dir):
    """Train and save an improved model."""
    print(f"\n{'='*70}")
    print(f"Training IMPROVED model for: {template.name}")
    print(f"{'='*70}")
    
    # Generate realistic data
    X, y_class, y_reg = generate_realistic_degradation_data(template)
    
    # Split: 80% train, 10% val, 10% test
    train_idx = int(0.8 * len(X))
    val_idx = int(0.9 * len(X))
    
    X_train, X_val, X_test = X[:train_idx], X[train_idx:val_idx], X[val_idx:]
    y_class_train, y_class_val, y_class_test = y_class[:train_idx], y_class[train_idx:val_idx], y_class[val_idx:]
    y_reg_train, y_reg_val, y_reg_test = y_reg[:train_idx], y_reg[train_idx:val_idx], y_reg[val_idx:]
    
    # Fit feature scaler
    scaler = MinMaxScaler()
    X_train_reshaped = X_train.reshape(-1, X_train.shape[-1])
    scaler.fit(X_train_reshaped)
    
    # Scale data
    X_train_scaled = scaler.transform(X_train_reshaped).reshape(X_train.shape)
    X_val_scaled = scaler.transform(X_val.reshape(-1, X_val.shape[-1])).reshape(X_val.shape)
    X_test_scaled = scaler.transform(X_test.reshape(-1, X_test.shape[-1])).reshape(X_test.shape)
    
    # Fit RUL scaler
    rul_scaler = MinMaxScaler()
    y_reg_train_scaled = rul_scaler.fit_transform(y_reg_train.reshape(-1, 1))
    y_reg_val_scaled = rul_scaler.transform(y_reg_val.reshape(-1, 1))
    y_reg_test_scaled = rul_scaler.transform(y_reg_test.reshape(-1, 1))
    
    # Create model
    model_name = template.name.lower().replace(' ', '_')
    model = create_improved_model((WINDOW_SIZE, X_train.shape[-1]), model_name)
    
    print(model.summary())
    
    # Train with callbacks
    print("\nTraining improved model...")
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
                patience=15,
                restore_best_weights=True
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-6
            )
        ]
    )
    
    # Test evaluation
    print("\nEvaluating on test set...")
    test_results = model.evaluate(
        X_test_scaled,
        {
            'classification_output': y_class_test,
            'regression_output': y_reg_test_scaled
        },
        verbose=0
    )
    
    # Save model
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, f'{model_name}_recurrent_model.keras')
    model.save(model_path, save_format='keras')
    print(f"[V] Model saved to: {model_path}")
    
    # Save scalers
    scaler_path = os.path.join(model_dir, f'{model_name}_scaler.joblib')
    joblib.dump(scaler, scaler_path)
    
    rul_scaler_path = os.path.join(model_dir, f'{model_name}_rul_scaler.joblib')
    joblib.dump(rul_scaler, rul_scaler_path)
    
    # Print metrics
    print(f"\n{'='*70}")
    print(f"FINAL METRICS for {template.name}:")
    print(f"  Classification Accuracy: {history.history['val_classification_output_accuracy'][-1]:.4f}")
    print(f"  Regression MAE: {history.history['val_regression_output_mae'][-1]:.4f}")
    print(f"  Test Classification Accuracy: {test_results[4]:.4f}")
    print(f"  Test Regression MAE: {test_results[5]:.4f}")
    print(f"{'='*70}")
    
    return model

def main():
    app = create_app()
    
    with app.app_context():
        templates = AssetTemplate.query.all()
        
        if not templates:
            print("No asset templates found!")
            return
        
        print(f"\nFound {len(templates)} templates:")
        for t in templates:
            print(f"  - {t.name}")
        
        base_model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        
        for template in templates:
            model_dir_name = template.name.upper().replace(' ', '_')
            model_dir = os.path.join(base_model_dir, model_dir_name)
            
            try:
                train_and_save_improved_model(template, model_dir)
                print(f"\n[V] Successfully trained IMPROVED model for {template.name}\n")
            except Exception as e:
                print(f"\n[X] Error training model for {template.name}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*70}")
        print("IMPROVED MODEL TRAINING COMPLETE!")
        print(f"{'='*70}")

if __name__ == '__main__':
    main()
