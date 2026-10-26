/**
 * Device Connection & Industrial Gateway Onboarding Controller
 * Handles physical machine connectivity, edge daemon config generation,
 * live handshake verification, and statistical baseline calibration.
 */

let currentConnectionMachineId = null;
let currentConnectionData = null;

function showDeviceConnectionModal(machineId) {
    const modal = document.getElementById('device-connection-modal');
    if (!modal) return;

    currentConnectionMachineId = machineId;

    const titleEl = document.getElementById('device-conn-title');
    const subtitleEl = document.getElementById('device-conn-subtitle');
    const modeBadge = document.getElementById('device-conn-mode-badge');
    const toggleBtn = document.getElementById('device-conn-toggle-mode-btn');
    const channelsTable = document.getElementById('device-conn-channels-table');
    const pingText = document.getElementById('device-conn-ping-text');
    const pingDot = document.getElementById('device-conn-ping-dot');

    if (titleEl) titleEl.textContent = `PHYSICAL ASSET GATEWAY: ${machineId.replace(/_/g, ' ')}`;
    if (subtitleEl) subtitleEl.textContent = `FETCHING EDGE CONNECTION PROFILE...`;
    if (channelsTable) channelsTable.innerHTML = `<div class="text-[var(--pdm-text-muted)] py-2">Loading channel schema...</div>`;
    if (pingText) pingText.textContent = `GATEWAY STANDBY`;
    if (pingDot) pingDot.className = 'w-2 h-2 rounded-full bg-[var(--pdm-status-offline)]';

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    fetch(`/api/ingest/connection-info?machine_id=${machineId}`)
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        })
        .then(data => {
            currentConnectionData = data;
            if (subtitleEl) subtitleEl.textContent = `${data.machine_type} | Location: ${data.location} | Endpoint: /api/ingest`;

            // Update Live vs Simulated status
            updateModeDisplay(data.is_live);

            // Populate Code Blocks
            const edgeCode = document.getElementById('code-edge-cmd');
            if (edgeCode) edgeCode.textContent = data.edge_agent_command;

            const curlCode = document.getElementById('code-curl-cmd');
            if (curlCode) curlCode.textContent = data.curl_command;

            const modbusCode = document.getElementById('code-modbus-cmd');
            if (modbusCode) {
                modbusCode.textContent = `python scripts/edge/pdm_modbus_bridge.py --plc-host 192.168.1.100 --plc-port 502 --machine-id ${machineId} --key ${data.device_token}`;
            }

            const mqttCode = document.getElementById('code-mqtt-cmd');
            if (mqttCode) {
                mqttCode.textContent = `python scripts/edge/pdm_mqtt_subscriber.py --broker 192.168.1.50 --topic pdm/${machineId}/telemetry --machine-id ${machineId} --key ${data.device_token}`;
            }

            // Populate Channels Table
            renderChannelsTable(data.channels);
        })
        .catch(err => {
            console.error('Connection info fetch error:', err);
            if (subtitleEl) subtitleEl.textContent = `Error loading connection credentials: ${err.message}`;
        });
}

function updateModeDisplay(isLive) {
    const modeBadge = document.getElementById('device-conn-mode-badge');
    const toggleBtn = document.getElementById('device-conn-toggle-mode-btn');

    if (modeBadge) {
        if (isLive) {
            modeBadge.textContent = 'LIVE HARDWARE INGESTION';
            modeBadge.className = 'pdm-tag pdm-tag-normal text-[10px] uppercase font-mono font-bold';
        } else {
            modeBadge.textContent = 'SIMULATED FEED';
            modeBadge.className = 'pdm-tag pdm-tag-warning text-[10px] uppercase font-mono';
        }
    }

    if (toggleBtn) {
        toggleBtn.textContent = isLive ? 'SWITCH TO SIMULATED FEED' : 'SWITCH TO LIVE HARDWARE FEED';
    }
}

function renderChannelsTable(channels) {
    const tableEl = document.getElementById('device-conn-channels-table');
    if (!tableEl) return;

    if (!channels || channels.length === 0) {
        tableEl.innerHTML = `<div class="text-[var(--pdm-text-muted)] py-2">No calibrated channels registered.</div>`;
        return;
    }

    tableEl.innerHTML = channels.map(c => `
        <div class="flex items-center justify-between py-1.5 border-b border-[var(--pdm-border-hairline)]">
            <div class="flex items-center gap-2">
                <span class="w-1.5 h-1.5 rounded-full bg-[var(--pdm-accent-base)]"></span>
                <span class="text-[var(--pdm-text-primary)] uppercase">${c.name}</span>
                <span class="text-[10px] text-[var(--pdm-text-muted)]">[${c.unit}]</span>
            </div>
            <div class="flex items-center gap-4 text-[10px] text-[var(--pdm-text-secondary)]">
                <span>WARN: <strong class="text-[var(--pdm-status-warning)]">${c.threshold_warn !== null ? c.threshold_warn : '--'}</strong></span>
                <span>CRIT: <strong class="text-[var(--pdm-status-critical)]">${c.threshold_crit !== null ? c.threshold_crit : '--'}</strong></span>
            </div>
        </div>
    `).join('');
}

