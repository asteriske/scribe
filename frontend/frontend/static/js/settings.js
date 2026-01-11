/**
 * Settings page JavaScript
 */

// State
let tagConfigs = {};
let defaultConfig = {};
let secretKeys = [];

// DOM Elements
const tagConfigList = document.getElementById('tagConfigList');
const defaultConfigEl = document.getElementById('defaultConfig');
const apiKeyList = document.getElementById('apiKeyList');
const addTagConfigBtn = document.getElementById('addTagConfigBtn');
const editDefaultBtn = document.getElementById('editDefaultBtn');
const addApiKeyBtn = document.getElementById('addApiKeyBtn');

// Tag Config Modal
const tagConfigModal = document.getElementById('tagConfigModal');
const tagConfigModalTitle = document.getElementById('tagConfigModalTitle');
const tagConfigForm = document.getElementById('tagConfigForm');
const tagConfigMode = document.getElementById('tagConfigMode');
const tagConfigOriginalName = document.getElementById('tagConfigOriginalName');
const tagNameInput = document.getElementById('tagName');
const tagApiEndpointInput = document.getElementById('tagApiEndpoint');
const tagModelInput = document.getElementById('tagModel');
const tagApiKeyRefSelect = document.getElementById('tagApiKeyRef');
const tagSystemPromptInput = document.getElementById('tagSystemPrompt');
const tagDestinationEmailsInput = document.getElementById('tagDestinationEmails');

// Default Config Modal
const defaultConfigModal = document.getElementById('defaultConfigModal');
const defaultConfigForm = document.getElementById('defaultConfigForm');
const defaultApiEndpointInput = document.getElementById('defaultApiEndpoint');
const defaultModelInput = document.getElementById('defaultModel');
const defaultApiKeyRefSelect = document.getElementById('defaultApiKeyRef');
const defaultSystemPromptInput = document.getElementById('defaultSystemPrompt');

// API Key Modal
const apiKeyModal = document.getElementById('apiKeyModal');
const apiKeyModalTitle = document.getElementById('apiKeyModalTitle');
const apiKeyForm = document.getElementById('apiKeyForm');
const apiKeyMode = document.getElementById('apiKeyMode');
const apiKeyNameInput = document.getElementById('apiKeyName');
const apiKeyValueInput = document.getElementById('apiKeyValue');

// Toast
const toast = document.getElementById('toast');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadAllData();
    setupEventListeners();
});

