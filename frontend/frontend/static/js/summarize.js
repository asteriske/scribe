/**
 * Summarize page JavaScript
 */

// State
let transcriptions = [];
let selectedTranscription = null;
let currentSummary = null;
let skip = 0;
const limit = 20;

// DOM Elements
const transcriptionList = document.getElementById('transcriptionList');
const loadMoreContainer = document.getElementById('loadMoreContainer');
const loadMoreBtn = document.getElementById('loadMoreBtn');
const configSection = document.getElementById('configSection');
const configInfo = document.getElementById('configInfo');
const summarizeForm = document.getElementById('summarizeForm');
const transcriptionIdInput = document.getElementById('transcriptionId');
const apiEndpointInput = document.getElementById('apiEndpoint');
const modelInput = document.getElementById('model');
const apiKeyInput = document.getElementById('apiKey');
const apiKeyHint = document.getElementById('apiKeyHint');
const systemPromptInput = document.getElementById('systemPrompt');
const tokenCount = document.getElementById('tokenCount');
const generateBtn = document.getElementById('generateBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const resultsSection = document.getElementById('resultsSection');
const summaryText = document.getElementById('summaryText');
const summaryTimestamp = document.getElementById('summaryTimestamp');
const summaryGenerationTime = document.getElementById('summaryGenerationTime');
const summaryTokens = document.getElementById('summaryTokens');
const downloadTxtBtn = document.getElementById('downloadTxtBtn');
const downloadJsonBtn = document.getElementById('downloadJsonBtn');
const viewHistoryLink = document.getElementById('viewHistoryLink');
const historyModal = document.getElementById('historyModal');
const historyList = document.getElementById('historyList');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadTranscriptions();
    setupEventListeners();
    checkPreselectedTranscription();
});

function setupEventListeners() {
    loadMoreBtn.addEventListener('click', loadMoreTranscriptions);
    summarizeForm.addEventListener('submit', handleGenerateSummary);
    downloadTxtBtn.addEventListener('click', () => downloadSummary('txt'));
    downloadJsonBtn.addEventListener('click', () => downloadSummary('json'));
    viewHistoryLink.addEventListener('click', (e) => {
        e.preventDefault();
        openHistoryModal();
    });
}

function checkPreselectedTranscription() {
    // Check URL for preselected transcription
    const urlParams = new URLSearchParams(window.location.search);
    const preselectedId = urlParams.get('transcription_id');
    if (preselectedId) {
        // Will be selected after transcriptions load
        window.preselectedId = preselectedId;
    }
}

// Load transcriptions
async function loadTranscriptions() {
    try {
        const response = await fetch(`/api/transcriptions?skip=${skip}&limit=${limit}&status=completed`);
        const data = await response.json();

        if (skip === 0) {
            transcriptions = data.items;
        } else {
            transcriptions = [...transcriptions, ...data.items];
        }

        renderTranscriptions();

        // Show/hide load more button
        if (data.items.length < limit || transcriptions.length >= data.total) {
            loadMoreContainer.style.display = 'none';
        } else {
            loadMoreContainer.style.display = 'block';
        }

        // Handle preselected transcription
        if (window.preselectedId) {
            const preselected = transcriptions.find(t => t.id === window.preselectedId);
            if (preselected) {
                selectTranscription(preselected);
            }
            window.preselectedId = null;
        }
    } catch (error) {
        console.error('Failed to load transcriptions:', error);
        transcriptionList.innerHTML = '<p class="error">Failed to load transcriptions</p>';
    }
}

function loadMoreTranscriptions() {
    skip += limit;
    loadTranscriptions();
}

