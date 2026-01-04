/**
 * WebSocket connection management for real-time updates
 */

let ws = null;
let reconnectTimer = null;
let heartbeatTimer = null;

/**
 * Connect to WebSocket server
 */
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
            // Clear any reconnection timers
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
            // Start heartbeat
            startHeartbeat();
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            } catch (err) {
                console.error('Error parsing WebSocket message:', err);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
            stopHeartbeat();
            // Try to reconnect after 5 seconds
            reconnectTimer = setTimeout(() => {
                console.log('Attempting to reconnect...');
                connectWebSocket();
            }, 5000);
        };
    } catch (err) {
        console.error('Error connecting to WebSocket:', err);
    }
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(message) {
    console.log('WebSocket message:', message);

    switch (message.type) {
        case 'status':
            updateProgress(message);
            break;
        case 'completed':
            handleCompletion(message);
            break;
        case 'error':
            handleError(message);
            break;
        case 'pong':
            // Heartbeat response
            break;
        default:
            console.log('Unknown message type:', message.type);
    }
}

/**
 * Update progress bar
 */
function updateProgress(data) {
    const statusElement = document.getElementById('status');
    const statusTitle = document.getElementById('statusTitle');
    const statusMessage = document.getElementById('statusMessage');
    const progressFill = document.getElementById('progressFill');

    if (statusElement && statusTitle && statusMessage && progressFill) {
        statusElement.style.display = 'block';
        statusTitle.textContent = data.status || 'Processing...';
        statusMessage.textContent = data.message || '';

        // Update progress bar
        const progress = data.progress || 0;
        progressFill.style.width = `${progress}%`;
    }
}

/**
 * Handle job completion
 */
function handleCompletion(data) {
    console.log('Job completed:', data);

    // Hide error message if showing
    hideError();

    // Show completion message
    const statusElement = document.getElementById('status');
    const statusTitle = document.getElementById('statusTitle');
    const statusMessage = document.getElementById('statusMessage');
    const progressFill = document.getElementById('progressFill');

    if (statusElement && statusTitle && statusMessage && progressFill) {
        statusElement.style.display = 'block';
        statusTitle.textContent = 'Completed!';
        statusMessage.textContent = 'Transcription complete. Redirecting...';
        progressFill.style.width = '100%';

        // Redirect to transcription page after a short delay
        setTimeout(() => {
            if (data.job_id) {
                window.location.href = `/transcriptions/${data.job_id}`;
            } else {
                // Reload the page to show the new transcription in the list
                window.location.reload();
            }
        }, 1000);
    }
}

/**
 * Handle error messages
 */
function handleError(data) {
    console.error('Job error:', data);
    showError(data.message || 'An error occurred during processing');

    // Hide status message
    const statusElement = document.getElementById('status');
    if (statusElement) {
        statusElement.style.display = 'none';
    }

    // Re-enable submit button if it exists
    const submitButton = document.getElementById('submitButton');
    if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = 'Transcribe';
    }
}

/**
 * Show error message
 */
function showError(message) {
    const errorElement = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');

    if (errorElement && errorMessage) {
        errorMessage.textContent = message;
        errorElement.style.display = 'block';
    }
}

/**
 * Hide error message
 */
function hideError() {
    const errorElement = document.getElementById('error');
    if (errorElement) {
        errorElement.style.display = 'none';
    }
}

/**
 * Start heartbeat ping
 */
function startHeartbeat() {
    stopHeartbeat(); // Clear any existing timer
    heartbeatTimer = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000); // Every 30 seconds
}

/**
 * Stop heartbeat ping
 */
function stopHeartbeat() {
    if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
    }
}

// Initialize WebSocket connection when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', connectWebSocket);
} else {
    connectWebSocket();
}
