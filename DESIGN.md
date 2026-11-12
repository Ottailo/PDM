# Machivital — Maintenance workbench

## Active design contract — 2026-11-12

```text
Product Truth    : Maintenance teams record machines, plan work, and retain reviewed completion records.
Audience State   : Scattered handovers become a clear next action.
Emotional Soul   : Practical confidence and legible responsibility, never invented machine health.
Surface Mode     : OPERATE (private workbench); TRUST-FIRST (public pilot information).
Chosen Archetype : Warm Authority, grounded in the plant's shift sheet and maintenance ledger.
Stack & Target   : Existing React/TypeScript/Vite; desktop and 320px+ phone.
MOTION_INTENSITY : 2/10; short deliberate feedback, reduced-motion respected.
VISUAL_DENSITY   : 6/10 workbench, 3/10 public page.
Signature Element: Machine → planned work → reviewed record; explanatory disclosures public, actual records private.
Typography       : Barlow / Source Sans 3; existing local font assets.
Palette Dynamic  : Sage surfaces, deep mineral ink, teal action accents, amber only for real attention states.
Anti-defaults    : No fake telemetry cockpit, inactive demo controls, synthetic customer metrics or status dots.
```

Shared tokens govern surfaces, borders, contrast, focus and action feedback. Record counts remain API-derived; no public dashboard imitation. Public publishing has its own React entry without private forms or API requests. Existing auth and maintenance actions retain their behavior. Details: [public deployment boundary](docs/PUBLIC_PILOT_DEPLOYMENT.md).

## Historical demo design specification — not active release contract

> 2026-11-12: Autonomous telemetry, physical condition and predictive statements below are not verified product truth. The current local React workbench uses its existing warm maintenance identity; PM phone improvements preserve that identity, not this retired cockpit spec. See [original-vision audit](docs/ORIGINAL_VISION_CROSSCHECK_2026-11-12.md) and [PM PRD](docs/PREVENTIVE_MAINTENANCE_PRD.md).

---

### MANDATORY GATE 0: THE DESIGN CONTRACT

```text
DESIGN CONTRACT
───────────────
Product Truth    : Mechavital empowers plant engineers and floor mechanics with autonomous real-time machinery vitality surveillance, multi-channel sensor streaming, remaining useful life (RUL) estimation, and root-cause failure mode diagnostics to eliminate catastrophic unplanned line downtime.
Surface Mode     : OPERATE (High-Density Industrial Plant Telemetry & Mobile Field Surveillance)
Design Read      : A rugged, high-density industrial control-room telemetry console and field technician workstation built on laser-etched cold steel ink surfaces (oklch(0.11 0.006 250)), razor-thin 1px structural hairlines, and DIN-caliber instrumentation typography (Chakra Petch + JetBrains Mono), where color is strictly locked to physical mechanical states and predictive degradation warnings.
Chosen Archetype : Archetype E (Signal Density — High-Precision Mechatronics Telemetry Console)
MOTION_INTENSITY : 2 / 10 — Restrained, functional motion physics strictly under 200ms (150ms deterministic telemetry ingestion pulse, 180ms ease-out modal/drawer reveals, tactile button depression).
VISUAL_DENSITY   : 9 / 10 — High-density instrumentation maximizing actionable machine telemetry, multivariate sensor readings (vibration mm/s, pressure bar, temperature °C, motor current A), and degradation curves per square inch.
Signature Element: Live Mechatronic Harmonic Spectral Oscilloscope & Dynamic Multi-Zone RUL Arc: A precision-calibrated real-time telemetry card featuring a continuous live sensor ribbon with interactive inspection scrubbers, a 3-zone color-calibrated RUL countdown bar (Critical <= 30m, Degrading 30-120m, Nominal > 120m), and an interactive Mechatronic Diagnostic Stethoscope mode.
Typography       : Chakra Petch (Display headers) / Plus Jakarta Sans (Body & UI) / JetBrains Mono (Tabular telemetry & metrics)
Accent Color     : Technical Industrial Sky Cyan oklch(0.68 0.12 225) (#38bdf8) — strictly under 5% screen area, reserved for active selection, focus rings, and non-alert interactive chrome.
Anti-defaults    : 
  1. Ban the generic dark obsidian SaaS clone with purple/blue blurry glow drop-shadows and emoji-filled cards.
  2. Ban fake "Engine Ready" / "● Nominal" status pills without real live sensor telemetry; if a machine has no stream, display an authentic "Awaiting Edge Packet Burst" empty state with copyable PLC connection commands.
```

---

### 1. Subject-Matter Grounding & Physical Telemetry Invariants
Mechavital is grounded directly in industrial discrete packaging mechatronics (bottling fillers, shrink-wrap sealers, pillow-pack formers, and robotic cartoning boxes):
- **Vibration Amplitude**: Root-Mean-Square (RMS) velocity ($mm/s$) and high-frequency bearing acceleration ($g$) calibrated to ISO 10816-3 machinery vibration standards.
- **Hydraulic & Pneumatic Pressure**: Real-time line pressure ($bar$ / $PSI$) with physical transducer bounds.
- **Thermal Profiles**: Temperature ($^\circ C$) with infrared thermal baseline drift monitoring.
- **Motor Electrical Load**: Current consumption ($A$) tracking mechanical binding, conveyor jams, and bearing friction.
- **Remaining Useful Life (RUL)**: Dual-Head GRU sequence regression projecting operational hours remaining before trip.

