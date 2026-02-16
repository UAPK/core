// Admin Dashboard JavaScript
const API_BASE = '/api/v1';

// State
let currentTab = 'dashboard';
let clients = [];
let invoices = [];
let summary = {
    total_invoices: 0,
    total_revenue: 0,
    total_outstanding: 0,
    total_paid: 0,
    total_overdue: 0
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupModals();
    loadDashboard();
});

// Tab Management
function setupTabs() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.dataset.tab);
        });
    });
}

function switchTab(tabName) {
    currentTab = tabName;

    // Update nav
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `${tabName}-panel`);
    });

    // Load data for tab
    if (tabName === 'dashboard') loadDashboard();
    else if (tabName === 'clients') loadClients();
    else if (tabName === 'invoices') loadInvoices();
}

// API Calls
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        alert('Error: ' + error.message);
        throw error;
    }
}

// Dashboard
async function loadDashboard() {
    showLoading('dashboard-panel');

    try {
        // Load summary stats
        summary = await apiCall('/invoices/summary');

        // Load recent clients and invoices
        const [clientsData, invoicesData] = await Promise.all([
            apiCall('/clients?page=1&page_size=5'),
            apiCall('/invoices?page=1&page_size=5')
        ]);

        renderDashboard(clientsData, invoicesData);
    } catch (error) {
        showError('dashboard-panel', 'Failed to load dashboard');
    }
}

