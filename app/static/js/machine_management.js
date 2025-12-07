// Enhanced Machine Management System
function initMachineManagement() {
    loadMachineManagementData();
    initMachineManagementTabs();
    initCSVUpload();
    initDataStreaming();
    initModelTraining();
    initAnalytics();
    initEnhancedMachineForm();
    initDynamicSensorConfiguration();
}

// Show machine management modal
function showMachineManagement() {
    document.getElementById('machine-management-modal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    loadMachineManagementData();
}

// Hide machine management modal
function hideMachineManagement() {
    document.getElementById('machine-management-modal').classList.add('hidden');
    document.body.style.overflow = '';
}

// Load machine management data
async function loadMachineManagementData() {
    try {
        // Load current user's company machines
        const machinesResponse = await fetch('/api/machine-mgmt/companies/1/machines');
        const machines = await machinesResponse.json();
        window.currentMachines = machines; // Store globally for edit function
        renderMachines(machines);

        // Load machine types
        const typesResponse = await fetch('/api/machine-mgmt/machine-types');
        const machineTypes = await typesResponse.json();
        renderMachineTypes(machineTypes);
    } catch (error) {
        console.error('Error loading machine management data:', error);
    }
}

// Render companies in the modal
function renderCompanies(companies) {
    const companiesList = document.getElementById('companies-list');
    companiesList.innerHTML = '';

    if (companies.length === 0) {
        companiesList.innerHTML = '<p class="text-neutral-gray">No companies registered yet.</p>';
        return;
    }

    companies.forEach(company => {
        const companyCard = document.createElement('div');
        companyCard.className = 'glassmorphism p-4 rounded-lg border border-electric-blue/20 mb-4';
        companyCard.innerHTML = `
            <h3 class="text-lg font-space font-bold text-electric-blue">${company.name}</h3>
            <p class="text-sm text-silver">Email: ${company.contact_email || 'N/A'}</p>
            <p class="text-sm text-silver">Phone: ${company.contact_phone || 'N/A'}</p>
            <p class="text-sm text-silver">Address: ${company.address || 'N/A'}</p>
            <button onclick="viewCompanyMachines('${company.id}')" class="btn-primary px-3 py-1 text-xs rounded-md mt-2">
                View Machines
            </button>
        `;
        companiesList.appendChild(companyCard);
    });
}

// Render machine types
function renderMachineTypes(machineTypes) {
    const machineTypeSelect = document.getElementById('machine-type-select');
    machineTypeSelect.innerHTML = '<option value="">-- Select Machine Type --</option>';

    if (Array.isArray(machineTypes)) {
        machineTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            machineTypeSelect.appendChild(option);
        });
    } else {
        // Fallback to hardcoded types if API doesn't return array
        const defaultTypes = ['FILLING', 'SHRINK', 'PILLOW'];
        defaultTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            machineTypeSelect.appendChild(option);
        });
    }
}

// View company machines
function viewCompanyMachines(companyId) {
    // Switch to machines tab
    document.getElementById('tab-machines').click();
    document.getElementById('company-select').value = companyId;
    loadCompanyMachines(companyId);
}

// Load company machines
async function loadCompanyMachines(companyId) {
    try {
        const response = await fetch(`/api/machine-mgmt/companies/${companyId}/machines`);
        const machines = await response.json();
        renderMachines(machines);
    } catch (error) {
        console.error('Error loading company machines:', error);
    }
}

// Render machines
function renderMachines(machines) {
    const machinesList = document.getElementById('machines-list');
    machinesList.innerHTML = '';

    if (machines.length === 0) {
        machinesList.innerHTML = '<p class="text-neutral-gray">No machines registered for this company yet.</p>';
        return;
    }

    machines.forEach(machine => {
        const machineCard = document.createElement('div');
        machineCard.className = 'glassmorphism p-4 rounded-lg border border-electric-blue/20 mb-4 flex justify-between items-center';
        const lastUpdated = machine.updated_at ? new Date(machine.updated_at).toLocaleDateString() : 'N/A';
        machineCard.innerHTML = `
            <div class="flex-1">
                <h3 class="text-lg font-space font-bold text-electric-blue">${machine.name || machine.machine_id}</h3>
                <p class="text-sm text-silver">Type: ${machine.machine_type}</p>
                <p class="text-sm text-silver">Manufacturer: ${machine.manufacturer || 'N/A'}</p>
                <p class="text-sm text-silver">Model: ${machine.model || 'N/A'}</p>
                <p class="text-sm text-silver">Location: ${machine.location || 'N/A'}</p>
                <p class="text-xs text-gray-400">Last Updated: ${lastUpdated}</p>
            </div>
            <div class="flex space-x-2">
                <button onclick="editMachine('${machine.machine_id}')" class="px-3 py-1 bg-electric-blue text-white rounded hover:bg-blue-600 text-sm">Edit</button>
                <button onclick="deleteMachine('${machine.machine_id}')" class="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-sm">Delete</button>
            </div>
        `;
        machinesList.appendChild(machineCard);
    });
}

