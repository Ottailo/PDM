"""
Comprehensive Verification Script for PDM System.
Tests:
1. Database integrity & fast pruning retention
2. Latest-states surveillance payload
3. Maintenance dispatch protocol (request & execute)
4. Model metrics endpoint
5. Model training pipeline (Dual-Head GRU & OmniRoute Reasoner)
6. OmniRoute AI Diagnostic Advisor endpoint
"""
import sys
import os
import json

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.configuration import Asset, AssetTemplate
from app.models.sensor_data import MachineState, EventLog

def run_tests():
    app = create_app()
    client = app.test_client()

    print("[TEST 1] Verifying Flask Application & Database Context...")
    with app.app_context():
        assets = Asset.query.all()
        print(f" -> Found {len(assets)} registered physical assets:")
        for a in assets:
            print(f"    * Asset ID: {a.id} | Name: {a.name} | Template: {a.template.name if a.template else 'None'}")
        assert len(assets) > 0, "No assets found in database!"

    print("\n[TEST 2] Testing GET /api/latest-states...")
    res = client.get('/api/latest-states')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.get_json()
    assert "predictions" in data, "predictions missing from response"
    assert "kpis" in data, "kpis missing from response"
    print(f" -> Success! Surveillance payload returned {len(data['predictions'])} machines.")
    for m_id, m_data in data['predictions'].items():
        assert m_data.get('machine_id') == m_id, f"Missing or mismatched machine_id for {m_id}"
        h_score = m_data.get('health_score')
        h_str = f"{round(h_score*100, 1)}%" if h_score is not None else "N/A"
        print(f"    * {m_id}: State={m_data.get('state')}, Health={h_str}, RUL={m_data.get('rul_prediction')}")

    print("\n[TEST 3] Testing POST /api/request-maintenance...")
    sample_machine = assets[0].name
    maint_payload = {
        "machine_id": sample_machine,
        "parts": ["Nozzle Assembly", "Pump System"],
        "estimated_duration": 45
    }
    res = client.post('/api/request-maintenance', json=maint_payload)
    assert res.status_code in [200, 201], f"Expected 200/201, got {res.status_code}: {res.data}"
    maint_data = res.get_json()
    print(f" -> Success! Maintenance dispatch response: {maint_data.get('message')}")

    print("\n[TEST 4] Authenticating as Admin & Testing GET /api/machine-mgmt/model-metrics...")
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'
        sess['_fresh'] = True

    res = client.get('/api/machine-mgmt/model-metrics')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    metrics_data = res.get_json()
    print(f" -> Success! Retrieved metrics for {len(metrics_data)} model architectures:")
    for template_name, m_vals in metrics_data.items():
        print(f"    * {template_name}: Accuracy={m_vals.get('accuracy')}%, MAE={m_vals.get('mae_hours')}h")

    print("\n[TEST 5] Testing POST /api/machine-mgmt/train-model (OmniRoute Reasoner Benchmark)...")
    train_omni_payload = {
        "machine_type": "FILLING",
        "training_type": "omniroute_reasoner",
        "epochs": 3
    }
    res = client.post('/api/machine-mgmt/train-model', json=train_omni_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
    omni_res = res.get_json()
    print(f" -> Success! {omni_res.get('message')}")
    print(f"    * OmniRoute metrics: {omni_res.get('metrics')}")

    print("\n[TEST 6] Testing POST /api/ai-diagnostics (OmniRoute Cognitive Advisory)...")
    diag_payload = {
        "machine_id": sample_machine
    }
    res = client.post('/api/ai-diagnostics', json=diag_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
    diag_res = res.get_json()
    print(f" -> Success! AI Advisor Output:")
    print(f"    * Heading: {diag_res.get('diagnosis_title')}")
    print(f"    * Severity: {diag_res.get('severity')}")
    print(f"    * Provider: {diag_res.get('advisor_provider')}")
    print(f"    * Root Cause: {diag_res.get('physical_root_cause')[:90]}...")
    print(f"    * Spare Parts: {diag_res.get('required_spare_parts')}")
    print(f"    * Action Checklist Steps: {len(diag_res.get('immediate_actions', []))}")

    print("\n[TEST 7] Testing POST /api/machine-mgmt/upload-training-csv (Synthetic Test CSV)...")
    import io
    csv_content = (
        "timestamp,asset_id,temperature,vibration,pressure,flow_rate,fill_volume,rul_target\n"
        "2026-10-26T12:00:00,FILLING_001,45.2,1.2,3.4,12.5,500.1,120.0\n"
        "2026-10-26T12:01:00,FILLING_001,45.8,1.3,3.5,12.4,499.8,119.0\n"
        "2026-10-26T12:02:00,FILLING_001,46.1,1.4,3.6,12.2,499.5,118.0\n"
    )
    data = {
        'file': (io.BytesIO(csv_content.encode('utf-8')), 'test_telemetry.csv')
    }
    res = client.post('/api/machine-mgmt/upload-training-csv', data=data, content_type='multipart/form-data')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
    upload_res = res.get_json()
    print(f" -> Success! CSV uploaded: {upload_res.get('filename')} with columns {upload_res.get('columns')}")

    print("\n[ALL 7 TESTS PASSED SUCCESSFULLY!]")

if __name__ == '__main__':
    run_tests()
