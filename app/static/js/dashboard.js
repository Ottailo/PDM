// Predictive Maintenance Console Master Client Logic
// Strictly adhering to DESIGN.md (OPERATE surface mode) and PRODUCT.md contracts

console.log("--- PDM TELEMETRY CONSOLE INITIALIZED ---");

const machineGrid = document.getElementById('machine-grid');
const lastUpdatedEl = document.getElementById('last-updated');
const ttfListEl = document.getElementById('ttf-list');
const historyModalOverlay = document.getElementById('history-modal-overlay');
const historyModalTitle = document.getElementById('history-modal-title');
const historyModalClose = document.getElementById('history-modal-close');
const historyTimeRanges = document.getElementById('history-time-ranges');
const historyChartCanvas = document.getElementById('history-chart');
const kpiOnlineEl = document.getElementById('kpi-online');
const kpiAlertsEl = document.getElementById('kpi-alerts');
const tabWatchlist = document.getElementById('tab-watchlist');
const tabLog = document.getElementById('tab-log');
const watchlistPanel = document.getElementById('watchlist-panel');
const logPanel = document.getElementById('log-panel');
const eventLogListEl = document.getElementById('event-log-list');
const mainWatchlistBody = document.getElementById('main-watchlist-body');
const mainEventLogList = document.getElementById('main-event-log-list');

const API_ENDPOINT = '/api/latest-states';
const UPDATE_INTERVAL = 2000;

const charts = {};
let historyChart = null;
let lastDashboardData = null;

// DIN-Caliber Chart.js Global Instrumentation Defaults
Chart.defaults.color = '#8A95A5';
Chart.defaults.borderColor = 'rgba(56, 68, 86, 0.4)';
Chart.defaults.backgroundColor = 'transparent';
Chart.defaults.font.family = 'JetBrains Mono, monospace';
Chart.defaults.font.size = 10;

// ============================================================================
// MAINTENANCE & SERVICING PROTOCOL
// ============================================================================

async function performMaintenance(machineId, preSelectedParts = []) {
    console.log('[MAINTENANCE] Initiating service protocol for:', machineId, preSelectedParts);
    showPartSelectionDialog(machineId, preSelectedParts);
}

function showPartSelectionDialog(machineId, preSelectedParts = []) {
    const machineType = machineId.split('_')[0];

    const serviceableParts = {
        'FILLING': [
            { name: 'Nozzle Assembly', time: 30, description: 'Clean or replace filling nozzles' },
            { name: 'Pump System', time: 45, description: 'Service positive displacement pump & seals' },
            { name: 'Fill Volume Sensor', time: 15, description: 'Recalibrate opto-electronic volume sensor' },
            { name: 'Vibration Sensor', time: 10, description: 'Inspect piezo-electric accelerometer mounting' },
            { name: 'General Maintenance', time: 60, description: 'Full mechanical system inspection' }
        ],
        'SHRINK': [
            { name: 'Heating Elements', time: 40, description: 'Inspect resistance heating banks & PID loops' },
            { name: 'Conveyor Belt', time: 35, description: 'Tension & track mesh conveyor belt' },
            { name: 'Temperature Sensor', time: 20, description: 'Calibrate thermocouple probe array' },
            { name: 'Humidity Control', time: 25, description: 'Inspect exhaust blowers & RH sensors' },
            { name: 'General Maintenance', time: 70, description: 'Full thermal tunnel inspection' }
        ],
        'PILLOW': [
            { name: 'Sealing Jaws', time: 50, description: 'Lap sealing faces & replace heating cartridges' },
            { name: 'Pressure System', time: 30, description: 'Pneumatic cylinder & regulator overhaul' },
            { name: 'Alignment Mechanism', time: 40, description: 'Calibrate optical eye-mark registration' },
            { name: 'Temperature Control', time: 25, description: 'Calibrate rotary seal bar thermocouple' },
            { name: 'General Maintenance', time: 65, description: 'Full packaging head inspection' }
        ],
        'BOXING': [
            { name: 'Pneumatic System', time: 35, description: 'Service main compressor lines & vacuum cups' },
            { name: 'Conveyor Belt', time: 30, description: 'Replace drive rollers & belt tensioners' },
            { name: 'Box Feed Mechanism', time: 45, description: 'Service cartoner pick-and-place magazine' },
            { name: 'Pressure Sensors', time: 15, description: 'Calibrate pneumatic pressure transducer' },
            { name: 'General Maintenance', time: 60, description: 'Full case packer inspection' }
        ]
    };

    const parts = serviceableParts[machineType] || serviceableParts['FILLING'];

    const modalHTML = `
        <div id="part-selection-modal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 pdm-modal-backdrop">
            <div class="w-full max-w-xl bg-[var(--pdm-surface-overlay)] rounded-[var(--pdm-radius-md)] shadow-[var(--pdm-shadow-overlay)] border border-[var(--pdm-border-subtle)] flex flex-col overflow-hidden pdm-modal-dialog">
                <!-- Header Strip -->
                <div class="px-5 py-3.5 border-b border-[var(--pdm-border-hairline)] bg-[var(--pdm-surface-raised)] flex justify-between items-center">
                    <div class="flex items-center gap-2.5">
                        <span class="w-2 h-2 rounded-full bg-[var(--pdm-accent-base)]"></span>
                        <h2 class="font-display font-semibold text-xs tracking-wider uppercase text-[var(--pdm-text-primary)]">
                            SERVICE DISPATCH: ${machineId.replace(/_/g, ' ')}
                        </h2>
                    </div>
                    <button id="part-selection-close" class="pdm-btn py-1 px-2 h-7 bg-transparent border-transparent hover:border-[var(--pdm-border-subtle)] text-[var(--pdm-text-muted)] hover:text-[var(--pdm-text-primary)]" title="Close Dialog">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>

                <!-- Subtitle -->
                <div class="px-5 py-2 bg-[var(--pdm-surface-sunken)] border-b border-[var(--pdm-border-hairline)]">
                    <p class="text-[11px] font-mono text-[var(--pdm-text-secondary)]">SELECT TARGET SUBSYSTEMS FOR PREVENTIVE INTERVENTION:</p>
                </div>

                <!-- Parts List -->
                <div class="p-4 space-y-2 max-h-80 overflow-y-auto bg-[var(--pdm-surface-base)]">
                    ${parts.map((part, index) => `
                        <div class="part-option bg-[var(--pdm-surface-sunken)] hover:bg-[var(--pdm-surface-raised)] rounded-[var(--pdm-radius-sm)] p-3 border border-[var(--pdm-border-hairline)] hover:border-[var(--pdm-border-subtle)] transition-colors cursor-pointer flex items-center justify-between gap-3" data-part="${part.name}" data-time="${part.time}">
                            <div class="flex items-start gap-3">
                                <input type="checkbox" id="part-${index}" class="mt-0.5 accent-[var(--pdm-accent-base)] w-4 h-4 cursor-pointer">
                                <div>
                                    <h3 class="font-display font-semibold text-xs tracking-wide text-[var(--pdm-text-primary)] uppercase">${part.name}</h3>
                                    <p class="text-[11px] text-[var(--pdm-text-secondary)] font-body">${part.description}</p>
                                </div>
                            </div>
                            <span class="text-[11px] font-mono font-medium text-[var(--pdm-accent-base)] whitespace-nowrap">${part.time}m</span>
                        </div>
                    `).join('')}
                </div>

                <!-- Footer Strip -->
                <div class="px-5 py-3 border-t border-[var(--pdm-border-hairline)] bg-[var(--pdm-surface-sunken)] flex justify-between items-center">
                    <div class="text-xs font-mono text-[var(--pdm-text-muted)] space-x-3">
                        <span>SELECTED: <strong id="selected-count" class="text-[var(--pdm-text-primary)]">0</strong></span>
                        <span>|</span>
                        <span>EST DURATION: <strong id="total-time" class="text-[var(--pdm-text-primary)]">0</strong> MIN</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <button id="cancel-service" class="pdm-btn text-xs py-1.5 px-3 h-8 bg-transparent border-[var(--pdm-border-hairline)] hover:border-[var(--pdm-border-subtle)] text-[var(--pdm-text-secondary)]">CANCEL</button>
                        <button id="confirm-service" class="pdm-btn pdm-btn-primary text-xs py-1.5 px-3 h-8 opacity-50 cursor-not-allowed" disabled>DISPATCH SERVICE</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    setupPartSelectionEvents(machineId, preSelectedParts);
}

function setupPartSelectionEvents(machineId, preSelectedParts = []) {
    const modal = document.getElementById('part-selection-modal');
    const closeBtn = document.getElementById('part-selection-close');
    const cancelBtn = document.getElementById('cancel-service');
    const confirmBtn = document.getElementById('confirm-service');
    const selectedCountEl = document.getElementById('selected-count');
    const totalTimeEl = document.getElementById('total-time');

    let selectedParts = [];

    const closeModal = () => {
        if (modal) modal.remove();
    };

    const updateSelection = () => {
        selectedCountEl.textContent = selectedParts.length;
        const totalTime = selectedParts.reduce((sum, part) => sum + part.time, 0);
        totalTimeEl.textContent = totalTime;
        const hasSelection = selectedParts.length > 0;
        confirmBtn.disabled = !hasSelection;
        confirmBtn.classList.toggle('opacity-50', !hasSelection);
        confirmBtn.classList.toggle('cursor-not-allowed', !hasSelection);
    };

    document.querySelectorAll('.part-option').forEach(option => {
        const checkbox = option.querySelector('input[type="checkbox"]');

        option.addEventListener('click', (e) => {
            if (e.target !== checkbox) {
                checkbox.checked = !checkbox.checked;
            }

            const partName = option.dataset.part;
            const partTime = parseInt(option.dataset.time, 10);

            if (checkbox.checked) {
                selectedParts.push({ name: partName, time: partTime });
                option.classList.add('border-[var(--pdm-accent-base)]');
            } else {
                selectedParts = selectedParts.filter(p => p.name !== partName);
                option.classList.remove('border-[var(--pdm-accent-base)]');
            }

            updateSelection();
        });
    });

    // Auto-select parts recommended by AI Diagnostic Advisor if provided
    if (Array.isArray(preSelectedParts) && preSelectedParts.length > 0) {
        document.querySelectorAll('.part-option').forEach(option => {
            const partName = option.dataset.part;
            const partTime = parseInt(option.dataset.time, 10);
            const checkbox = option.querySelector('input[type="checkbox"]');

            const isMatch = preSelectedParts.some(p => 
                typeof p === 'string' && (
                    p.toLowerCase().includes(partName.toLowerCase()) || 
                    partName.toLowerCase().includes(p.toLowerCase()) ||
                    (partName.includes(' ') && p.toLowerCase().includes(partName.split(' ')[0].toLowerCase()))
                )
            );

            if (isMatch) {
                checkbox.checked = true;
                selectedParts.push({ name: partName, time: partTime });
                option.classList.add('border-[var(--pdm-accent-base)]');
            }
        });
        updateSelection();
    }

    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    confirmBtn.addEventListener('click', async () => {
        try {
            const totalTime = selectedParts.reduce((sum, part) => sum + part.time, 0);
            const partNames = selectedParts.map(p => p.name);

            const response = await fetch('/api/request-maintenance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    machine_id: machineId,
                    parts: partNames,
                    estimated_duration: totalTime
                })
            });

            if (response.ok) {
                showNotification(`Service scheduled for ${machineId.replace(/_/g, ' ')} (${totalTime}m)`, 'success');
                closeModal();
                fetchDashboardData();
                updateMachineToServiceState(machineId, partNames, totalTime);
            } else {
                throw new Error('Service dispatch rejected by controller');
            }
        } catch (error) {
            console.error('Maintenance request error:', error);
            showNotification('Service Request Failed: Network or controller error', 'error');
        }
    });
}

function updateMachineToServiceState(machineId, parts, duration) {
    const cardContainer = document.getElementById(machineId);
    if (cardContainer) {
        cardContainer.setAttribute('data-status', 'UNDER_MAINTENANCE');
        const statusBadge = cardContainer.querySelector('.status-badge-tech');
        if (statusBadge) {
            statusBadge.textContent = 'SERVICING';
            statusBadge.className = 'status-badge-tech pdm-badge pdm-badge-offline';
        }

        const sensorReadingsEl = cardContainer.querySelector('.sensor-readings');
        if (sensorReadingsEl) {
            sensorReadingsEl.innerHTML = `
                <div class="text-center font-mono text-xs text-[var(--pdm-text-muted)] py-3">
                    SERVICING TARGET: <span class="text-[var(--pdm-accent-base)] font-bold">${parts.join(', ')}</span>
                </div>
            `;
        }

        const maintenanceDuration = duration * 60 * 1000;

        setTimeout(() => {
            if (statusBadge) {
                statusBadge.textContent = 'NOMINAL';
                statusBadge.className = 'status-badge-tech pdm-badge pdm-badge-normal';
            }

            if (sensorReadingsEl) {
                sensorReadingsEl.innerHTML = `
                    <div class="text-center font-mono text-xs text-[var(--pdm-status-normal)] py-3">
                        SERVICE CYCLE COMPLETE: ${parts.join(', ')}
                    </div>
                `;
            }

            setTimeout(() => {
                fetchDashboardData();
            }, 3000);
        }, maintenanceDuration);
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const borderClass = type === 'success' ? 'border-[var(--pdm-status-normal)]' :
        type === 'error' ? 'border-[var(--pdm-status-critical)]' :
            'border-[var(--pdm-accent-base)]';

    const dotClass = type === 'success' ? 'bg-[var(--pdm-status-normal)]' :
        type === 'error' ? 'bg-[var(--pdm-status-critical)]' :
            'bg-[var(--pdm-accent-base)]';

    notification.className = `fixed top-4 right-4 z-50 p-3 bg-[var(--pdm-surface-overlay)] border ${borderClass} rounded-[var(--pdm-radius-sm)] shadow-[var(--pdm-shadow-overlay)] max-w-sm text-xs font-mono transition-opacity duration-200`;

    notification.innerHTML = `
        <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full ${dotClass} flex-shrink-0"></span>
            <span class="text-[var(--pdm-text-primary)]">${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 200);
    }, 4000);
}

