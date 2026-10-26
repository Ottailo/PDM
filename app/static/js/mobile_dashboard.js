/**
 * PDM Industrial Remote Surveillance — Mobile Field Operations Engine
 * 
 * Surface Mode: OPERATE | High Density | 2000ms Polling | Haptic Alarms
 */

// Global State
let latestPredictions = {};
let latestKpis = {};
let latestEvents = [];
let activeFilter = 'ALL';
let activeTab = 'SURVEILLANCE';
let hapticsEnabled = true;
let previousStates = {};
let isPolling = false;
let pollTimer = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initHaptics();
    startPolling();
    setupVisibilityHandler();
    initGatewayProfiles();
});

// Haptic & Audio Support
function initHaptics() {
    const stored = localStorage.getItem('machivital_mobile_haptics') || localStorage.getItem('pdm_mobile_haptics');
    if (stored !== null) {
        hapticsEnabled = stored === 'true';
    }
    updateHapticButtonLabel();
}

function toggleHaptics() {
    hapticsEnabled = !hapticsEnabled;
    localStorage.setItem('machivital_mobile_haptics', hapticsEnabled ? 'true' : 'false');
    updateHapticButtonLabel();
    if (hapticsEnabled && navigator.vibrate) {
        navigator.vibrate(60);
    }
}

function updateHapticButtonLabel() {
    const label = document.getElementById('haptic-label');
    if (label) {
        label.textContent = hapticsEnabled ? 'HAPTIC: ON' : 'HAPTIC: OFF';
    }
}

function triggerAlarmVibration() {
    if (hapticsEnabled && navigator.vibrate) {
        // High urgency industrial stutter vibration
        navigator.vibrate([200, 100, 200, 100, 400]);
    }
}

// Background tab throttler
function setupVisibilityHandler() {
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            clearInterval(pollTimer);
        } else {
            fetchFleetState();
            pollTimer = setInterval(fetchFleetState, 2000);
        }
    });
}

function startPolling() {
    fetchFleetState();
    pollTimer = setInterval(fetchFleetState, 2000);
}

// Fetch Fleet Telemetry
async function fetchFleetState() {
    if (isPolling) return;
    isPolling = true;

    const startTime = performance.now();
    try {
        const response = await fetch('/api/latest-states');
        const latency = Math.round(performance.now() - startTime);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        latestPredictions = data.predictions || {};
        latestKpis = data.kpis || {};
        latestEvents = data.event_log || [];

        // Update latency and sync readouts
        const latencyEl = document.getElementById('mob-kpi-latency');
        if (latencyEl) latencyEl.textContent = `${latency} ms`;

        const syncEl = document.getElementById('mobile-last-sync');
        if (syncEl) syncEl.textContent = new Date().toLocaleTimeString();

        // Flash Heartbeat LED
        flashHeartbeatLed(true);

        // Check for new critical/warning transitions
        detectAlarmTransitions(latestPredictions);

        // Update KPIs
        updateKpis(latestKpis, latestPredictions);

        // Render Active Views
        if (activeTab === 'SURVEILLANCE') {
            renderSurveillanceCards();
        } else if (activeTab === 'INCIDENTS') {
            renderIncidentsList();
        } else if (activeTab === 'WORKORDERS') {
            renderWorkOrdersList();
        }

    } catch (err) {
        console.warn('Telemetry polling error:', err);
        flashHeartbeatLed(false);
        const syncEl = document.getElementById('mobile-last-sync');
        if (syncEl) syncEl.textContent = 'OFFLINE (RETRYING)';
    } finally {
        isPolling = false;
    }
}

function flashHeartbeatLed(healthy) {
    const led = document.getElementById('mobile-heartbeat-led');
    if (!led) return;
    if (healthy) {
        led.style.backgroundColor = 'var(--pdm-status-normal)';
    } else {
        led.style.backgroundColor = 'var(--pdm-status-critical)';
    }
}

