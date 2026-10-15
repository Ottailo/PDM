# PDM — Industrial Predictive Maintenance System
## Visual Design Contract & Surface Specification

---

### 1. Design Read
> **"A rugged, high-density industrial control-room telemetry console built on dark cool-tinted ink surfaces, single-pixel hairline architecture, and DIN-caliber instrumentation typography, where color is strictly locked to physical machine states and predictive degradation warnings."**

---

### 2. Surface Mode & Three Dials
* **Primary Surface Mode:** `OPERATE` (High-density industrial control room, zero decorative distraction, operational reliability).
* **The Three Dials (out of 10):**
  * `VARIANCE: 3 / 10` — Rigorous consistency across cards, tables, modal dialogues, and charts. High visual discipline; zero whimsical surprises.
  * `MOTION: 2 / 10` — Restrained, functional motion physics strictly under 200ms. No decorative pulsing; animations exist only for genuine real-time data tick confirmations and modal state entrances.
  * `DENSITY: 8 / 10` — Compact technical instrumentation maximizing actionable machine telemetry per square inch on factory screens and control consoles.

---

### 3. Complete Semantic Token Block

The color system is constructed using **OKLCH-tinted neutrals** tinted slightly toward an industrial cold steel hue (`hue: 245`, `chroma: 0.008–0.012`) to eliminate dead pure-gray `#808080` and pitch black `#000000`. Color is strictly forbidden as decoration; it is reserved exclusively for semantic operational states.

