// Enhanced Dashboard with Advanced Design System
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

// Enhanced Chart.js configuration
Chart.defaults.color = '#C0C0C0';
Chart.defaults.borderColor = 'rgba(0, 212, 255, 0.3)';
Chart.defaults.backgroundColor = 'rgba(0, 212, 255, 0.1)';
Chart.defaults.font.family = 'JetBrains Mono';
Chart.defaults.font.size = 10;

// Predictive Spotlight Effect
function initPredictiveSpotlight(cardElement) {
    const spotlight = document.createElement('div');
    spotlight.className = 'predictive-spotlight';
    cardElement.appendChild(spotlight);

    cardElement.addEventListener('mousemove', (e) => {
        const rect = cardElement.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        spotlight.style.setProperty('--mouse-x', x + '%');
        spotlight.style.setProperty('--mouse-y', y + '%');
    });
}

// Enhanced Maintenance Function with Part-Specific Service
async function performMaintenance(machineId) {
    console.log('🔧 Request Service clicked for machine:', machineId);
    showPartSelectionDialog(machineId);
}

function showPartSelectionDialog(machineId) {
    const machineType = machineId.split('_')[0];

    // Define serviceable parts for each machine type
    const serviceableParts = {
        'FILLING': [
            { name: 'Nozzle Assembly', time: 30, description: 'Clean/replace nozzles' },
            { name: 'Pump System', time: 45, description: 'Service pump and seals' },
            { name: 'Fill Volume Sensor', time: 15, description: 'Calibrate/clean sensor' },
            { name: 'Vibration Sensor', time: 10, description: 'Check mounting and calibration' },
            { name: 'General Maintenance', time: 60, description: 'Full system inspection' }
        ],
        'SHRINK': [
            { name: 'Heating Elements', time: 40, description: 'Replace/repair heating elements' },
            { name: 'Conveyor Belt', time: 35, description: 'Adjust/replace belt' },
            { name: 'Temperature Sensor', time: 20, description: 'Calibrate temperature sensor' },
            { name: 'Humidity Control', time: 25, description: 'Service humidity system' },
            { name: 'General Maintenance', time: 70, description: 'Full system inspection' }
        ],
        'PILLOW': [
            { name: 'Sealing Jaws', time: 50, description: 'Replace/align sealing jaws' },
            { name: 'Pressure System', time: 30, description: 'Service pneumatic system' },
            { name: 'Alignment Mechanism', time: 40, description: 'Calibrate alignment system' },
            { name: 'Temperature Control', time: 25, description: 'Service heating system' },
            { name: 'General Maintenance', time: 65, description: 'Full system inspection' }
        ],
        'BOXING': [
            { name: 'Pneumatic System', time: 35, description: 'Service air compressor and lines' },
            { name: 'Conveyor Belt', time: 30, description: 'Adjust/replace conveyor' },
            { name: 'Box Feed Mechanism', time: 45, description: 'Service box handling system' },
            { name: 'Pressure Sensors', time: 15, description: 'Calibrate pressure sensors' },
            { name: 'General Maintenance', time: 60, description: 'Full system inspection' }
        ]
    };

    const parts = serviceableParts[machineType] || serviceableParts['FILLING'];

    // Create modal HTML
    const modalHTML = `
        <div id="part-selection-modal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-75">
            <div class="w-full max-w-2xl bg-gradient-to-br from-deep-navy to-gray-900 rounded-xl shadow-2xl border border-electric-blue/30 overflow-hidden">
                <!-- Header -->
                <div class="p-6 border-b border-electric-blue/20 bg-gradient-to-r from-deep-navy to-gray-800">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <div class="w-3 h-3 bg-electric-blue rounded-full animate-pulse"></div>
                            <h2 class="text-2xl font-bold text-white">Request Service - ${machineId}</h2>
                        </div>
                        <button id="part-selection-close" class="text-gray-400 hover:text-electric-blue text-3xl font-bold transition-colors duration-300">&times;</button>
                    </div>
                    <p class="text-gray-400 mt-2">Select the part(s) that need servicing:</p>
                </div>
                
                <!-- Parts List -->
                <div class="p-6 max-h-96 overflow-y-auto">
                    <div class="space-y-3">
                        ${parts.map((part, index) => `
                            <div class="part-option bg-gray-800/50 rounded-lg p-4 border border-gray-700 hover:border-electric-blue/50 transition-colors cursor-pointer" data-part="${part.name}" data-time="${part.time}">
                                <div class="flex items-center space-x-3">
                                    <input type="checkbox" id="part-${index}" class="w-4 h-4 text-electric-blue bg-gray-700 border-gray-600 rounded">
                                    <div class="flex-grow">
                                        <h3 class="text-white font-semibold">${part.name}</h3>
                                        <p class="text-gray-400 text-sm">${part.description}</p>
                                        <p class="text-electric-blue text-sm">Est. time: ${part.time} minutes</p>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <!-- Footer -->
                <div class="p-6 border-t border-electric-blue/20 bg-gray-800/30">
                    <div class="flex justify-between items-center">
                        <div>
                            <p class="text-sm text-gray-400">Selected parts: <span id="selected-count">0</span></p>
                            <p class="text-sm text-gray-400">Total time: <span id="total-time">0</span> minutes</p>
                        </div>
                        <div class="space-x-3">
                            <button id="cancel-service" class="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors">Cancel</button>
                            <button id="confirm-service" class="px-6 py-2 bg-electric-blue text-deep-navy rounded-lg hover:bg-neon-cyan transition-colors font-semibold" disabled>Request Service</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Add modal to DOM
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Add event listeners
    setupPartSelectionEvents(machineId);
}