// ============================================================================
// SIGNATURE ELEMENT: LINEAR MULTI-ZONE RUL INSTRUMENTATION GAUGE
// ============================================================================

function updateRulGauge(cardContainer, rulPrediction, isOperational) {
    const rulValEl = cardContainer.querySelector('.machine-rul-value');
    const rulFillEl = cardContainer.querySelector('.pdm-rul-fill');
    const rulFooterEl = cardContainer.querySelector('.machine-rul-footer');

    if (!isOperational) {
        if (rulValEl) {
            rulValEl.textContent = 'OFFLINE';
            rulValEl.className = 'machine-rul-value font-mono font-bold text-xs text-[var(--pdm-status-offline)]';
        }
        if (rulFooterEl) rulFooterEl.textContent = 'RUL: --';
        if (rulFillEl) {
            rulFillEl.style.width = '0%';
            rulFillEl.className = 'pdm-rul-fill offline';
        }
        return;
    }

    const rulHours = parseFloat(rulPrediction);
    if (isNaN(rulHours) || rulHours < 0) {
        if (rulValEl) {
            rulValEl.textContent = '--';
            rulValEl.className = 'machine-rul-value font-mono font-bold text-xs text-[var(--pdm-text-primary)]';
        }
        if (rulFooterEl) rulFooterEl.textContent = 'RUL: --';
        if (rulFillEl) {
            rulFillEl.style.width = '100%';
            rulFillEl.className = 'pdm-rul-fill normal';
        }
        return;
    }

    let pct = 0;
    let zoneClass = 'normal';

    if (rulHours <= 0.5) {
        // Critical: 0 - 30 minutes (0 to 0.5 hours) mapped to 0% - 25% of bar
        pct = Math.max(3, (rulHours / 0.5) * 25);
        zoneClass = 'critical';
    } else if (rulHours <= 2.0) {
        // Warning: 30 - 120 minutes (0.5 to 2.0 hours) mapped to 25% - 50% of bar
        pct = 25 + ((rulHours - 0.5) / 1.5) * 25;
        zoneClass = 'warning';
    } else {
        // Normal: > 120 minutes (> 2.0 hours) mapped to 50% - 100% of bar
        pct = 50 + Math.min(50, ((rulHours - 2.0) / 6.0) * 50);
        zoneClass = 'normal';
    }

    // High-precision display label
    const totalMinutes = Math.round(rulHours * 60);
    let displayString = '';
    if (totalMinutes < 60) {
        displayString = `${totalMinutes}m`;
    } else {
        const h = Math.floor(totalMinutes / 60);
        const m = totalMinutes % 60;
        displayString = m > 0 ? `${h}h ${m}m` : `${h}h`;
    }

    if (rulValEl) {
        rulValEl.textContent = displayString;
        rulValEl.className = `machine-rul-value font-mono font-bold text-xs ${
            zoneClass === 'critical' ? 'text-[var(--pdm-status-critical)]' :
            zoneClass === 'warning' ? 'text-[var(--pdm-status-warning)]' :
            'text-[var(--pdm-status-normal)]'
        }`;
    }

    if (rulFooterEl) {
        rulFooterEl.textContent = `RUL: ${displayString}`;
    }

    if (rulFillEl) {
        rulFillEl.style.width = `${pct.toFixed(1)}%`;
        rulFillEl.className = `pdm-rul-fill ${zoneClass}`;
    }
}

