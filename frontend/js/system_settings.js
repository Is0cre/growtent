/**
 * System Settings page functionality
 * Enhanced with visual controls, time pickers, and sliders
 */

// Tab switching
document.querySelectorAll('.settings-tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active class from all tabs and contents
        document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.settings-tab-content').forEach(c => c.classList.remove('active'));
        
        // Add active class to clicked tab and its content
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab)?.classList.add('active');
    });
});

// Load all settings
async function loadAllSettings() {
    await Promise.all([
        loadTimelapseSettings(),
        loadAlertSettings(),
        loadAISettings(),
        loadSyncSettings(),
        loadTelegramSettings(),
        loadScheduledTasks(),
        loadOpenRouterModels()
    ]);
}

// Load available OpenRouter models
async function loadOpenRouterModels() {
    try {
        const response = await fetch('/api/system-settings/openrouter/models');
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('openrouterModel');
            if (select) {
                select.innerHTML = '';
                for (const [modelId, displayName] of Object.entries(data.data)) {
                    const option = document.createElement('option');
                    option.value = modelId;
                    option.textContent = displayName;
                    select.appendChild(option);
                }
            }
        }
    } catch (error) {
        console.error('Error loading OpenRouter models:', error);
    }
}

// Timelapse settings
async function loadTimelapseSettings() {
    try {
        const response = await fetch('/api/system-settings/timelapse');
        const data = await response.json();
        
        if (data.success) {
            // Update slider value and display
            const intervalSlider = document.getElementById('tlIntervalSlider');
            const intervalDisplay = document.getElementById('tlIntervalDisplay');
            if (intervalSlider && intervalDisplay) {
                intervalSlider.value = data.data.default_interval || 300;
                intervalDisplay.textContent = formatInterval(intervalSlider.value);
            }
            
            document.getElementById('tlFps').value = data.data.default_fps || 30;
            
            const autoStartToggle = document.getElementById('tlAutoStart');
            if (autoStartToggle) {
                autoStartToggle.checked = data.data.auto_start_on_project !== false;
            }
        }
    } catch (error) {
        console.error('Error loading timelapse settings:', error);
    }
}

function formatInterval(seconds) {
    const sec = parseInt(seconds);
    if (sec < 60) return `${sec} seconds`;
    if (sec < 3600) return `${Math.floor(sec / 60)} minutes`;
    return `${Math.floor(sec / 3600)} hour${sec >= 7200 ? 's' : ''}`;
}

// Update interval display when slider changes
document.getElementById('tlIntervalSlider')?.addEventListener('input', (e) => {
    const display = document.getElementById('tlIntervalDisplay');
    if (display) {
        display.textContent = formatInterval(e.target.value);
    }
});

document.getElementById('timelapseSettingsForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const intervalSlider = document.getElementById('tlIntervalSlider');
    const data = {
        default_interval: parseInt(intervalSlider?.value || 300),
        default_fps: parseInt(document.getElementById('tlFps').value),
        auto_start_on_project: document.getElementById('tlAutoStart').checked
    };
    
    try {
        const response = await fetch('/api/system-settings/timelapse', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        showNotification(result.message || 'Settings saved', result.success ? 'success' : 'error');
    } catch (error) {
        showNotification('Failed to save settings', 'error');
    }
});

// Alert settings with sliders
async function loadAlertSettings() {
    try {
        const response = await fetch('/api/system-settings/alerts');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('alertsEnabled').checked = data.data.enabled !== false;
            
            // Temperature sliders
            updateSliderValue('tempMinSlider', 'tempMinValue', data.data.temp_min || 15);
            updateSliderValue('tempMaxSlider', 'tempMaxValue', data.data.temp_max || 32);
            
            // Humidity sliders
            updateSliderValue('humidityMinSlider', 'humidityMinValue', data.data.humidity_min || 40);
            updateSliderValue('humidityMaxSlider', 'humidityMaxValue', data.data.humidity_max || 80);
            
            document.getElementById('notificationInterval').value = data.data.notification_interval || 300;
        }
    } catch (error) {
        console.error('Error loading alert settings:', error);
    }
}