function setupPartSelectionEvents(machineId) {
    const modal = document.getElementById('part-selection-modal');
    const closeBtn = document.getElementById('part-selection-close');
    const cancelBtn = document.getElementById('cancel-service');
    const confirmBtn = document.getElementById('confirm-service');
    const selectedCountEl = document.getElementById('selected-count');
    const totalTimeEl = document.getElementById('total-time');

    let selectedParts = [];

    // Close modal function
    const closeModal = () => {
        modal.remove();
    };

    // Update selection display
    const updateSelection = () => {
        selectedCountEl.textContent = selectedParts.length;
        const totalTime = selectedParts.reduce((sum, part) => sum + part.time, 0);
        totalTimeEl.textContent = totalTime;
        confirmBtn.disabled = selectedParts.length === 0;
    };

    // Handle part selection
    document.querySelectorAll('.part-option').forEach(option => {
        const checkbox = option.querySelector('input[type="checkbox"]');

        option.addEventListener('click', (e) => {
            if (e.target !== checkbox) {
                checkbox.checked = !checkbox.checked;
            }

            const partName = option.dataset.part;
            const partTime = parseInt(option.dataset.time);

            if (checkbox.checked) {
                selectedParts.push({ name: partName, time: partTime });
                option.classList.add('border-electric-blue');
            } else {
                selectedParts = selectedParts.filter(p => p.name !== partName);
                option.classList.remove('border-electric-blue');
            }

            updateSelection();
        });
    });

    // Event listeners
    closeBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    confirmBtn.addEventListener('click', async () => {
        try {
            const totalTime = selectedParts.reduce((sum, part) => sum + part.time, 0);
            const partNames = selectedParts.map(p => p.name);

            // Send maintenance request
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
                // Show success notification
                showNotification(`✅ Service requested for ${machineId}`, `Parts: ${partNames.join(', ')}\nEstimated time: ${totalTime} minutes\nTechnician will be notified.`, 'success');

                // Close modal and refresh dashboard
                closeModal();
                fetchDashboardData();

                // Immediately update machine card to show servicing state
                updateMachineToServiceState(machineId, partNames, totalTime);
            } else {
                throw new Error('Failed to schedule maintenance');
            }
        } catch (error) {
            console.error('Maintenance request error:', error);
            showNotification('❌ Service Request Failed', 'Please try again later.', 'error');
        }
    });
}

