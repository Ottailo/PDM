#!/usr/bin/env python3
"""
PDM Real-World Factory & Mobile Surveillance Comprehensive Verification Suite
=============================================================================

Validates:
1. Zero Simulation Default (ENABLE_SIMULATOR == False)
2. Watchdog Heartbeat Detection:
   - Awaiting Telemetry (zero telemetry)
   - Signal Dropped (timeout > 45s)
   - Auto-Recovery to Live (fresh packet < 45s)
3. Live Edge Ingestion via /api/ingest
4. Telemetry Anomaly Detection & Alert State
5. Mobile Remote Surveillance Web App (/mobile) & PWA Manifest (/manifest.json)
6. Mobile Work Order Dispatch API (/api/request-maintenance)
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.sensor_data import SensorData, MachineState, EventLog
from app.models.configuration import Asset, AssetTemplate, AssetSensor, SensorTemplate, Location
from app.services.predictor import PredictiveService

def run_tests():
    print("=" * 78)
    print("PDM REAL-WORLD FACTORY & MOBILE SURVEILLANCE VERIFICATION SUITE")
    print("=" * 78)

    # Boot App with rock-solid auto-anchored database configuration
    app = create_app({'TESTING': True})
    client = app.test_client()

    with app.app_context():
        # TEST 1: Zero Simulation Default Verification
        print("\n[TEST 1] Verifying Zero Synthetic Simulator Default...")
        enable_sim = app.config.get('ENABLE_SIMULATOR')
        assert enable_sim is False, f"Expected ENABLE_SIMULATOR to default to False, got {enable_sim}"
        print(f"  [OK] Confirmed ENABLE_SIMULATOR is False. Backend simulation thread is disabled by default.")

        # Ensure seed asset template and asset exist
        template = AssetTemplate.query.filter_by(name="FILLING").first()
        if not template:
            template = AssetTemplate(name="FILLING", description="High-Speed Rotary Filling Machine")
            db.session.add(template)
            db.session.commit()

        loc = Location.query.first()
        if not loc:
            loc = Location(name="Line 1 - Bottling", site="Main Factory")
            db.session.add(loc)
            db.session.commit()

        # Create or retrieve test asset with ZERO telemetry
        test_zero_id = "TEST_AWAITING_001"
        asset_zero = Asset.query.filter_by(name=test_zero_id).first()
        if not asset_zero:
            asset_zero = Asset(
                name=test_zero_id,
                asset_template_id=template.id,
                location_id=loc.id,
                company_id=1,
                status="Active"
            )
            db.session.add(asset_zero)
            db.session.commit()

        # Clean any historical sensor data for this test asset
        SensorData.query.filter(SensorData.sensor_id.like(f"{test_zero_id}_%")).delete(synchronize_session=False)
        db.session.commit()

        # TEST 2: Watchdog Awaiting Telemetry State
        print("\n[TEST 2] Verifying Watchdog 'Awaiting Telemetry' on asset with zero sensor packets...")
        predictor = PredictiveService()
        preds = predictor.get_predictions()
        zero_pred = preds.get(test_zero_id)
        assert zero_pred is not None, f"Asset {test_zero_id} missing from predictions"
        assert zero_pred["state"] == "Awaiting Telemetry", f"Expected state 'Awaiting Telemetry', got {zero_pred['state']}"
        assert zero_pred["is_online"] is False, f"Expected is_online to be False"
        assert zero_pred["telemetry_status"] == "AWAITING_TELEMETRY", f"Expected telemetry_status 'AWAITING_TELEMETRY'"
        print(f"  [OK] State: {zero_pred['state']} | is_online: {zero_pred['is_online']} | Telemetry: {zero_pred['telemetry_status']}")
        print(f"  [OK] Message: {zero_pred['watchdog_message']}")

        # TEST 3: Watchdog Signal Dropped Detection (>45s)
        print("\n[TEST 3] Verifying Watchdog 'Signal Dropped' when edge telemetry stream halts...")
        stale_time = datetime.utcnow() - timedelta(seconds=75)
        # Inject reading timestamped 75 seconds ago
        stale_reading = SensorData(
            timestamp=stale_time,
            sensor_id=f"{test_zero_id}_Vibration",
            value=0.35
        )
        db.session.add(stale_reading)
        db.session.commit()

        preds = predictor.get_predictions()
        dropped_pred = preds.get(test_zero_id)
        assert dropped_pred is not None, f"Asset {test_zero_id} missing from predictions"
        assert dropped_pred["state"] == "Signal Dropped", f"Expected state 'Signal Dropped', got {dropped_pred['state']}"
        assert dropped_pred["is_online"] is False, f"Expected is_online to be False"
        assert dropped_pred["telemetry_status"] == "SIGNAL_DROPPED", f"Expected telemetry_status 'SIGNAL_DROPPED'"
        assert dropped_pred["anomaly_detected"] is True, f"Expected anomaly_detected to be True"
        assert dropped_pred["last_seen_seconds"] >= 70, f"Expected last_seen_seconds >= 70, got {dropped_pred['last_seen_seconds']}"
        print(f"  [OK] State: {dropped_pred['state']} | Anomaly: {dropped_pred['anomaly_detected']} | Last Seen: {dropped_pred['last_seen_seconds']}s ago")
        print(f"  [OK] Root Cause: {dropped_pred['predicted_failure']}")
        print(f"  [OK] RCA Action 1: {dropped_pred['rca_steps'][0]}")

        # TEST 4: Live Hardware Ingest & Auto-Recovery
        print("\n[TEST 4] Verifying Live Hardware Ingest & Auto-Recovery to 'Live' / 'Normal'...")
        now = datetime.utcnow()
        fresh_reading = SensorData(
            timestamp=now,
            sensor_id=f"{test_zero_id}_Vibration",
            value=0.36
        )
        db.session.add(fresh_reading)
        db.session.commit()

        preds = predictor.get_predictions()
        live_pred = preds.get(test_zero_id)
        assert live_pred["state"] == "Normal", f"Expected state 'Normal', got {live_pred['state']}"
        assert live_pred["is_online"] is True, f"Expected is_online to be True"
        assert live_pred["telemetry_status"] == "LIVE", f"Expected telemetry_status 'LIVE'"
        assert live_pred["last_seen_seconds"] <= 5.0, f"Expected last_seen_seconds <= 5.0, got {live_pred['last_seen_seconds']}"
        print(f"  [OK] Recovered State: {live_pred['state']} | is_online: {live_pred['is_online']} | Last Seen: {live_pred['last_seen_seconds']}s ago")

        # TEST 5: Real API Ingestion via POST /api/ingest
        print("\n[TEST 5] Verifying Edge Ingestion via POST /api/ingest endpoint...")
        ingest_payload = {
            "machine_id": test_zero_id,
            "readings": {
                "Speed": 1450.0,
                "Temperature": 63.2,
                "Pressure": 4.15,
                "Vibration": 0.37
            }
        }
        res = client.post(
            '/api/ingest',
            data=json.dumps(ingest_payload),
            headers={'Content-Type': 'application/json', 'X-API-Key': 'dev-api-key'}
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
        ingest_resp = json.loads(res.data)
        assert ingest_resp.get("status") == "success"
        print(f"  [OK] Ingest HTTP 200 OK — Ingested 4 channels for {test_zero_id}")

        # TEST 6: Mobile Remote Surveillance Web App (/mobile) & Manifest
        print("\n[TEST 6] Verifying Mobile Remote Web App & PWA Manifest...")
        res_mobile = client.get('/mobile')
        assert res_mobile.status_code == 200, f"Expected 200 from /mobile, got {res_mobile.status_code}"
        mobile_html = res_mobile.data.decode('utf-8')
        assert "PDM Remote — Field Plant Surveillance" in mobile_html, "Missing title in mobile HTML"
        assert "mobile_dashboard.js" in mobile_html, "Missing mobile_dashboard.js script tag"
        assert "manifest.json" in mobile_html, "Missing manifest.json link"
        assert "mobile-diagnostic-drawer" in mobile_html, "Missing diagnostic drawer in mobile HTML"
        print("  [OK] GET /mobile returned 200 OK with valid mobile surveillance HTML and mechatronic drawer.")

        res_manifest = client.get('/manifest.json')
        assert res_manifest.status_code == 200, f"Expected 200 from /manifest.json, got {res_manifest.status_code}"
        manifest_data = json.loads(res_manifest.data)
        assert manifest_data.get("name") == "PDM Industrial Remote Surveillance"
        assert manifest_data.get("start_url") == "/mobile"
        assert manifest_data.get("display") == "standalone"
        print(f"  [OK] GET /manifest.json returned 200 OK with standalone PWA configuration.")

        # TEST 7: Mobile Work Order Dispatch API
        print("\n[TEST 7] Verifying Mobile Work Order Dispatch via POST /api/request-maintenance...")
        wo_payload = {
            "machine_id": test_zero_id,
            "parts": ["High-Speed Deep Groove Bearings", "PTFE Seals"],
            "estimated_duration": 45,
            "technician_notes": "Field technician dispatched via mobile surveillance remote."
        }
        res_wo = client.post(
            '/api/request-maintenance',
            data=json.dumps(wo_payload),
            headers={'Content-Type': 'application/json'}
        )
        assert res_wo.status_code == 200, f"Expected 200 from /api/request-maintenance, got {res_wo.status_code}"
        wo_resp = json.loads(res_wo.data)
        assert wo_resp.get("status") == "success"

        # Verify EventLog recorded the work order
        event = EventLog.query.filter_by(machine_id=test_zero_id, event_type="Maintenance").order_by(EventLog.timestamp.desc()).first()
        assert event is not None, "Expected EventLog entry for maintenance"
        assert "High-Speed Deep Groove Bearings" in event.details
        print(f"  [OK] Work order dispatched successfully: {event.details}")

        # Cleanup test asset
        SensorData.query.filter(SensorData.sensor_id.like(f"{test_zero_id}_%")).delete(synchronize_session=False)
        MachineState.query.filter_by(machine_id=test_zero_id).delete(synchronize_session=False)
        EventLog.query.filter_by(machine_id=test_zero_id).delete(synchronize_session=False)
        Asset.query.filter_by(name=test_zero_id).delete(synchronize_session=False)
        db.session.commit()
        print(f"  [OK] Teardown cleaned test asset {test_zero_id}.")

    print("\n" + "=" * 78)
    print("ALL 7 REAL-WORLD FACTORY & MOBILE SURVEILLANCE TESTS PASSED (EXIT CODE 0)")
    print("=" * 78)

if __name__ == "__main__":
    run_tests()