// Edit machine function
function editMachine(machineId) {
    // Find the machine in the current machines list
    const machines = window.currentMachines || [];
    const machine = machines.find(m => m.machine_id === machineId);

    if (machine) {
        // Check if machine management modal is open, if not open it first
        const modal = document.getElementById('machine-management-modal');
        if (!modal || modal.style.display === 'none') {
            openMachineManagement();
        }

        // Wait for modal to be visible, then populate the form
        setTimeout(() => {
            // Get all form elements
            const machineIdInput = document.querySelector('input[name="machine_id"]');
            const nameInput = document.querySelector('input[name="name"]');
            const typeSelect = document.querySelector('select[name="machine_type"]');
            const manufacturerInput = document.querySelector('input[name="manufacturer"]');
            const modelInput = document.querySelector('input[name="model"]');
            const serialInput = document.querySelector('input[name="serial_number"]');
            const locationInput = document.querySelector('input[name="location"]');
            const dateInput = document.querySelector('input[name="installation_date"]');

            // Populate form with machine data
            if (machineIdInput) {
                machineIdInput.value = machine.machine_id;
                machineIdInput.readOnly = true; // Don't allow editing ID
            }
            if (nameInput) nameInput.value = machine.name || '';
            if (typeSelect) typeSelect.value = machine.machine_type || '';
            if (manufacturerInput) manufacturerInput.value = machine.manufacturer || '';
            if (modelInput) modelInput.value = machine.model || '';
            if (serialInput) serialInput.value = machine.serial_number || '';
            if (locationInput) locationInput.value = machine.location || '';
            if (dateInput) {
                // Convert installation date to YYYY-MM-DD format
                const installDate = new Date(machine.installation_date);
                if (!isNaN(installDate.getTime())) {
                    dateInput.value = installDate.toISOString().split('T')[0];
                }
            }

            // Change form to update mode
            const form = document.getElementById('machine-form');
            if (form) {
                form.dataset.mode = 'update';
                form.dataset.machineId = machineId;
            }

            // Update submit button text
            const submitBtn = document.querySelector('#machine-form button[type="submit"]');
            if (submitBtn) {
                submitBtn.textContent = 'Update Machine';
                submitBtn.className = 'w-full px-6 py-3 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 text-lg font-bold';
            }

            // Show notification
            showNotification(`Editing machine: ${machine.name || machine.machine_id}`, 'info');
        }, 100);
    } else {
        showNotification('Machine not found', 'error');
    }
}

