"""
Comprehensive Verification for Real-World Industrial Pilot Facilities
======================================================================
Tests:
1. Ingestion Gateway Handshake (/api/ingest/ping)
2. Ingestion Connection Profile (/api/ingest/connection-info)
3. Live Ingestion Token Authentication & Telemetry Ingestion
4. Mode Toggle (Live Hardware Ingestion vs. Simulated)
5. Automated Statistical Baseline Calibration (/api/machine-mgmt/calibrate-asset)
6. Industrial Incident Alert Dispatcher
7. PdmEdgeAgent Store-and-Forward Buffer Integrity
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.configuration import Asset, AssetSensor
from app.models.sensor_data import SensorData, MachineState, EventLog

def run_pilot_verification():
    app = create_app()
    client = app.test_client()

    print("[PILOT TEST 1] Handshake Test: GET /api/ingest/ping...")
    res = client.get('/api/ingest/ping?machine_id=FILLING_001&key=dev-api-key')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    ping_data = res.get_json()
    assert ping_data.get('status') == 'online'
    assert ping_data.get('authenticated') is True
    print(f" -> Handshake OK: {ping_data.get('service')} (Authenticated: {ping_data.get('authenticated')})")

    print("\n[PILOT TEST 2] Connection Profile: GET /api/ingest/connection-info?machine_id=FILLING_001...")
    res = client.get('/api/ingest/connection-info?machine_id=FILLING_001')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    conn_info = res.get_json()
    assert conn_info.get('machine_id') == 'FILLING_001'
    assert len(conn_info.get('channels', [])) > 0
    assert "curl_command" in conn_info
    assert "edge_agent_command" in conn_info
    print(f" -> Success! Asset Profile: {conn_info.get('machine_type')} | Token: {conn_info.get('device_token')}")
    print(f"    Channels: {[c['name'] for c in conn_info['channels']]}")

    print("\n[PILOT TEST 3] Live Ingestion Test: POST /api/ingest with machine-specific token...")
    telemetry_packet = {
        "machine_id": "FILLING_001",
        "timestamp": "2026-10-26T13:30:00Z",
        "sensors": {
            "Fill_Volume_Sensor": 100.45,
            "Nozzle_Pressure": 2.25,
            "Vibration": 0.14
        }
    }
    res = client.post(
        '/api/ingest',
        json=telemetry_packet,
        headers={"X-API-Key": "pdm_live_FILLING_001"}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
    ingest_res = res.get_json()
    assert ingest_res.get('status') == 'success'
    assert ingest_res.get('readings_ingested') >= 1
    print(f" -> Ingestion Success! Ingested {ingest_res.get('readings_ingested')} channels (Asset Mode: {ingest_res.get('asset_mode')})")

    print("\n[PILOT TEST 4] Toggle Ingestion Mode: POST /api/ingest/toggle-mode...")
    res = client.post(
        '/api/ingest/toggle-mode',
        json={"machine_id": "FILLING_001", "mode": "Live"}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    toggle_res = res.get_json()
    assert toggle_res.get('mode') == 'Live'
    assert toggle_res.get('is_live') is True
    print(f" -> Success! FILLING_001 set to Live Hardware Mode (is_live={toggle_res.get('is_live')})")

    print("\n[PILOT TEST 5] Auto-Baseline Calibration: POST /api/machine-mgmt/calibrate-asset...")
    with client.session_transaction() as sess:
        sess['_user_id'] = '1'
        sess['_fresh'] = True

    res = client.post(
        '/api/machine-mgmt/calibrate-asset',
        json={"machine_id": "FILLING_001", "samples": 50}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
    cal_res = res.get_json()
    print(f" -> Calibration Success! {cal_res.get('message')}")
    for ch_name, bounds in cal_res.get('calibrated_channels', {}).items():
        print(f"    * {ch_name}: Mean={bounds['mean']}, Std={bounds['std']}, Warn={bounds['warn']}, Crit={bounds['crit']}")

    print("\n[PILOT TEST 6] Industrial Incident Alert Dispatcher Test...")
    from app.services.alert_dispatcher import IndustrialAlertDispatcher
    mock_telemetry = {
        "machine_type": "FILLING",
        "location": "Bottling Line 1",
        "health_score": 0.42,
        "rul_prediction": 14.5,
        "predicted_failure": "Nozzle Clog"
    }
    mock_diagnosis = {
        "physical_root_cause": "Cavitation and progressive particulate crystallization in filling nozzle orifice.",
        "required_spare_parts": ["Nozzle Assembly (Part #NZL-316L)", "PTFE Seal Kit"],
        "immediate_actions": [
            "De-energize pneumatic fluid manifold",
            "Perform CIP hot caustic wash cycle"
        ]
    }
    with app.app_context():
        dispatched = IndustrialAlertDispatcher.dispatch_incident(
            machine_id="FILLING_001",
            state="Critical Failure Imminent",
            telemetry=mock_telemetry,
            diagnosis=mock_diagnosis
        )
        assert dispatched is True, "Expected incident dispatch to return True"
        # Check EventLog
        latest_event = EventLog.query.filter_by(machine_id="FILLING_001", event_type="Alert").order_by(EventLog.timestamp.desc()).first()
        assert latest_event is not None
        print(f" -> Alert Dispatched & Logged to DB: {latest_event.details}")

    print("\n[PILOT TEST 7] Edge Buffer Offline Store-and-Forward Test...")
    from scripts.edge.pdm_edge_agent import PdmEdgeBuffer
    test_db = "instance/test_edge_buffer.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    buf = PdmEdgeBuffer(db_path=test_db, max_size=100)
    buf.enqueue({"sample": 1})
    buf.enqueue({"sample": 2})
    assert buf.get_pending_count() == 2
    batch = buf.fetch_batch(limit=10)
    assert len(batch) == 2
    buf.mark_success([batch[0][0]])
    assert buf.get_pending_count() == 1
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except Exception:
        pass
    print(" -> Edge Store-and-Forward Buffer Integrity: Verified!")

    print("\n[ALL 7 PILOT FACILITIES VERIFIED AND OPERATIONAL - EXIT 0]")

if __name__ == '__main__':
    run_pilot_verification()