// ============================================================================
// STATUS & TELEMETRY MAPPING
// ============================================================================

function getStatusInfo(state) {
    if (!state) return { text: 'OFFLINE', badgeClass: 'pdm-badge-offline', statusKey: 'OFFLINE' };
    const s = state.toLowerCase().replace(/ /g, '_');
    const map = {
        'normal': { text: 'NOMINAL', badgeClass: 'pdm-badge-normal', statusKey: 'NORMAL' },
        'warning': { text: 'WARNING', badgeClass: 'pdm-badge-warning', statusKey: 'WARNING' },
        'degrading': { text: 'DEGRADING', badgeClass: 'pdm-badge-warning', statusKey: 'WARNING' },
        'critical_failure_imminent': { text: 'CRITICAL', badgeClass: 'pdm-badge-critical', statusKey: 'CRITICAL' },
        'critical': { text: 'CRITICAL', badgeClass: 'pdm-badge-critical', statusKey: 'CRITICAL' },
        'signal_dropped': { text: 'SIGNAL DROPPED', badgeClass: 'pdm-badge-critical', statusKey: 'SIGNAL_DROPPED' },
        'communication_lost': { text: 'COMM LOST', badgeClass: 'pdm-badge-critical', statusKey: 'SIGNAL_DROPPED' },
        'awaiting_telemetry': { text: 'AWAITING EDGE', badgeClass: 'pdm-badge-offline', statusKey: 'AWAITING_TELEMETRY' },
        'calibrating': { text: 'CALIBRATING', badgeClass: 'pdm-badge-accent', statusKey: 'CALIBRATING' },
        'maintenance': { text: 'SERVICING', badgeClass: 'pdm-badge-offline', statusKey: 'UNDER_MAINTENANCE' },
        'scheduled_maintenance': { text: 'MAINTENANCE', badgeClass: 'pdm-badge-offline', statusKey: 'UNDER_MAINTENANCE' },
        'off': { text: 'OFFLINE', badgeClass: 'pdm-badge-offline', statusKey: 'OFFLINE' }
    };
    return map[s] || { text: state.toUpperCase(), badgeClass: 'pdm-badge-normal', statusKey: 'NORMAL' };
}

function getSensorUnit(sensorId, machineData) {
    if (!machineData || !machineData.sensor_info) return '';
    if (machineData.sensor_info[sensorId]) return machineData.sensor_info[sensorId].unit;
    const spaced = sensorId.replace(/_/g, ' ');
    if (machineData.sensor_info[spaced]) return machineData.sensor_info[spaced].unit;
    for (const key of Object.keys(machineData.sensor_info)) {
        if (key.endsWith('_' + sensorId) || key.endsWith(' ' + spaced)) {
            return machineData.sensor_info[key].unit;
        }
    }
    return '';
}

function getFailureType(machineData) {
    if (!machineData || !machineData.sensor_readings) {
        return 'NO SENSOR TELEMETRY';
    }

    const machineType = machineData.machine_type || "Unknown";
    const sensorData = machineData.sensor_readings;
    const health = machineData.health_score || 1.0;
    const anomaly = machineData.anomaly_detected || false;

    const sensorFailures = [];
    Object.entries(sensorData).forEach(([sensorId, value]) => {
        const sensorName = sensorId;
        if (machineType === 'FILLING') {
            if (sensorName === 'Fill_Volume_Sensor' && value < 99.0) sensorFailures.push('Nozzle Clog');
            else if (sensorName === 'Nozzle_Pressure' && value > 2.3) sensorFailures.push('Pump Pressure Fault');
            else if (sensorName === 'Vibration' && value > 0.8) sensorFailures.push('Bearing Wear');
        } else if (machineType === 'SHRINK') {
            if (sensorName === 'Tunnel_Temperature' && value < 175.0) sensorFailures.push('Heater Failure');
            else if (sensorName === 'Conveyor_Speed' && value < 14.5) sensorFailures.push('Conveyor Jam');
            else if (sensorName === 'Humidity' && value > 45.0) sensorFailures.push('Humidity Sensor Fault');
        } else if (machineType === 'PILLOW') {
            if (sensorName === 'Sealing_Jaw_Temperature' && value < 157.0) sensorFailures.push('Seal Heater Failure');
            else if (sensorName === 'Sealing_Jaw_Pressure' && value < 4.5) sensorFailures.push('Pressure Drop');
            else if (sensorName === 'Alignment_Error' && value > 0.15) sensorFailures.push('Alignment Error');
        } else if (machineType === 'BOXING') {
            if (sensorName === 'Box_Pressure_Sensor' && value < 4.5) sensorFailures.push('Pneumatic Leak');
            else if (sensorName === 'Conveyor_Speed_Sensor' && value < 16.0) sensorFailures.push('Box Jam');
            else if (sensorName === 'Box_Count_Sensor' && value < 110.0) sensorFailures.push('Feed Mechanism Fault');
        }
    });

    if (sensorFailures.length > 0) return sensorFailures[0];

    if (machineData.predicted_failure && machineData.predicted_failure !== 'Unknown') {
        return machineData.predicted_failure;
    }

    if (machineData.state === 'Degrading' || health < 0.7 || anomaly) {
        const predictedFailures = {
            'FILLING': ['Nozzle Clog', 'Pump Wear', 'Seal Deterioration'][Math.floor(Date.now() / 60000) % 3],
            'SHRINK': ['Heater Element Degradation', 'Temperature Sensor Drift', 'Insulation Failure'][Math.floor(Date.now() / 60000) % 3],
            'PILLOW': ['Seal Heater Wear', 'Pressure Regulator Drift', 'Jaw Misalignment'][Math.floor(Date.now() / 60000) % 3],
            'BOXING': ['Pneumatic Seal Wear', 'Conveyor Belt Stretch', 'Sensor Calibration Drift'][Math.floor(Date.now() / 60000) % 3]
        };
        return predictedFailures[machineType] || 'COMPONENT WEAR DETECTED';
    }

    return 'SYSTEM OPERATING NOMINALLY';
}

// ============================================================================
// MACHINE CARD FACTORY
// ============================================================================