---

### 2. Semantic OKLCH Token Architecture

```css
:root {
  /* Canvas & Surface Layers (Dark Theme - Control Room Native) */
  --mv-canvas: oklch(0.11 0.006 250);          /* Primary console dark floor #0c0e12 */
  --mv-surface-base: oklch(0.14 0.007 250);    /* Standard card & instrument surface #12161e */
  --mv-surface-raised: oklch(0.18 0.008 250);  /* Header, toolbar & elevated panel #181e28 */
  --mv-surface-overlay: oklch(0.22 0.010 250); /* Modal dialog & drawer background #1f2633 */
  --mv-surface-sunken: oklch(0.09 0.005 250);  /* Inset telemetry wells & oscilloscope #090b0e */

  /* Hairline Structural Borders (Razor 1px dividers, zero diffuse drops) */
  --mv-border-hairline: rgba(255, 255, 255, 0.08); /* Razor hairline divider between panels */
  --mv-border-subtle: oklch(0.26 0.010 250);       /* Standard card & input borders */
  --mv-border-strong: oklch(0.38 0.012 250);       /* Focus rings, selected tab lines */

  /* Monochromatic Typographic Gradients */
  --mv-text-primary: oklch(0.93 0.006 80);    /* Crisp readout headers, primary numbers #eceeed */
  --mv-text-secondary: oklch(0.70 0.008 80);  /* Field labels, tabular column headers #b0b5be */
  --mv-text-muted: oklch(0.50 0.006 80);      /* Engineering units, timestamps, inactive icons #7b8390 */
  --mv-text-inverse: oklch(0.11 0.006 250);   /* Dark text on bright status badges */

  /* ONE Locked Technical Accent (Non-Alert Interactive Chrome, <5% Screen Area) */
  --mv-accent-base: oklch(0.68 0.12 225);      /* Technical industrial sky cyan #38bdf8 */
  --mv-accent-muted: rgba(56, 189, 248, 0.10); /* Accent subtle background fill */
  --mv-accent-hover: oklch(0.74 0.14 225);     /* Active interactive state */

  /* Semantic Operational State Signals */
  --mv-status-normal: oklch(0.65 0.16 150);        /* Muted industrial emerald #10b981 */
  --mv-status-normal-bg: rgba(16, 185, 129, 0.12); /* Emerald well fill */
  --mv-status-normal-border: rgba(16, 185, 129, 0.35);

  --mv-status-warning: oklch(0.75 0.16 75);        /* Industrial amber #f59e0b */
  --mv-status-warning-bg: rgba(245, 158, 11, 0.12); /* Amber warning fill */
  --mv-status-warning-border: rgba(245, 158, 11, 0.35);

  --mv-status-critical: oklch(0.60 0.22 25);       /* Safety vermilion #f43f5e */
  --mv-status-critical-bg: rgba(244, 63, 94, 0.14); /* Vermilion alert fill */
  --mv-status-critical-border: rgba(244, 63, 94, 0.40);

  --mv-status-offline: oklch(0.50 0.010 250);      /* Slate neutral #64748b */
  --mv-status-offline-bg: rgba(100, 116, 139, 0.12);
  --mv-status-offline-border: rgba(100, 116, 139, 0.25);
}
```

---

### 3. The 5 Complete View States

1. **State 1: Loading Skeleton**:
   - Zero layout shift (CLS < 0.01).
   - Monochromatic 4-cell matrix pulse matching card height and widths.
2. **State 2: Telemetry Pipeline Interrupted (Error)**:
   - High-contrast alert card with diagnostic error trace.
   - Dedicated "RECONNECT STREAM" trigger with exponential backoff indicator.
3. **State 3: Awaiting Edge Telemetry (Empty State)**:
   - Rendered when a machine is provisioned but hasn't received edge bursts.
   - Live copyable curl and Python edge feeder snippet for immediate floor PLC testing.
4. **State 4: Degraded / Anomalous Telemetry (Partial State)**:
   - Anomalous channels flagged with warning amber / trip vermilion LED pips.
   - Delta indicators tracking rate of change ($\uparrow +0.14$).
5. **State 5: Active Operational Surveillance (Success State)**:
   - High-density 2x2 sensor readings with units.
   - 3-zone linear RUL instrumentation gauge bar.
   - Real-time hairline ribbon sparkline chart (Chart.js duration: 0 for zero jitter).
   - Tactical action triggers: `[GATEWAY]`, `[ADVISOR]`, `[HISTORY]`, `[SERVICE]`.

---

### 4. Field Mobile Technician Experience (`/mobile`)
- Mobile PWA with touch-first 44px+ hit areas.
- Tactile bottom navigation bar (`FLEET`, `INCIDENTS`, `ORDERS`, `CONNECT`).
- Slide-up mechatronic root-cause diagnostic drawer powered by OmniRoute LLM.
- 1-Tap emergency maintenance work order dispatch modal with pre-filled spare parts.
- Haptic alarm feedback (`navigator.vibrate([200, 100, 200])`) on fault detection.