```css
:root {
  /* ==========================================================================
     PDM INDUSTRIAL DESIGN SYSTEM - ROOT TOKENS
     Base Neutral Hue: 245 (Industrial Cold Steel)
     ========================================================================== */

  /* Neutral Canvas & Surface Layers (Dark Theme - Control Room Native) */
  --pdm-canvas: oklch(0.14 0.009 245);          /* #11141a - Primary console floor */
  --pdm-surface-base: oklch(0.18 0.011 245);    /* #181d26 - Standard card & panel surface */
  --pdm-surface-raised: oklch(0.22 0.012 245);  /* #212733 - Hover, table header, drawer surface */
  --pdm-surface-overlay: oklch(0.26 0.014 245); /* #2a3240 - Modal dialog & popover background */
  --pdm-surface-sunken: oklch(0.11 0.008 245);   /* #0c0e13 - Inset telemetry wells & code panels */

  /* Hairline Structural Borders (Razor 1px dividers, zero diffuse drops) */
  --pdm-border-hairline: oklch(0.25 0.010 245); /* Hairline divider between panels */
  --pdm-border-subtle: oklch(0.32 0.012 245);   /* Standard card & input borders */
  --pdm-border-strong: oklch(0.42 0.015 245);   /* Focus rings, selected tab underlines */

  /* Monochromatic Typographic Gradients */
  --pdm-text-primary: oklch(0.96 0.005 245);    /* Crisp readout headers, primary metrics */
  --pdm-text-secondary: oklch(0.75 0.008 245);  /* Field labels, tabular column headers */
  --pdm-text-muted: oklch(0.55 0.010 245);      /* Engineering units, timestamps, inactive icons */
  --pdm-text-inverse: oklch(0.14 0.009 245);    /* Text on solid status badges */

  /* ONE Locked Technical Accent (Non-Alert Interactive Chrome, <80% Saturation) */
  --pdm-accent-base: oklch(0.68 0.12 225);      /* #38bdf8 / Technical industrial cyan */
  --pdm-accent-muted: oklch(0.25 0.04 225);     /* Accent subtle background fill */
  --pdm-accent-hover: oklch(0.74 0.13 225);     /* Active interactive state */

  /* Semantic Operational State Signals (Strictly Reserved for Machinery Status) */
  /* Normal / Healthy State (Nominal operation, RUL > 120m) */
  --pdm-status-normal: oklch(0.65 0.16 150);        /* #10b981 - Muted industrial emerald */
  --pdm-status-normal-bg: oklch(0.20 0.04 150);     /* Emerald well fill */
  --pdm-status-normal-border: oklch(0.40 0.08 150); /* Emerald hairline indicator */

  /* Warning / Degrading State (Predictive wear detected, 30m < RUL <= 120m) */
  --pdm-status-warning: oklch(0.75 0.16 75);        /* #f59e0b - Industrial amber */
  --pdm-status-warning-bg: oklch(0.22 0.05 75);     /* Amber warning fill */
  --pdm-status-warning-border: oklch(0.45 0.10 75); /* Amber hairline indicator */

  /* Critical / Imminent Trip State (Action required, RUL <= 30m) */
  --pdm-status-critical: oklch(0.60 0.22 25);       /* #f43f5e - Safety vermilion */
  --pdm-status-critical-bg: oklch(0.20 0.06 25);    /* Vermilion alert fill */
  --pdm-status-critical-border: oklch(0.42 0.12 25);/* Vermilion hairline indicator */

  /* Maintenance / Offline State (Active service dispatch or unpowered) */
  --pdm-status-offline: oklch(0.55 0.015 245);      /* #64748b - Slate neutral */
  --pdm-status-offline-bg: oklch(0.18 0.010 245);   /* Muted gray fill */
  --pdm-status-offline-border: oklch(0.30 0.012 245);

  /* Elevation Shadows (Strict Razor Occlusion - Zero Saturated Glows) */
  --pdm-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.4);
  --pdm-shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -2px rgba(0, 0, 0, 0.5);
  --pdm-shadow-overlay: 0 16px 32px -4px rgba(0, 0, 0, 0.7);

  /* Spacing Scale (4px Base Grid) */
  --pdm-space-1: 4px;
  --pdm-space-2: 8px;
  --pdm-space-3: 12px;
  --pdm-space-4: 16px;
  --pdm-space-5: 20px;
  --pdm-space-6: 24px;
  --pdm-space-8: 32px;

  /* Corner Radii (Crisp Machined Radii - No Pill-Shaped Over-Rounding) */
  --pdm-radius-none: 0px;
  --pdm-radius-sm: 2px;
  --pdm-radius-md: 4px;
  --pdm-radius-lg: 6px;

  /* Typography Scales */
  --font-display: "Chakra Petch", "Barlow Semi Condensed", -apple-system, sans-serif;
  --font-body: "Plus Jakarta Sans", -apple-system, sans-serif;
  --font-mono: "JetBrains Mono", "IBM Plex Mono", monospace;
}

/* Light Theme High-Contrast Mode (for daylight outdoor loading docks / bright factory rooms) */
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    --pdm-canvas: oklch(0.96 0.005 245);
    --pdm-surface-base: oklch(1.0 0.0 0);
    --pdm-surface-raised: oklch(0.93 0.006 245);
    --pdm-surface-overlay: oklch(1.0 0.0 0);
    --pdm-surface-sunken: oklch(0.91 0.008 245);

    --pdm-border-hairline: oklch(0.85 0.008 245);
    --pdm-border-subtle: oklch(0.75 0.012 245);
    --pdm-border-strong: oklch(0.50 0.015 245);

    --pdm-text-primary: oklch(0.15 0.010 245);
    --pdm-text-secondary: oklch(0.35 0.012 245);
    --pdm-text-muted: oklch(0.52 0.010 245);
    --pdm-text-inverse: oklch(0.98 0.002 245);

    --pdm-accent-base: oklch(0.50 0.14 225);
    --pdm-accent-muted: oklch(0.90 0.03 225);
    --pdm-accent-hover: oklch(0.42 0.15 225);

    --pdm-status-normal: oklch(0.45 0.16 150);
    --pdm-status-normal-bg: oklch(0.92 0.04 150);
    --pdm-status-normal-border: oklch(0.70 0.10 150);

    --pdm-status-warning: oklch(0.55 0.17 70);
    --pdm-status-warning-bg: oklch(0.93 0.05 75);
    --pdm-status-warning-border: oklch(0.75 0.12 75);

    --pdm-status-critical: oklch(0.48 0.22 25);
    --pdm-status-critical-bg: oklch(0.92 0.06 25);
    --pdm-status-critical-border: oklch(0.70 0.15 25);

    --pdm-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    --pdm-shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    --pdm-shadow-overlay: 0 16px 32px -4px rgba(0, 0, 0, 0.15);
  }
}
```