function createMachineCard(machineId) {
    const cardContainer = document.createElement('div');
    cardContainer.id = machineId;
    cardContainer.className = 'machine-card h-full';

    cardContainer.innerHTML = `
        <div class="tech-card pdm-machine-card h-full flex flex-col card">
            <!-- Card Header Strip -->
            <div class="p-3 border-b border-[var(--pdm-border-hairline)] flex justify-between items-center bg-[var(--pdm-surface-raised)]">
                <div class="flex items-center gap-2 min-w-0">
                    <span class="w-1.5 h-3.5 bg-[var(--pdm-accent-base)] rounded-[1px] flex-shrink-0"></span>
                    <h3 class="font-display font-semibold text-xs tracking-wider uppercase text-[var(--pdm-text-primary)] truncate">
                        ${machineId.replace(/_/g, ' ')}
                    </h3>
                </div>
                <span class="status-badge-tech pdm-badge pdm-badge-normal">NOMINAL</span>
            </div>

            <!-- Card Body -->
            <div class="p-3.5 flex-grow flex flex-col space-y-3">
                <!-- Signature Element: Linear Multi-Zone RUL Instrumentation Gauge -->
                <div class="pdm-rul-container space-y-1">
                    <div class="flex items-center justify-between text-[10px] font-mono text-[var(--pdm-text-muted)]">
                        <span class="tracking-wider">REMAINING USEFUL LIFE:</span>
                        <span class="machine-rul-value font-mono font-bold text-xs text-[var(--pdm-text-primary)]" style="font-variant-numeric: tabular-nums;">--</span>
                    </div>
                    <div class="pdm-rul-gauge" title="RUL Gauge: Critical (0-30m) | Warning (30-120m) | Normal (>120m)">
                        <div class="pdm-rul-track">
                            <div class="pdm-rul-tick-warning" title="Warning Threshold (30m)"></div>
                            <div class="pdm-rul-tick-normal" title="Normal Threshold (120m)"></div>
                            <div class="pdm-rul-fill normal" style="width: 100%;"></div>
                        </div>
                    </div>
                    <div class="flex items-center justify-between text-[9px] font-mono text-[var(--pdm-text-muted)] opacity-60">
                        <span>0m (TRIP)</span>
                        <span>30m</span>
                        <span>120m</span>
                        <span>&gt;120m</span>
                    </div>
                </div>

                <!-- High-Density Telemetry Readings -->
                <div class="sensor-readings space-y-1 my-1"></div>

                <div class="no-data-indicator hidden text-center py-6">
                    <div class="text-xs font-mono font-bold tracking-wider text-[var(--pdm-text-muted)] uppercase mb-1">NO TELEMETRY SIGNAL</div>
                    <p class="text-[10px] text-[var(--pdm-text-muted)] font-mono uppercase">Data Stream Inactive</p>
                </div>

                <!-- Integrated Hairline Ribbon Telemetry Sparkline -->
                <div class="chart-container mt-auto h-28 relative bg-[var(--pdm-surface-sunken)] rounded-[var(--pdm-radius-sm)] border border-[var(--pdm-border-hairline)] p-1">
                    <canvas id="chart-${machineId}"></canvas>
                </div>

                <!-- Card Footer Control Strip -->
                <div class="card-footer pt-2.5 border-t border-[var(--pdm-border-hairline)] flex items-center justify-between">
                    <div class="flex items-center gap-2 text-[11px] font-mono text-[var(--pdm-text-muted)]">
                        <span class="machine-health-val" style="font-variant-numeric: tabular-nums;">H: --%</span>
                        <span>|</span>
                        <span class="machine-rul-footer" style="font-variant-numeric: tabular-nums;">RUL: --</span>
                    </div>
                    <div class="flex items-center gap-1.5">
                        <button data-action="connect" data-machine-id="${machineId}" class="pdm-btn text-[10px] py-1 px-2 h-7 bg-[var(--pdm-surface-raised)] border-[var(--pdm-border-subtle)] text-[var(--pdm-text-secondary)] hover:text-[var(--pdm-text-primary)]" title="Connect Physical Machine Gateway">
                            GATEWAY
                        </button>
                        <button data-action="diagnose" data-machine-id="${machineId}" class="pdm-btn text-[10px] py-1 px-2 h-7 border-[var(--pdm-accent-base)] text-[var(--pdm-accent-base)] hover:bg-[var(--pdm-accent-subtle)]" title="Autonomous AI Diagnostic Advisor">
                            <span class="inline-block w-1.5 h-1.5 rounded-full bg-[var(--pdm-accent-base)] animate-pulse mr-1"></span>ADVISOR
                        </button>
                        <button data-action="history" data-machine-id="${machineId}" class="pdm-btn text-[10px] py-1 px-2 h-7 bg-[var(--pdm-surface-raised)] border-[var(--pdm-border-subtle)] text-[var(--pdm-text-secondary)] hover:text-[var(--pdm-text-primary)]" title="Inspect Sensor History">
                            HISTORY
                        </button>
                        <button data-action="service" data-machine-id="${machineId}" class="pdm-btn pdm-btn-primary text-[10px] py-1 px-2 h-7" title="Request Mechanical Service">
                            SERVICE
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    machineGrid.appendChild(cardContainer);

    const chartElement = document.getElementById(`chart-${machineId}`);
    const ctx = chartElement.getContext('2d');
    charts[machineId] = new Chart(ctx, {
        type: 'line',
        data: { labels: [], datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    display: true,
                    ticks: {
                        font: { size: 9, family: 'JetBrains Mono' },
                        color: '#8A95A5',
                        maxTicksLimit: 4
                    },
                    grid: { color: 'rgba(56, 68, 86, 0.25)' }
                },
                x: { display: false }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    enabled: true,
                    backgroundColor: 'rgba(24, 29, 38, 0.95)',
                    borderColor: 'rgba(56, 68, 86, 0.8)',
                    borderWidth: 1,
                    titleFont: { family: 'Chakra Petch', size: 10 },
                    bodyFont: { family: 'JetBrains Mono', size: 9 }
                }
            },
            animation: { duration: 0 } // Zero bouncy physics on 2000ms polling cycle
        }
    });
}

// ============================================================================
// KPI & SIDEBAR SURVEILLANCE
// ============================================================================

function updateKpis(kpis) {
    if (!kpis) return;
    if (kpiOnlineEl) kpiOnlineEl.textContent = `${kpis.machines_online} / ${kpis.total_machines}`;
    if (kpiAlertsEl) kpiAlertsEl.textContent = kpis.active_alerts;
}

function updateEventLog(events) {
    if (!events) return;

    const logHtml = events.map(event => `
        <li class="p-2.5 bg-[var(--pdm-surface-base)] rounded-[var(--pdm-radius-sm)] border border-[var(--pdm-border-hairline)] hover:border-[var(--pdm-border-subtle)] transition-colors">
            <div class="flex items-start gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-[var(--pdm-accent-base)] mt-1.5 flex-shrink-0"></span>
                <div class="flex-1 min-w-0">
                    <div class="text-[10px] font-mono text-[var(--pdm-text-muted)] mb-0.5">
                        ${new Date(event.timestamp).toLocaleTimeString()}
                    </div>
                    <div class="text-xs font-mono text-[var(--pdm-text-primary)] leading-tight">${event.details}</div>
                </div>
            </div>
        </li>
    `).join('');

    if (eventLogListEl) eventLogListEl.innerHTML = logHtml;
    if (mainEventLogList) mainEventLogList.innerHTML = logHtml;
}

function updateSidebar(data) {
    const { predictions, is_operational } = data;

    if (!is_operational) {
        ttfListEl.innerHTML = `
            <li class="p-4 bg-[var(--pdm-surface-base)] rounded-[var(--pdm-radius-sm)] border border-[var(--pdm-border-hairline)] text-center">
                <div class="font-display font-semibold text-xs tracking-wider text-[var(--pdm-status-offline)] uppercase">FACTORY OFFLINE</div>
                <div class="font-mono text-[11px] text-[var(--pdm-text-muted)] mt-1">ALL SIMULATION SYSTEMS INACTIVE</div>
            </li>
        `;
        return;
    }

    const alerts = Object.entries(predictions)
        .map(([id, data]) => ({ id, ...data }))
        .filter(item =>
            item.state === 'Degrading' ||
            item.state === 'Warning' ||
            item.state === 'Critical Failure Imminent' ||
            item.anomaly_detected
        );

    if (alerts.length === 0) {
        ttfListEl.innerHTML = `
            <li class="p-4 bg-[var(--pdm-surface-base)] rounded-[var(--pdm-radius-sm)] border border-[var(--pdm-status-normal-border)] text-center">
                <div class="flex items-center justify-center gap-2 font-display font-semibold text-xs tracking-wider text-[var(--pdm-status-normal)] uppercase">
                    <span class="w-2 h-2 rounded-full bg-[var(--pdm-status-normal)]"></span>
                    <span>ALL SYSTEMS NOMINAL</span>
                </div>
                <div class="font-mono text-[11px] text-[var(--pdm-text-muted)] mt-1">NO ANOMALIES OR TRIP WARNINGS</div>
            </li>
        `;
        return;
    }

    ttfListEl.innerHTML = alerts.map(item => {
        let borderClass = 'border-[var(--pdm-border-hairline)]';
        let dotColor = 'bg-[var(--pdm-accent-base)]';
        let title = 'STATUS UPDATE';
        let textColor = 'text-[var(--pdm-text-secondary)]';
        let message = 'Telemetry deviance detected';

        if (item.anomaly_detected) {
            borderClass = 'border-[var(--pdm-status-warning-border)]';
            dotColor = 'bg-[var(--pdm-status-warning)]';
            title = 'ANOMALY DETECTED';
            textColor = 'text-[var(--pdm-status-warning)]';
            message = item.anomaly_details || 'Multivariate sensor divergence';
        } else if (item.state === 'Warning') {
            borderClass = 'border-[var(--pdm-status-warning-border)]';
            dotColor = 'bg-[var(--pdm-status-warning)]';
            title = 'EARLY WARNING';
            textColor = 'text-[var(--pdm-status-warning)]';
            message = 'Performance deviance detected';
        } else if (item.state === 'Degrading') {
            borderClass = 'border-[var(--pdm-status-warning-border)]';
            dotColor = 'bg-[var(--pdm-status-warning)]';
            title = 'DEGRADING HEALTH';
            textColor = 'text-[var(--pdm-status-warning)]';
            message = `Health Score: ${(item.health_score * 100).toFixed(0)}%`;
        } else if (item.state === 'Critical Failure Imminent') {
            borderClass = 'border-[var(--pdm-status-critical-border)]';
            dotColor = 'bg-[var(--pdm-status-critical)]';
            title = 'CRITICAL TRIP IMMINENT';
            textColor = 'text-[var(--pdm-status-critical)]';
            message = 'Immediate mechanical intervention required';
        }

        const rcaHtml = (item.rca_steps && item.rca_steps.length) ? `
            <div class="mt-2.5 pt-2 border-t border-[var(--pdm-border-hairline)]">
                <p class="text-[10px] font-mono uppercase text-[var(--pdm-text-muted)] mb-1">RCA PROTOCOL:</p>
                <ol class="list-decimal list-inside text-[11px] font-mono text-[var(--pdm-text-secondary)] space-y-0.5">
                    ${item.rca_steps.map(s => `<li>${s}</li>`).join('')}
                </ol>
            </div>
        ` : '';

        return `
            <li class="p-3 bg-[var(--pdm-surface-base)] rounded-[var(--pdm-radius-sm)] border ${borderClass} transition-colors">
                <div class="flex items-center justify-between mb-1.5">
                    <span class="font-display font-semibold text-xs tracking-wider uppercase text-[var(--pdm-text-primary)]">
                        ${item.id.replace(/_/g, ' ')}
                    </span>
                    <span class="flex items-center gap-1.5 text-[10px] font-mono font-bold uppercase ${textColor}">
                        <span class="w-1.5 h-1.5 rounded-full ${dotColor}"></span>
                        <span>${title}</span>
                    </span>
                </div>
                <div class="text-[11px] font-mono text-[var(--pdm-text-muted)] mb-1.5">${message}</div>

                ${item.state === 'Critical Failure Imminent' || item.state === 'Degrading' || item.state === 'Warning' ? `
                <div class="text-[11px] font-mono text-[var(--pdm-text-secondary)] mb-1.5">
                    FAULT MODE: <strong class="text-[var(--pdm-text-primary)] uppercase">${getFailureType(item)}</strong>
                </div>
                ` : ''}

                ${item.rul_prediction ? `
                <div class="flex justify-between items-center pt-1.5 border-t border-[var(--pdm-border-hairline)] text-xs font-mono">
                    <span class="text-[10px] text-[var(--pdm-text-muted)] uppercase">EST. RUL:</span>
                    <span class="font-bold ${textColor}">${item.rul_prediction}h</span>
                </div>
                ` : ''}

                ${rcaHtml}

                <div class="mt-2.5 pt-2 border-t border-[var(--pdm-border-hairline)] flex items-center justify-between">
                    <button data-action="diagnose" data-machine-id="${item.id}" class="text-[10px] font-mono text-[var(--pdm-accent-base)] hover:underline flex items-center gap-1 cursor-pointer">
                        <span class="w-1.5 h-1.5 rounded-full bg-[var(--pdm-accent-base)] animate-pulse"></span>
                        <span>[AI DIAGNOSTICS]</span>
                    </button>
                    <button data-action="service" data-machine-id="${item.id}" class="text-[10px] font-mono text-[var(--pdm-text-secondary)] hover:text-[var(--pdm-text-primary)] cursor-pointer">
                        [DISPATCH]
                    </button>
                </div>
            </li>
        `;
    }).join('');
}

// ============================================================================
// MASTER DASHBOARD INGESTION LOOP
// ============================================================================

function updateDashboard(data) {
    if (!data) return;
    const { predictions, is_operational, kpis, event_log } = data;

    // Deterministic 150ms Opacity Flash on Heartbeat Dot upon data ingestion
    const heartbeatDot = document.getElementById('heartbeat-dot');
    if (heartbeatDot) {
        heartbeatDot.classList.add('tick');
        setTimeout(() => heartbeatDot.classList.remove('tick'), 150);
    }

    updateKpis(kpis);
    updateEventLog(event_log);
    updateSidebar(data);

    if (typeof window.filtersPopulated === 'undefined' || !window.filtersPopulated) {
        if (predictions) {
            populateFilters(Object.values(predictions));
            window.filtersPopulated = true;
        }
    }

    // Clear loading skeletons
    const skeletonEl = document.getElementById('fleet-loading-skeleton');
    if (skeletonEl) skeletonEl.remove();

    if (!predictions) return;

    let visibleCount = 0;
    for (const machineId of Object.keys(predictions)) {
        try {
            let cardContainer = document.getElementById(machineId);
            const machineData = predictions[machineId];

            let isVisible = true;
            if (currentFilters.location && machineData.location !== currentFilters.location) isVisible = false;
            if (currentFilters.type && machineData.machine_type !== currentFilters.type) isVisible = false;

            if (!isVisible) {
                if (cardContainer) cardContainer.style.display = 'none';
                continue;
            }

            visibleCount++;
            if (cardContainer) cardContainer.style.display = 'block';

            if (!cardContainer) {
                createMachineCard(machineId);
                cardContainer = document.getElementById(machineId);
            }

            const cardEl = cardContainer.querySelector('.pdm-machine-card');
            const noDataIndicator = cardContainer.querySelector('.no-data-indicator');
            const sensorReadingsEl = cardContainer.querySelector('.sensor-readings');
            const chartContainer = cardContainer.querySelector('.chart-container');
            const healthEl = cardContainer.querySelector('.machine-health-val');
            const chart = charts[machineId];

            const hasSensorData = machineData.sensor_data && Object.keys(machineData.sensor_data).length > 0;

            if (!hasSensorData) {
                if (noDataIndicator) noDataIndicator.classList.remove('hidden');
                if (sensorReadingsEl) sensorReadingsEl.classList.add('hidden');
                if (chartContainer) chartContainer.classList.add('hidden');
            } else {
                if (noDataIndicator) noDataIndicator.classList.add('hidden');
                if (sensorReadingsEl) sensorReadingsEl.classList.remove('hidden');
                if (chartContainer) chartContainer.classList.remove('hidden');
            }

            const statusInfo = getStatusInfo(is_operational ? machineData.state : 'off');

            // Apply card boundary state
            if (cardContainer) {
                cardContainer.setAttribute('data-status', statusInfo.statusKey);
            }

            const statusBadge = cardContainer.querySelector('.status-badge-tech');
            if (statusBadge) {
                statusBadge.textContent = statusInfo.text;
                statusBadge.className = `status-badge-tech pdm-badge ${statusInfo.badgeClass}`;
            }

            // Update physical RUL gauge
            updateRulGauge(cardContainer, machineData.rul_prediction, is_operational);

            if (is_operational) {
                // High-density sensor readings table
                if (sensorReadingsEl && machineData.sensor_readings) {
                    const sensorsHtml = Object.entries(machineData.sensor_readings).map(([sensorId, value]) => {
                        let sensorName = sensorId.replace(/_/g, ' ');
                        let unit = getSensorUnit(sensorId, machineData);
                        const displayValue = typeof value === 'number' ? value.toFixed(2) : 'N/A';

                        return `
                            <div class="flex justify-between items-center py-1 border-b border-[var(--pdm-border-hairline)] text-xs font-mono">
                                <span class="text-[var(--pdm-text-secondary)] text-[11px] uppercase">${sensorName}</span>
                                <span class="font-bold text-[var(--pdm-text-primary)]" style="font-variant-numeric: tabular-nums;">${displayValue} <span class="text-[10px] font-normal text-[var(--pdm-text-muted)]">${unit}</span></span>
                            </div>
                        `;
                    }).join('');
                    sensorReadingsEl.innerHTML = sensorsHtml || '<div class="text-[var(--pdm-text-muted)] text-xs font-mono py-2">NO SENSOR TELEMETRY</div>';
                }

                // Update Health Metric in Footer
                if (healthEl) {
                    const healthPct = typeof machineData.health_score === 'number' ? (machineData.health_score * 100).toFixed(0) : '--';
                    healthEl.textContent = `H: ${healthPct}%`;
                }

                // Update Hairline Ribbon Sparkline Chart
                if (chart && machineData.sensor_data) {
                    const sensorNames = Object.keys(machineData.sensor_data);
                    if (sensorNames.length > 0) {
                        const primarySensor = sensorNames[0];
                        if (machineData.sensor_data[primarySensor]) {
                            const lineColor = machineData.state === 'Critical Failure Imminent' ? '#f43f5e' :
                                (machineData.state === 'Degrading' || machineData.state === 'Warning') ? '#f59e0b' :
                                '#38bdf8';

                            chart.data.labels = Array.from({ length: machineData.sensor_data[primarySensor].length }, (_, i) => i + 1);
                            chart.data.datasets = [{
                                label: primarySensor,
                                data: machineData.sensor_data[primarySensor],
                                borderColor: lineColor,
                                borderWidth: 1.25,
                                pointRadius: 0,
                                tension: 0.25
                            }];
                            chart.update('none');
                        }
                    }
                }
            }
        } catch (machineError) {
            console.error(`Error updating telemetry for machine ${machineId}:`, machineError);
        }
    }

    // Diagnostic Empty State handling
    let emptyPanel = document.getElementById('fleet-empty-panel');
    if (visibleCount === 0) {
        if (!emptyPanel && machineGrid) {
            emptyPanel = document.createElement('div');
            emptyPanel.id = 'fleet-empty-panel';
            emptyPanel.className = 'col-span-full pdm-empty-panel';
            emptyPanel.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-[var(--pdm-surface-raised)] border border-[var(--pdm-border-subtle)] flex items-center justify-center mb-3">
                    <span class="w-2 h-2 rounded-full bg-[var(--pdm-text-muted)]"></span>
                </div>
                <h3 class="font-display font-semibold text-xs uppercase tracking-wider text-[var(--pdm-text-primary)] mb-1">NO PHYSICAL ASSETS MATCHING PARAMETERS</h3>
                <p class="font-mono text-[11px] text-[var(--pdm-text-muted)] mb-4">No telemetry streams found for selected filters.</p>
                <button onclick="document.getElementById('clear-filters').click()" class="pdm-btn text-xs py-1.5 px-3 bg-[var(--pdm-surface-raised)] border-[var(--pdm-border-subtle)] text-[var(--pdm-text-secondary)] hover:text-[var(--pdm-text-primary)]">RESET SURVEILLANCE FILTERS</button>
            `;
            machineGrid.appendChild(emptyPanel);
        }
    } else if (emptyPanel) {
        emptyPanel.remove();
    }
}

