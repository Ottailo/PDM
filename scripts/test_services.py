import sys
import os
import time

# Add app directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.services.predictor import PredictiveService, _MODEL_CACHE
from app.services.simulator import DataSimulator

app = create_app()

with app.app_context():
    print("Testing PredictiveService caching...")
    start = time.time()
    p1 = PredictiveService()
    t1 = time.time() - start
    print(f"First init time: {t1:.4f}s")
    
    start = time.time()
    p2 = PredictiveService()
    t2 = time.time() - start
    print(f"Second init time: {t2:.4f}s")
    
    if t2 < t1 and t2 < 0.1:
        print("PASS: PredictiveService is caching models.")
    else:
        print("FAIL: PredictiveService might be reloading models.")
        
    print("\nTesting DataSimulator lazy init...")
    # Mocking db.session to check for calls would be ideal, but for now just check speed
    start = time.time()
    s1 = DataSimulator()
    t_sim = time.time() - start
    print(f"Simulator init time: {t_sim:.4f}s")
    
    if t_sim < 0.1:
        print("PASS: DataSimulator init is fast (lazy).")
    else:
        print("FAIL: DataSimulator init is slow.")
