"""
Advanced Predictive Maintenance Platform
Main application entry point
"""
import os
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
        while True:
            try:
                simulator.generate_sensor_data()
                time.sleep(app.config['SIMULATOR_UPDATE_INTERVAL'])
            except Exception as e:
                app.logger.error(f"Simulator error: {str(e)}")
                time.sleep(5)  # Wait before retrying

if __name__ == '__main__':
    from app import create_app, socketio
    
    app = create_app()
    
    # Start simulator in background thread
    simulator_thread = threading.Thread(target=run_simulator, args=(app,), daemon=True)
    simulator_thread.start()
    
    # Run Flask app with SocketIO
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