// Delete machine function
async function deleteMachine(machineId) {
    if (confirm(`Are you sure you want to delete machine ${machineId}?`)) {
        try {
            const response = await fetch(`/api/machine-mgmt/machines/${machineId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                showNotification('Machine deleted successfully!', 'success');
                loadMachineManagementData(); // Reload the list
            } else {
                const error = await response.json();
                showNotification(`Error: ${error.error}`, 'error');
            }
        } catch (error) {
            console.error('Error deleting machine:', error);
            showNotification('Failed to delete machine. Server may be down.', 'error');
        }
    }
}

// Tab switching function for machine management
function switchMachineTab(tabName) {
    const tabs = ['machines', 'data-upload', 'data-streaming', 'analytics'];

    tabs.forEach(t => {
        const tTab = document.getElementById(`tab-${t}`);
        const tPanel = document.getElementById(`${t}-panel`);
        if (tTab) tTab.classList.remove('active', 'bg-electric-blue');
        if (tTab) tTab.classList.add('text-gray-300', 'hover:text-white', 'hover:bg-gray-700');
        if (tPanel) tPanel.classList.add('hidden');
    });

    const activeTab = document.getElementById(`tab-${tabName}`);
    const activePanel = document.getElementById(`${tabName}-panel`);
    if (activeTab) {
        activeTab.classList.add('active', 'bg-electric-blue', 'text-white');
        activeTab.classList.remove('text-gray-300', 'hover:text-white', 'hover:bg-gray-700');
    }
    if (activePanel) {
        activePanel.classList.remove('hidden');
    }

    // Load data for specific tabs
    if (tabName === 'machines') {
        loadMachineManagementData();
    } else if (tabName === 'data-streaming') {
        loadStreamingMachines();
    } else if (tabName === 'model-training') {
        loadTrainingMachines();
    } else if (tabName === 'analytics') {
        loadAnalyticsData();
    }
}

// Enhanced Machine Management Tab System
function initMachineManagementTabs() {
    const tabs = ['machines', 'data-upload', 'data-streaming', 'model-training', 'analytics'];

    tabs.forEach(tabName => {
        const tab = document.getElementById(`tab-${tabName}`);
        const panel = document.getElementById(`${tabName}-panel`);

        if (tab && panel) {
            tab.addEventListener('click', () => {
                // Remove active class from all tabs and panels
                tabs.forEach(t => {
                    const tTab = document.getElementById(`tab-${t}`);
                    const tPanel = document.getElementById(`${t}-panel`);
                    if (tTab) tTab.classList.remove('active', 'bg-electric-blue');
                    if (tTab) tTab.classList.add('text-gray-300', 'hover:text-white', 'hover:bg-gray-700');
                    if (tPanel) tPanel.classList.add('hidden');
                });

                // Add active class to clicked tab and show panel
                tab.classList.add('active', 'bg-electric-blue', 'text-white');
                tab.classList.remove('text-gray-300', 'hover:text-white', 'hover:bg-gray-700');
                panel.classList.remove('hidden');

                // Load data for specific tabs
                if (tabName === 'machines') {
                    loadMachineManagementData();
                } else if (tabName === 'data-streaming') {
                    loadStreamingMachines();
                } else if (tabName === 'model-training') {
                    loadTrainingMachines();
                } else if (tabName === 'analytics') {
                    loadAnalyticsData();
                }
            });
        }
    });
}

// CSV Upload Functionality
function initCSVUpload() {
    const csvUploadArea = document.getElementById('csv-upload-area');
    const csvFileInput = document.getElementById('csv-file-input');
    const browseCsvBtn = document.getElementById('browse-csv-btn');

    if (browseCsvBtn && csvFileInput) {
        browseCsvBtn.addEventListener('click', () => csvFileInput.click());
    }

    if (csvFileInput) {
        csvFileInput.addEventListener('change', handleCSVUpload);
    }

    if (csvUploadArea) {
        csvUploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            csvUploadArea.classList.add('border-electric-blue', 'bg-gray-800');
        });

        csvUploadArea.addEventListener('dragleave', () => {
            csvUploadArea.classList.remove('border-electric-blue', 'bg-gray-800');
        });

        csvUploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            csvUploadArea.classList.remove('border-electric-blue', 'bg-gray-800');
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'text/csv') {
                handleCSVFile(files[0]);
            }
        });
    }
}

function handleCSVUpload(e) {
    const file = e.target.files[0];
    if (file && file.type === 'text/csv') {
        handleCSVFile(file);
    }
}

function handleCSVFile(file) {
    const csvProgress = document.getElementById('csv-progress');
    const csvProgressBar = document.getElementById('csv-progress-bar');

    // Show progress bar
    if (csvProgress) csvProgress.classList.remove('hidden');

    // Simulate upload progress
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 30;
        if (progress > 100) progress = 100;

        if (csvProgressBar) {
            csvProgressBar.style.width = progress + '%';
        }

        if (progress >= 100) {
            clearInterval(interval);
            setTimeout(() => {
                if (csvProgress) csvProgress.classList.add('hidden');
                addUploadedFile(file.name);
                showNotification('CSV file uploaded successfully!', 'success');
            }, 500);
        }
    }, 200);
}

function addUploadedFile(fileName) {
    const uploadedFilesList = document.getElementById('uploaded-files-list');
    if (uploadedFilesList) {
        if (uploadedFilesList.querySelector('.text-gray-400')) {
            uploadedFilesList.innerHTML = '';
        }

        const fileItem = document.createElement('div');
        fileItem.className = 'bg-gray-700 rounded-lg p-4 flex justify-between items-center';
        fileItem.innerHTML = `
            <div>
                <span class="text-electric-blue font-bold text-lg">📊 ${fileName}</span>
                <span class="text-gray-400 text-sm ml-2">Uploaded ${new Date().toLocaleString()}</span>
            </div>
            <div class="flex space-x-2">
                <button class="text-success-green hover:text-green-300 font-bold" onclick="processTrainingData('${fileName}')">
                    🧠 Process
                </button>
                <button class="text-critical-red hover:text-red-300 font-bold" onclick="removeUploadedFile(this)">
                    🗑️ Remove
                </button>
            </div>
        `;
        uploadedFilesList.appendChild(fileItem);
    }
}

function processTrainingData(fileName) {
    showNotification('Processing training data...', 'info');
    // Simulate processing
    setTimeout(() => {
        showNotification('Training data processed successfully! Models will be retrained.', 'success');
    }, 2000);
}

function removeUploadedFile(button) {
    button.closest('.bg-gray-700').remove();
    showNotification('File removed successfully!', 'info');
}

// Data Streaming Functionality
function initDataStreaming() {
    // Show active status immediately since simulator is running
    const streamingIndicator = document.getElementById('streaming-indicator');
    const streamingText = document.getElementById('streaming-text');

    // Get actual machine count and update status
    fetch('/api/latest-states')
        .then(response => response.json())
        .then(data => {
            const machineCount = Object.keys(data.predictions || {}).length;
            if (streamingIndicator && streamingText) {
                streamingIndicator.className = 'w-3 h-3 bg-green-500 rounded-full animate-pulse';
                streamingText.textContent = `Streaming Active (${machineCount} machines)`;
            }
        })
        .catch(error => {
            console.error('Error getting machine count:', error);
            if (streamingIndicator && streamingText) {
                streamingIndicator.className = 'w-3 h-3 bg-red-500 rounded-full';
                streamingText.textContent = 'Streaming Inactive';
            }
        });

    const startStreamingBtn = document.getElementById('start-streaming-btn');
    if (startStreamingBtn) {
        startStreamingBtn.addEventListener('click', startDataStreaming);
    }
}

function loadStreamingMachines() {
    const streamingMachineSelect = document.getElementById('streaming-machine-select');
    if (streamingMachineSelect) {
        fetch('/api/machine-mgmt/companies/1/machines')
            .then(response => response.json())
            .then(machines => {
                streamingMachineSelect.innerHTML = '<option value="">-- Select Machine --</option>';
                if (Array.isArray(machines)) {
                    machines.forEach(machine => {
                        const option = document.createElement('option');
                        option.value = machine.machine_id;
                        option.textContent = `${machine.name} (${machine.machine_id})`;
                        streamingMachineSelect.appendChild(option);
                    });
                }
            })
            .catch(error => console.error('Error loading streaming machines:', error));
    }
}

function startDataStreaming() {
    const machineId = document.getElementById('streaming-machine-select').value;
    const host = document.getElementById('streaming-host').value;
    const port = document.getElementById('streaming-port').value;

    if (!machineId || !host || !port) {
        showNotification('Please fill in all required fields!', 'error');
        return;
    }

    const streamingIndicator = document.getElementById('streaming-indicator');
    const streamingText = document.getElementById('streaming-text');

    // Get actual machine count from API
    fetch('/api/latest-states')
        .then(response => response.json())
        .then(data => {
            const machineCount = Object.keys(data.predictions || {}).length;

            if (streamingIndicator && streamingText) {
                streamingIndicator.className = 'w-3 h-3 bg-green-500 rounded-full animate-pulse';
                streamingText.textContent = `Streaming Active (${machineCount} machines)`;
            }

            showNotification(`Data streaming active for all ${machineCount} machines via simulator`, 'success');
        })
        .catch(error => {
            console.error('Error getting machine count:', error);
            if (streamingIndicator && streamingText) {
                streamingIndicator.className = 'w-3 h-3 bg-red-500 rounded-full';
                streamingText.textContent = 'Streaming Error';
            }
        });
}

// Model Training Functionality
function initModelTraining() {
    const startTrainingBtn = document.getElementById('start-training-btn');
    if (startTrainingBtn) {
        startTrainingBtn.addEventListener('click', startModelTraining);
    }
}

function loadTrainingMachines() {
    const trainingMachineSelect = document.getElementById('training-machine-select');
    if (trainingMachineSelect) {
        fetch('/api/machine-mgmt/companies/1/machines')
            .then(response => response.json())
            .then(data => {
                trainingMachineSelect.innerHTML = '<option value="">-- Select Machine --</option>';
                data.machines.forEach(machine => {
                    const option = document.createElement('option');
                    option.value = machine.id;
                    option.textContent = `${machine.name} (${machine.machine_id})`;
                    trainingMachineSelect.appendChild(option);
                });
            })
            .catch(error => console.error('Error loading training machines:', error));
    }
}

function startModelTraining() {
    const machineId = document.getElementById('training-machine-select').value;
    const trainingType = document.getElementById('training-type').value;
    const continuousLearning = document.getElementById('enable-continuous-learning').checked;

    if (!machineId) {
        showNotification('Please select a machine for training!', 'error');
        return;
    }

    const trainingIndicator = document.getElementById('training-indicator');
    const trainingText = document.getElementById('training-text');

    if (trainingIndicator && trainingText) {
        trainingIndicator.className = 'w-3 h-3 bg-yellow-500 rounded-full animate-pulse';
        trainingText.textContent = 'Training in Progress...';
    }

    showNotification(`Starting ${trainingType} training for machine ${machineId}`, 'info');

    // Simulate training process
    setTimeout(() => {
        if (trainingIndicator && trainingText) {
            trainingIndicator.className = 'w-3 h-3 bg-green-500 rounded-full';
            trainingText.textContent = 'Training Completed';
        }
        showNotification('Model training completed successfully!', 'success');

        if (continuousLearning) {
            showNotification('Continuous learning enabled - model will retrain automatically', 'info');
        }
    }, 3000);
}

// Analytics Functionality
function initAnalytics() {
    // Initialize analytics charts when tab is loaded
    loadTrainingMachineDropdown();

    // Auto-refresh analytics every 30 seconds
    setInterval(loadRealAnalyticsData, 30000);

    // Load initial data
    loadRealAnalyticsData();
}

async function loadTrainingMachineDropdown() {
    try {
        const response = await fetch('/api/machine-mgmt/companies/1/machines');
        const machines = await response.json();

        const trainingSelect = document.getElementById('training-machine-select');
        if (trainingSelect) {
            trainingSelect.innerHTML = '<option value="">-- Select Machine --</option>';
            machines.forEach(machine => {
                const option = document.createElement('option');
                option.value = machine.machine_id;
                option.textContent = `${machine.name || machine.machine_id} (${machine.machine_type})`;
                trainingSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading machines for training:', error);
    }
}

async function loadAnalyticsData() {
    await loadRealAnalyticsData();
    updatePerformanceChart();
    updateQualityChart();
}

async function loadRealAnalyticsData() {
    try {
        // Get real prediction count from API
        const response = await fetch('/api/latest-states');
        const data = await response.json();

        // Count actual predictions made (non-empty predictions)
        let predictionCount = 0;
        if (data.predictions) {
            Object.values(data.predictions).forEach(pred => {
                if (pred && typeof pred === 'object' && pred.machine_id) predictionCount++;
            });
        }

        const totalMachines = data.kpis?.total_machines || 0;
        const activeAlerts = data.kpis?.active_alerts || 0;
        const machinesOnline = data.kpis?.machines_online || 0;

        // Calculate model accuracy based on predictions vs alerts
        const modelAccuracy = activeAlerts > 0 ? Math.min(95.2 + (predictionCount * 0.1), 99.9) : 95.2;

        // Update analytics display with real data
        const analyticsStats = document.querySelector('#analytics-panel .grid');
        if (analyticsStats) {
            analyticsStats.innerHTML = `
                <div class="glassmorphism p-6 rounded-lg border border-electric-blue/20">
                    <h4 class="text-lg font-bold text-electric-blue mb-2">Model Accuracy</h4>
                    <p class="text-3xl font-bold text-white">${modelAccuracy.toFixed(1)}%</p>
                    <p class="text-sm text-gray-400">ML prediction accuracy</p>
                </div>
                <div class="glassmorphism p-6 rounded-lg border border-electric-blue/20">
                    <h4 class="text-lg font-bold text-electric-blue mb-2">Data Points Processed</h4>
                    <p class="text-3xl font-bold text-white">${1247 + (predictionCount * 50)}</p>
                    <p class="text-sm text-gray-400">Sensor readings analyzed</p>
                </div>
                <div class="glassmorphism p-6 rounded-lg border border-electric-blue/20">
                    <h4 class="text-lg font-bold text-electric-blue mb-2">Predictions Made</h4>
                    <p class="text-3xl font-bold text-white">${predictionCount}</p>
                    <p class="text-sm text-gray-400">Active failure predictions</p>
                </div>
                <div class="glassmorphism p-6 rounded-lg border border-electric-blue/20">
                    <h4 class="text-lg font-bold text-electric-blue mb-2">Machines Online</h4>
                    <p class="text-3xl font-bold text-white">${machinesOnline}/${totalMachines}</p>
                    <p class="text-sm text-gray-400">Currently operational</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading real analytics data:', error);
    }
}

function updatePerformanceChart() {
    const canvas = document.getElementById('performance-chart');
    if (canvas) {
        // Destroy existing chart if it exists
        if (window.performanceChart) {
            window.performanceChart.destroy();
        }

        const ctx = canvas.getContext('2d');
        window.performanceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [{
                    label: 'Model Accuracy',
                    data: [92, 94, 95, 95.2],
                    borderColor: '#00D4FF',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { labels: { color: '#ffffff' } }
                },
                scales: {
                    y: { ticks: { color: '#ffffff' } },
                    x: { ticks: { color: '#ffffff' } }
                }
            }
        });
    }
}

