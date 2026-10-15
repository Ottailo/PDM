import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Starting import test...")
try:
    from app.services.predictor import PredictiveService
    print("Imported PredictiveService class.")
    service = PredictiveService()
    print("Initialized PredictiveService.")
except Exception as e:
    print(f"Caught exception: {e}")
    import traceback
    traceback.print_exc()

print("Test finished.")
