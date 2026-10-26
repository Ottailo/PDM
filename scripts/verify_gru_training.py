"""
Verify Keras Dual-Head GRU Training pipeline.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.services.trainer import train_model_for_template

def test_gru():
    app = create_app()
    with app.app_context():
        print("Starting 1-epoch Dual-Head GRU training test for FILLING...")
        success, metrics, msg = train_model_for_template(
            template_name="FILLING",
            epochs=1,
            num_samples=1000
        )
        print(f"Success: {success}")
        print(f"Message: {msg}")
        print(f"Metrics: {metrics}")
        assert success, f"GRU training failed: {msg}"
        assert "accuracy" in metrics
        print("Dual-Head GRU training verified!")

if __name__ == '__main__':
    test_gru()