function updateSliderValue(sliderId, displayId, value) {
    const slider = document.getElementById(sliderId);
    const display = document.getElementById(displayId);
    if (slider) slider.value = value;
    if (display) display.textContent = value;
}

// Add event listeners for all sliders
['tempMinSlider', 'tempMaxSlider', 'humidityMinSlider', 'humidityMaxSlider'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', (e) => {
        const displayId = id.replace('Slider', 'Value');
        const display = document.getElementById(displayId);
        if (display) display.textContent = e.target.value;
    });
});

document.getElementById('alertSettingsForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        enabled: document.getElementById('alertsEnabled').checked,
        temp_min: parseFloat(document.getElementById('tempMinSlider')?.value || 15),
        temp_max: parseFloat(document.getElementById('tempMaxSlider')?.value || 32),
        humidity_min: parseFloat(document.getElementById('humidityMinSlider')?.value || 40),
        humidity_max: parseFloat(document.getElementById('humidityMaxSlider')?.value || 80),
        notification_interval: parseInt(document.getElementById('notificationInterval').value)
    };
    
    try {
        const response = await fetch('/api/system-settings/alerts', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        showNotification(result.message || 'Settings saved', result.success ? 'success' : 'error');
    } catch (error) {
        showNotification('Failed to save settings', 'error');
    }
});

// AI settings
async function loadAISettings() {
    try {
        const response = await fetch('/api/system-settings/ai-analysis');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('aiEnabled').checked = data.data.enabled === true;
            document.getElementById('aiScheduleTime').value = data.data.daily_schedule_time || '12:00';
            document.getElementById('aiSendTelegram').checked = data.data.send_to_telegram !== false;
            document.getElementById('aiSendExternal').checked = data.data.send_to_external_server !== false;
            
            // Set the current model
            const modelSelect = document.getElementById('openrouterModel');
            if (modelSelect && data.data.model) {
                modelSelect.value = data.data.model;
            }
            
            // Update API key status
            const apiKeyStatus = document.getElementById('apiKeyStatus');
            if (apiKeyStatus) {
                if (data.data.has_api_key) {
                    apiKeyStatus.innerHTML = '<span class="status-ok">✓ API key configured</span>';
                } else {
                    apiKeyStatus.innerHTML = '<span class="status-missing">✗ API key not set</span>';
                }
            }
        }
    } catch (error) {
        console.error('Error loading AI settings:', error);
    }
}

document.getElementById('aiSettingsForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        enabled: document.getElementById('aiEnabled').checked,
        daily_schedule_time: document.getElementById('aiScheduleTime').value,
        send_to_telegram: document.getElementById('aiSendTelegram').checked,
        send_to_external_server: document.getElementById('aiSendExternal').checked
    };
    
    try {
        const response = await fetch('/api/system-settings/ai-analysis', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        showNotification(result.message || 'Settings saved', result.success ? 'success' : 'error');
    } catch (error) {
        showNotification('Failed to save settings', 'error');
    }
});

document.getElementById('openrouterSettingsForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        api_key: document.getElementById('openrouterApiKey').value,
        model: document.getElementById('openrouterModel').value
    };
    
    try {
        const response = await fetch('/api/system-settings/openrouter', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        document.getElementById('openrouterApiKey').value = ''; // Clear for security
        showNotification(result.message || 'Settings saved', result.success ? 'success' : 'error');
        loadAISettings(); // Refresh to show updated status
    } catch (error) {
        showNotification('Failed to save settings', 'error');
    }
});

// Sync settings
async function loadSyncSettings() {
    try {
        const [syncResponse, statusResponse] = await Promise.all([
            fetch('/api/system-settings/external-sync'),
            fetch('/api/sync/status')
        ]);
        
        const syncData = await syncResponse.json();
        const statusData = await statusResponse.json();
        
        if (syncData.success) {
            document.getElementById('syncEnabled').checked = syncData.data.enabled === true;
            document.getElementById('syncInterval').value = syncData.data.sync_interval || 300;
            document.getElementById('syncPhotos').checked = syncData.data.sync_photos !== false;
            document.getElementById('syncSensorData').checked = syncData.data.sync_sensor_data !== false;
            document.getElementById('syncProjectInfo').checked = syncData.data.sync_project_info !== false;
            document.getElementById('syncAnalysisReports').checked = syncData.data.sync_analysis_reports !== false;
            
            document.getElementById('serverEnabled').checked = syncData.data.server_enabled === true;
            document.getElementById('serverUrl').value = syncData.data.server_url || '';
            document.getElementById('authType').value = syncData.data.auth_type || 'api_key';
        }
        
        if (statusData.success) {
            updateSyncStatus(statusData.data);
        }
    } catch (error) {
        console.error('Error loading sync settings:', error);
    }
}

