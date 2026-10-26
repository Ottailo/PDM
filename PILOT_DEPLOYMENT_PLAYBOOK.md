# Machivital — Industrial Pilot Deployment & Physical Machine Onboarding Playbook

This document is the operational and engineering blueprint for piloting the **Machivital Autonomous Machinery Vitality & Telemetry Console** in a real-world manufacturing plant, packaging line, CNC workshop, or industrial facility.

---

## 1. High-Level Pilot Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           FACTORY FLOOR / EDGE ENVIRONMENT                     │
├─────────────────────┬──────────────────────────┬───────────────────────────────┤
│ Physical Asset 1    │ Physical Asset 2         │ Smart IoT Sensors             │
│ (Siemens S7-1500)   │ (Schneider / Modicon)    │ (IFM / Banner / Vibration)    │
│ [Modbus TCP :502]   │ [Modbus TCP :502]        │ [MQTT Broker :1883]           │
└──────────┬──────────┴────────────┬─────────────┴───────────────┬───────────────┘
           │                       │                             │
           ▼                       ▼                             ▼
   pdm_modbus_bridge.py    pdm_modbus_bridge.py        pdm_mqtt_subscriber.py
           │                       │                             │
           └───────────────────────┼─────────────────────────────┘
                                   │
                                   ▼
                       ┌─────────────────────────┐
                       │   pdm_edge_agent.py     │
                       │ (IPC / Raspberry Pi)    │
                       │ [Store-and-Forward FIFO]│
                       │ [SQLite edge_buffer.db] │
                       └───────────┬─────────────┘
                                   │ TLS 1.3 / HTTPS POST
                                   │ Token: pdm_live_<machine_id>
                                   ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                       PDM CLOUD / ON-PREMISES SERVER                          │
├────────────────────────────────────────────────────────────────────────────────┤
│ Ingest Gateway:  POST /api/ingest (Dynamic Schema & Token Auth)                │
│ Baseline Engine: Auto-calibrates empirical mean (μ) & standard dev (σ)         │
│ ML Inference:    Dual-Head GRU sequence neural networks (15ms latency)         │
│ Cognitive AI:    OmniRoute LLM (Gemini 2.5 Flash / LLaMA 3.3 70B)              │
│ Alert Hub:       Webhooks (Slack/Teams/MaintainX) & Telegram Incident Bot      │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Step-by-Step Pilot Execution Runbook

### Phase 1: Machine Selection & Sensor Audit (Day 1 - 2)
1. **Select Target Pilot Machine**:
   - Choose 1–3 critical assets where unpredicted downtime causes bottlenecking (e.g. rotary filler, case packer, air compressor, hydraulic press).
2. **Identify Telemetry Channels**:
   - Every physical asset requires 2 to 6 key physical channels:
     - **Vibration (RMS velocity $mm/s$ or acceleration $g$)**: Mechanical bearing wear, imbalance, looseness.
     - **Temperature ($^\circ C$)**: Thermal buildup in bearings, motor windings, or heaters.
     - **Pressure ($bar$ / $psi$)**: Pneumatics, hydraulic manifolds, fluid delivery lines.
     - **Current / Power ($A$ / $kW$)**: Motor loading and mechanical binding.
     - **Flow / Volume ($L/min$ / $ml$)**: Displacement pump delivery or nozzle flow.

### Phase 2: Register Asset in PDM Console (Day 2)
1. Open the PDM Console (`http://<server-ip>:5000`).
2. Click **MACHINERY &amp; CONFIG** (or press the admin configuration button).
3. Under **MACHINERY REGISTRY**:
   - Enter Machine ID (e.g. `MCH-FILL-001`).
   - Select Asset Template (e.g. `FILLING`, `BOXING`, `SHRINK`, or create a Custom Template).
   - Enter Factory Location (e.g. `Packaging Line 2, Bay B`).
   - Add the specific sensor channels.
4. Click **REGISTER ASSET TO REGISTRY**.
   - The asset immediately appears on the Surveillance Grid.

### Phase 3: Connect Physical Machine Telemetry (Day 3)
Click the **GATEWAY** button on the registered machine card to open the **Physical Asset Onboarding Gateway**. PDM offers four production connection modes:

#### Option A: Universal Python Edge Daemon (Recommended for Pilots)
Deploy on an edge computer (industrial IPC, Raspberry Pi CM4, or local PC) with Python 3:
```bash
python scripts/edge/pdm_edge_agent.py \
  --host http://<pdm-server-ip>:5000 \
  --machine-id MCH-FILL-001 \
  --key pdm_live_MCH-FILL-001 \
  --interval 2.0
```
- **Store-and-Forward**: If the factory Wi-Fi or Ethernet drops, `pdm_edge_agent.py` automatically buffers up to 50,000 readings in a local SQLite file (`edge_buffer.db`) and automatically drains them when connectivity recovers.

#### Option B: Modbus TCP Bridge (Direct PLC Connection)
If the machine is controlled by a Siemens, Schneider, Allen-Bradley, or Beckhoff PLC with Modbus TCP enabled:
```bash
python scripts/edge/pdm_modbus_bridge.py \
  --plc-host 192.168.1.100 \
  --plc-port 502 \
  --host http://<pdm-server-ip>:5000 \
  --machine-id MCH-FILL-001 \
  --key pdm_live_MCH-FILL-001
```

