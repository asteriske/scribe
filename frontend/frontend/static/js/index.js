/**
 * Index page functionality - form submission and recent transcriptions
 */

// Global tag input instance
let tagInput = null;

/**
 * Handle form submission
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('transcribeForm');
    const submitButton = document.getElementById('submitButton');
    const urlInput = document.getElementById('url');

    // Initialize tag input
    const tagContainer = document.getElementById('tagInput');
    if (tagContainer) {
        tagInput = new TagInput(tagContainer, []);
    }

    if (form) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            const url = urlInput.value.trim();
            if (!url) {
                showError('Please enter a URL');
                return;
            }

            // Disable submit button
            submitButton.disabled = true;
            submitButton.textContent = 'Processing...';

            // Hide any previous errors
            hideError();

            try {
                // Get tags from tag input
                const tags = tagInput ? tagInput.getTags() : [];

                const response = await fetch('/api/transcribe', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url, tags }),
                });

                if (!response.ok) {
                    if (response.status === 409) {
                        // Job already exists
                        const data = await response.json();
                        showError(data.detail || 'A transcription for this URL is already in progress');
                    } else if (response.status === 400) {
                        const data = await response.json();
                        showError(data.detail || 'Invalid URL provided');
                    } else {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    // Re-enable submit button
                    submitButton.disabled = false;
                    submitButton.textContent = 'Transcribe';
                    return;
                }

                const data = await response.json();
                console.log('Transcription started:', data);

                // Clear form
                urlInput.value = '';
                if (tagInput) {
                    tagInput.setTags([]);
                }

                // Show status message
                const statusElement = document.getElementById('status');
                if (statusElement) {
                    statusElement.style.display = 'block';
                }

                // WebSocket will handle progress updates via app.js
                // The form will remain disabled until completion or error

            } catch (error) {
                console.error('Error submitting form:', error);
                showError(error.message || 'Failed to start transcription. Please try again.');
                // Re-enable submit button
                submitButton.disabled = false;
                submitButton.textContent = 'Transcribe';
            }
        });
    }

    // Load recent transcriptions on page load
    loadRecent();

    // Auto-refresh recent transcriptions every 30 seconds
    setInterval(loadRecent, 30000);
});

/**
 * Load recent transcriptions
 */
async function loadRecent() {
    const recentList = document.getElementById('recentList');
    if (!recentList) return;

    try {
        const response = await fetch('/api/transcriptions?limit=10');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const transcriptions = await response.json();

        if (transcriptions.items.length === 0) {
            recentList.innerHTML = '<p class="loading">No recent transcriptions</p>';
            return;
        }

        // Build HTML for transcriptions list
        const html = transcriptions.items.map(t => {
            const createdDate = new Date(t.created_at).toLocaleString();
            const statusClass = t.status.toLowerCase().replace(' ', '-');

            // Render tags
            const tagsHtml = t.tags && t.tags.length > 0
                ? `<div class="transcription-tags">
                     <div class="tags-display">
                       ${t.tags.map(tag => `<span class="tag-chip">${escapeHtml(tag)}</span>`).join('')}
                       <button class="btn-edit-tags" onclick="editTags('${escapeHtml(t.id)}', event)">Edit</button>
                     </div>
                     <div class="tags-edit" id="tags-edit-${escapeHtml(t.id)}" style="display:none">
                       <div id="tags-input-${escapeHtml(t.id)}"></div>
                       <button class="btn-save" onclick="saveTags('${escapeHtml(t.id)}', event)">Save</button>
                       <button class="btn-cancel" onclick="cancelEditTags('${escapeHtml(t.id)}', event)">Cancel</button>
                     </div>
                   </div>`
                : `<div class="transcription-tags">
                     <div class="tags-display">
                       <button class="btn-edit-tags" onclick="editTags('${escapeHtml(t.id)}', event)">Add Tags</button>
                     </div>
                     <div class="tags-edit" id="tags-edit-${escapeHtml(t.id)}" style="display:none">
                       <div id="tags-input-${escapeHtml(t.id)}"></div>
                       <button class="btn-save" onclick="saveTags('${escapeHtml(t.id)}', event)">Save</button>
                       <button class="btn-cancel" onclick="cancelEditTags('${escapeHtml(t.id)}', event)">Cancel</button>
                     </div>
                   </div>`;

            return `
                <div class="transcription-item" id="item-${escapeHtml(t.id)}">
                    <div class="transcription-header">
                        <div>
                            <div class="transcription-title">${escapeHtml(t.source.title || 'Untitled')}</div>
                            <a href="${escapeHtml(t.source.url)}" class="transcription-url" target="_blank" rel="noopener">${escapeHtml(truncateUrl(t.source.url))}</a>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span class="status-badge ${statusClass}">${escapeHtml(t.status)}</span>
                            <button onclick="deleteTranscription('${escapeHtml(t.id)}')" class="btn-delete" title="Delete transcription">🗑️</button>
                        </div>
                    </div>
                    <div class="transcription-meta">
                        <span>Created: ${createdDate}</span>
                        ${t.duration_seconds ? `<span>Duration: ${formatDuration(t.duration_seconds)}</span>` : ''}
                    </div>
                    ${tagsHtml}
                    ${t.status === 'completed' ? `<a href="/transcriptions/${t.id}" class="view-link">View Transcription →</a>` : ''}
                </div>
            `;
        }).join('');

        recentList.innerHTML = `<div class="transcription-list">${html}</div>`;

    } catch (error) {
        console.error('Error loading recent transcriptions:', error);
        recentList.innerHTML = '<p class="loading">Failed to load recent transcriptions</p>';
    }
}