function updateSyncStatus(status) {
    const indicator = document.getElementById('syncStatusIndicator');
    const lastSync = document.getElementById('lastSyncTime');
    
    if (status.enabled && status.configured) {
        indicator.innerHTML = '<i class="fas fa-circle" style="color: green;"></i> Enabled';
    } else if (status.configured) {
        indicator.innerHTML = '<i class="fas fa-circle" style="color: orange;"></i> Disabled';
    } else {
        indicator.innerHTML = '<i class="fas fa-circle" style="color: gray;"></i> Not Configured';
    }
    
    lastSync.textContent = status.last_sync ? 
        `Last sync: ${new Date(status.last_sync).toLocaleString()}` : 
        'Last sync: Never';
}

document.getElementById('syncNowBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('syncNowBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    try {
        const response = await fetch('/api/sync/now', { method: 'POST' });
        const data = await response.json();
        
        showNotification(data.message || 'Sync started', data.success ? 'success' : 'error');
        
        // Refresh status after delay
        setTimeout(loadSyncSettings, 3000);
    } catch (error) {
        showNotification('Sync failed', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-sync"></i> Sync Now';
    }
});

document.getElementById('testConnectionBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('testConnectionBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    try {
        const response = await fetch('/api/sync/test', { method: 'POST' });
        const data = await response.json();
        
        if (data.success && data.data.connected) {
            showNotification('Connection successful!', 'success');
        } else {
            showNotification(data.data?.error || 'Connection failed', 'error');
        }
    } catch (error) {
        showNotification('Connection test failed', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-plug"></i> Test Connection';
    }
});

document.getElementById('syncSettingsForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        enabled: document.getElementById('syncEnabled').checked,
        sync_interval: parseInt(document.getElementById('syncInterval').value),
        sync_photos: document.getElementById('syncPhotos').checked,
        sync_sensor_data: document.getElementById('syncSensorData').checked,
        sync_project_info: document.getElementById('syncProjectInfo').checked,
        sync_analysis_reports: document.getElementById('syncAnalysisReports').checked
    };
    
    try {
        const response = await fetch('/api/system-settings/external-sync', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        showNotification(result.message || 'Settings saved', result.success ? 'success' : 'error');
    } catch (error) {
        showNotification('Failed to save settings', 'error');
    }
});

document.getElementById('externalServerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        enabled: document.getElementById('serverEnabled').checked,
        url: document.getElementById('serverUrl').value,
        auth_type: document.getElementById('authType').value,
        api_key: document.getElementById('serverApiKey').value,
        bearer_token: document.getElementById('bearerToken').value
    };
    
    try {
        const response = await fetch('/api/system-settings/external-server', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        document.getElementById('serverApiKey').value = '';
        document.getElementById('bearerToken').value = '';
        showNotification(result.message || 'Settings saved', result.success ? 'success' : 'error');
        loadSyncSettings();
    } catch (error) {
        showNotification('Failed to save settings', 'error');
    }
});

// Show/hide auth fields based on type
document.getElementById('authType')?.addEventListener('change', (e) => {
    const apiKeyGroup = document.getElementById('apiKeyGroup');
    const bearerGroup = document.getElementById('bearerGroup');
    
    apiKeyGroup.style.display = e.target.value === 'api_key' ? 'block' : 'none';
    bearerGroup.style.display = e.target.value === 'bearer' ? 'block' : 'none';
});