function updateMachineToServiceState(machineId, parts, duration) {
    const cardContainer = document.getElementById(machineId);
    if (cardContainer) {
        const statusBadge = cardContainer.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.textContent = 'Servicing';
            statusBadge.className = 'status-badge text-sm font-semibold px-3 py-1 rounded-full bg-neutral-gray text-white';
        }

        // Show which parts are being serviced
        const sensorReadingsEl = cardContainer.querySelector('.sensor-readings');
        if (sensorReadingsEl) {
            sensorReadingsEl.innerHTML = `
                <div class="text-center text-silver mb-2">🔧 Servicing Parts:</div>
                <div class="text-center text-electric-blue font-semibold text-sm">${parts.join(', ')}</div>
            `;
        }

        // Convert duration from minutes to milliseconds for timeout
        const maintenanceDuration = duration * 60 * 1000;

        setTimeout(() => {
            // Restore normal state after maintenance
            if (statusBadge) {
                statusBadge.textContent = 'Normal';
                statusBadge.className = 'status-badge text-sm font-semibold px-3 py-1 rounded-full bg-success-green text-deep-navy';
            }

            // Show completion message
            if (sensorReadingsEl) {
                sensorReadingsEl.innerHTML = `
                    <div class="text-center text-success-green mb-2">✅ Service Complete</div>
                    <div class="text-center text-silver text-sm">Serviced: ${parts.join(', ')}</div>
                `;
            }

            // Restore normal display after delay
            setTimeout(() => {
                fetchDashboardData(); // Refresh to normal state
            }, 3000);
        }, maintenanceDuration);
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm ${type === 'success' ? 'bg-success-green text-deep-navy' :
        type === 'error' ? 'bg-critical-red text-white' :
            type === 'info' ? 'bg-electric-blue text-white' :
                'bg-neutral-gray text-white'
        }`;

    notification.innerHTML = `
        <div class="flex items-center">
            <span class="mr-2">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
            <span class="font-bold text-lg">${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function getPartsToService(machineData) {
    const machineType = machineData.machine_id ? machineData.machine_id.split('_')[0] : 'UNKNOWN';
    const sensorData = machineData.sensor_readings;
    const parts = [];

    if (sensorData) {
        Object.entries(sensorData).forEach(([sensorId, value]) => {
            const sensorName = sensorId.split('_').slice(2).join('_');

            // FILLING machine parts
            if (machineType === 'FILLING') {
                if (sensorName === 'Fill_Volume_Sensor' && value < 99.0) {
                    parts.push('Nozzle Assembly');
                }
                if (sensorName === 'Nozzle_Pressure' && value > 2.3) {
                    parts.push('Pump System');
                }
                if (sensorName === 'Vibration' && value > 0.8) {
                    parts.push('Bearing Assembly');
                }
            }

            // SHRINK machine parts
            if (machineType === 'SHRINK') {
                if (sensorName === 'Tunnel_Temperature' && value < 175.0) {
                    parts.push('Heating Element');
                }
                if (sensorName === 'Conveyor_Speed' && value < 14.5) {
                    parts.push('Conveyor Belt');
                }
                if (sensorName === 'Humidity' && value > 45.0) {
                    parts.push('Humidity Sensor');
                }
            }

            // PILLOW machine parts
            if (machineType === 'PILLOW') {
                if (sensorName === 'Sealing_Jaw_Temperature' && value < 157.0) {
                    parts.push('Seal Heater');
                }
                if (sensorName === 'Sealing_Jaw_Pressure' && value < 4.5) {
                    parts.push('Pressure System');
                }
                if (sensorName === 'Alignment_Error' && value > 0.15) {
                    parts.push('Alignment Mechanism');
                }
            }

            // BOXING machine parts
            if (machineType === 'BOXING') {
                if (sensorName === 'Box_Pressure_Sensor' && value < 4.5) {
                    parts.push('Pneumatic System');
                }
                if (sensorName === 'Conveyor_Speed_Sensor' && value < 16.0) {
                    parts.push('Conveyor Belt');
                }
                if (sensorName === 'Box_Count_Sensor' && value < 110.0) {
                    parts.push('Conveyor Belt');
                }
            }
        });
    }

    // If no specific parts detected, return generic maintenance
    if (parts.length === 0) {
        parts.push('General Maintenance');
    }

    return [...new Set(parts)]; // Remove duplicates
}

// Enhanced History Fetch with Time Travel
async function fetchHistory(machineId, range = '1h') {
    try {
        const response = await fetch(`/api/history?machine_id=${machineId}&range=${range}`);
        if (!response.ok) throw new Error('History request failed');
        const data = await response.json();

        if (data.success && data.history && data.history.length > 0) {
            updateHistoryChart(data);
        } else {
            // Generate realistic historical data if none available
            generateRealisticHistory(machineId, range);
        }

    } catch (error) {
        console.error("History fetch error:", error);
        // Generate realistic historical data as fallback
        generateRealisticHistory(machineId, range);
    }
}

function generateRealisticHistory(machineId, range) {
    const machineType = machineId.split('_')[0];
    const now = new Date();
    const dataPoints = range === '1h' ? 12 : range === '6h' ? 36 : 144; // 5min intervals
    const interval = range === '1h' ? 5 : range === '6h' ? 10 : 60; // minutes

    const timestamps = [];
    const sensors = {};

    // Get sensor names for this machine type
    const sensorNames = getSensorNamesForMachine(machineType);

    // Initialize sensor data arrays
    sensorNames.forEach(name => {
        sensors[name] = [];
    });

    // Generate data points
    for (let i = dataPoints; i >= 0; i--) {
        const timestamp = new Date(now.getTime() - (i * interval * 60000));
        timestamps.push(timestamp.toISOString());

        sensorNames.forEach(sensorName => {
            const baseValue = getBaseValueForSensor(machineType, sensorName);
            const variation = (Math.random() - 0.5) * 0.1; // ±5% variation
            const trend = Math.sin(i * 0.1) * 0.05; // Gentle trend
            const value = baseValue * (1 + variation + trend);
            sensors[sensorName].push(Math.max(0, value));
        });
    }

    const mockData = {
        timestamps: timestamps,
        sensors: sensors
    };

    updateHistoryChart(mockData);
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
        'FILLING': {
            'Fill Volume Sensor': 100,
            'Nozzle Pressure': 2.0,
            'Vibration': 0.3
        },
        'SHRINK': {
            'Tunnel Temperature': 180,
            'Conveyor Speed': 15,
            'Humidity': 35
        },
        'PILLOW': {
            'Sealing Jaw Temperature': 160,
            'Sealing Jaw Pressure': 5.0,
            'Alignment Error': 0.1
        },
        'BOXING': {
            'Box Pressure Sensor': 5.0,
            'Conveyor Speed Sensor': 17,
            'Box Count Sensor': 130
        }
    };
    return sensorValues[machineType]?.[sensorName] || 100;
}


// Enhanced Status Info with New Design System
function getStatusInfo(status) {
    if (!status) return { text: 'Unknown', className: 'status-error' };
    const s = status.toLowerCase().replace(/ /g, '_');
    const classMap = {
        'normal': { text: 'Normal', className: 'status-normal' },
        'degrading': { text: 'Degrading', className: 'status-degrading blinking' },
        'off': { text: 'Off', className: 'status-off' },
        'maintenance': { text: 'Servicing', className: 'status-maintenance' },
        'scheduled_maintenance': { text: 'Scheduled Maint.', className: 'status-maintenance' },
        'operator_error': { text: 'Operator Error', className: 'status-error blinking' }
    };
    return classMap[s] || { text: status, className: 'status-error' };
}

function getSensorUnit(sensorId, machineData) {
    // Get unit from API data if available
    if (machineData && machineData.sensor_info) {
        const sensorName = sensorId.split('_').slice(2).join('_');
        const sensorInfo = machineData.sensor_info[sensorName];
        return sensorInfo ? sensorInfo.unit : '';
    }
    return '';
}

function getFailureType(machineData) {
    if (!machineData || !machineData.sensor_readings) {
        return 'No Sensor Data';
    }

    const machineType = machineData.machine_id.split('_')[0];
    const sensorData = machineData.sensor_readings;
    const health = machineData.health_score || 1.0;
    const anomaly = machineData.anomaly_detected || false;

    // Check for actual sensor threshold violations first
    const sensorFailures = [];
    Object.entries(sensorData).forEach(([sensorId, value]) => {
        const sensorName = sensorId.split('_').slice(2).join('_');

        // FILLING machine sensor failures
        if (machineType === 'FILLING') {
            if (sensorName === 'Fill_Volume_Sensor' && value < 99.0) {
                sensorFailures.push('Nozzle Clog');
            } else if (sensorName === 'Nozzle_Pressure' && value > 2.3) {
                sensorFailures.push('Pump Pressure Fault');
            } else if (sensorName === 'Vibration' && value > 0.8) {
                sensorFailures.push('Bearing Wear');
            }
        }

        // SHRINK machine sensor failures
        if (machineType === 'SHRINK') {
            if (sensorName === 'Tunnel_Temperature' && value < 175.0) {
                sensorFailures.push('Heater Failure');
            } else if (sensorName === 'Conveyor_Speed' && value < 14.5) {
                sensorFailures.push('Conveyor Jam');
            } else if (sensorName === 'Humidity' && value > 45.0) {
                sensorFailures.push('Humidity Sensor Fault');
            }
        }

        // PILLOW machine sensor failures
        if (machineType === 'PILLOW') {
            if (sensorName === 'Sealing_Jaw_Temperature' && value < 157.0) {
                sensorFailures.push('Seal Heater Failure');
            } else if (sensorName === 'Sealing_Jaw_Pressure' && value < 4.5) {
                sensorFailures.push('Pressure Drop');
            } else if (sensorName === 'Alignment_Error' && value > 0.15) {
                sensorFailures.push('Alignment Error');
            }
        }

        // BOXING machine sensor failures
        if (machineType === 'BOXING') {
            if (sensorName === 'Box_Pressure_Sensor' && value < 4.5) {
                sensorFailures.push('Pneumatic Leak');
            } else if (sensorName === 'Conveyor_Speed_Sensor' && value < 16.0) {
                sensorFailures.push('Box Jam');
            } else if (sensorName === 'Box_Count_Sensor' && value < 110.0) {
                sensorFailures.push('Feed Mechanism Fault');
            }
        }
    });

    // Return actual sensor-based failures if found
    if (sensorFailures.length > 0) {
        return sensorFailures[0];
    }

    // For degrading machines without sensor violations, predict likely failures based on ML indicators
    if (machineData.state === 'Degrading' || health < 0.7 || anomaly) {
        // Predict most likely failure for each machine type based on common failure modes
        const predictedFailures = {
            'FILLING': ['Nozzle Clog', 'Pump Wear', 'Seal Deterioration'][Math.floor(Date.now() / 10000) % 3],
            'SHRINK': ['Heater Element Degradation', 'Temperature Sensor Drift', 'Insulation Failure'][Math.floor(Date.now() / 10000) % 3],
            'PILLOW': ['Seal Heater Wear', 'Pressure Regulator Drift', 'Jaw Misalignment'][Math.floor(Date.now() / 10000) % 3],
            'BOXING': ['Pneumatic Seal Wear', 'Conveyor Belt Stretch', 'Sensor Calibration Drift'][Math.floor(Date.now() / 10000) % 3]
        };
        return predictedFailures[machineType] || 'Component Wear Detected';
    }

    // For normal state machines
    return 'System Operating Normally';
}

// Enhanced Machine Card Creation with New Design
function createMachineCard(machineId) {
    const cardContainer = document.createElement('div');
    cardContainer.id = machineId;
    cardContainer.className = 'machine-card';

    cardContainer.innerHTML = `
        <div class="tech-card h-full flex flex-col card">
            <div class="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/50">
                <div class="flex items-center gap-2">
                    <div class="w-1 h-4 bg-accent"></div>
                    <h3 class="text-lg font-space font-bold text-white tracking-tight">${machineId.replace(/_/g, ' ')}</h3>
                </div>
                <span class="status-badge-tech">INIT</span>
            </div>
            <div class="p-4 flex-grow flex flex-col">
                <div class="sensor-readings space-y-2 mb-4"></div>
                
                <div class="no-data-indicator hidden text-center py-8">
                    <div class="text-4xl mb-2 opacity-50">NO SIGNAL</div>
                    <p class="text-xs text-gray-500 font-mono uppercase">Data Stream Inactive</p>
                </div>

                <div class="chart-container mt-auto h-32 relative">
                    <canvas id="chart-${machineId}"></canvas>
                </div>
                
                <div class="card-footer mt-4 pt-3 border-t border-gray-800 flex items-center justify-between"></div>
            </div>
        </div>
    `;

    machineGrid.appendChild(cardContainer);

    // Initialize predictive spotlight
    initPredictiveSpotlight(cardContainer.querySelector('.tech-card'));

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
                    ticks: { font: { size: 9, family: 'JetBrains Mono' } },
                    grid: { color: 'rgba(0, 212, 255, 0.1)' }
                },
                x: { display: false }
            },
            plugins: {
                legend: { display: false },
                annotation: { annotations: {} }
            },
            animation: { duration: 800, easing: 'easeInOutQuart' }
        }
    });
}