// Alarm Transition Detector
function detectAlarmTransitions(predictions) {
    let triggeredAlarm = false;

    for (const [id, m] of Object.entries(predictions)) {
        const prevState = previousStates[id];
        const currState = m.state || 'Unknown';

        const isAlarmState = ['Critical', 'Critical Failure Imminent', 'Signal Dropped', 'Warning'].includes(currState);
        const wasAlarmState = ['Critical', 'Critical Failure Imminent', 'Signal Dropped', 'Warning'].includes(prevState);

        if (isAlarmState && !wasAlarmState) {
            triggeredAlarm = true;
        }

        previousStates[id] = currState;
    }

    if (triggeredAlarm) {
        triggerAlarmVibration();
    }
}

// KPI Strip
function updateKpis(kpis, predictions) {
    const total = Object.keys(predictions).length;
    let online = 0;
    let alerts = 0;
    let dropped = 0;
    let attention = 0;

    for (const [id, m] of Object.entries(predictions)) {
        const s = (m.state || '').toLowerCase();
        if (m.is_online) online++;
        if (s.includes('critical') || s.includes('warning') || s.includes('dropped') || s.includes('degrading')) {
            alerts++;
            attention++;
        }
        if (s.includes('dropped')) {
            dropped++;
        }
    }

    const onlineEl = document.getElementById('mob-kpi-online');
    if (onlineEl) onlineEl.textContent = `${online} / ${total}`;

    const alertsEl = document.getElementById('mob-kpi-alerts');
    if (alertsEl) alertsEl.textContent = `${alerts}`;

    const countAttention = document.getElementById('count-attention');
    if (countAttention) countAttention.textContent = attention;

    const countDropped = document.getElementById('count-dropped');
    if (countDropped) countDropped.textContent = dropped;

    const alertDot = document.getElementById('bottom-alert-dot');
    if (alertDot) {
        if (alerts > 0) alertDot.classList.remove('hidden');
        else alertDot.classList.add('hidden');
    }

    const incidentBadge = document.getElementById('incident-counter-badge');
    if (incidentBadge) incidentBadge.textContent = `${alerts} ACTIVE`;
}