#### Option C: MQTT Industrial Broker Bridge
If wireless vibration transducers or IoT nodes publish to a local MQTT broker (Mosquitto, EMQX, HiveMQ):
```bash
python scripts/edge/pdm_mqtt_subscriber.py \
  --broker 192.168.1.50 \
  --topic factory/line1/+/sensors \
  --host http://<pdm-server-ip>:5000 \
  --machine-id MCH-FILL-001 \
  --key pdm_live_MCH-FILL-001
```

#### Option D: Direct REST Ingestion (cURL / SCADA / Node-RED)
Any SCADA system (Ignition, Kepware, Node-RED, AWS IoT) can directly POST JSON:
```bash
curl -X POST "http://<pdm-server-ip>:5000/api/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pdm_live_MCH-FILL-001" \
  -d '{
    "machine_id": "MCH-FILL-001",
    "timestamp": "2026-10-26T14:00:00Z",
    "sensors": {
      "Vibration": 0.14,
      "Nozzle_Pressure": 2.21,
      "Fill_Volume_Sensor": 100.2
    }
  }'
```

### Phase 4: Statistical Baseline Calibration (Day 4)
1. Run the physical machine under normal operating conditions for 15–30 minutes to collect clean operational telemetry.
2. In the Gateway Dialog, click **AUTO-CALIBRATE BASELINE** (or call `POST /api/machine-mgmt/calibrate-asset`).
3. PDM automatically computes:
   - Empirical mean ($\mu$) and standard deviation ($\sigma$).
   - Warning boundary envelope: $\mu + 2.5\sigma$.
   - Critical trip threshold: $\mu + 3.5\sigma$.
4. This eliminates synthetic guesswork and calibrates alarms to the unique mechanical tolerances of the pilot asset.

### Phase 5: Zero-Shot OmniRoute Diagnostics & Alerting (Day 5 - 14)
1. As the machine runs, telemetry is monitored every 2 seconds.
2. If any multivariate drift or sensor breach occurs:
   - The status badge transitions to **WARNING** or **CRITICAL**.
   - The **ADVISOR** button pulses with live diagnostic availability.
   - Click **ADVISOR** to view the **OmniRoute LLM Root Cause Analysis**:
     - Mechatronic fault diagnosis (e.g. Cavitation, Nozzle Clog, Bearing Deterioration).
     - Breached telemetry evidence table.
     - Interactive physical safety/inspection checklist.
     - Required replacement parts and estimated repair window.
3. Click **DISPATCH WORK ORDER**:
   - The Service Dispatch dialog opens with the exact recommended spare parts pre-selected.
   - Confirming service puts the machine into maintenance mode and tracks the intervention.
4. **Automated Incident Escalation**:
   - Configure `ALERT_WEBHOOK_URL` (Slack, Teams, MaintainX) or `TELEGRAM_ALERT_CHAT_ID` / `TELEGRAM_BOT_TOKEN` in Doppler / `.env`.
   - On-call reliability engineers receive instant notification tickets directly on mobile.

---

## 3. Pilot Readiness Checklist & Facilities Matrix

| Pilot Facility | Facility Status | Verification Command / Proof |
|---|---|---|
| **V2 Asset Registry & CRUD** | Available & Verified | `verify_full_system.py` TEST 1 |
| **Ingestion API (`/api/ingest`)** | Available & Verified | `verify_edge_and_pilot.py` TEST 3 |
| **Token Authentication (`pdm_live_*`)** | Available & Verified | `verify_edge_and_pilot.py` TEST 1 & 3 |
| **Edge Gateway Daemon (`pdm_edge_agent.py`)** | Available & Verified | `verify_edge_and_pilot.py` TEST 7 |
| **Store-and-Forward SQLite Buffer** | Available & Verified | `scripts/edge/pdm_edge_agent.py` |
| **Modbus TCP Gateway (`pdm_modbus_bridge.py`)** | Available & Verified | `scripts/edge/pdm_modbus_bridge.py` |
| **MQTT IoT Bridge (`pdm_mqtt_subscriber.py`)** | Available & Verified | `scripts/edge/pdm_mqtt_subscriber.py` |
| **Live Hardware Mode Toggle** | Available & Verified | `verify_edge_and_pilot.py` TEST 4 |
| **Simulator Bypass for Live Assets** | Available & Verified | `app/services/simulator.py` line 135 |
| **Auto-Baseline Calibrator** | Available & Verified | `verify_edge_and_pilot.py` TEST 5 |
| **Dual-Head GRU Sequence Trainer** | Available & Verified | `verify_gru_training.py` exit 0 |
| **OmniRoute Diagnostic Advisory** | Available & Verified | `verify_full_system.py` TEST 6 |
| **Industrial Incident Dispatcher** | Available & Verified | `verify_edge_and_pilot.py` TEST 6 |
| **Device Connection Modal UI** | Available & Verified | `#device-connection-modal` in `modals.html` |
