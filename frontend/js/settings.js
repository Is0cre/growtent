// Settings functionality
async function loadSettings() {
    await loadDeviceSettings();
    await loadAlertSettings();
}

async function loadDeviceSettings() {
    try {
        const response = await api.get('/api/settings/devices');
        if (response.success) {
            const container = document.getElementById('deviceSettings');
            container.innerHTML = '<h2>Device Settings</h2>';
            
            for (const [deviceName, settings] of Object.entries(response.data)) {
                const card = createDeviceSettingsCard(deviceName, settings);
                container.appendChild(card);
            }
        }
    } catch (error) {
        console.error('Error loading device settings:', error);
    }
}

function createDeviceSettingsCard(deviceName, settings) {
    const card = document.createElement('div');
    card.className = 'card';
    
    const displayName = deviceName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    
    card.innerHTML = `
        <div class="card-header">
            <h3>${displayName}</h3>
        </div>
        <div class="card-body">
            <div class="form-group">
                <label><input type="checkbox" ${settings.enabled ? 'checked' : ''} 
                       id="${deviceName}_enabled"> Enabled</label>
            </div>
            <div class="form-group">
                <label>Control Mode</label>
                <select id="${deviceName}_mode">
                    <option value="schedule" ${settings.mode === 'schedule' ? 'selected' : ''}>Schedule</option>
                    <option value="threshold" ${settings.mode === 'threshold' ? 'selected' : ''}>Threshold</option>
                    <option value="auto" ${settings.mode === 'auto' ? 'selected' : ''}>Auto (Schedule + Threshold)</option>
                    <option value="manual" ${settings.mode === 'manual' ? 'selected' : ''}>Manual</option>
                </select>
            </div>
            <div class="form-group">
                <label>Schedule (JSON)</label>
                <textarea id="${deviceName}_schedule" rows="4">${JSON.stringify(settings.schedule || [], null, 2)}</textarea>
            </div>
            <div class="form-group">
                <label>Thresholds (JSON)</label>
                <textarea id="${deviceName}_thresholds" rows="3">${JSON.stringify(settings.thresholds || {}, null, 2)}</textarea>
            </div>
            <button class="btn btn-primary" onclick="saveDeviceSettings('${deviceName}')">
                <i class="fas fa-save"></i> Save ${displayName} Settings
            </button>
        </div>
    `;
    
    return card;
}

async function saveDeviceSettings(deviceName) {
    try {
        const enabled = document.getElementById(`${deviceName}_enabled`).checked;
        const mode = document.getElementById(`${deviceName}_mode`).value;
        const scheduleText = document.getElementById(`${deviceName}_schedule`).value;
        const thresholdsText = document.getElementById(`${deviceName}_thresholds`).value;
        
        let schedule, thresholds;
        try {
            schedule = JSON.parse(scheduleText);
            thresholds = JSON.parse(thresholdsText);
        } catch (e) {
            alert('Invalid JSON format');
            return;
        }
        
        const response = await api.put(`/api/settings/devices/${deviceName}`, {
            enabled,
            mode,
            schedule,
            thresholds
        });
        
        if (response.success) {
            showNotification('Settings saved!');
        }
    } catch (error) {
        console.error('Error saving device settings:', error);
        alert('Failed to save settings');
    }
}

async function loadAlertSettings() {
    try {
        const response = await api.get('/api/settings/alerts');
        if (response.success && response.data) {
            const data = response.data;
            document.getElementById('alertsEnabled').checked = data.enabled;
            document.getElementById('tempMin').value = data.temp_min || '';
            document.getElementById('tempMax').value = data.temp_max || '';
            document.getElementById('humidityMin').value = data.humidity_min || '';
            document.getElementById('humidityMax').value = data.humidity_max || '';
        }
    } catch (error) {
        console.error('Error loading alert settings:', error);
    }
}

document.getElementById('saveAlertSettings').addEventListener('click', async () => {
    try {
        const enabled = document.getElementById('alertsEnabled').checked;
        const temp_min = parseFloat(document.getElementById('tempMin').value) || null;
        const temp_max = parseFloat(document.getElementById('tempMax').value) || null;
        const humidity_min = parseFloat(document.getElementById('humidityMin').value) || null;
        const humidity_max = parseFloat(document.getElementById('humidityMax').value) || null;
        
        const response = await api.put('/api/settings/alerts', {
            enabled,
            temp_min,
            temp_max,
            humidity_min,
            humidity_max,
            notification_interval: 300
        });
        
        if (response.success) {
            showNotification('Alert settings saved!');
        }
    } catch (error) {
        console.error('Error saving alert settings:', error);
        alert('Failed to save settings');
    }
});
