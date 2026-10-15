# PDM — Industrial Predictive Maintenance System
## Product Truth, Operational Context & Domain Specification

---

### 1. Product Vision & Mission
PDM is a real-time, high-reliability industrial predictive maintenance platform engineered for discrete beverage, food, and consumer packaging lines. The system continuously samples multi-channel physical telemetry across four mechanical packaging asset classes (`FILLING`, `SHRINK`, `PILLOW`, and `BOXING`), streaming readings into pre-trained dual-head Keras GRU sequence models. 

The inference engine calculates two simultaneous operational outputs:
1. **Remaining Useful Life (RUL):** Continuous projection of remaining operational minutes/hours before catastrophic failure.
2. **Mechanical Fault Classification:** Multi-class diagnosis pinpointing imminent failure modes (`Nozzle Clog`, `Pump Pressure Fault`, `Bearing Wear`, `Heater Failure`, `Conveyor Jam`, `Seal Heater Failure`, `Alignment Error`, `Pneumatic Leak`, `Box Jam`, `Feed Mechanism Fault`).

The platform exists to replace reactive firefighting and static calendar-based maintenance schedules with telemetry-driven, precision interventions that protect uptime, reduce scrap rates, and maintain line throughput.

---

### 2. Target Audience & Operator Personas

#### A. Line Operators & Floor Mechanics
* **Environment:** Industrial packaging floors, high ambient noise (85-95 dB), varied factory lighting, vibrations, greasy/gloved hands, rugged tablets or touch monitors mounted at line ends.
* **Primary Jobs-to-be-Done:**
  * Scan all lines in under three seconds to verify green status across filling, wrapping, and boxing stations.
  * Receive high-contrast visual warnings when an asset's RUL drops below 120 minutes (Warning) or 30 minutes (Critical).
  * Identify the exact mechanical subsystem and sensor channel causing anomalous degradation.
  * Dispatch targeted component work orders with pre-calculated repair durations and specific replacement parts.
* **Mental Model:** "Keep the line moving. Tell me what is failing, which sensor proves it, what part to grab from the crib, and how long I have before the line trips."

#### B. Plant Operations & Maintenance Supervisors
* **Environment:** Control room multi-monitor consoles, desktop web browsers, shift handover meetings.
* **Primary Jobs-to-be-Done:**
  * Track fleet-wide asset availability, uptime percentages, and active fault counts across factory zones.
  * Audit sensor telemetry history (1-hour, 6-hour, and 24-hour degradation trajectories) to validate model predictions against actual wear.
  * Manage equipment registry: register new physical assets, assign physical factory coordinates, and tune sensor threshold configurations.
  * Train and deploy updated GRU sequence model weights using uploaded historical CSV run-to-failure datasets.
  * Configure streaming data bridges across industrial protocols (OPC-UA, Modbus TCP, MQTT broker, and REST endpoints).
  * Administer tenant users, role-based access control (`admin`, `user`, `viewer`), and global maintenance window toggles.

---

### 3. Operating Context & Physical Environment
* **Lighting & Display Conditions:** Variable factory floor ambient glare, 1080p rugged industrial touchscreen terminals, wall-mounted control room overview monitors, and mobile tablets. High-contrast typography and glare-resistant dark surfaces are functional necessities, not aesthetic choices.
* **Latency & Polling Rhythms:** Telemetry updates stream on a deterministic 2000ms polling cycle. Number displays must never cause layout shift or horizontal jitter.
* **Fault Cost Profile:** Unplanned downtime on a primary packaging line costs between $4,000 and $18,000 per hour in lost output, product spoilage, and operator idle time. Ambiguous or decorative interfaces create cognitive drag and delayed reaction times.

---

### 4. Voice, Tone & Microcopy Standards
* **Core Voice Attributes:** Calm, terse, technical, definitive, and strictly operational.
* **Copywriting Rules:**
  * **Zero Artificial Hype:** Ban words such as *elevate*, *unleash*, *next-gen*, *revolutionary*, *empower*, *seamless*, *game-changer*, *robust*, and *testament*.
  * **Zero Em-Dash Slogans:** Eliminate decorative em-dashes (`—`) in headers and marketing-style subheads.
  * **Active Operational Verbs:** Use direct imperative language: "Dispatch work order", "Acknowledge alert", "Export telemetry CSV", "Set calibration baseline", "Inspect nozzle assembly".
  * **Strict Metric Precision:** Every number must carry its physical engineering unit (`bar`, `deg C`, `mm/s`, `m/min`, `boxes/min`, `mL`).
  * **Direct Error Explanations:** State the failing component, the threshold violation, and the immediate corrective protocol.

---

### 5. Domain Mechatronics Architecture

#### Asset Classes & Physical Telemetry Channels
1. **Liquid Filling Station (`FILLING`)**
   * Primary Telemetry: Nozzle Pressure (`bar`), Fill Volume (`mL`), Pump Vibration (`mm/s`), Infeed Velocity (`m/min`).
   * Primary Failure Modes: Nozzle Clog, Pump Pressure Fault, Valve Seal Degradation.
   * Standard Replacement Subsystems: Nozzle Assembly (25m repair), High-Pressure Pump Seals (45m repair).

