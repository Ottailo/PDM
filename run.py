"""
Advanced Predictive Maintenance Platform
Main application entry point
"""
import os
import warnings

# Suppress all Python warnings globally (including TensorFlow/Keras deprecations)
warnings.filterwarnings('ignore')

# Configure TensorFlow BEFORE any TensorFlow imports
# Suppress TensorFlow C++ INFO messages
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'  # 0=all, 1=no INFO, 2=no WARNING, 3=only ERROR
# Disable oneDNN custom operations message
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
# Enable TensorFlow 2.x behavior
os.environ['TF2_BEHAVIOR'] = '1'

import threading
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_simulator(app):
    """Run the data simulator in a separate thread."""
    from app.services.simulator import DataSimulator
    
    with app.app_context():
        simulator = DataSimulator()
        simulator.ensure_initialized()
        while True:
            try:
                simulator.generate_sensor_data()
                time.sleep(app.config['SIMULATOR_UPDATE_INTERVAL'])
            except Exception as e:
                app.logger.error(f"Simulator error: {str(e)}")
                time.sleep(5)  # Wait before retrying

from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # Start simulator in background thread if enabled
    if app.config.get('ENABLE_SIMULATOR', True):
        simulator_thread = threading.Thread(target=run_simulator, args=(app,), daemon=True)
        simulator_thread.start()
        app.logger.info("Simulator started")
    else:
        app.logger.info("Simulator disabled - waiting for real data")

    # Start online learning service
    if app.config.get('ENABLE_ONLINE_LEARNING', True):
        from app.services.online_learning import start_online_learning
        start_online_learning(app)
        app.logger.info("Online learning service started")
    
    # Run Flask app with SocketIO
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