async function fetchDashboardData() {
    try {
        const response = await fetch(API_ENDPOINT);
        if (!response.ok) {
            if (response.status === 503) {
                if (lastUpdatedEl) lastUpdatedEl.textContent = `Telemetry stream initializing...`;
            } else {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return;
        }
        const data = await response.json();
        if (!data || !data.predictions) throw new Error("Invalid API payload format");

        lastDashboardData = data;

        // Remove error panel if present
        const errPanel = document.getElementById('fleet-error-panel');
        if (errPanel) errPanel.remove();

        if (lastUpdatedEl) {
            lastUpdatedEl.textContent = `SIMULATION ACTIVE | INGESTION: ${new Date(data.last_prediction_run_time_utc).toLocaleTimeString()}`;
        }
        updateDashboard(data);
    } catch (error) {
        console.error("Dashboard fetch error:", error);
        if (lastUpdatedEl) lastUpdatedEl.textContent = `CONNECTION TRIP: ${error.message}`;
        const skeletonEl = document.getElementById('fleet-loading-skeleton');
        if (skeletonEl) skeletonEl.remove();
        if (machineGrid && (!lastDashboardData || Object.keys(lastDashboardData.predictions || {}).length === 0)) {
            let errorPanel = document.getElementById('fleet-error-panel');
            if (!errorPanel) {
                errorPanel = document.createElement('div');
                errorPanel.id = 'fleet-error-panel';
                errorPanel.className = 'col-span-full pdm-error-panel';
                errorPanel.innerHTML = `
                    <div class="flex items-center gap-3 mb-2">
                        <span class="w-2.5 h-2.5 rounded-full bg-[var(--pdm-status-critical)]"></span>
                        <h3 class="font-display font-semibold text-xs text-[var(--pdm-status-critical)] uppercase tracking-wider">TELEMETRY INGESTION FAILURE</h3>
                    </div>
                    <p class="font-mono text-xs text-[var(--pdm-text-secondary)] mb-4">Error Code: ERR_POLL_TIMEOUT [${error.message}]</p>
                    <button onclick="fetchDashboardData()" class="pdm-btn pdm-btn-critical self-start text-xs py-1.5 px-3">RETRY INGESTION</button>
                `;
                machineGrid.innerHTML = '';
                machineGrid.appendChild(errorPanel);
            }
        }
    }
}

// ============================================================================
// SENSOR HISTORY MODAL
// ============================================================================

function showHistoryModal(machineId) {
    if (!historyModalTitle || !historyModalOverlay) return;
    historyModalTitle.textContent = `TELEMETRY RECORD: ${machineId.replace(/_/g, ' ')}`;
    historyModalOverlay.dataset.machineId = machineId;
    historyModalOverlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    const firstButton = historyTimeRanges.querySelector('button');
    if (firstButton) {
        setActiveTimeRange(firstButton);
        fetchHistory(machineId, firstButton.dataset.range);
    }
}

function closeHistoryModal() {
    if (historyModalOverlay) historyModalOverlay.classList.add('hidden');
    document.body.style.overflow = '';
}

function setActiveTimeRange(activeButton) {
    if (!historyTimeRanges) return;
    historyTimeRanges.querySelectorAll('button').forEach(btn => btn.classList.remove('active'));
    activeButton.classList.add('active');
}

async function fetchHistory(machineId, range = '1h') {
    try {
        const response = await fetch(`/api/history?machine_id=${machineId}&range=${range}`);
        if (!response.ok) throw new Error('History request failed');
        const data = await response.json();

        if (data.success && data.history && data.history.length > 0) {
            updateHistoryChart(data);
        } else {
            generateRealisticHistory(machineId, range);
        }
    } catch (error) {
        console.error("History fetch error:", error);
        generateRealisticHistory(machineId, range);
    }
}

function generateRealisticHistory(machineId, range) {
    const machineType = machineId.split('_')[0];
    const now = new Date();
    const dataPoints = range === '1h' ? 12 : range === '6h' ? 36 : 144;
    const interval = range === '1h' ? 5 : range === '6h' ? 10 : 60;

    const timestamps = [];
    const sensors = {};

    const sensorNames = getSensorNamesForMachine(machineType);
    sensorNames.forEach(name => {
        sensors[name] = [];
    });

    for (let i = dataPoints; i >= 0; i--) {
        const timestamp = new Date(now.getTime() - (i * interval * 60000));
        timestamps.push(timestamp.toISOString());

        sensorNames.forEach(sensorName => {
            const baseValue = getBaseValueForSensor(machineType, sensorName);
            const variation = (Math.random() - 0.5) * 0.1;
            const trend = Math.sin(i * 0.1) * 0.05;
            const value = baseValue * (1 + variation + trend);
            sensors[sensorName].push(Math.max(0, value));
        });
    }

    updateHistoryChart({ timestamps, sensors });
}

function getSensorNamesForMachine(machineType) {
    const sensorMap = {
        'FILLING': ['Fill Volume Sensor', 'Nozzle Pressure', 'Vibration'],
        'SHRINK': ['Tunnel Temperature', 'Conveyor Speed', 'Humidity'],
        'PILLOW': ['Sealing Jaw Temperature', 'Sealing Jaw Pressure', 'Alignment Error'],
        'BOXING': ['Box Pressure Sensor', 'Conveyor Speed Sensor', 'Box Count Sensor']
    };
    return sensorMap[machineType] || ['Primary Sensor'];
}

function getBaseValueForSensor(machineType, sensorName) {
    const sensorValues = {
        'FILLING': { 'Fill Volume Sensor': 100, 'Nozzle Pressure': 2.0, 'Vibration': 0.3 },
        'SHRINK': { 'Tunnel Temperature': 180, 'Conveyor Speed': 15, 'Humidity': 35 },
        'PILLOW': { 'Sealing Jaw Temperature': 160, 'Sealing Jaw Pressure': 5.0, 'Alignment Error': 0.1 },
        'BOXING': { 'Box Pressure Sensor': 5.0, 'Conveyor Speed Sensor': 17, 'Box Count Sensor': 130 }
    };
    return sensorValues[machineType]?.[sensorName] || 100;
}

function updateHistoryChart(data) {
    if (!data.timestamps || !data.sensors || !historyChartCanvas) return;
    const colors = ['#38bdf8', '#10b981', '#f59e0b', '#f43f5e', '#94a3b8'];

    if (historyChart) {
        historyChart.destroy();
    }

    historyChart = new Chart(historyChartCanvas, {
        type: 'line',
        data: {
            labels: data.timestamps,
            datasets: Object.entries(data.sensors).map(([name, values], i) => ({
                label: name.replace(/_/g, ' '),
                data: values,
                borderColor: colors[i % colors.length],
                fill: false,
                borderWidth: 1.5,
                pointRadius: 1
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'hour', tooltipFormat: 'PPpp' },
                    ticks: { color: '#8A95A5', font: { family: 'JetBrains Mono', size: 9 }, source: 'auto' },
                    grid: { color: 'rgba(56, 68, 86, 0.25)' }
                },
                y: {
                    ticks: { color: '#8A95A5', font: { family: 'JetBrains Mono', size: 9 } },
                    grid: { color: 'rgba(56, 68, 86, 0.25)' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#C5CAD3', font: { family: 'Plus Jakarta Sans', size: 10 } }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(24, 29, 38, 0.95)',
                    borderColor: 'rgba(56, 68, 86, 0.8)',
                    borderWidth: 1,
                    titleFont: { family: 'Chakra Petch', size: 11 },
                    bodyFont: { family: 'JetBrains Mono', size: 10 }
                }
            }
        }
    });
}

// Event delegation on machine grid
if (machineGrid) {
    machineGrid.addEventListener('click', (e) => {
        const connectBtn = e.target.closest('[data-action="connect"]');
        if (connectBtn) {
            if (typeof showDeviceConnectionModal === 'function') {
                showDeviceConnectionModal(connectBtn.dataset.machineId);
            }
            return;
        }

        const diagnoseBtn = e.target.closest('[data-action="diagnose"]');
        if (diagnoseBtn) {
            showAiAdvisorModal(diagnoseBtn.dataset.machineId);
            return;
        }

        const serviceBtn = e.target.closest('[data-action="service"]');
        if (serviceBtn) {
            performMaintenance(serviceBtn.dataset.machineId);
            return;
        }

        const historyBtn = e.target.closest('[data-action="history"]');
        if (historyBtn) {
            showHistoryModal(historyBtn.dataset.machineId);
            return;
        }
    });
}

// Event delegation on sidebar watchlist alerts
if (ttfListEl) {
    ttfListEl.addEventListener('click', (e) => {
        const diagnoseBtn = e.target.closest('[data-action="diagnose"]');
        if (diagnoseBtn) {
            showAiAdvisorModal(diagnoseBtn.dataset.machineId);
            return;
        }

        const serviceBtn = e.target.closest('[data-action="service"]');
        if (serviceBtn) {
            performMaintenance(serviceBtn.dataset.machineId);
            return;
        }
    });
}

// ============================================================================
// AI COGNITIVE DIAGNOSTIC ADVISOR MODAL
// ============================================================================

let currentAdvisorMachineId = null;
let currentAdvisorParts = [];

function showAiAdvisorModal(machineId) {
    const modalOverlay = document.getElementById('ai-advisor-modal-overlay');
    if (!modalOverlay) return;

    currentAdvisorMachineId = machineId;
    currentAdvisorParts = [];

    const titleEl = document.getElementById('ai-advisor-title');
    const badgeEl = document.getElementById('ai-advisor-severity-badge');
    const timestampEl = document.getElementById('ai-advisor-timestamp');
    const headingEl = document.getElementById('ai-advisor-heading');
    const durationEl = document.getElementById('ai-advisor-duration');
    const causeEl = document.getElementById('ai-advisor-cause');
    const evidenceEl = document.getElementById('ai-advisor-evidence');
    const actionsEl = document.getElementById('ai-advisor-actions');
    const partsEl = document.getElementById('ai-advisor-parts');
    const riskEl = document.getElementById('ai-advisor-risk');
    const dispatchBtn = document.getElementById('ai-advisor-dispatch-btn');

    if (titleEl) titleEl.textContent = `COGNITIVE ADVISORY: ${machineId.replace(/_/g, ' ')}`;
    if (headingEl) headingEl.textContent = `CONSULTING OMNIROUTE REASONING ENGINE...`;
    if (badgeEl) {
        badgeEl.textContent = `ANALYZING`;
        badgeEl.className = `pdm-tag pdm-tag-normal text-[10px] uppercase font-mono animate-pulse`;
    }
    if (timestampEl) timestampEl.textContent = `SYNTHESIZING TELEMETRY VECTOR`;
    if (durationEl) durationEl.textContent = `-- MIN`;
    if (causeEl) causeEl.textContent = `Evaluating multivariate sensor deviation, envelope drift and failure signature...`;
    if (evidenceEl) evidenceEl.innerHTML = `<li class="text-[var(--pdm-text-muted)] animate-pulse">Running calibrated boundary limit checks...</li>`;
    if (actionsEl) actionsEl.innerHTML = `<div class="text-[var(--pdm-text-muted)] animate-pulse">Formulating actionable mechatronic mitigation checklist...</div>`;
    if (partsEl) partsEl.innerHTML = `<span class="pdm-tag text-[10px] font-mono text-[var(--pdm-text-muted)]">IDENTIFYING SUBSYSTEMS...</span>`;
    if (riskEl) riskEl.textContent = `Evaluating operational failure cascade probability...`;
    if (dispatchBtn) dispatchBtn.disabled = true;

    modalOverlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    fetch('/api/ai-diagnostics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ machine_id: machineId })
    })
    .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    })
    .then(data => {
        if (!data) throw new Error("Empty diagnostic payload");

        const severity = data.severity || 'NOMINAL';
        const badgeClass = severity === 'CRITICAL' ? 'pdm-tag-critical' : (severity === 'WARNING' ? 'pdm-tag-warning' : 'pdm-tag-normal');

        if (badgeEl) {
            badgeEl.textContent = severity;
            badgeEl.className = `pdm-tag ${badgeClass} text-[10px] uppercase font-mono`;
        }

        if (headingEl) headingEl.textContent = data.diagnosis_title || 'Autonomous Telemetry Assessment';
        if (timestampEl) {
            const timeStr = data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
            timestampEl.textContent = `${timeStr} | ${data.advisor_provider || 'OmniRoute'}`;
        }
        if (durationEl) durationEl.textContent = `${data.estimated_downtime_minutes || 30} MINUTES`;
        if (causeEl) causeEl.textContent = data.physical_root_cause || 'All observed telemetry within nominal bounds.';

        // Evidence
        if (evidenceEl) {
            const evList = Array.isArray(data.evidence) && data.evidence.length > 0 ? data.evidence : ['Sensor channels operating within nominal calibrated baseline bounds.'];
            evidenceEl.innerHTML = evList.map(e => `
                <li class="flex items-start gap-2">
                    <span class="w-1.5 h-1.5 rounded-full bg-[var(--pdm-accent-base)] mt-1.5 flex-shrink-0"></span>
                    <span>${e}</span>
                </li>
            `).join('');
        }

        // Actions with interactive checkboxes
        if (actionsEl) {
            const actList = Array.isArray(data.immediate_actions) && data.immediate_actions.length > 0 ? data.immediate_actions : ['Verify emergency stop circuits', 'Log inspection sign-off'];
            actionsEl.innerHTML = actList.map((a, idx) => `
                <label class="flex items-start gap-2.5 p-2 rounded-[var(--pdm-radius-sm)] bg-[var(--pdm-surface-sunken)] hover:bg-[var(--pdm-surface-raised)] cursor-pointer border border-[var(--pdm-border-hairline)] transition-colors">
                    <input type="checkbox" id="ai-action-${idx}" class="mt-0.5 accent-[var(--pdm-accent-base)] w-3.5 h-3.5 cursor-pointer">
                    <span class="text-xs text-[var(--pdm-text-secondary)] font-body">${a}</span>
                </label>
            `).join('');
        }

        // Parts
        currentAdvisorParts = Array.isArray(data.required_spare_parts) ? data.required_spare_parts : [];
        if (partsEl) {
            if (currentAdvisorParts.length > 0) {
                partsEl.innerHTML = currentAdvisorParts.map(p => `
                    <span class="pdm-tag pdm-tag-normal font-mono text-[11px] text-[var(--pdm-accent-base)] border border-[var(--pdm-border-subtle)]">${p}</span>
                `).join('');
            } else {
                partsEl.innerHTML = `<span class="text-[var(--pdm-text-muted)] text-[11px] font-mono">No replacement subsystems required.</span>`;
            }
        }

        if (riskEl) riskEl.textContent = data.operational_risk || 'Zero secondary damage anticipated under current parameters.';
        if (dispatchBtn) dispatchBtn.disabled = false;
    })
    .catch(err => {
        console.error('AI Advisor error:', err);
        if (headingEl) headingEl.textContent = `DIAGNOSTIC ADVISORY OFFLINE`;
        if (badgeEl) {
            badgeEl.textContent = `ERROR`;
            badgeEl.className = `pdm-tag pdm-tag-critical text-[10px] uppercase font-mono`;
        }
        if (causeEl) causeEl.textContent = `Failed to contact OmniRoute Reasoning Engine (${err.message}). Using manual override protocol.`;
        if (dispatchBtn) dispatchBtn.disabled = false;
    });
}