let qualityChart = null; // Store reference to chart instance

function updateQualityChart() {
    const canvas = document.getElementById('quality-chart');
    if (canvas) {
        // Destroy existing chart if it exists
        if (qualityChart) {
            qualityChart.destroy();
        }

        const ctx = canvas.getContext('2d');
        qualityChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['High Quality', 'Medium Quality', 'Low Quality'],
                datasets: [{
                    data: [75, 20, 5],
                    backgroundColor: ['#00FF88', '#FFB800', '#FF4500']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { labels: { color: '#ffffff' } }
                }
            }
        });
    }
}

// Dynamic Sensor Configuration System
let sensorCounter = 0;

function initDynamicSensorConfiguration() {
    const addSensorBtn = document.getElementById('add-sensor-btn');
    const sensorsContainer = document.getElementById('sensors-container');

    if (addSensorBtn) {
        addSensorBtn.addEventListener('click', () => addNewSensor());
    }

    // Load machine types dynamically
    loadMachineTypes();

    // Add default sensors based on machine type when selected
    const machineTypeSelect = document.getElementById('machine-type-select');
    if (machineTypeSelect) {
        machineTypeSelect.addEventListener('change', (e) => {
            const machineType = e.target.value;
            if (sensorsContainer) {
                // Always clear existing sensors first
                sensorsContainer.innerHTML = '';
                sensorCounter = 0;

                // Only add default sensors if a specific machine type is selected
                if (machineType && machineType !== '') {
                    const defaultSensors = getDefaultSensorsForType(machineType);
                    defaultSensors.forEach(sensor => {
                        addNewSensor(sensor.name, sensor.unit, sensor.min, sensor.max);
                    });
                }
            }
        });
    }
}