function setupEventListeners() {
    addTagConfigBtn.addEventListener('click', () => openTagConfigModal('create'));
    editDefaultBtn.addEventListener('click', openDefaultConfigModal);
    addApiKeyBtn.addEventListener('click', () => openApiKeyModal('create'));

    tagConfigForm.addEventListener('submit', handleTagConfigSubmit);
    defaultConfigForm.addEventListener('submit', handleDefaultConfigSubmit);
    apiKeyForm.addEventListener('submit', handleApiKeySubmit);

    // Close modals on outside click
    [tagConfigModal, defaultConfigModal, apiKeyModal].forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

async function loadAllData() {
    await Promise.all([
        loadTagConfigs(),
        loadSecrets()
    ]);
}

// Load tag configurations
async function loadTagConfigs() {
    try {
        const response = await fetch('/api/config/tags');
        const data = await response.json();

        defaultConfig = data.default;
        tagConfigs = data.tags || {};

        renderTagConfigs();
        renderDefaultConfig();

    } catch (error) {
        console.error('Failed to load tag configs:', error);
        tagConfigList.innerHTML = '<p class="error">Failed to load configurations</p>';
    }
}

// Load secrets (key names only)
async function loadSecrets() {
    try {
        const response = await fetch('/api/config/secrets');
        const data = await response.json();
        secretKeys = data.keys || [];

        renderApiKeys();
        updateApiKeyRefSelects();

    } catch (error) {
        console.error('Failed to load secrets:', error);
        apiKeyList.innerHTML = '<p class="error">Failed to load API keys</p>';
    }
}

// Render tag configurations
function renderTagConfigs() {
    const tagNames = Object.keys(tagConfigs);

    if (tagNames.length === 0) {
        tagConfigList.innerHTML = '<p>No tag configurations defined.</p>';
        return;
    }

    tagConfigList.innerHTML = tagNames.map(tagName => {
        const config = tagConfigs[tagName];
        const destEmails = config.destination_emails && config.destination_emails.length > 0
            ? escapeHtml(config.destination_emails.join(', '))
            : 'Reply to sender';
        return `
            <div class="config-card">
                <div class="config-header">
                    <span class="config-name">${escapeHtml(tagName)}</span>
                    <div class="config-actions">
                        <button class="btn-edit" onclick="openTagConfigModal('edit', '${escapeHtml(tagName)}')">Edit</button>
                        <button class="btn-delete" onclick="deleteTagConfig('${escapeHtml(tagName)}')">&times;</button>
                    </div>
                </div>
                <div class="config-details">
                    <div class="config-detail">
                        <span class="config-detail-label">Model</span>
                        <span class="config-detail-value">${escapeHtml(config.model)}</span>
                    </div>
                    <div class="config-detail">
                        <span class="config-detail-label">Endpoint</span>
                        <span class="config-detail-value truncate">${escapeHtml(config.api_endpoint)}</span>
                    </div>
                    <div class="config-detail">
                        <span class="config-detail-label">API Key</span>
                        <span class="config-detail-value">${config.api_key_ref ? escapeHtml(config.api_key_ref) : 'None'}</span>
                    </div>
                    <div class="config-detail">
                        <span class="config-detail-label">Destination</span>
                        <span class="config-detail-value truncate">${destEmails}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Render default configuration
function renderDefaultConfig() {
    defaultConfigEl.innerHTML = `
        <div class="config-details">
            <div class="config-detail">
                <span class="config-detail-label">Model</span>
                <span class="config-detail-value">${escapeHtml(defaultConfig.model)}</span>
            </div>
            <div class="config-detail">
                <span class="config-detail-label">Endpoint</span>
                <span class="config-detail-value truncate">${escapeHtml(defaultConfig.api_endpoint)}</span>
            </div>
            <div class="config-detail">
                <span class="config-detail-label">API Key</span>
                <span class="config-detail-value">${defaultConfig.api_key_ref ? escapeHtml(defaultConfig.api_key_ref) : 'None'}</span>
            </div>
            <div class="config-detail" style="grid-column: 1 / -1;">
                <span class="config-detail-label">System Prompt</span>
                <span class="config-detail-value">${escapeHtml(defaultConfig.system_prompt)}</span>
            </div>
        </div>
    `;
}

// Render API keys
function renderApiKeys() {
    if (secretKeys.length === 0) {
        apiKeyList.innerHTML = '<p>No API keys configured.</p>';
        return;
    }

    apiKeyList.innerHTML = secretKeys.map(keyName => `
        <div class="api-key-item">
            <span class="key-name">${escapeHtml(keyName)}</span>
            <div class="key-actions">
                <button class="btn-edit" onclick="openApiKeyModal('edit', '${escapeHtml(keyName)}')">Edit</button>
                <button class="btn-delete" onclick="deleteApiKey('${escapeHtml(keyName)}')">&times;</button>
            </div>
        </div>
    `).join('');
}

// Update API key reference dropdowns
function updateApiKeyRefSelects() {
    const options = '<option value="">None</option>' +
        secretKeys.map(key => `<option value="${escapeHtml(key)}">${escapeHtml(key)}</option>`).join('');

    tagApiKeyRefSelect.innerHTML = options;
    defaultApiKeyRefSelect.innerHTML = options;
}

// Tag Config Modal
function openTagConfigModal(mode, tagName = null) {
    tagConfigMode.value = mode;
    tagConfigOriginalName.value = tagName || '';

    if (mode === 'create') {
        tagConfigModalTitle.textContent = 'Add Tag Configuration';
        tagNameInput.value = '';
        tagApiEndpointInput.value = '';
        tagModelInput.value = '';
        tagApiKeyRefSelect.value = '';
        tagSystemPromptInput.value = '';
        tagDestinationEmailsInput.value = '';
        tagNameInput.disabled = false;
    } else {
        tagConfigModalTitle.textContent = 'Edit Tag Configuration';
        const config = tagConfigs[tagName];
        tagNameInput.value = tagName;
        tagApiEndpointInput.value = config.api_endpoint;
        tagModelInput.value = config.model;
        tagApiKeyRefSelect.value = config.api_key_ref || '';
        tagSystemPromptInput.value = config.system_prompt;
        tagDestinationEmailsInput.value = (config.destination_emails || []).join(', ');
        tagNameInput.disabled = true;
    }

    tagConfigModal.style.display = 'flex';
}

function closeTagConfigModal() {
    tagConfigModal.style.display = 'none';
}

async function handleTagConfigSubmit(e) {
    e.preventDefault();

    const mode = tagConfigMode.value;
    const tagName = tagNameInput.value.trim();
    const destinationEmailsRaw = tagDestinationEmailsInput.value.trim();
    const destinationEmails = destinationEmailsRaw
        ? destinationEmailsRaw.split(',').map(e => e.trim()).filter(e => e)
        : [];
    const requestBody = {
        tag_name: tagName,
        api_endpoint: tagApiEndpointInput.value.trim(),
        model: tagModelInput.value.trim(),
        api_key_ref: tagApiKeyRefSelect.value || null,
        system_prompt: tagSystemPromptInput.value.trim(),
        destination_emails: destinationEmails
    };

    try {
        let response;
        if (mode === 'create') {
            response = await fetch('/api/config/tags', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
        } else {
            const originalName = tagConfigOriginalName.value;
            response = await fetch(`/api/config/tags/${encodeURIComponent(originalName)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save tag configuration');
        }

        showToast('Tag configuration saved successfully', 'success');
        closeTagConfigModal();
        await loadTagConfigs();

    } catch (error) {
        console.error('Failed to save tag config:', error);
        showToast(error.message, 'error');
    }
}

async function deleteTagConfig(tagName) {
    if (!confirm(`Are you sure you want to delete the configuration for "${tagName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/config/tags/${encodeURIComponent(tagName)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete tag configuration');
        }

        showToast('Tag configuration deleted', 'success');
        await loadTagConfigs();

    } catch (error) {
        console.error('Failed to delete tag config:', error);
        showToast(error.message, 'error');
    }
}

// Default Config Modal
function openDefaultConfigModal() {
    defaultApiEndpointInput.value = defaultConfig.api_endpoint;
    defaultModelInput.value = defaultConfig.model;
    defaultApiKeyRefSelect.value = defaultConfig.api_key_ref || '';
    defaultSystemPromptInput.value = defaultConfig.system_prompt;

    defaultConfigModal.style.display = 'flex';
}

function closeDefaultConfigModal() {
    defaultConfigModal.style.display = 'none';
}

async function handleDefaultConfigSubmit(e) {
    e.preventDefault();

    const requestBody = {
        api_endpoint: defaultApiEndpointInput.value.trim(),
        model: defaultModelInput.value.trim(),
        api_key_ref: defaultApiKeyRefSelect.value || null,
        system_prompt: defaultSystemPromptInput.value.trim()
    };

    try {
        const response = await fetch('/api/config/tags/default', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save default configuration');
        }

        showToast('Default configuration saved successfully', 'success');
        closeDefaultConfigModal();
        await loadTagConfigs();

    } catch (error) {
        console.error('Failed to save default config:', error);
        showToast(error.message, 'error');
    }
}

// API Key Modal
function openApiKeyModal(mode, keyName = null) {
    apiKeyMode.value = mode;

    if (mode === 'create') {
        apiKeyModalTitle.textContent = 'Add API Key';
        apiKeyNameInput.value = '';
        apiKeyValueInput.value = '';
        apiKeyNameInput.disabled = false;
    } else {
        apiKeyModalTitle.textContent = 'Edit API Key';
        apiKeyNameInput.value = keyName;
        apiKeyValueInput.value = '';
        apiKeyValueInput.placeholder = 'Enter new value to update';
        apiKeyNameInput.disabled = true;
    }

    apiKeyModal.style.display = 'flex';
}

function closeApiKeyModal() {
    apiKeyModal.style.display = 'none';
}

async function handleApiKeySubmit(e) {
    e.preventDefault();

    const requestBody = {
        key_name: apiKeyNameInput.value.trim(),
        key_value: apiKeyValueInput.value.trim()
    };

    try {
        const response = await fetch('/api/config/secrets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save API key');
        }

        showToast('API key saved successfully', 'success');
        closeApiKeyModal();
        await loadSecrets();

    } catch (error) {
        console.error('Failed to save API key:', error);
        showToast(error.message, 'error');
    }
}

async function deleteApiKey(keyName) {
    if (!confirm(`Are you sure you want to delete the API key "${keyName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/config/secrets/${encodeURIComponent(keyName)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete API key');
        }

        showToast('API key deleted', 'success');
        await loadSecrets();

    } catch (error) {
        console.error('Failed to delete API key:', error);
        showToast(error.message, 'error');
    }
}

// Toast notification
function showToast(message, type = 'success') {
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.style.display = 'block';

    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

// Utility function
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
