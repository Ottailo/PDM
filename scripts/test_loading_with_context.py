import sys
import os
from flask import Flask

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = Flask(__name__)
app.config['MODEL_BASE_DIR'] = os.path.join(os.getcwd(), 'app', 'models', 'saved_models')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pdm.db'

# Mock DB
from app import db
db.init_app(app)

print("Starting context test...")

with app.app_context():
    try:
        from app.services.predictor import PredictiveService
        print("Imported service.")
        service = PredictiveService()
        print("Service initialized. Models loaded: ", service.models_loaded)
    except Exception as e:
        print(f"CRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()

print("Context test finished.")