2. **Thermal Shrink Tunnel (`SHRINK`)**
   * Primary Telemetry: Tunnel Temperature (`deg C`), Blower Velocity (`m/s`), Heating Element Amperage (`A`), Conveyor Speed (`m/min`).
   * Primary Failure Modes: Heating Element Failure, Thermocouple Drift, Blower Motor Bearing Wear.
   * Standard Replacement Subsystems: Ceramic Heating Elements (40m repair), Blower Fan Motor (60m repair).

3. **Horizontal Flow Wrapper (`PILLOW`)**
   * Primary Telemetry: Sealing Jaw Temperature (`deg C`), Sealing Jaw Pressure (`bar`), Film Tension (`N`), Film Feed Rate (`m/min`).
   * Primary Failure Modes: Sealing Jaw Misalignment, Seal Heater Burnout, Film Tension Loss.
   * Standard Replacement Subsystems: Rotary Sealing Jaws (35m repair), Film Roll Tensioner (20m repair).

4. **Case Packer & Boxing Unit (`BOXING`)**
   * Primary Telemetry: Pneumatic Line Pressure (`bar`), Box Feed Count (`boxes/min`), Arm Actuation Vibration (`mm/s`), Jam Sensor State (`binary`).
   * Primary Failure Modes: Box Magazine Jam, Pneumatic Cylinder Leak, Mechanical Arm Misalignment.
   * Standard Replacement Subsystems: Pneumatic Actuator Cylinder (30m repair), Suction Cup Vacuum Assembly (15m repair).

#### Predictive Thresholds & State Engine
* **NORMAL (`RUL > 120 minutes`):** Machine running within nominal operating envelopes. Fleet status indicator: Muted Industrial Emerald (`#10b981`).
* **WARNING (`30 minutes < RUL <= 120 minutes`):** Progressive sensor deviation detected; mechanical wear signature identified. Preventive maintenance window open. Fleet status indicator: Industrial Amber (`#f59e0b`).
* **CRITICAL (`RUL <= 30 minutes`):** Severe degradation signature; trip or mechanical seizure imminent. Immediate intervention required. Fleet status indicator: Safety Vermilion (`#f43f5e`).
* **UNDER_MAINTENANCE:** Machine taken offline for active service dispatch. Telemetry paused; maintenance timer elapsed. Fleet status indicator: Neutral Slate (`#64748b`).

---

### 6. Content Inventory: Routes, Screens & Operational Jobs

| Route / View | Operational Job | Data Interfaces & Controls |
|---|---|---|
| `GET /login`, `POST /login` | Secure operator/engineer authentication. | Credentials input, session persistence toggle, role-based redirection (`/dashboard` vs `/admin/dashboard`). |
| `GET /logout` | Terminate session credentials. | Clears cookie tokens, redirects to `/login`. |
| `GET /setup-admin` | Bootstrap initialization for root plant administrator. | Username, password, email setup. Permanently locked after initial creation. |
| `GET /` & `GET /dashboard` | Primary plant fleet overview & control room dashboard. | High-density status strip, location filter (`Line 1`, `Line 2`, `Packaging Bay B`), machine type filters, dynamic machine cards grid, live alert feed, and RUL watchlist sidebar. |
| Component: Header Status Strip | Real-time plant health overview. | Online count vs total fleet (`Online: X / Y`), critical alert counter, polling heartbeat ticker, user profile menu, admin console trigger. |
| Component: Watchlist & Event Log Dock | High-priority asset tracking and chronological incident feed. | Assets ordered ascending by RUL, chronological factory alarm log with timestamps, severity levels, and deep-link triggers to asset cards. |
| Component: Sensor History Dialog | Deep-dive telemetry degradation analysis. | Multi-channel interactive time-series charts (Chart.js), time window toggles (`1h`, `6h`, `24h`), threshold breach markers. |
| Component: Service Work Order Modal | Maintenance ticket dispatch. | Asset metadata, component checklist with estimated repair durations (minutes), technician notes input, submission to `/api/request-maintenance`. |
| Component: Machine Management Modal | Plant engineering and data science management. | 4 operational tabs: Machine Registration (CRUD), Historical CSV Training Ingestion, Live Industrial Streaming configuration (OPC-UA/Modbus/MQTT/REST), Model Training & Validation. |
| `GET /admin/dashboard` | Central plant administration console. | 4 operational modules: User Management (RBAC: admin, user, viewer), Machine Template & Location Configuration, System Health telemetry, and Global Maintenance Mode override. |

---

### 7. Five Operational UI States
Every data-bound screen, table, modal, and card must render explicitly across five states:
1. **Loading State:** Monochromatic tabular bone skeletons preserving exact component dimensions to guarantee zero layout shift.
2. **Empty State:** High-signal diagnostic message explaining why no telemetry or assets are displayed (e.g. "No assets registered for Location: Bay 4"), paired with a primary registration action.
3. **Error State:** Concrete failure reason (e.g., "Telemetry stream disconnected on port 5000", "Inference model weights not loaded for model_gru_pillow.h5"), accompanied by a manual reconnect button and diagnostic code.
4. **Partial State:** Graceful handling of offline or uncalibrated channels (e.g., "Channel 4 [Fill Volume] offline — running RUL model on 9-channel degraded fallback mode").
5. **Populated State:** High-density, real-time data display with tabular numbers, precise status indicators, and sub-300ms transitions.