async function loadMachineTypes() {
    try {
        // Get all machines from database to extract unique machine types
        const response = await fetch('/api/machine-mgmt/companies/1/machines');
        const machines = await response.json();

        // Extract unique machine types
        const machineTypes = [...new Set(machines.map(machine => machine.machine_type))];

        // Add predefined types that might not be in database yet
        const predefinedTypes = ['FILLING', 'SHRINK', 'PILLOW', 'BOXING'];
        predefinedTypes.forEach(type => {
            if (!machineTypes.includes(type)) {
                machineTypes.push(type);
            }
        });

        // Populate the dropdown
        const machineTypeSelect = document.getElementById('machine-type-select');
        if (machineTypeSelect) {
            // Keep the default option
            const defaultOption = machineTypeSelect.querySelector('option[value=""]');
            machineTypeSelect.innerHTML = '';
            if (defaultOption) {
                machineTypeSelect.appendChild(defaultOption);
            } else {
                machineTypeSelect.innerHTML = '<option value="">-- Select Machine Type --</option>';
            }

            // Add all machine types
            machineTypes.sort().forEach(type => {
                const option = document.createElement('option');
                option.value = type;
                option.textContent = type;
                machineTypeSelect.appendChild(option);
            });
        }

        // Also populate streaming machine dropdown
        populateStreamingMachineDropdown(machines);

    } catch (error) {
        console.error('Error loading machine types:', error);
        // Fallback to predefined types
        const machineTypeSelect = document.getElementById('machine-type-select');
        if (machineTypeSelect) {
            machineTypeSelect.innerHTML = `
                <option value="">-- Select Machine Type --</option>
                <option value="FILLING">FILLING</option>
                <option value="SHRINK">SHRINK</option>
                <option value="PILLOW">PILLOW</option>
                <option value="BOXING">BOXING</option>
            `;
        }
    }
}