function renderDashboard(clientsData, invoicesData) {
    const panel = document.getElementById('dashboard-panel');

    panel.innerHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Revenue</div>
                <div class="stat-value">€${summary.total_revenue.toFixed(2)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Outstanding</div>
                <div class="stat-value">€${summary.total_outstanding.toFixed(2)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Invoices</div>
                <div class="stat-value">${summary.total_invoices}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Clients</div>
                <div class="stat-value">${clientsData.total}</div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Recent Invoices</h2>
                <button class="btn btn-primary btn-sm" onclick="switchTab('invoices')">View All</button>
            </div>
            <div class="card-body">
                ${invoicesData.invoices.length > 0 ? renderInvoiceTable(invoicesData.invoices) : '<p class="text-muted">No invoices yet</p>'}
            </div>
        </div>

        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Recent Clients</h2>
                <button class="btn btn-primary btn-sm" onclick="switchTab('clients')">View All</button>
            </div>
            <div class="card-body">
                ${clientsData.clients.length > 0 ? renderClientTable(clientsData.clients) : '<p class="text-muted">No clients yet</p>'}
            </div>
        </div>
    `;
}

// Clients
async function loadClients() {
    showLoading('clients-panel');

    try {
        const data = await apiCall('/clients?page=1&page_size=100');
        clients = data.clients;
        renderClients();
    } catch (error) {
        showError('clients-panel', 'Failed to load clients');
    }
}

function renderClients() {
    const panel = document.getElementById('clients-panel');

    panel.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Clients</h2>
                <button class="btn btn-primary" onclick="openCreateClientModal()">
                    + Add Client
                </button>
            </div>
            <div class="card-body">
                ${clients.length > 0 ? renderClientTable(clients) : renderEmptyState('No clients yet', 'Create your first client to get started')}
            </div>
        </div>
    `;
}

function renderClientTable(clientList) {
    return `
        <table class="table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Country</th>
                    <th>Revenue</th>
                    <th>Outstanding</th>
                    <th>Invoices</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${clientList.map(client => `
                    <tr>
                        <td><strong>${escapeHtml(client.name)}</strong></td>
                        <td>${escapeHtml(client.billing_email || '-')}</td>
                        <td>${escapeHtml(client.country_code || '-')}</td>
                        <td>€${client.total_revenue.toFixed(2)}</td>
                        <td>€${client.outstanding_balance.toFixed(2)}</td>
                        <td>${client.total_invoices}</td>
                        <td>
                            <button class="btn btn-secondary btn-sm" onclick="openCreateInvoiceModal('${client.id}')">Create Invoice</button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Invoices
async function loadInvoices() {
    showLoading('invoices-panel');

    try {
        const data = await apiCall('/invoices?page=1&page_size=100');
        invoices = data.invoices;
        renderInvoices();
    } catch (error) {
        showError('invoices-panel', 'Failed to load invoices');
    }
}

function renderInvoices() {
    const panel = document.getElementById('invoices-panel');

    panel.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Invoices</h2>
            </div>
            <div class="card-body">
                ${invoices.length > 0 ? renderInvoiceTable(invoices) : renderEmptyState('No invoices yet', 'Create invoices from the Clients tab')}
            </div>
        </div>
    `;
}

function renderInvoiceTable(invoiceList) {
    return `
        <table class="table">
            <thead>
                <tr>
                    <th>Invoice #</th>
                    <th>Client</th>
                    <th>Date</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${invoiceList.map(invoice => `
                    <tr>
                        <td class="font-mono">${escapeHtml(invoice.invoice_number)}</td>
                        <td>${escapeHtml(invoice.organization_name || 'Unknown')}</td>
                        <td>${formatDate(invoice.issued_at)}</td>
                        <td><strong>€${invoice.total.toFixed(2)}</strong></td>
                        <td>${renderStatusBadge(invoice.status)}</td>
                        <td>
                            ${invoice.status !== 'paid' ? `<button class="btn btn-success btn-sm" onclick="markInvoicePaid('${invoice.id}')">Mark Paid</button>` : ''}
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Modals
function setupModals() {
    // Close modal when clicking outside
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function openCreateClientModal() {
    document.getElementById('client-form').reset();
    openModal('create-client-modal');
}

function openCreateInvoiceModal(clientId = '') {
    const form = document.getElementById('invoice-form');
    form.reset();
    if (clientId) {
        form.querySelector('[name="organization_id"]').value = clientId;
    }
    openModal('create-invoice-modal');
}

// Form Handlers
async function handleCreateClient(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    const data = {
        name: formData.get('name'),
        slug: formData.get('slug'),
        billing_email: formData.get('billing_email') || null,
        contact_name: formData.get('contact_name') || null,
        contact_email: formData.get('contact_email') || null,
        vat_id: formData.get('vat_id') || null,
        country_code: formData.get('country_code') || null,
        currency: formData.get('currency') || 'EUR'
    };

    try {
        await apiCall('/clients', {
            method: 'POST',
            body: JSON.stringify(data)
        });

        closeModal('create-client-modal');
        alert('Client created successfully!');
        loadClients();
    } catch (error) {
        // Error already shown by apiCall
    }
}

async function handleCreateInvoice(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    const data = {
        organization_id: formData.get('organization_id'),
        items: [{
            description: formData.get('description'),
            quantity: parseInt(formData.get('quantity')),
            unit_price: parseFloat(formData.get('unit_price'))
        }],
        customer_country: formData.get('customer_country') || null,
        due_days: parseInt(formData.get('due_days')) || 30
    };

    try {
        await apiCall('/invoices', {
            method: 'POST',
            body: JSON.stringify(data)
        });

        closeModal('create-invoice-modal');
        alert('Invoice created successfully!');
        loadInvoices();
        loadDashboard();
    } catch (error) {
        // Error already shown by apiCall
    }
}

async function markInvoicePaid(invoiceId) {
    if (!confirm('Mark this invoice as paid?')) return;

    try {
        await apiCall(`/invoices/${invoiceId}/mark-paid`, {
            method: 'POST'
        });

        alert('Invoice marked as paid!');
        loadInvoices();
        loadDashboard();
    } catch (error) {
        // Error already shown by apiCall
    }
}

// Utilities
function renderStatusBadge(status) {
    const badges = {
        'draft': 'badge-gray',
        'sent': 'badge-warning',
        'paid': 'badge-success',
        'overdue': 'badge-danger'
    };
    return `<span class="badge ${badges[status] || 'badge-gray'}">${status.toUpperCase()}</span>`;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoading(panelId) {
    document.getElementById(panelId).innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading...</p></div>';
}

function showError(panelId, message) {
    document.getElementById(panelId).innerHTML = `<div class="empty-state"><p>${message}</p></div>`;
}

function renderEmptyState(title, message) {
    return `
        <div class="empty-state">
            <div class="empty-state-icon">📋</div>
            <div class="empty-state-text"><strong>${title}</strong></div>
            <p class="text-muted">${message}</p>
        </div>
    `;
}