// Tab Switching
function switchTab(tabName) {
    activeTab = tabName;

    // Toggle container visibilities
    const containers = {
        'SURVEILLANCE': document.getElementById('mobile-feed-container'),
        'INCIDENTS': document.getElementById('incidents-container'),
        'WORKORDERS': document.getElementById('workorders-container'),
        'GATEWAY': document.getElementById('gateway-tab-container')
    };

    for (const [name, el] of Object.entries(containers)) {
        if (!el) continue;
        if (name === tabName) {
            el.classList.remove('hidden');
        } else {
            el.classList.add('hidden');
        }
    }

    // Toggle nav active styles
    const tabs = ['SURVEILLANCE', 'INCIDENTS', 'WORKORDERS', 'GATEWAY'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab-${t}`);
        if (!btn) return;
        if (t === tabName) {
            btn.classList.add('text-[var(--pdm-accent-base)]');
            btn.classList.remove('text-[var(--pdm-text-muted)]');
        } else {
            btn.classList.remove('text-[var(--pdm-accent-base)]');
            btn.classList.add('text-[var(--pdm-text-muted)]');
        }
    });

    if (tabName === 'SURVEILLANCE') renderSurveillanceCards();
    if (tabName === 'INCIDENTS') renderIncidentsList();
    if (tabName === 'WORKORDERS') renderWorkOrdersList();
}

// Filter Handling
function setFilter(filter) {
    activeFilter = filter;
    const filterPills = ['ALL', 'ATTENTION', 'LIVE', 'DROPPED'];
    filterPills.forEach(f => {
        const el = document.getElementById(`filter-${f}`);
        if (!el) return;
        if (f === filter) {
            el.className = 'filter-pill px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-wider bg-[var(--pdm-accent-base)] text-black font-semibold';
        } else {
            el.className = 'filter-pill px-2.5 py-0.5 rounded-full text-[10px] font-mono tracking-wider bg-[var(--pdm-surface-sunken)] text-[var(--pdm-text-muted)] border border-[var(--pdm-border-hairline)]';
        }
    });
    renderSurveillanceCards();
}

// Render Machinery Cards
function renderSurveillanceCards() {
    const container = document.getElementById('mobile-feed-container');
    if (!container) return;

    const machineEntries = Object.entries(latestPredictions);
    if (machineEntries.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-[var(--pdm-text-muted)] font-mono text-xs">
                NO ASSETS DISCOVERED ON FACTORY BUS
            </div>
        `;
        return;
    }

    // Apply Filter
    const filtered = machineEntries.filter(([id, m]) => {
        const s = (m.state || '').toLowerCase();
        if (activeFilter === 'ATTENTION') {
            return s.includes('critical') || s.includes('warning') || s.includes('dropped') || s.includes('degrading');
        }
        if (activeFilter === 'LIVE') {
            return m.is_online === true;
        }
        if (activeFilter === 'DROPPED') {
            return s.includes('dropped');
        }
        return true;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12 text-[var(--pdm-text-muted)] font-mono text-xs">
                NO ASSETS MATCH CURRENT FILTER (${activeFilter})
            </div>
        `;
        return;
    }

    let html = '';
    for (const [id, m] of filtered) {
        const statusMeta = formatStatus(m.state, m.is_online);
        const rul = calculateRulDisplay(m);
        const readings = m.sensor_readings || {};
        const lastSeen = formatLastSeen(m.last_seen_seconds, m.telemetry_status);

        html += `
        <div class="bg-[var(--mv-surface-base)] border ${statusMeta.cardBorder} rounded-[3px] p-3 space-y-2.5 shadow-sm active:bg-[var(--mv-surface-raised)] transition-colors">
            <!-- Card Header: Machine ID, Type, Badge -->
            <div class="flex items-center justify-between">
                <div>
                    <div class="flex items-center gap-2">
                        <span class="font-mono font-bold text-sm tracking-wide text-[var(--mv-text-primary)]">${id}</span>
                        <span class="text-[9px] font-mono px-1.5 py-0.5 rounded-[2px] bg-[var(--mv-surface-sunken)] border border-[var(--mv-border-hairline)] text-[var(--mv-text-muted)] uppercase">
                            ${m.machine_type || 'ASSET'}
                        </span>
                    </div>
                    <div class="text-[10px] font-mono text-[var(--mv-text-muted)] mt-0.5">
                        LOC: ${m.location || 'MAIN FLOOR'}
                    </div>
                </div>
                <span class="font-mono text-[10px] font-bold px-2 py-0.5 rounded-[2px] ${statusMeta.badgeClass}">
                    ${statusMeta.text}
                </span>
            </div>

            <!-- RUL Gauge Instrumentation Bar -->
            <div class="space-y-1">
                <div class="flex items-center justify-between text-[10px] font-mono">
                    <span class="text-[var(--mv-text-muted)]">REMAINING USEFUL LIFE:</span>
                    <span class="font-bold ${statusMeta.rulTextClass}">${rul.label}</span>
                </div>
                <div class="h-1.5 w-full bg-[var(--mv-surface-sunken)] rounded-[2px] overflow-hidden flex border border-[var(--mv-border-hairline)]">
                    <div style="width: ${rul.fillPercent}%" class="h-full ${rul.barColor} transition-all duration-300"></div>
                </div>
            </div>

            <!-- Primary Telemetry Metrics Pill Grid -->
            <div class="grid grid-cols-3 gap-1.5 font-mono text-center">
                ${renderMetricTile('SPEED / RPM', readings.Speed || readings.RPM, 'rpm')}
                ${renderMetricTile('TEMP', readings.Temperature, '°C')}
                ${renderMetricTile('PRESSURE', readings.Pressure, 'bar')}
            </div>

            <!-- Edge Telemetry Watchdog Footnote -->
            <div class="pt-1 border-t border-[var(--mv-border-hairline)] flex items-center justify-between text-[9px] font-mono text-[var(--mv-text-muted)]">
                <span>SIGNAL: <strong class="${statusMeta.signalClass}">${lastSeen}</strong></span>
                <span>CHANNELS: ${Object.keys(readings).length} ACTIVE</span>
            </div>

            <!-- Mobile Quick Actions -->
            <div class="grid grid-cols-2 gap-2 pt-1">
                <button onclick="openDiagnosticDrawer('${id}')"
                    class="py-1.5 px-2 bg-[var(--mv-surface-sunken)] border border-[var(--mv-border-subtle)] hover:border-[var(--mv-accent-base)] text-[var(--mv-text-primary)] font-mono text-[10px] font-bold rounded-[2px] flex items-center justify-center gap-1 active:scale-98">
                    <svg class="w-3 h-3 text-[var(--mv-accent-base)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                    </svg>
                    DIAGNOSE
                </button>
                <button onclick="openWorkOrderModalFor('${id}')"
                    class="py-1.5 px-2 bg-[var(--mv-surface-raised)] border border-[var(--mv-border-subtle)] text-[var(--mv-text-secondary)] font-mono text-[10px] font-bold rounded-[2px] flex items-center justify-center gap-1 active:scale-98">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
                    </svg>
                    WORK ORDER
                </button>
            </div>
        </div>
        `;
    }

    container.innerHTML = html;
}

function renderMetricTile(label, val, unit) {
    const formatted = (val !== undefined && val !== null && !isNaN(val)) ? Number(val).toFixed(1) : '--';
    return `
    <div class="p-1.5 bg-[var(--pdm-surface-sunken)] border border-[var(--pdm-border-hairline)] rounded">
        <div class="text-[8px] text-[var(--pdm-text-muted)] uppercase tracking-wider">${label}</div>
        <div class="text-xs font-bold text-[var(--pdm-text-primary)] mt-0.5">${formatted} <span class="text-[8px] font-normal text-[var(--pdm-text-muted)]">${unit}</span></div>
    </div>
    `;
}

function formatStatus(rawState, isOnline) {
    const s = (rawState || '').toLowerCase();
    if (s.includes('critical')) {
        return {
            text: 'CRITICAL',
            badgeClass: 'bg-rose-950/80 text-rose-400 border border-rose-800',
            cardBorder: 'border-rose-900/80',
            rulTextClass: 'text-rose-400',
            signalClass: 'text-rose-400'
        };
    }
    if (s.includes('dropped')) {
        return {
            text: 'SIGNAL DROPPED',
            badgeClass: 'bg-rose-950/40 text-rose-300 border border-rose-800 border-dashed',
            cardBorder: 'border-rose-900/60',
            rulTextClass: 'text-rose-400',
            signalClass: 'text-rose-400'
        };
    }
    if (s.includes('warning') || s.includes('degrading')) {
        return {
            text: 'WARNING',
            badgeClass: 'bg-amber-950/80 text-amber-400 border border-amber-800',
            cardBorder: 'border-amber-900/80',
            rulTextClass: 'text-amber-400',
            signalClass: 'text-amber-400'
        };
    }
    if (s.includes('maintenance')) {
        return {
            text: 'SERVICING',
            badgeClass: 'bg-sky-950/80 text-sky-400 border border-sky-800',
            cardBorder: 'border-sky-900/60',
            rulTextClass: 'text-sky-400',
            signalClass: 'text-sky-400'
        };
    }
    if (s.includes('awaiting')) {
        return {
            text: 'AWAITING EDGE',
            badgeClass: 'bg-zinc-900 text-zinc-400 border border-zinc-700',
            cardBorder: 'border-[var(--pdm-border-subtle)]',
            rulTextClass: 'text-zinc-400',
            signalClass: 'text-zinc-400'
        };
    }
    return {
        text: 'NOMINAL',
        badgeClass: 'bg-emerald-950/80 text-emerald-400 border border-emerald-800',
        cardBorder: 'border-[var(--pdm-border-hairline)]',
        rulTextClass: 'text-emerald-400',
        signalClass: 'text-emerald-400'
    };
}

function calculateRulDisplay(machine) {
    const state = (machine.state || '').toLowerCase();
    if (state.includes('dropped')) {
        return { label: 'TELEMETRY OFFLINE', fillPercent: 0, barColor: 'bg-rose-600' };
    }
    if (state.includes('awaiting')) {
        return { label: 'NO TELEMETRY', fillPercent: 0, barColor: 'bg-zinc-600' };
    }
    if (state.includes('maintenance')) {
        return { label: 'UNDER REPAIR', fillPercent: 50, barColor: 'bg-sky-500' };
    }

    const ttf = machine.ttf_hours !== undefined ? machine.ttf_hours : machine.rul_prediction;
    if (ttf === null || ttf === undefined) {
        return { label: '> 168h (NOMINAL)', fillPercent: 100, barColor: 'bg-emerald-500' };
    }

    if (ttf <= 0.5) {
        return { label: `${Math.round(ttf * 60)}m (IMMINENT)`, fillPercent: 15, barColor: 'bg-rose-500' };
    }
    if (ttf <= 2.0) {
        return { label: `${ttf.toFixed(1)}h (CRITICAL)`, fillPercent: 35, barColor: 'bg-rose-500' };
    }
    if (ttf <= 24.0) {
        return { label: `${ttf.toFixed(1)}h (DEGRADING)`, fillPercent: 65, barColor: 'bg-amber-500' };
    }
    return { label: `${ttf.toFixed(0)}h (GOOD)`, fillPercent: 100, barColor: 'bg-emerald-500' };
}

function formatLastSeen(seconds, telemetryStatus) {
    if (telemetryStatus === 'AWAITING_TELEMETRY' || seconds === null || seconds === undefined) {
        return 'NO PACKETS';
    }
    if (seconds < 5) return 'JUST NOW (<2s)';
    if (seconds < 60) return `${Math.round(seconds)}s AGO`;
    return `${Math.round(seconds / 60)}m AGO`;
}

// Incidents Tab
function renderIncidentsList() {
    const container = document.getElementById('incidents-list');
    if (!container) return;

    const incidents = [];
    for (const [id, m] of Object.entries(latestPredictions)) {
        const s = (m.state || '').toLowerCase();
        if (s.includes('critical') || s.includes('dropped') || s.includes('warning') || s.includes('degrading')) {
            incidents.push({ id, ...m });
        }
    }

    if (incidents.length === 0) {
        container.innerHTML = `
            <div class="text-center py-10 bg-[var(--pdm-surface-base)] border border-[var(--pdm-border-hairline)] rounded p-4 font-mono text-xs text-[var(--pdm-text-muted)]">
                ✓ ALL FACTORY MACHINERY OPERATING NOMINALLY. ZERO ACTIVE ALARMS.
            </div>
        `;
        return;
    }

    let html = '';
    for (const inc of incidents) {
        const meta = formatStatus(inc.state, inc.is_online);
        html += `
        <div class="bg-[var(--pdm-surface-base)] border ${meta.cardBorder} rounded p-3 space-y-2 font-mono">
            <div class="flex items-center justify-between">
                <span class="font-display font-bold text-sm text-[var(--pdm-text-primary)]">${inc.id}</span>
                <span class="text-[9px] font-bold px-2 py-0.5 rounded ${meta.badgeClass}">${meta.text}</span>
            </div>
            <div class="text-xs text-[var(--pdm-text-secondary)] font-sans">
                ${inc.predicted_failure || inc.watchdog_message || 'Anomaly detected in high-frequency sensor telemetry.'}
            </div>
            <div class="flex items-center justify-between pt-1 border-t border-[var(--pdm-border-hairline)] text-[10px]">
                <span class="text-[var(--pdm-text-muted)]">SEVERITY: HIGH</span>
                <button onclick="openDiagnosticDrawer('${inc.id}')"
                    class="text-[var(--pdm-accent-base)] font-bold hover:underline">
                    INSPECT ROOT-CAUSE →
                </button>
            </div>
        </div>
        `;
    }

    container.innerHTML = html;
}

// Work Orders Tab
function renderWorkOrdersList() {
    const container = document.getElementById('workorders-list');
    if (!container) return;

    const maintenanceEvents = (latestEvents || []).filter(e => e.event_type === 'Maintenance');

    if (maintenanceEvents.length === 0) {
        container.innerHTML = `
            <div class="text-center py-10 bg-[var(--pdm-surface-base)] border border-[var(--pdm-border-hairline)] rounded p-4 font-mono text-xs text-[var(--pdm-text-muted)]">
                NO ACTIVE WORK ORDERS DISPATCHED.
            </div>
        `;
        return;
    }

    let html = '';
    for (const ev of maintenanceEvents) {
        html += `
        <div class="bg-[var(--pdm-surface-base)] border border-[var(--pdm-border-hairline)] rounded p-3 space-y-1 font-mono text-xs">
            <div class="flex items-center justify-between text-[10px]">
                <span class="font-bold text-[var(--pdm-accent-base)]">${ev.machine_id}</span>
                <span class="text-[var(--pdm-text-muted)]">${new Date(ev.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="text-[var(--pdm-text-primary)] text-xs font-sans">${ev.details}</div>
            <div class="text-[9px] text-[var(--pdm-status-normal)] pt-1">STATUS: IN PROGRESS / SCHEDULED</div>
        </div>
        `;
    }

    container.innerHTML = html;
}

// Mechatronic Diagnostic Drawer
let currentDiagnosticMachineId = null;

async function openDiagnosticDrawer(machineId) {
    currentDiagnosticMachineId = machineId;
    const m = latestPredictions[machineId] || {};

    const drawer = document.getElementById('mobile-diagnostic-drawer');
    const backdrop = document.getElementById('mobile-diagnostic-backdrop');
    if (!drawer || !backdrop) return;

    // Set Machine Header
    document.getElementById('drawer-machine-id').textContent = machineId;
    const badge = document.getElementById('drawer-status-badge');
    const meta = formatStatus(m.state, m.is_online);
    badge.textContent = meta.text;
    badge.className = `font-mono text-[9px] font-bold px-2 py-0.5 rounded ${meta.badgeClass}`;

    // Show loading state
    document.getElementById('drawer-severity').textContent = 'CALCULATING...';
    document.getElementById('drawer-root-cause').textContent = 'Querying Machivital Cognitive Diagnostic Engine...';
    document.getElementById('drawer-checklist').innerHTML = '<div class="text-[10px] text-[var(--pdm-text-muted)]">Generating physical inspection steps...</div>';
    document.getElementById('drawer-parts-list').innerHTML = '';

    // Animate open
    drawer.classList.remove('drawer-closed');
    drawer.classList.add('drawer-open');
    backdrop.classList.remove('pointer-events-none');
    backdrop.classList.add('opacity-100');

    // Trigger AI Diagnostic API
    try {
        const res = await fetch('/api/ai-diagnostics', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                machine_id: machineId,
                readings: m.sensor_readings || {},
                state: m.state || 'Normal',
                machine_type: m.machine_type || 'FILLING'
            })
        });

        if (!res.ok) throw new Error('Diagnostic query failed');
        const data = await res.json();
        const diag = data.diagnosis || {};

        document.getElementById('drawer-severity').textContent = diag.severity || (m.state === 'Critical Failure Imminent' ? 'CRITICAL' : 'WARNING');
        document.getElementById('drawer-root-cause').textContent = diag.physical_root_cause || m.predicted_failure || 'Mechanical bearing cage micro-fracture induced by excessive radial load.';

        // Checklist
        const actions = diag.immediate_actions || m.rca_steps || [
            'Isolate drive motor and lock-out electrical circuit',
            'Inspect radial bearing play with dial indicator (< 0.05mm)',
            'Check lubricant viscosity and thermal discoloration',
            'Verify shaft alignment with laser tool'
        ];

        let checklistHtml = '';
        actions.forEach((act, idx) => {
            checklistHtml += `
            <label class="flex items-start gap-2 bg-[var(--pdm-surface-base)] p-2 rounded border border-[var(--pdm-border-hairline)] text-[11px] text-[var(--pdm-text-primary)]">
                <input type="checkbox" onchange="handleChecklistTap(this)" class="mt-0.5 rounded accent-[var(--pdm-accent-base)]">
                <span>${act}</span>
            </label>
            `;
        });
        document.getElementById('drawer-checklist').innerHTML = checklistHtml;

        // Recommended Parts
        const parts = diag.replacement_parts || ['Deep Groove Radial Bearings (6205-2RSH)', 'PTFE Rotary Shaft Seal (35x52x7)'];
        let partsHtml = '';
        parts.forEach(p => {
            partsHtml += `<span class="px-2 py-0.5 bg-[var(--pdm-surface-raised)] border border-[var(--pdm-border-subtle)] rounded text-[10px] text-[var(--pdm-text-secondary)]">${p}</span>`;
        });
        document.getElementById('drawer-parts-list').innerHTML = partsHtml;

    } catch (err) {
        console.warn('AI Diagnostic error:', err);
        document.getElementById('drawer-severity').textContent = 'OFFLINE HEURISTIC';
        document.getElementById('drawer-root-cause').textContent = m.watchdog_message || m.predicted_failure || 'High-frequency telemetry breach detected on primary drive axis.';
    }
}

function handleChecklistTap(cb) {
    if (hapticsEnabled && navigator.vibrate) {
        navigator.vibrate(40);
    }
}

function closeDiagnosticDrawer() {
    const drawer = document.getElementById('mobile-diagnostic-drawer');
    const backdrop = document.getElementById('mobile-diagnostic-backdrop');
    if (!drawer || !backdrop) return;

    drawer.classList.add('drawer-closed');
    drawer.classList.remove('drawer-open');
    backdrop.classList.add('pointer-events-none');
    backdrop.classList.remove('opacity-100');
}

// Work Order Modal
function openWorkOrderFromDrawer() {
    closeDiagnosticDrawer();
    openWorkOrderModalFor(currentDiagnosticMachineId);
}

function openWorkOrderModalFor(machineId) {
    const modal = document.getElementById('mobile-workorder-modal');
    if (!modal) return;
    document.getElementById('wo-target-machine').value = machineId || 'FILLING_001';
    modal.classList.remove('hidden');
}

function openManualWorkOrderModal() {
    const firstMachine = Object.keys(latestPredictions)[0] || 'FILLING_001';
    openWorkOrderModalFor(firstMachine);
}

function closeWorkOrderModal() {
    const modal = document.getElementById('mobile-workorder-modal');
    if (modal) modal.classList.add('hidden');
}

async function submitWorkOrder() {
    const machineId = document.getElementById('wo-target-machine').value;
    const duration = parseInt(document.getElementById('wo-duration').value, 10) || 30;
    const btn = document.getElementById('wo-submit-btn');

    const selectedParts = [];
    document.querySelectorAll('#wo-parts-selector input:checked').forEach(el => {
        selectedParts.push(el.value);
    });

    btn.disabled = true;
    btn.textContent = 'SCHEDULING SERVICE...';

    try {
        const res = await fetch('/api/request-maintenance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                machine_id: machineId,
                parts: selectedParts,
                estimated_duration: duration
            })
        });

        if (!res.ok) throw new Error('Service dispatch failed');

        if (hapticsEnabled && navigator.vibrate) {
            navigator.vibrate([100, 50, 100]);
        }

        closeWorkOrderModal();
        fetchFleetState();
        switchTab('WORKORDERS');

    } catch (err) {
        alert('Failed to dispatch work order: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'CONFIRM & SCHEDULE SERVICE';
    }
}

// Gateway Profile Initializer
function initGatewayProfiles() {
    const urlEl = document.getElementById('gw-url-display');
    if (urlEl) {
        urlEl.textContent = `${window.location.origin}/api/ingest`;
    }
}

async function sendMobileIngestTest() {
    const btn = document.getElementById('mobile-test-burst-btn');
    const out = document.getElementById('mobile-burst-result');
    btn.disabled = true;
    btn.textContent = 'TRANSMITTING...';
    out.textContent = '';

    try {
        const payload = {
            machine_id: 'FILLING_001',
            readings: {
                Speed: 1450 + Math.random() * 20,
                Temperature: 64.2 + Math.random() * 2,
                Pressure: 4.1 + Math.random() * 0.2,
                Vibration: 0.38 + Math.random() * 0.05
            }
        };

        const res = await fetch('/api/ingest', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': 'dev-api-key'
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        out.textContent = `✓ Ingest ACK 200 OK — ${JSON.stringify(data.readings || data.status)}`;
        out.className = 'text-[10px] font-mono text-[var(--pdm-status-normal)] font-bold';

        // Refresh immediately to show Live state
        fetchFleetState();

    } catch (err) {
        out.textContent = `✗ Transmission Error: ${err.message}`;
        out.className = 'text-[10px] font-mono text-[var(--pdm-status-critical)] font-bold';
    } finally {
        btn.disabled = false;
        btn.textContent = 'TRANSMIT TEST EDGE PACKET (FILLING_001)';
    }
}