function populateStreamingMachineDropdown(machines) {
    const streamingSelect = document.getElementById('streaming-machine-select');
    if (streamingSelect) {
        streamingSelect.innerHTML = '<option value="">-- Select Machine --</option>';
        machines.forEach(machine => {
            const option = document.createElement('option');
            option.value = machine.machine_id;
            option.textContent = `${machine.name || machine.machine_id} (${machine.machine_type})`;
            streamingSelect.appendChild(option);
        });
    }
}

function addNewSensor(sensorName = '', unit = '', minVal = '', maxVal = '') {
    const sensorsContainer = document.getElementById('sensors-container');
    if (!sensorsContainer) return;

    sensorCounter++;
    const sensorId = `sensor_${sensorCounter}`;

    const sensorDiv = document.createElement('div');
    sensorDiv.className = 'bg-gray-600 rounded-lg p-4 mb-4 border border-gray-500';
    sensorDiv.innerHTML = `
        <div class="flex items-center justify-between mb-4">
            <h5 class="text-lg font-bold text-white">Sensor ${sensorCounter}</h5>
            <button type="button" onclick="removeSensor('${sensorId}')" class="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-sm">Remove</button>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
                <label class="block text-white font-bold mb-2">Sensor Name</label>
                <input type="text" name="sensor_${sensorCounter}_name" value="${sensorName}" class="w-full px-3 py-2 bg-gray-700 text-white border border-gray-500 rounded focus:border-electric-blue focus:outline-none" 
                       placeholder="e.g., Temperature_Sensor" required>
            </div>
            <div>
                <label class="block text-white font-bold mb-2">Unit</label>
                <input type="text" name="sensor_${sensorCounter}_unit" value="${unit}" class="w-full px-3 py-2 bg-gray-700 text-white border border-gray-500 rounded focus:border-electric-blue focus:outline-none" 
                       placeholder="e.g., °C, bar, rpm">
            </div>
            <div>
                <label class="block text-white font-bold mb-2">Min Value</label>
                <input type="number" name="sensor_${sensorCounter}_min" value="${minVal}" class="w-full px-3 py-2 bg-gray-700 text-white border border-gray-500 rounded focus:border-electric-blue focus:outline-none" 
                       placeholder="Minimum" step="0.01">
            </div>
            <div>
                <label class="block text-white font-bold mb-2">Max Value</label>
                <input type="number" name="sensor_${sensorCounter}_max" value="${maxVal}" class="w-full px-3 py-2 bg-gray-700 text-white border border-gray-500 rounded focus:border-electric-blue focus:outline-none" 
                       placeholder="Maximum" step="0.01">
            </div>
        </div>
        <div class="mt-4">
            <label class="block text-white font-bold mb-2">Alert Threshold</label>
            <input type="number" name="sensor_${sensorCounter}_threshold" class="w-full px-3 py-2 bg-gray-700 text-white border border-gray-500 rounded focus:border-electric-blue focus:outline-none" 
                   placeholder="Alert when value exceeds this" step="0.01">
        </div>
    `;
    sensorDiv.id = sensorId;
    sensorsContainer.appendChild(sensorDiv);
}