// Store tag input instances for editing
const tagInputInstances = {};

/**
 * Enter edit mode for tags
 */
function editTags(transcriptionId, event) {
    event.preventDefault();
    event.stopPropagation();

    // Hide display, show edit
    const item = document.getElementById(`item-${transcriptionId}`);
    const display = item.querySelector('.tags-display');
    const edit = item.querySelector('.tags-edit');

    display.style.display = 'none';
    edit.style.display = 'block';

    // Get current tags from display
    const chips = display.querySelectorAll('.tag-chip');
    const currentTags = Array.from(chips).map(chip => chip.textContent.trim());

    // Initialize tag input if not exists
    const inputContainer = document.getElementById(`tags-input-${transcriptionId}`);
    if (!tagInputInstances[transcriptionId]) {
        tagInputInstances[transcriptionId] = new TagInput(inputContainer, currentTags);
    } else {
        tagInputInstances[transcriptionId].setTags(currentTags);
    }
}

/**
 * Save edited tags
 */
async function saveTags(transcriptionId, event) {
    event.preventDefault();
    event.stopPropagation();

    const tagInputInstance = tagInputInstances[transcriptionId];
    if (!tagInputInstance) return;

    const tags = tagInputInstance.getTags();

    try {
        const response = await fetch(`/api/transcriptions/${transcriptionId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ tags })
        });

        if (!response.ok) {
            throw new Error('Failed to update tags');
        }

        // Reload the list
        await loadRecent();

    } catch (error) {
        console.error('Error saving tags:', error);
        alert('Failed to update tags. Please try again.');
    }
}

/**
 * Cancel tag editing
 */
function cancelEditTags(transcriptionId, event) {
    event.preventDefault();
    event.stopPropagation();

    // Hide edit, show display
    const item = document.getElementById(`item-${transcriptionId}`);
    const display = item.querySelector('.tags-display');
    const edit = item.querySelector('.tags-edit');

    display.style.display = 'flex';
    edit.style.display = 'none';
}

/**
 * Helper: Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Helper: Truncate URL for display
 */
function truncateUrl(url, maxLength = 60) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
}

/**
 * Helper: Format duration in seconds to readable format
 */
function formatDuration(seconds) {
    if (!seconds) return 'Unknown';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

/**
 * Delete a transcription
 */
async function deleteTranscription(id) {
    if (!confirm('Are you sure you want to delete this transcription? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/transcriptions/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Reload the recent transcriptions list
            await loadRecent();
        } else {
            alert('Failed to delete transcription. Please try again.');
        }
    } catch (error) {
        console.error('Error deleting transcription:', error);
        alert('Failed to delete transcription. Please try again.');
    }
}
