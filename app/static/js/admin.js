// Admin Dashboard Logic

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadUsers();
    loadSystemStats();

    // Refresh stats every 30 seconds
    setInterval(loadSystemStats, 30000);
});

function initTabs() {
    const tabs = ['users', 'config', 'system', 'settings'];

    tabs.forEach(tab => {
        const btn = document.getElementById(`tab-${tab}`);
        const panel = document.getElementById(`panel-${tab}`);
        if (!btn || !panel) return;

        btn.addEventListener('click', () => {
            // Deactivate all
            tabs.forEach(t => {
                const b = document.getElementById(`tab-${t}`);
                const p = document.getElementById(`panel-${t}`);
                if (b) {
                    b.classList.remove('text-[var(--pdm-accent-base)]', 'border-b-2', 'border-[var(--pdm-accent-base)]', 'font-semibold');
                    b.classList.add('text-[var(--pdm-text-muted)]');
                }
                if (p) p.classList.add('hidden');
            });

            // Activate clicked
            btn.classList.add('text-[var(--pdm-accent-base)]', 'border-b-2', 'border-[var(--pdm-accent-base)]', 'font-semibold');
            btn.classList.remove('text-[var(--pdm-text-muted)]');
            panel.classList.remove('hidden');
        });
    });
}

async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users');
        if (!response.ok) throw new Error('Failed to fetch users');

        const users = await response.json();
        renderUsersTable(users);
        updateUserStats(users);
    } catch (error) {
        console.error('Error loading users:', error);
        showNotification('Error loading users', 'error');
    }
}

function renderUsersTable(users) {
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    users.forEach(user => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-[var(--pdm-surface-raised)] border-b border-[var(--pdm-border-hairline)] transition-colors';
        tr.innerHTML = `
            <td class="px-5 py-3 font-mono font-medium text-xs text-[var(--pdm-text-primary)]">${user.username}</td>
            <td class="px-5 py-3 font-mono text-xs text-[var(--pdm-text-secondary)]">${user.email}</td>
            <td class="px-5 py-3">
                <span class="${getRoleBadgeClass(user.role)}">
                    ${user.role.toUpperCase()}
                </span>
            </td>
            <td class="px-5 py-3 text-[var(--pdm-text-muted)] font-mono text-xs">${new Date(user.created_at).toLocaleDateString()}</td>
            <td class="px-5 py-3 text-right">
                <button onclick="deleteUser(${user.id})" class="pdm-btn text-xs py-1 px-2 h-7 bg-transparent border-transparent hover:border-[var(--pdm-status-critical)] text-[var(--pdm-text-muted)] hover:text-[var(--pdm-status-critical)]" title="Delete User">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function getRoleBadgeClass(role) {
    switch (role) {
        case 'admin': return 'pdm-tag pdm-tag-warning';
        case 'viewer': return 'pdm-tag bg-[var(--pdm-surface-sunken)] text-[var(--pdm-text-muted)] border-[var(--pdm-border-hairline)]';
        default: return 'pdm-tag pdm-tag-normal';
    }
}

function updateUserStats(users) {
    document.getElementById('total-users-count').textContent = users.length;
    document.getElementById('admin-users-count').textContent = users.filter(u => u.role === 'admin').length;
    // Active sessions would come from a real backend in prod
    document.getElementById('active-sessions-count').textContent = Math.floor(Math.random() * users.length) + 1;
}

// Modal Functions
function openAddUserModal() {
    document.getElementById('add-user-modal').classList.remove('hidden');
}

function closeAddUserModal() {
    document.getElementById('add-user-modal').classList.add('hidden');
    document.getElementById('add-user-form').reset();
}

async function submitAddUser() {
    const form = document.getElementById('add-user-form');
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/api/admin/users', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showNotification('User created successfully', 'success');
            closeAddUserModal();
            loadUsers();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to create user', 'error');
        }
    } catch (error) {
        console.error('Error creating user:', error);
        showNotification('Network error', 'error');
    }
}

async function deleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;

    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('User deleted successfully', 'success');
            loadUsers();
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to delete user', 'error');
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        showNotification('Network error', 'error');
    }
}

async function loadSystemStats() {
    try {
        const response = await fetch('/api/admin/system-stats');
        if (response.ok) {
            const stats = await response.json();
            // In a real app, update charts/graphs here
            console.log('System Stats:', stats);
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const borderClass = type === 'success' ? 'border-[var(--pdm-status-normal)]' :
        type === 'error' ? 'border-[var(--pdm-status-critical)]' :
            'border-[var(--pdm-accent-base)]';

    notification.className = `fixed top-4 right-4 z-50 p-3 bg-[var(--pdm-surface-overlay)] border ${borderClass} rounded-[var(--pdm-radius-sm)] shadow-[var(--pdm-shadow-overlay)] max-w-sm text-xs font-mono transition-opacity duration-200`;

    notification.innerHTML = `
        <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full ${type === 'success' ? 'bg-[var(--pdm-status-normal)]' : type === 'error' ? 'bg-[var(--pdm-status-critical)]' : 'bg-[var(--pdm-accent-base)]'}"></span>
            <span class="text-[var(--pdm-text-primary)]">${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 200);
    }, 4000);
}