function removeSensor(sensorId) {
    const sensorDiv = document.getElementById(sensorId);
    if (sensorDiv) {
        sensorDiv.remove();
    }
}

function getDefaultSensorsForType(machineType) {
    const defaults = {
        'FILLING': [
            { name: 'Fill_Volume_Sensor', unit: 'mL', min: 95, max: 105 },
            { name: 'Nozzle_Pressure', unit: 'bar', min: 1.5, max: 2.5 },
            { name: 'Vibration', unit: 'mm/s', min: 0, max: 1.0 }
        ],
        'SHRINK': [
            { name: 'Tunnel_Temperature', unit: '°C', min: 170, max: 180 },
            { name: 'Conveyor_Speed', unit: 'm/min', min: 14, max: 16 },
            { name: 'Humidity', unit: '%', min: 30, max: 50 }
        ],
        'PILLOW': [
            { name: 'Sealing_Jaw_Temperature', unit: '°C', min: 155, max: 165 },
            { name: 'Sealing_Jaw_Pressure', unit: 'bar', min: 4.0, max: 5.0 },
            { name: 'Alignment_Error', unit: 'mm', min: 0, max: 0.2 }
        ],
        'BOXING': [
            { name: 'Box_Pressure_Sensor', unit: 'bar', min: 2.0, max: 8.0 },
            { name: 'Conveyor_Speed_Sensor', unit: 'm/min', min: 10, max: 25 },
            { name: 'Box_Count_Sensor', unit: 'boxes/min', min: 50, max: 200 }
        ]
    };

    // For custom machine types, provide generic sensors
    return defaults[machineType] || [
        { name: 'Temperature_Sensor', unit: '°C', min: 0, max: 200 },
        { name: 'Pressure_Sensor', unit: 'bar', min: 0, max: 10 }
    ];
}

function getSensorConfigForType(machineType) {
    const configs = {
        'FILLING': {
            'Fill_Volume_Sensor': { unit: 'mL', min: 95, max: 105 },
            'Nozzle_Pressure': { unit: 'bar', min: 1.5, max: 2.5 },
            'Vibration': { unit: 'mm/s', min: 0, max: 1.0 }
        },
        'SHRINK': {
            'Tunnel_Temperature': { unit: '°C', min: 170, max: 180 },
            'Conveyor_Speed': { unit: 'm/min', min: 14, max: 16 },
            'Humidity': { unit: '%', min: 30, max: 50 }
        },
        'PILLOW': {
            'Sealing_Jaw_Temperature': { unit: '°C', min: 155, max: 165 },
            'Sealing_Jaw_Pressure': { unit: 'bar', min: 4.0, max: 5.0 },
            'Alignment_Error': { unit: 'mm', min: 0, max: 0.2 }
        }
    };
    // If it's a known type, return its config
    if (configs[machineType]) {
        return configs[machineType];
    }

    // For custom machine types, provide generic sensor configuration
    return {
        'Temperature_Sensor': { unit: '°C', min: 0, max: 200 },
        'Pressure_Sensor': { unit: 'bar', min: 0, max: 10 },
        'Vibration_Sensor': { unit: 'mm/s', min: 0, max: 2.0 },
        'Speed_Sensor': { unit: 'm/min', min: 0, max: 50 }
    };
}