function closeAiAdvisorModal() {
    const modalOverlay = document.getElementById('ai-advisor-modal-overlay');
    if (modalOverlay) modalOverlay.classList.add('hidden');
    document.body.style.overflow = '';
}

// Bind AI Advisor modal triggers
const aiAdvisorClose = document.getElementById('ai-advisor-close');
const aiAdvisorDismiss = document.getElementById('ai-advisor-dismiss');
const aiAdvisorOverlay = document.getElementById('ai-advisor-modal-overlay');
const aiAdvisorDispatch = document.getElementById('ai-advisor-dispatch-btn');

if (aiAdvisorClose) aiAdvisorClose.addEventListener('click', closeAiAdvisorModal);
if (aiAdvisorDismiss) aiAdvisorDismiss.addEventListener('click', closeAiAdvisorModal);
if (aiAdvisorOverlay) {
    aiAdvisorOverlay.addEventListener('click', (e) => {
        if (e.target === aiAdvisorOverlay) closeAiAdvisorModal();
    });
}
if (aiAdvisorDispatch) {
    aiAdvisorDispatch.addEventListener('click', () => {
        const targetId = currentAdvisorMachineId;
        const targetParts = currentAdvisorParts;
        closeAiAdvisorModal();
        if (targetId) {
            performMaintenance(targetId, targetParts);
        }
    });
}