---

### 4. Typography Roles & Hierarchy

To eliminate generic AI default typography (`Inter` everywhere without role hierarchy), PDM enforces three distinct typographic engines:

1. **Display & Machine Headers:** `Chakra Petch` (or `Barlow Semi Condensed`).
   * Character: DIN-spec condensed, industrial, precision-machined geometry.
   * Usage: System status headers, Machine Asset IDs (`#MCH-FILL-01`), Modal titles, Key diagnostic labels.
   * Attributes: `font-family: var(--font-display); font-weight: 600; letter-spacing: -0.02em; text-transform: uppercase;`.

2. **Interface Body & Metadata:** `Plus Jakarta Sans` (or `IBM Plex Sans`).
   * Character: Clean, geometric yet human-readable under poor display conditions.
   * Usage: Descriptions, form inputs, button labels, modal instructions, table metadata.
   * Attributes: `font-family: var(--font-body); font-weight: 400/500; letter-spacing: -0.01em;`.

3. **Telemetry Readouts & Sensor Data:** `JetBrains Mono` (or `IBM Plex Mono`).
   * Character: Monospaced engineering font with wide apertures and high optical distinctness for digits.
   * Usage: Sensor measurements (`4.2 bar`, `88.4 °C`), RUL timers (`01h 42m`), sensor timestamps, network port indicators, fault codes.
   * Mandatory Rule: `font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1, "zero" 1;`. This guarantees zero horizontal jitter when telemetry polls every 2000ms.

```css
/* Typography Scale Classes */
.pdm-display-lg {
  font-family: var(--font-display);
  font-size: 1.25rem;
  line-height: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.02em;
  text-transform: uppercase;
}
.pdm-display-sm {
  font-family: var(--font-display);
  font-size: 0.875rem;
  line-height: 1.125rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.pdm-telemetry-value {
  font-family: var(--font-mono);
  font-size: 1.125rem;
  line-height: 1.25rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.pdm-telemetry-unit {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  color: var(--pdm-text-muted);
  text-transform: uppercase;
  margin-left: 2px;
}
.pdm-label {
  font-family: var(--font-body);
  font-size: 0.75rem;
  line-height: 1rem;
  font-weight: 500;
  color: var(--pdm-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
```

---

### 5. Layout Grid & Spacing Rhythm
* **Shell Structure:** 100dvh full-bleed viewport shell with rigid non-scrolling header strip (48px height), flexible 12-column dynamic machine fleet grid, and a collapsible/resizable right inspection dock (Watchlist / Alert Stream).
* **Grid Hierarchy:**
  * Control Header: Fixed 48px height, 16px horizontal padding, hairline bottom border.
  * Filter & Utility Bar: 40px height with inline segmented radio controls.
  * Machine Fleet Canvas: Auto-fill CSS grid: `grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px;`.
  * Inspection Sidebar Dock: Default 340px width, resizable down to 280px or collapsible to 48px rail.
* **Component Padding Rhythm:** Strict 4px rhythm (`4px`, `8px`, `12px`, `16px`). Machine cards use `padding: 12px` to prevent wasted dead space.

---

### 6. The Single Signature Element
**The Linear Multi-Zone RUL Instrumentation Gauge with Integrated Hairline Telemetry Ribbon.**