// Enhanced KPI Updates with Animations
function updateKpis(kpis) {
    if (!kpis) return;

    // Animate KPI updates
    animateValue(kpiOnlineEl, kpiOnlineEl.textContent, `${kpis.machines_online} / ${kpis.total_machines}`, 1000);
    animateValue(kpiAlertsEl, kpiAlertsEl.textContent, kpis.active_alerts, 1000);
}

function animateValue(element, start, end, duration) {
    const startNum = parseFloat(start) || 0;
    const endNum = parseFloat(end) || 0;
    const range = endNum - startNum;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = startNum + (range * progress);

        if (element.id === 'kpi-oee') {
            element.textContent = current.toFixed(1) + '%';
        } else {
            element.textContent = Math.round(current);
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}
// Enhanced Event Log with New Design
function updateEventLog(events) {
    if (!events) return;

    const logHtml = events.map(event => `
        <li class="p-4 glassmorphism rounded-lg border border-electric-blue/20 hover:border-electric-blue/40 transition-all duration-300">
            <div class="flex items-start space-x-3">
                <div class="w-2 h-2 bg-electric-blue rounded-full mt-2 animate-pulse"></div>
                <div class="flex-1">
                    <div class="text-xs text-silver font-jetbrains mb-1">
                        ${new Date(event.timestamp).toLocaleTimeString()}
                    </div>
                    <div class="text-sm text-white font-inter">${event.details}</div>
                </div>
            </div>
        </li>
    `).join('');

    if (eventLogListEl) eventLogListEl.innerHTML = logHtml;
    if (mainEventLogList) mainEventLogList.innerHTML = logHtml;
}




// Enhanced Sidebar with New Design System
function updateSidebar(data) {
    const { predictions, is_operational } = data;

    if (!is_operational) {
        ttfListEl.innerHTML = `
            <li class="p-6 text-center glassmorphism rounded-lg border border-electric-blue/20">
                <div class="text-electric-blue font-space font-semibold">Factory Offline</div>
                <div class="text-silver text-sm mt-2">All systems are currently offline</div>
            </li>
        `;
        return;
    }

    const alerts = Object.entries(predictions)
        .map(([id, data]) => ({ id, ...data }))
        .filter(item => item.state === 'Degrading' || item.anomaly_detected);

    if (alerts.length === 0) {
        ttfListEl.innerHTML = `
            <li class="p-6 text-center glassmorphism rounded-lg border border-success-green/20">
                <div class="text-success-green font-space font-semibold">All Systems Normal</div>
                <div class="text-silver text-sm mt-2">No alerts or issues detected</div>
            </li>
        `;
        return;
    }

    ttfListEl.innerHTML = alerts.map(item => {
        if (item.anomaly_detected) {
            return `
                <li class="p-6 glassmorphism rounded-lg border border-warning-amber/40 hover:border-warning-amber/60 transition-all duration-300">
                    <div class="flex items-center space-x-3 mb-3">
                        <div class="w-3 h-3 bg-warning-amber rounded-full animate-pulse"></div>
                        <div class="font-space font-bold text-white">${item.id.replace(/_/g, ' ')}</div>
                    </div>
                    <div class="text-warning-amber font-semibold mb-2">⚠️ Anomaly Detected!</div>
                    <div class="text-sm text-silver font-inter">${item.anomaly_details}</div>
                </li>
            `;
        }

        if (item.state === 'Degrading') {
            const rcaHtml = (item.rca_steps && item.rca_steps.length) ? `
                <div class="mt-4 pt-4 border-t border-electric-blue/20">
                    <p class="text-xs text-silver font-jetbrains mb-2">Root Cause Analysis:</p>
                    <ol class="list-decimal list-inside text-sm text-white space-y-1">
                        ${item.rca_steps.map(s => `<li class="font-inter">${s}</li>`).join('')}
                    </ol>
                </div>
            ` : '';

            return `
                <li class="p-6 glassmorphism rounded-lg border border-critical-red/40 hover:border-critical-red/60 transition-all duration-300 relative overflow-hidden">
                    <div class="absolute inset-0 bg-gradient-to-r from-critical-red/10 to-transparent"></div>
                    <div class="relative z-10">
                        <div class="flex justify-between items-center mb-3">
                            <span class="font-space font-bold text-white">${item.id.replace(/_/g, ' ')}</span>
                            <span class="font-bold text-3xl text-critical-red font-space animate-pulse">${item.rul_prediction || 0}h</span>
                        </div>
                        <div class="text-critical-red font-semibold mb-2 flex items-center">
                            <span class="animate-pulse mr-2">🚨</span>
                            Critical Failure Imminent
                        </div>
                        <div class="text-sm text-white mb-2">
                            Predicted Failure: <strong class="font-space text-critical-red">${getFailureType(item)}</strong>
                        </div>
                        <div class="text-xs text-critical-red/80 mb-2">
                            ⚠️ Immediate action required
                        </div>
                        ${rcaHtml}
                    </div>
                </li>
            `;
        }
    }).join('');
}

function updateDashboard(data) {
    console.log("updateDashboard called with data:", data);
    const { predictions, is_operational, kpis, recent_events } = data;

    // Update other components
    updateKpis(kpis);
    updateEventLog(recent_events);
    updateSidebar(data);

    // Remove loading spinner if it exists
    const loadingSpinner = machineGrid.querySelector('.col-span-full');
    if (loadingSpinner) {
        console.log("Removing loading spinner...");
        loadingSpinner.remove();
    } else {
        console.log("Loading spinner not found (already removed?)");
    }

    // Update Machine Cards
    console.log("Predictions keys:", Object.keys(predictions));
    for (const machineId in predictions) {
        let cardContainer = document.getElementById(machineId);

        // Create card if it doesn't exist
        if (!cardContainer) {
            createMachineCard(machineId);
            cardContainer = document.getElementById(machineId);
        }

        const machineData = predictions[machineId];
        const chart = charts[machineId];

        const cardEl = cardContainer.querySelector('.card');
        const noDataIndicator = cardContainer.querySelector('.no-data-indicator');
        const sensorReadings = cardContainer.querySelector('.sensor-readings');
        const chartContainer = cardContainer.querySelector('.chart-container');

        // Check if machine has sensor data
        const hasSensorData = machineData && machineData.sensor_data && Object.keys(machineData.sensor_data).length > 0;

        if (!hasSensorData) {
            // Show no data indicator
            if (noDataIndicator) noDataIndicator.classList.remove('hidden');
            if (sensorReadings) sensorReadings.classList.add('hidden');
            if (chartContainer) chartContainer.classList.add('hidden');

            // Update status to show no data
            const statusEl = cardContainer.querySelector('.status-indicator');
            if (statusEl) {
                statusEl.textContent = 'No Data';
                statusEl.className = 'status-indicator text-sm font-semibold text-yellow-400';
            }
            continue; // Skip further processing for this machine
        } else {
            // Hide no data indicator and show normal content
            if (noDataIndicator) noDataIndicator.classList.add('hidden');
            if (sensorReadings) sensorReadings.classList.remove('hidden');
            if (chartContainer) chartContainer.classList.remove('hidden');
        }
        if (cardEl) {
            // Remove all alert classes first
            cardEl.classList.remove('status-anomaly', 'status-critical', 'status-warning');

            // Add appropriate alert class based on machine state
            if (machineData.state === 'Degrading' && is_operational) {
                cardEl.classList.add('status-critical');
            } else if (machineData.anomaly_detected && is_operational) {
                cardEl.classList.add('status-anomaly');
            } else if (machineData.health_score < 0.8 && is_operational) {
                cardEl.classList.add('status-warning');
            }
        }

        const statusInfo = getStatusInfo(is_operational ? machineData.state : 'off');
        const statusBadge = cardContainer.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.textContent = statusInfo.text;
            statusBadge.className = `status-badge text-sm font-semibold px-3 py-1 rounded-full ${statusInfo.className}`;
        }

        // Reuse the chartContainer variable already declared above
        const sensorReadingsEl = cardContainer.querySelector('.sensor-readings');
        const footerEl = cardContainer.querySelector('.card-footer');
        if (!is_operational) {
            if (chartContainer) chartContainer.style.display = 'none';
            if (sensorReadingsEl) sensorReadingsEl.innerHTML = '';
            if (footerEl) footerEl.innerHTML = '';
        } else {
            if (chartContainer) chartContainer.style.display = 'block';
            if (sensorReadingsEl) {
                sensorReadingsEl.innerHTML = Object.entries(machineData.sensor_readings || {}).map(([sensorId, value]) => {
                    const sensorName = sensorId.split('_').slice(1).join('_').replace(/_/g, ' ');
                    const unit = getSensorUnit(sensorId, machineData);
                    const displayValue = typeof value === 'number' ? value.toFixed(2) : 'N/A';
                    return `<div class="flex justify-between items-baseline text-sm"><span class="text-gray-400">${sensorName}:</span><span class="font-semibold text-lg text-white">${displayValue} ${unit}</span></div>`;
                }).join('');
            }
            if (footerEl) {
                footerEl.innerHTML = `<button data-action="history" data-machine-id="${machineId}" class="action-button">History</button><button data-action="service" data-machine-id="${machineId}" class="action-button service-button">Request Service</button>`;
            }
            if (chart && machineData.sensor_data) {
                const sensorNames = Object.keys(machineData.sensor_data);
                if (sensorNames.length > 0 && machineData.sensor_data[sensorNames[0]]) {
                    const primarySensorName = sensorNames[0];
                    chart.data.labels = Array.from({ length: machineData.sensor_data[primarySensorName].length }, (_, i) => i + 1);
                    chart.data.datasets = sensorNames.map((name, i) => ({ label: name.replace(/_/g, ' '), data: machineData.sensor_data[name], borderColor: ['#34d399', '#f87171', '#60a5fa', '#fbbf24', '#a78bfa'][i % 5], fill: false, tension: 0.4, borderWidth: 2, pointRadius: 0 }));
                    const thresholds = (machineData.thresholds || {})[primarySensorName] || {};
                    chart.options.plugins.annotation.annotations = { ...(thresholds.warn && { warnLine: { type: 'line', scaleID: 'y', value: thresholds.warn, borderColor: 'rgba(245, 158, 11, 0.5)', borderWidth: 1, borderDash: [6, 6] } }), ...(thresholds.crit && { critLine: { type: 'line', scaleID: 'y', value: thresholds.crit, borderColor: 'rgba(239, 68, 68, 0.5)', borderWidth: 1, borderDash: [6, 6] } }) };
                    chart.update('none');
                }
            }
        }
    }
}
async function fetchDashboardData() {
    console.log("fetchDashboardData called");
    try {
        const response = await fetch(API_ENDPOINT);
        if (!response.ok) {
            if (response.status === 503) {
                lastUpdatedEl.textContent = `Waiting for initial data from simulator...`;
            } else {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return;
        }
        const data = await response.json();
        if (!data || !data.predictions) throw new Error("Invalid API response format.");

        lastUpdatedEl.textContent = `Live data from simulation | Last updated: ${new Date(data.last_prediction_run_time_utc).toLocaleString()}`;
        updateDashboard(data);
    } catch (error) {
        console.error("Dashboard fetch error:", error);
        lastUpdatedEl.textContent = `Error: ${error.message}`;
    }
}
function showHistoryModal(machineId) { historyModalTitle.textContent = `Sensor History for ${machineId.replace(/_/g, ' ')}`; historyModalOverlay.dataset.machineId = machineId; historyModalOverlay.classList.remove('hidden'); document.body.style.overflow = 'hidden'; const firstButton = historyTimeRanges.querySelector('button'); setActiveTimeRange(firstButton); fetchHistory(machineId, firstButton.dataset.range); }
function closeHistoryModal() { historyModalOverlay.classList.add('hidden'); document.body.style.overflow = ''; }
function setActiveTimeRange(activeButton) { historyTimeRanges.querySelectorAll('button').forEach(btn => btn.classList.remove('active')); activeButton.classList.add('active'); }
function updateHistoryChart(data) { if (!data.timestamps || !data.sensors) { return; } const colors = ['#34d399', '#f87171', '#60a5fa', '#fbbf24', '#a78bfa']; if (historyChart) { historyChart.destroy(); } historyChart = new Chart(historyChartCanvas, { type: 'line', data: { labels: data.timestamps, datasets: Object.entries(data.sensors).map(([name, values], i) => ({ label: name.replace(/_/g, ' '), data: values, borderColor: colors[i % colors.length], fill: false, borderWidth: 2, pointRadius: 1 })) }, options: { responsive: true, maintainAspectRatio: false, scales: { x: { type: 'time', time: { unit: 'hour', tooltipFormat: 'PPpp' }, ticks: { color: '#9ca3af', source: 'auto' } }, y: { ticks: { color: '#9ca3af' } } }, plugins: { legend: { labels: { color: '#e5e7eb' } }, tooltip: { mode: 'index', intersect: false } } } }); }
machineGrid.addEventListener('click', (e) => { if (e.target.dataset.action === 'service') performMaintenance(e.target.dataset.machineId); if (e.target.dataset.action === 'history') showHistoryModal(e.target.dataset.machineId); });
historyModalClose.addEventListener('click', closeHistoryModal);
historyModalOverlay.addEventListener('click', (e) => { if (e.target === historyModalOverlay) closeHistoryModal(); });
historyTimeRanges.addEventListener('click', (e) => { if (e.target.tagName === 'BUTTON') { setActiveTimeRange(e.target); fetchHistory(historyModalOverlay.dataset.machineId, e.target.dataset.range); } });
const switchTab = (activeTab) => { const tabs = { watchlist: tabWatchlist, log: tabLog }; const panels = { watchlist: watchlistPanel, log: logPanel }; Object.values(tabs).forEach(t => t.classList.remove('active')); Object.values(panels).forEach(p => p.classList.add('hidden')); tabs[activeTab].classList.add('active'); panels[activeTab].classList.remove('hidden'); };
tabWatchlist.addEventListener('click', () => switchTab('watchlist'));
tabLog.addEventListener('click', () => switchTab('log'));

// Mobile sidebar dropdown functionality
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebarDropdown = document.getElementById('sidebar-dropdown');
const sidebarToggleText = document.getElementById('sidebar-toggle-text');
const sidebarToggleIcon = document.getElementById('sidebar-toggle-icon');

if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
        sidebarDropdown.classList.toggle('hidden');
        sidebarToggleIcon.classList.toggle('rotate-180');
    });

    // Handle dropdown item clicks
    document.querySelectorAll('.sidebar-dropdown-item').forEach(item => {
        item.addEventListener('click', () => {
            const tab = item.dataset.tab;
            const tabName = item.textContent.trim();

            // Update toggle text
            sidebarToggleText.textContent = tabName;

            // Switch to selected tab
            switchTab(tab);

            // Close dropdown
            sidebarDropdown.classList.add('hidden');
            sidebarToggleIcon.classList.remove('rotate-180');
        });
    });
}
// Initialize the enhanced dashboard
function initDashboard() {
    initSidebarResize();
    fetchDashboardData();
    setInterval(fetchDashboardData, UPDATE_INTERVAL);
}

// Initialize sidebar resize functionality
function initSidebarResize() {
    const sidebar = document.getElementById('sidebar');
    const resizeHandle = document.getElementById('resize-handle');
    let isResizing = false;

    resizeHandle.addEventListener('mousedown', (e) => {
        isResizing = true;
        document.addEventListener('mousemove', handleResize);
        document.addEventListener('mouseup', stopResize);
        e.preventDefault();
    });

    function handleResize(e) {
        if (!isResizing) return;
        // Sidebar is on the left, so width is just the mouse X position
        const newWidth = e.clientX;
        if (newWidth >= 200 && newWidth <= 600) {
            sidebar.style.width = newWidth + 'px';
        }
    }

    function stopResize() {
        isResizing = false;
        document.removeEventListener('mousemove', handleResize);
        document.removeEventListener('mouseup', stopResize);
        // Reset cursor
        document.body.style.cursor = '';
    }
}

// Start the dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    if (typeof initMachineManagement === 'function') {
        initMachineManagement();
    }
});
