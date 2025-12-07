// Admin Dashboard Logic

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadUsers();
    loadSystemStats();

    // Refresh stats every 30 seconds
    setInterval(loadSystemStats, 30000);
});

function initTabs() {
    const tabs = ['users', 'system', 'settings'];

    tabs.forEach(tab => {
        const btn = document.getElementById(`tab-${tab}`);
        const panel = document.getElementById(`panel-${tab}`);

        btn.addEventListener('click', () => {
            // Deactivate all
            tabs.forEach(t => {
                document.getElementById(`tab-${t}`).classList.remove('text-electric-blue', 'border-b-2', 'border-electric-blue', 'font-semibold');
                document.getElementById(`tab-${t}`).classList.add('text-gray-400');
                document.getElementById(`panel-${t}`).classList.add('hidden');
            });

            // Activate clicked
            btn.classList.add('text-electric-blue', 'border-b-2', 'border-electric-blue', 'font-semibold');
            btn.classList.remove('text-gray-400');
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
    tbody.innerHTML = '';

    users.forEach(user => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-gray-700/50 transition-colors';
        tr.innerHTML = `
            <td class="px-6 py-4 font-medium text-white">${user.username}</td>
            <td class="px-6 py-4 text-gray-300">${user.email}</td>
            <td class="px-6 py-4">
                <span class="px-2 py-1 text-xs rounded-full ${getRoleBadgeClass(user.role)}">
                    ${user.role.toUpperCase()}
                </span>
            </td>
            <td class="px-6 py-4 text-gray-400 text-sm">${new Date(user.created_at).toLocaleDateString()}</td>
            <td class="px-6 py-4 text-right">
                <button onclick="deleteUser(${user.id})" class="text-gray-400 hover:text-critical-red transition-colors" title="Delete User">
                    🗑️
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function getRoleBadgeClass(role) {
    switch (role) {
        case 'admin': return 'bg-warning-amber/20 text-warning-amber border border-warning-amber/30';
        case 'viewer': return 'bg-gray-600 text-gray-200';
        default: return 'bg-electric-blue/20 text-electric-blue border border-electric-blue/30';
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
    // Reusing the notification system from dashboard.js if available, 
    // or creating a simple one here
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm ${type === 'success' ? 'bg-success-green text-deep-navy' :
            type === 'error' ? 'bg-critical-red text-white' :
                'bg-electric-blue text-white'
        }`;

    notification.innerHTML = `
        <div class="flex items-center">
            <span class="mr-2 font-bold">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}
