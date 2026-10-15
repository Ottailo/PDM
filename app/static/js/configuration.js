// Configuration Management Logic

document.addEventListener('DOMContentLoaded', () => {
    // Load data when config tab is clicked
    const configTab = document.getElementById('tab-config');
    if (configTab) {
        configTab.addEventListener('click', () => {
            loadTemplates();
            loadAssets();
        });
    }
});

// --- Templates ---

async function loadTemplates() {
    try {
        const response = await fetch('/api/config/templates');
        if (!response.ok) throw new Error('Failed to fetch templates');
        const templates = await response.json();
        renderTemplatesTable(templates);
        updateAssetTemplateOptions(templates); // Update dropdown in Asset modal
    } catch (error) {
        console.error('Error loading templates:', error);
        showNotification('Error loading templates', 'error');
    }
}

function renderTemplatesTable(templates) {
    const tbody = document.getElementById('templates-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    templates.forEach(t => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-[var(--pdm-surface-raised)] border-b border-[var(--pdm-border-hairline)] transition-colors';
        tr.innerHTML = `
            <td class="px-5 py-3 font-mono font-medium text-xs text-[var(--pdm-text-primary)]">${t.name}</td>
            <td class="px-5 py-3 text-xs text-[var(--pdm-text-secondary)]">${t.description || '-'}</td>
            <td class="px-5 py-3 font-mono text-xs text-[var(--pdm-text-muted)]">${t.version || '-'}</td>
            <td class="px-5 py-3 text-right">
                <div class="flex items-center justify-end gap-1.5">
                    <button onclick="openEditTemplateModal(${t.id})" class="pdm-btn text-xs py-1 px-2 h-7 bg-transparent border-transparent hover:border-[var(--pdm-border-subtle)] text-[var(--pdm-text-secondary)] hover:text-[var(--pdm-accent-base)]" title="Edit Template">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
                        </svg>
                    </button>
                    <button onclick="deleteTemplate(${t.id})" class="pdm-btn text-xs py-1 px-2 h-7 bg-transparent border-transparent hover:border-[var(--pdm-status-critical)] text-[var(--pdm-text-muted)] hover:text-[var(--pdm-status-critical)]" title="Delete Template">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Assets ---

async function loadAssets() {
    try {
        const response = await fetch('/api/config/assets');
        if (!response.ok) throw new Error('Failed to fetch assets');
        const assets = await response.json();
        renderAssetsTable(assets);
    } catch (error) {
        console.error('Error loading assets:', error);
        showNotification('Error loading assets', 'error');
    }
}

function renderAssetsTable(assets) {
    const tbody = document.getElementById('assets-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    assets.forEach(a => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-[var(--pdm-surface-raised)] border-b border-[var(--pdm-border-hairline)] transition-colors';
        tr.innerHTML = `
            <td class="px-5 py-3 font-mono font-medium text-xs text-[var(--pdm-text-primary)]">${a.name}</td>
            <td class="px-5 py-3 text-xs text-[var(--pdm-text-secondary)]">${a.template_name}</td>
            <td class="px-5 py-3 text-xs text-[var(--pdm-text-secondary)]">${a.location_name || '-'}</td>
            <td class="px-5 py-3">
                <span class="${a.status === 'Active' ? 'pdm-tag pdm-tag-normal' : 'pdm-tag bg-[var(--pdm-surface-sunken)] text-[var(--pdm-text-muted)] border-[var(--pdm-border-hairline)]'}">
                    ${a.status.toUpperCase()}
                </span>
            </td>
            <td class="px-5 py-3 text-right">
                <div class="flex items-center justify-end gap-1.5">
                    <button onclick="openEditAssetModal(${a.id})" class="pdm-btn text-xs py-1 px-2 h-7 bg-transparent border-transparent hover:border-[var(--pdm-border-subtle)] text-[var(--pdm-text-secondary)] hover:text-[var(--pdm-accent-base)]" title="Edit Asset">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
                        </svg>
                    </button>
                    <button onclick="deleteAsset(${a.id})" class="pdm-btn text-xs py-1 px-2 h-7 bg-transparent border-transparent hover:border-[var(--pdm-status-critical)] text-[var(--pdm-text-muted)] hover:text-[var(--pdm-status-critical)]" title="Delete Asset">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Modals ---

function openAddTemplateModal() {
    document.getElementById('add-template-modal').classList.remove('hidden');
}

function closeAddTemplateModal() {
    document.getElementById('add-template-modal').classList.add('hidden');
    document.getElementById('add-template-form').reset();
}

async function submitAddTemplate() {
    const form = document.getElementById('add-template-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/api/config/templates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showNotification('Template created successfully', 'success');
            closeAddTemplateModal();
            loadTemplates();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to create template', 'error');
        }
    } catch (error) {
        console.error('Error creating template:', error);
        showNotification('Network error', 'error');
    }
}

// --- Edit Template Functions ---

async function openEditTemplateModal(id) {
    try {
        const response = await fetch(`/api/config/templates/${id}`);
        if (!response.ok) throw new Error('Failed to fetch template');
        const template = await response.json();

        document.getElementById('edit-template-id').value = template.id;
        document.getElementById('edit-template-name').value = template.name;
        document.getElementById('edit-template-description').value = template.description || '';
        document.getElementById('edit-template-manufacturer').value = template.manufacturer || '';
        document.getElementById('edit-template-version').value = template.version || '';

        document.getElementById('edit-template-modal').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading template:', error);
        showNotification('Error loading template', 'error');
    }
}

function closeEditTemplateModal() {
    document.getElementById('edit-template-modal').classList.add('hidden');
    document.getElementById('edit-template-form').reset();
}

async function submitEditTemplate() {
    const form = document.getElementById('edit-template-form');
    const formData = new FormData(form);
    const id = formData.get('id');
    const data = Object.fromEntries(formData.entries());
    delete data.id; // Remove id from data payload

    try {
        const response = await fetch(`/api/config/templates/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showNotification('Template updated successfully', 'success');
            closeEditTemplateModal();
            loadTemplates();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to update template', 'error');
        }
    } catch (error) {
        console.error('Error updating template:', error);
        showNotification('Network error', 'error');
    }
}

function openAddAssetModal() {
    document.getElementById('add-asset-modal').classList.remove('hidden');
    loadLocations(); // Load locations when opening modal
}

function closeAddAssetModal() {
    document.getElementById('add-asset-modal').classList.add('hidden');
    document.getElementById('add-asset-form').reset();
}

async function submitAddAsset() {
    const form = document.getElementById('add-asset-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    // Add default company ID (hardcoded for now, or fetch from user context)
    data.company_id = 1;

    try {
        const response = await fetch('/api/config/assets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showNotification('Asset created successfully', 'success');
            closeAddAssetModal();
            loadAssets();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to create asset', 'error');
        }
    } catch (error) {
        console.error('Error creating asset:', error);
        showNotification('Network error', 'error');
    }
}

// --- Edit Asset Functions ---

async function openEditAssetModal(id) {
    try {
        const response = await fetch(`/api/config/assets/${id}`);
        if (!response.ok) throw new Error('Failed to fetch asset');
        const asset = await response.json();

        document.getElementById('edit-asset-id').value = asset.id;
        document.getElementById('edit-asset-name').value = asset.name;
        document.getElementById('edit-asset-serial').value = asset.serial_number || '';
        document.getElementById('edit-asset-status').value = asset.status || 'Active';

        //Load locations and set selected
        await loadLocationsForEdit();
        document.getElementById('edit-asset-location').value = asset.location_id || '';

        document.getElementById('edit-asset-modal').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading asset:', error);
        showNotification('Error loading asset', 'error');
    }
}

function closeEditAssetModal() {
    document.getElementById('edit-asset-modal').classList.add('hidden');
    document.getElementById('edit-asset-form').reset();
}

async function submitEditAsset() {
    const form = document.getElementById('edit-asset-form');
    const formData = new FormData(form);
    const id = formData.get('id');
    const data = Object.fromEntries(formData.entries());
    delete data.id; // Remove id from data payload

    try {
        const response = await fetch(`/api/config/assets/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showNotification('Asset updated successfully', 'success');
            closeEditAssetModal();
            loadAssets();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to update asset', 'error');
        }
    } catch (error) {
        console.error('Error updating asset:', error);
        showNotification('Network error', 'error');
    }
}

// --- Delete Functions ---

async function deleteTemplate(id) {
    if (!confirm('Are you sure you want to delete this template?')) return;
    try {
        const response = await fetch(`/api/config/templates/${id}`, { method: 'DELETE' });
        if (response.ok) {
            showNotification('Template deleted successfully', 'success');
            loadTemplates();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to delete template', 'error');
        }
    } catch (error) {
        console.error('Error deleting template:', error);
        showNotification('Network error', 'error');
    }
}

async function deleteAsset(id) {
    if (!confirm('Are you sure you want to delete this asset?')) return;
    try {
        const response = await fetch(`/api/config/assets/${id}`, { method: 'DELETE' });
        if (response.ok) {
            showNotification('Asset deleted successfully', 'success');
            loadAssets();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to delete asset', 'error');
        }
    } catch (error) {
        console.error('Error deleting asset:', error);
        showNotification('Network error', 'error');
    }
}

// --- Helpers ---

function updateAssetTemplateOptions(templates) {
    const select = document.getElementById('asset-template');
    if (!select) return;
    select.innerHTML = '<option value="">Select Template</option>';
    templates.forEach(t => {
        const option = document.createElement('option');
        option.value = t.id;
        option.textContent = t.name;
        select.appendChild(option);
    });
}

async function loadLocations() {
    try {
        const response = await fetch('/api/config/locations');
        if (response.ok) {
            const locations = await response.json();
            const select = document.getElementById('asset-location');
            if (!select) return;
            select.innerHTML = '<option value="">Select Location</option>';
            locations.forEach(l => {
                const option = document.createElement('option');
                option.value = l.id;
                option.textContent = l.name; // Could improve to show hierarchy
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading locations:', error);
    }
}

async function loadLocationsForEdit() {
    try {
        const response = await fetch('/api/config/locations');
        if (response.ok) {
            const locations = await response.json();
            const select = document.getElementById('edit-asset-location');
            if (!select) return;
            select.innerHTML = '<option value="">Select Location</option>';
            locations.forEach(l => {
                const option = document.createElement('option');
                option.value = l.id;
                option.textContent = l.name; // Could improve to show hierarchy
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading locations:', error);
    }
}