function renderTranscriptions() {
    if (transcriptions.length === 0) {
        transcriptionList.innerHTML = '<p>No completed transcriptions found.</p>';
        return;
    }

    transcriptionList.innerHTML = transcriptions.map(t => `
        <div class="transcription-item ${selectedTranscription?.id === t.id ? 'selected' : ''}"
             data-id="${t.id}"
             onclick="selectTranscription(transcriptions.find(tr => tr.id === '${t.id}'))">
            <input type="radio"
                   name="transcription"
                   value="${t.id}"
                   ${selectedTranscription?.id === t.id ? 'checked' : ''}>
            <div class="transcription-info">
                <div class="transcription-title">${escapeHtml(t.source?.title || t.id)}</div>
                <div class="transcription-meta">
                    <span>${formatDate(t.created_at)}</span>
                    <span>${t.word_count?.toLocaleString() || 0} words</span>
                    ${t.tags?.length ? `<span>${t.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join(' ')}</span>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

async function selectTranscription(transcription) {
    selectedTranscription = transcription;
    transcriptionIdInput.value = transcription.id;

    // Update UI
    renderTranscriptions();
    configSection.style.display = 'block';
    resultsSection.style.display = 'none';
    errorMessage.style.display = 'none';

    // Load configuration based on tags
    await loadConfiguration(transcription.tags || []);

    // Estimate tokens
    estimateTokens(transcription);
}

async function loadConfiguration(tags) {
    try {
        // Fetch tag configs
        const response = await fetch('/api/config/tags');
        const configs = await response.json();

        // Find matching tag config
        let configSource = 'system_default';
        let matchedConfig = configs.default;

        for (const tag of tags) {
            if (configs.tags && configs.tags[tag]) {
                matchedConfig = configs.tags[tag];
                configSource = `tag:${tag}`;
                break;
            }
        }

        // Populate form
        apiEndpointInput.value = matchedConfig.api_endpoint;
        modelInput.value = matchedConfig.model;
        systemPromptInput.value = matchedConfig.system_prompt;

        // Show config info
        if (configSource === 'system_default') {
            configInfo.textContent = 'Using default configuration';
        } else {
            configInfo.textContent = `Using configuration from tag: ${configSource.replace('tag:', '')}`;
        }

        // Show API key hint
        if (matchedConfig.api_key_ref) {
            apiKeyHint.textContent = `Using saved key: ${matchedConfig.api_key_ref}`;
            apiKeyInput.placeholder = `Leave blank to use saved "${matchedConfig.api_key_ref}" key`;
        } else {
            apiKeyHint.textContent = '';
            apiKeyInput.placeholder = 'Leave blank if not required';
        }

    } catch (error) {
        console.error('Failed to load configuration:', error);
        configInfo.textContent = 'Failed to load configuration';
    }
}

function estimateTokens(transcription) {
    // Rough estimate: ~4 characters per token
    const wordCount = transcription.word_count || 0;
    const estimatedChars = wordCount * 5; // avg word length
    const estimatedTokens = Math.round(estimatedChars / 4);
    tokenCount.textContent = `Estimated tokens: ~${estimatedTokens.toLocaleString()}`;
}

async function handleGenerateSummary(e) {
    e.preventDefault();

    // Show loading
    summarizeForm.style.display = 'none';
    loadingIndicator.style.display = 'block';
    errorMessage.style.display = 'none';

    const requestBody = {
        transcription_id: transcriptionIdInput.value,
        api_endpoint: apiEndpointInput.value,
        model: modelInput.value,
        system_prompt: systemPromptInput.value
    };

    // Only include API key if provided
    if (apiKeyInput.value.trim()) {
        requestBody.api_key = apiKeyInput.value.trim();
    }

    try {
        const response = await fetch('/api/summaries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to generate summary');
        }

        currentSummary = data;
        displaySummary(data);

    } catch (error) {
        console.error('Failed to generate summary:', error);
        errorText.textContent = error.message;
        errorMessage.style.display = 'block';
    } finally {
        loadingIndicator.style.display = 'none';
        summarizeForm.style.display = 'block';
    }
}

function displaySummary(summary) {
    summaryText.textContent = summary.summary_text;
    summaryTimestamp.textContent = `Generated: ${formatDateTime(summary.created_at)}`;
    summaryGenerationTime.textContent = `Time: ${(summary.generation_time_ms / 1000).toFixed(1)}s`;

    if (summary.prompt_tokens || summary.completion_tokens) {
        summaryTokens.textContent = `Tokens: ${summary.prompt_tokens || 0} / ${summary.completion_tokens || 0}`;
    } else {
        summaryTokens.textContent = '';
    }

    resultsSection.style.display = 'block';

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function downloadSummary(format) {
    if (!currentSummary) return;

    window.location.href = `/api/summaries/${currentSummary.id}/export/${format}`;
}

async function openHistoryModal() {
    if (!selectedTranscription) return;

    historyModal.style.display = 'flex';
    historyList.innerHTML = '<p class="loading">Loading...</p>';

    try {
        const response = await fetch(`/api/summaries?transcription_id=${selectedTranscription.id}`);
        const data = await response.json();

        if (data.items.length === 0) {
            historyList.innerHTML = '<p>No summaries found for this transcription.</p>';
            return;
        }

        historyList.innerHTML = data.items.map(s => `
            <div class="history-item">
                <div class="history-meta">
                    <span>${formatDateTime(s.created_at)}</span>
                    <span>${s.model}</span>
                    <span>${s.config_source}</span>
                </div>
                <div class="history-text">${escapeHtml(s.summary_text)}</div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Failed to load history:', error);
        historyList.innerHTML = '<p class="error">Failed to load summary history</p>';
    }
}

function closeHistoryModal() {
    historyModal.style.display = 'none';
}

// Close modal on outside click
historyModal.addEventListener('click', (e) => {
    if (e.target === historyModal) {
        closeHistoryModal();
    }
});

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString();
}