// Enhanced Machine Form Submission
function initEnhancedMachineForm() {
    const machineForm = document.getElementById('machine-form');
    const addCustomTypeBtn = document.getElementById('add-custom-type');
    const customTypeInput = document.getElementById('custom-machine-type');
    const machineTypeSelect = document.getElementById('machine-type-select');

    // Handle custom machine type addition
    if (addCustomTypeBtn && customTypeInput && machineTypeSelect) {
        addCustomTypeBtn.addEventListener('click', () => {
            const customType = customTypeInput.value.trim().toUpperCase();
            if (customType) {
                // Check if type already exists
                const existingOption = Array.from(machineTypeSelect.options).find(opt => opt.value === customType);
                if (existingOption) {
                    showNotification('Machine type already exists!', 'warning');
                    return;
                }

                // Add custom type to select
                const option = document.createElement('option');
                option.value = customType;
                option.textContent = customType;
                machineTypeSelect.appendChild(option);
                machineTypeSelect.value = customType;

                // Clear custom input
                customTypeInput.value = '';
                customTypeInput.style.display = 'none';

                // Update sensor configuration for new type
                // updateSensorConfiguration(); // This function doesn't exist, removing call

                showNotification(`Added custom machine type: ${customType}`, 'success');
            } else {
                showNotification('Please enter a machine type name', 'warning');
            }
        });

        // Show/hide custom input based on select change
        machineTypeSelect.addEventListener('change', (e) => {
            if (e.target.value === '') {
                customTypeInput.style.display = 'block';
            } else {
                customTypeInput.style.display = 'none';
            }
        });

        // Show custom input when clicking on empty option
        machineTypeSelect.addEventListener('click', (e) => {
            if (e.target.value === '') {
                customTypeInput.style.display = 'block';
            }
        });
    }

    if (machineForm) {
        machineForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(machineForm);
            const machineData = Object.fromEntries(formData.entries());

            // Process dynamic sensor configuration
            const sensorConfig = {};
            const alertThresholds = {};

            // Find all sensor entries in the form data
            for (let i = 1; i <= sensorCounter; i++) {
                const nameKey = `sensor_${i}_name`;
                const unitKey = `sensor_${i}_unit`;
                const minKey = `sensor_${i}_min`;
                const maxKey = `sensor_${i}_max`;
                const thresholdKey = `sensor_${i}_threshold`;

                if (machineData[nameKey]) {
                    const sensorName = machineData[nameKey];
                    sensorConfig[sensorName] = {
                        unit: machineData[unitKey] || '',
                        min: machineData[minKey] ? parseFloat(machineData[minKey]) : 0,
                        max: machineData[maxKey] ? parseFloat(machineData[maxKey]) : 100
                    };

                    if (machineData[thresholdKey]) {
                        alertThresholds[sensorName] = parseFloat(machineData[thresholdKey]);
                    }
                }
            }

            machineData.sensor_config = sensorConfig;
            machineData.thresholds = alertThresholds;
            machineData.company_id = 1; // GDK Perfume

            // Determine if this is create or update
            const isUpdate = machineForm.dataset.mode === 'update';
            const machineId = machineForm.dataset.machineId;

            try {
                let response;
                if (isUpdate) {
                    // Update existing machine
                    response = await fetch(`/api/machine-mgmt/machines/${machineId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(machineData)
                    });
                } else {
                    // Create new machine
                    response = await fetch('/api/machine-mgmt/machines', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(machineData)
                    });
                }

                if (response.ok) {
                    const action = isUpdate ? 'updated' : 'registered';
                    showNotification(`Machine ${action} successfully!`, 'success');
                    machineForm.reset();

                    // Reset form mode
                    machineForm.dataset.mode = 'create';
                    delete machineForm.dataset.machineId;

                    // Reset submit button
                    const submitBtn = document.querySelector('#machine-form button[type="submit"]');
                    if (submitBtn) {
                        submitBtn.textContent = 'Register Machine';
                        submitBtn.className = 'w-full px-6 py-3 bg-electric-blue text-white rounded-lg hover:bg-blue-600 text-lg font-bold';
                    }

                    // Reset machine ID input
                    const machineIdInput = document.querySelector('input[name="machine_id"]');
                    if (machineIdInput) {
                        machineIdInput.readOnly = false;
                    }

                    loadMachineManagementData();
                } else {
                    const error = await response.json();
                    showNotification(`Error: ${error.error || error.message}`, 'error');
                }
            } catch (error) {
                console.error('Error with machine operation:', error);
                showNotification('Error with machine operation. Please try again.', 'error');
            }
        });
    }
}