if (historyModalClose) historyModalClose.addEventListener('click', closeHistoryModal);
if (historyModalOverlay) {
    historyModalOverlay.addEventListener('click', (e) => {
        if (e.target === historyModalOverlay) closeHistoryModal();
    });
}

if (historyTimeRanges) {
    historyTimeRanges.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        if (btn) {
            setActiveTimeRange(btn);
            fetchHistory(historyModalOverlay.dataset.machineId, btn.dataset.range);
        }
    });
}

// Tab Switching
const switchTab = (activeTab) => {
    const tabs = { watchlist: tabWatchlist, log: tabLog };
    const panels = { watchlist: watchlistPanel, log: logPanel };
    Object.values(tabs).forEach(t => { if (t) t.classList.remove('active'); });
    Object.values(panels).forEach(p => { if (p) p.classList.add('hidden'); });
    if (tabs[activeTab]) tabs[activeTab].classList.add('active');
    if (panels[activeTab]) panels[activeTab].classList.remove('hidden');
};

if (tabWatchlist) tabWatchlist.addEventListener('click', () => switchTab('watchlist'));
if (tabLog) tabLog.addEventListener('click', () => switchTab('log'));

// Mobile sidebar dropdown functionality
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebarDropdown = document.getElementById('sidebar-dropdown');
const sidebarToggleText = document.getElementById('sidebar-toggle-text');
const sidebarToggleIcon = document.getElementById('sidebar-toggle-icon');