Rather than rendering generic circular progress rings, neon donut meters, or pulsating cards, every PDM Machine Card is anchored by a precision physical gauge:
1. **Segmented Remaining Useful Life Track:** A 6px segmented horizontal gauge divided into three physical threshold zones:
   * Critical Zone: Left 0%–25% (marked with a safety vermilion indicator line at 30 min threshold).
   * Warning Zone: Middle 25%–50% (marked with an industrial amber indicator line at 120 min threshold).
   * Nominal Zone: Right 50%–100% (emerald track).
2. **Current Telemetry Ribbon:** A hairline single-pixel SVG sparkline tracing the primary fault-driving sensor channel across the last 30 readings, rendered with zero gradient fills, zero glow filters, and tabular numeric high/low bounds.

---

### 7. Motion Laws & Interaction Physics
All motion in PDM is functional, deterministic, and non-distracting:
* **Duration Limit:** All state transitions MUST complete in `<= 200ms`.
* **Easing Function:** Strong custom ease-out: `cubic-bezier(0.23, 1, 0.32, 1)`. No bouncy springs, elastic overshoots, or slow ease-in curves.
* **Modal & Flyout Entrances:** Enter from `transform: scale(0.97)` and `opacity: 0` to `scale(1)` and `opacity: 1`. Never animate from `scale(0)`.
* **Zero Keyboard Animation:** Keyboard shortcut commands, tab switching, and arrow-key fleet navigation trigger instant `0ms` DOM updates.
* **Hover State Isolation:** All `:hover` transforms are strictly gated behind `@media (hover: hover) and (pointer: fine)`.
* **No `transition: all`:** Every transition property must be explicitly named (e.g. `transition: transform 150ms cubic-bezier(0.23, 1, 0.32, 1), background-color 150ms ease`).
* **Live-Data Heartbeat Tick:** Real-time polling updates (2000ms) are indicated solely by a single 150ms opacity flash (`opacity: 0.4 -> 1.0`) on the header status beacon. Decorative, continuous `@keyframes pulse` is strictly banned.
* **Reduced Motion:** Honor `prefers-reduced-motion: reduce` by zeroing all durations (`animation-duration: 0.01ms !important; transition-duration: 0.01ms !important;`).

---

### 8. Mobile & Industrial Terminal Standards (`mobile-native`)
* **Touch Targets:** All interactive buttons, segmented pills, and table action triggers maintain a minimum touch bounding box of `40px x 40px` (`min-height: 40px`).
* **Input Auto-Zoom Prevention:** Form inputs (`<input>`, `<select>`) enforce `font-size: 16px` under `@media (pointer: coarse)` to prevent iOS Safari from zooming into the form.
* **Touch Action:** Interactive elements declare `touch-action: manipulation;` and `-webkit-tap-highlight-color: transparent;`.
* **App Shell Sizing:** Body and modal backdrops utilize `100dvh` to account for mobile browser URL bars, with `overscroll-behavior: contain;`.
* **Safe-Area Insets:** Edge-docked components respect `padding-bottom: env(safe-area-inset-bottom);`.

---

### 9. Kill List & Anti-Slop Enforcement Table