function closeDeviceConnectionModal() {
    const modal = document.getElementById('device-connection-modal');
    if (modal) modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// Handshake verification
function testGatewayHandshake() {
    if (!currentConnectionMachineId) return;

    const pingText = document.getElementById('device-conn-ping-text');
    const pingDot = document.getElementById('device-conn-ping-dot');
    const token = currentConnectionData ? currentConnectionData.device_token : 'dev-api-key';

    if (pingText) pingText.textContent = `TRANSMITTING HANDSHAKE...`;
    if (pingDot) pingDot.className = 'w-2 h-2 rounded-full bg-[var(--pdm-status-warning)] animate-ping';

    const start = Date.now();
    fetch('/api/ingest/ping', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': token
        },
        body: JSON.stringify({ machine_id: currentConnectionMachineId })
    })
    .then(res => res.json())
    .then(data => {
        const latency = Date.now() - start;
        if (data.status === 'online') {
            if (pingText) pingText.textContent = `HANDSHAKE VERIFIED (${latency}ms) [${data.authenticated ? 'AUTH OK' : 'NO AUTH'}]`;
            if (pingDot) pingDot.className = 'w-2 h-2 rounded-full bg-[var(--pdm-status-normal)]';
            if (typeof showNotification === 'function') {
                showNotification(`Gateway ping successful (${latency}ms). Ingestion online.`, 'success');
            }
        } else {
            throw new Error('Unexpected handshake response');
        }
    })
    .catch(err => {
        if (pingText) pingText.textContent = `HANDSHAKE FAILED (${err.message})`;
        if (pingDot) pingDot.className = 'w-2 h-2 rounded-full bg-[var(--pdm-status-critical)]';
        if (typeof showNotification === 'function') {
            showNotification(`Handshake error: ${err.message}`, 'error');
        }
    });
}

// Empirical statistical envelope auto-calibration
function triggerAutoCalibration() {
    if (!currentConnectionMachineId) return;

    if (typeof showNotification === 'function') {
        showNotification(`Computing empirical baseline statistics for ${currentConnectionMachineId}...`, 'info');
    }

    fetch('/api/machine-mgmt/calibrate-asset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            machine_id: currentConnectionMachineId,
            samples: 200
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            if (typeof showNotification === 'function') {
                showNotification(data.message, 'success');
            }
            // Refresh connection info to show updated thresholds
            showDeviceConnectionModal(currentConnectionMachineId);
        } else {
            if (typeof showNotification === 'function') {
                showNotification(`Calibration: ${data.error}`, 'error');
            }
        }
    })
    .catch(err => {
        console.error('Calibration error:', err);
        if (typeof showNotification === 'function') {
            showNotification(`Calibration error: ${err.message}`, 'error');
        }
    });
}

// Ingestion mode toggle (Live vs Simulated)
function toggleAssetFeedMode() {
    if (!currentConnectionMachineId || !currentConnectionData) return;

    const newMode = currentConnectionData.is_live ? 'Active' : 'Live';

    fetch('/api/ingest/toggle-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            machine_id: currentConnectionMachineId,
            mode: newMode
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            currentConnectionData.is_live = data.is_live;
            updateModeDisplay(data.is_live);
            if (typeof showNotification === 'function') {
                showNotification(`Machine ${currentConnectionMachineId} mode set to: ${data.mode}`, 'success');
            }
            if (typeof fetchDashboardData === 'function') {
                fetchDashboardData();
            }
        } else {
            throw new Error(data.error);
        }
    })
    .catch(err => {
        console.error('Toggle mode error:', err);
        if (typeof showNotification === 'function') {
            showNotification(`Failed to toggle mode: ${err.message}`, 'error');
        }
    });
}

// Wire Global Listeners for Device Connection Modal
document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('device-connection-modal');
    const closeBtn = document.getElementById('device-conn-close');
    const dismissBtn = document.getElementById('device-conn-dismiss-btn');
    const pingBtn = document.getElementById('device-conn-ping-btn');
    const calibrateBtn = document.getElementById('device-conn-calibrate-btn');
    const toggleBtn = document.getElementById('device-conn-toggle-mode-btn');

    if (closeBtn) closeBtn.addEventListener('click', closeDeviceConnectionModal);
    if (dismissBtn) dismissBtn.addEventListener('click', closeDeviceConnectionModal);
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeDeviceConnectionModal();
        });
    }

    if (pingBtn) pingBtn.addEventListener('click', testGatewayHandshake);
    if (calibrateBtn) calibrateBtn.addEventListener('click', triggerAutoCalibration);
    if (toggleBtn) toggleBtn.addEventListener('click', toggleAssetFeedMode);

    // Protocol Tabs
    document.querySelectorAll('.device-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.device-tab-btn').forEach(b => {
                b.classList.remove('active', 'border-[var(--pdm-accent-base)]', 'text-[var(--pdm-accent-base)]');
                b.classList.add('border-transparent', 'text-[var(--pdm-text-secondary)]');
            });
            btn.classList.add('active', 'border-[var(--pdm-accent-base)]', 'text-[var(--pdm-accent-base)]');
            btn.classList.remove('border-transparent', 'text-[var(--pdm-text-secondary)]');

            const tab = btn.dataset.tab;
            ['edge-agent', 'curl-rest', 'modbus-tcp', 'mqtt-broker'].forEach(t => {
                const panel = document.getElementById(`device-tab-panel-${t}`);
                if (panel) {
                    if (t === tab) panel.classList.remove('hidden');
                    else panel.classList.add('hidden');
                }
            });
        });
    });

    // Copy to clipboard buttons
    document.querySelectorAll('.copy-code-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const codeEl = document.getElementById(targetId);
            if (codeEl) {
                navigator.clipboard.writeText(codeEl.textContent.trim()).then(() => {
                    const originalText = btn.textContent;
                    btn.textContent = 'COPIED!';
                    btn.classList.add('text-[var(--pdm-accent-base)]');
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.classList.remove('text-[var(--pdm-accent-base)]');
                    }, 2000);
                });
            }
        });
    });
});