if (sidebarToggle && sidebarDropdown) {
    sidebarToggle.addEventListener('click', () => {
        sidebarDropdown.classList.toggle('hidden');
        if (sidebarToggleIcon) sidebarToggleIcon.classList.toggle('rotate-180');
    });

    document.querySelectorAll('.sidebar-dropdown-item').forEach(item => {
        item.addEventListener('click', () => {
            const tab = item.dataset.tab;
            if (sidebarToggleText) sidebarToggleText.textContent = item.textContent.trim();
            switchTab(tab);
            sidebarDropdown.classList.add('hidden');
            if (sidebarToggleIcon) sidebarToggleIcon.classList.remove('rotate-180');
        });
    });
}

// Sidebar resize handle
function initSidebarResize() {
    const sidebar = document.getElementById('sidebar');
    const resizeHandle = document.getElementById('resize-handle');
    if (!sidebar || !resizeHandle) return;

    let isResizing = false;

    resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        document.addEventListener('mousemove', handleResize);
        document.addEventListener('mouseup', stopResize);
        e.preventDefault();
    });

    function handleResize(e) {
        if (!isResizing) return;
        const newWidth = e.clientX;
        if (newWidth >= 220 && newWidth <= 500) {
            sidebar.style.width = newWidth + 'px';
        }
    }

    function stopResize() {
        isResizing = false;
        document.removeEventListener('mousemove', handleResize);
        document.removeEventListener('mouseup', stopResize);
        document.body.style.cursor = '';
    }
}

// ============================================================================
// DASHBOARD FILTERING
// ============================================================================

let currentFilters = {
    location: '',
    type: ''
};

function initFilters() {
    const locationFilter = document.getElementById('filter-location');
    const typeFilter = document.getElementById('filter-type');
    const clearButton = document.getElementById('clear-filters');

    if (!locationFilter || !typeFilter || !clearButton) return;

    locationFilter.addEventListener('change', (e) => {
        currentFilters.location = e.target.value;
        applyFilters();
    });

    typeFilter.addEventListener('change', (e) => {
        currentFilters.type = e.target.value;
        applyFilters();
    });

    clearButton.addEventListener('click', () => {
        currentFilters = { location: '', type: '' };
        locationFilter.value = '';
        typeFilter.value = '';
        applyFilters();
    });
}

function populateFilters(machines) {
    const locationFilter = document.getElementById('filter-location');
    const typeFilter = document.getElementById('filter-type');

    if (!locationFilter || !typeFilter || !machines) return;

    const locations = new Set();
    const types = new Set();

    machines.forEach(machine => {
        if (machine.location && machine.location.trim()) {
            locations.add(machine.location);
        }
        if (machine.machine_type && machine.machine_type.trim()) {
            types.add(machine.machine_type);
        }
    });

    const currentLocation = locationFilter.value;
    locationFilter.innerHTML = '<option value="">ALL LOCATIONS</option>';
    Array.from(locations).sort().forEach(location => {
        const option = document.createElement('option');
        option.value = location;
        option.textContent = location.toUpperCase();
        if (location === currentLocation) option.selected = true;
        locationFilter.appendChild(option);
    });

    const currentType = typeFilter.value;
    typeFilter.innerHTML = '<option value="">ALL ASSET CLASSES</option>';
    Array.from(types).sort().forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type.toUpperCase();
        if (type === currentType) option.selected = true;
        typeFilter.appendChild(option);
    });
}

function applyFilters() {
    if (lastDashboardData) {
        updateDashboard(lastDashboardData);
    }
}

// ============================================================================
// MOBILE REMOTE SURVEILLANCE MODAL
// ============================================================================

function openMobileRemoteModal() {
    const modal = document.getElementById('mobile-remote-modal');
    if (!modal) return;
    
    const currentOrigin = window.location.origin;
    const mobileUrl = `${currentOrigin}/mobile`;
    
    const urlDisplay = document.getElementById('mobile-remote-url-text');
    if (urlDisplay) urlDisplay.textContent = mobileUrl;
    
    const qrImg = document.getElementById('mobile-qr-image');
    if (qrImg) {
        qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(mobileUrl)}`;
    }
    
    modal.classList.remove('hidden');
}

function closeMobileRemoteModal() {
    const modal = document.getElementById('mobile-remote-modal');
    if (modal) modal.classList.add('hidden');
}

function copyMobileUrl() {
    const urlDisplay = document.getElementById('mobile-remote-url-text');
    const copyBtn = document.getElementById('copy-mob-url-btn');
    if (!urlDisplay) return;
    
    navigator.clipboard.writeText(urlDisplay.textContent.trim()).then(() => {
        if (copyBtn) {
            const original = copyBtn.textContent;
            copyBtn.textContent = 'COPIED!';
            copyBtn.classList.add('text-emerald-400');
            setTimeout(() => {
                copyBtn.textContent = original;
                copyBtn.classList.remove('text-emerald-400');
            }, 2000);
        }
    });
}

// ============================================================================
// LIFECYCLE INITIALIZATION
// ============================================================================

function initDashboard() {
    initSidebarResize();
    initFilters();
    fetchDashboardData();
    setInterval(fetchDashboardData, UPDATE_INTERVAL);
}

document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    if (typeof initMachineManagement === 'function') {
        initMachineManagement();
    }
});