| # | Slop Tell Identified in Audit | Concrete File & Line Location | Refactoring / Removal Rule |
|---|---|---|---|
| 1 | Broken Token Architecture & Undefined Variables | `app/templates/base.html:26-31`, `app/static/css/style.css:5-37` | Replace fake Tailwind vars (`electric-blue`, `neon-cyan`, `deep-navy`) with verified `:root` tokens (`--pdm-canvas`, `--pdm-surface-*`, `--pdm-accent-*`, `--pdm-status-*`). |
| 2 | Hardcoded Hex Color Strings in Telemetry Charts | `app/static/js/dashboard.js:27-30, 1006, 1053` | Replace rainbow array `['#34d399', '#f87171', '#60a5fa', ...]` and `#00d4ff` with semantic OKLCH/RGB tokens derived directly from CSS variables. |
| 3 | Saturated Purple & Blue Cyber Gradients | `app/templates/login.html:12, 16-19`, `app/templates/components/machine_management_modal.html:7, 148, 207`, `app/templates/components/modals.html:5, 8, 37` | Remove all multi-stop gradient bars and neon glows. Replace with flat `--pdm-surface-base` and hairline `--pdm-border-subtle` borders. |
| 4 | Decorative Pulses & Unanchored Loop Animations | `app/templates/components/header.html:10`, `app/templates/components/modals.html:10`, `app/static/js/dashboard.js:99, 692, 796`, `app/static/js/machine_management.js:428, 486, 541`, `style.css:182-196` | Strip all `animate-pulse`, `pulse-glow`, and `animate-pulse-slow` classes from non-ticker elements. State colors remain solid and legible. |
| 5 | Emoji Characters Used as Interface Graphics | `app/templates/components/sidebar.html:25, 29, 61`, `machine_management_modal.html:10, 24, 29, 52, 133, ...`, `admin_dashboard.html:62, 73, 84`, `dashboard.js:223, 236, 746-771`, `configuration.js:42, 82` | Eliminate all raw Unicode emojis. Replace with precision inline SVGs or clean Lucide/Tabler icon paths with `stroke-width="1.5"`. |
| 6 | Mouse-Following Flashlight Gradient Effect | `app/static/js/dashboard.js:34-46` (`predictive-spotlight`) | Delete the mousemove flashlight event listener entirely. It creates unnecessary DOM layout recalcs and reads as a gamer portfolio gimmick. |
| 7 | Backdrop Blur Overuse (`backdrop-blur-sm`, `blur(10px)`) | `app/templates/login.html:16`, `app/templates/components/machine_management_modal.html:2` | Remove GPU-expensive backdrop filters. Use opaque, high-contrast dark surface fills with crisp hairline borders (`--pdm-surface-overlay`). |
| 8 | Generic 3-Card Stat Grids & Fake Metric Mockups | `app/templates/admin_dashboard.html:54-88, 178-214`, `machine_management_modal.html:300-314`, `machine_management.js:618-644` | Remove synthetic calculation formulas (`1247 + (predictionCount * 50)`) and fake latency metrics (`12ms`, `99.9%`). Display authentic fleet operational counts and model telemetry. |
| 9 | Typography & CDN Fragility | `app/templates/base.html:13, 17, 20` | Remove unused Font Awesome CDN stylesheet and unoptimized Google Fonts. Import `Chakra Petch`, `Plus Jakarta Sans`, and `JetBrains Mono`. Enforce `font-variant-numeric: tabular-nums`. |
| 10 | Numeric Layout Jitter During 2000ms Polling | `app/static/js/dashboard.js:490-580`, `app/templates/dashboard.html` | Apply `font-variant-numeric: tabular-nums;` to all sensor readouts, RUL numbers, and timestamps so telemetry updates don't cause horizontal layout jumps. |

---

### 10. The Five View States Specification
To guarantee resilience across edge cases and network interruptions, every view must implement:

1. **Loading State:** Monochromatic structural skeleton cards with hairline borders and a subtle 150ms opacity pulse (`opacity: 0.35 <-> 0.65`). Exact dimensions matching final cards to ensure zero Cumulative Layout Shift (CLS = 0).
2. **Empty State:** High-contrast technical diagnostic panel with asset icon, clear root cause description (e.g. "No machinery registered for Plant Bay: Line 3"), and a primary action trigger ("Add Asset to Line 3").
3. **Error State:** High-visibility safety border (`--pdm-status-critical-border`), explicit technical error code (e.g. `ERR_TELEMETRY_SOCKET_TIMEOUT: Port 5000`), and a direct retry action ("Re-establish Stream").
4. **Partial State:** For assets with one or more disconnected sensor channels, show nominal telemetry with degraded indicator badges ("Channel 3 [Pump Vibration] Offline — Operating on 9-Channel Redundancy").
5. **Populated State:** High-density operational view with tabular-numeric readouts, segmented RUL gauge, live status badge, and sub-200ms interaction response.