// Telegram settings
async function loadTelegramSettings() {
    try {
        const response = await fetch('/api/system-settings/telegram');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('telegramChatId').value = data.data.chat_id || '';
            
            // Show masked token status
            const tokenStatus = document.getElementById('tokenStatus');
            if (tokenStatus) {
                if (data.data.has_bot_token) {
                    tokenStatus.innerHTML = `<span class="status-ok">✓ Token configured (${data.data.masked_bot_token})</span>`;
                } else {
                    tokenStatus.innerHTML = '<span class="status-missing">✗ Token not set</span>';
                }
            }
        }
    } catch (error) {
        console.error('Error loading Telegram settings:', error);
    }
}

document.getElementById('telegramSettingsForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {
        bot_token: document.getElementById('telegramBotToken').value,
        chat_id: document.getElementById('telegramChatId').value
    };
    
    try {
        const response = await fetch('/api/system-settings/telegram', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        document.getElementById('telegramBotToken').value = '';
        showNotification(result.message || 'Settings saved', result.success ? 'success' : 'error');
        loadTelegramSettings();
    } catch (error) {
        showNotification('Failed to save settings', 'error');
    }
});

// Scheduled tasks
async function loadScheduledTasks() {
    try {
        const response = await fetch('/api/system-settings/scheduled-tasks');
        const data = await response.json();
        
        const container = document.getElementById('scheduledTasksList');
        
        if (!data.success || !data.data || data.data.length === 0) {
            container.innerHTML = '<p class="no-data">No scheduled tasks configured</p>';
            return;
        }
        
        container.innerHTML = data.data.map(task => `
            <div class="task-item">
                <div class="task-info">
                    <strong>${task.name || task.id}</strong>
                    <span class="task-schedule">
                        Next run: ${task.next_run ? new Date(task.next_run).toLocaleString() : 'Not scheduled'}
                    </span>
                    ${task.last_run ? `<span class="task-last-run">Last run: ${new Date(task.last_run).toLocaleString()}</span>` : ''}
                </div>
                <div class="task-actions">
                    <button class="btn btn-small ${task.paused ? 'btn-primary' : 'btn-secondary'}" 
                            onclick="toggleTask('${task.id}', ${task.paused})">
                        ${task.paused ? 'Enable' : 'Disable'}
                    </button>
                    <button class="btn btn-small btn-primary" onclick="runTask('${task.id}')">
                        Run Now
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading scheduled tasks:', error);
    }
}

async function toggleTask(taskId, currentlyPaused) {
    try {
        const response = await fetch(`/api/system-settings/scheduled-tasks/${taskId}/toggle?enabled=${currentlyPaused}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        showNotification(data.message || 'Task updated', data.success ? 'success' : 'error');
        loadScheduledTasks();
    } catch (error) {
        showNotification('Failed to toggle task', 'error');
    }
}

async function runTask(taskId) {
    try {
        const response = await fetch(`/api/system-settings/scheduled-tasks/${taskId}/run`, {
            method: 'POST'
        });
        
        const data = await response.json();
        showNotification(data.message || 'Task executed', data.success ? 'success' : 'error');
        loadScheduledTasks();
    } catch (error) {
        showNotification('Failed to run task', 'error');
    }
}

// Reload config button
document.getElementById('reloadConfigBtn')?.addEventListener('click', async () => {
    try {
        const response = await fetch('/api/system-settings/reload', { method: 'POST' });
        const data = await response.json();
        
        showNotification(data.message || 'Config reloaded', data.success ? 'success' : 'error');
        loadAllSettings();
    } catch (error) {
        showNotification('Failed to reload config', 'error');
    }
});

// Initialize when page becomes visible
function initSystemSettingsPage() {
    loadAllSettings();
}

// Auto-refresh when page is shown
const systemSettingsObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.target.id === 'page-system-settings' && 
            mutation.target.classList.contains('active')) {
            initSystemSettingsPage();
        }
    });
});

const systemSettingsPage = document.getElementById('page-system-settings');
if (systemSettingsPage) {
    systemSettingsObserver.observe(systemSettingsPage, { attributes: true, attributeFilter: ['class'] });
}

// Helper notification function (if not already defined)
if (typeof showNotification !== 'function') {
    function showNotification(message, type = 'info') {
        console.log(`[${type.toUpperCase()}] ${message}`);
        // Simple alert fallback
        if (type === 'error') {
            alert('Error: ' + message);
        }
    }
}
