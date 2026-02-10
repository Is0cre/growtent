// Dashboard functionality
let dashboardChart = null;

async function loadDashboard() {
    await loadSensorData();
    await loadDevices();
    await loadQuickStats();
    await loadDashboardChart();
    
    // Refresh sensor data every 10 seconds
    setInterval(loadSensorData, 10000);
}

async function loadSensorData() {
    try {
        const response = await api.get('/api/sensors/current');
        if (response.success && response.data) {
            const data = response.data;
            document.getElementById('tempValue').textContent = formatNumber(data.temperature);
            document.getElementById('humidityValue').textContent = formatNumber(data.humidity);
            document.getElementById('pressureValue').textContent = formatNumber(data.pressure);
            document.getElementById('gasValue').textContent = Math.round(data.gas_resistance);
        }
    } catch (error) {
        console.error('Error loading sensor data:', error);
    }
}

async function loadDevices() {
    try {
        const response = await api.get('/api/devices/');
        if (response.success) {
            const devicesList = document.getElementById('devicesList');
            devicesList.innerHTML = '';
            
            response.data.forEach(device => {
                const deviceItem = document.createElement('div');
                deviceItem.className = 'device-item';
                deviceItem.innerHTML = `
                    <div class="device-name">
                        <i class="fas fa-plug"></i>
                        ${device.display_name}
                    </div>
                    <label class="device-toggle">
                        <input type="checkbox" ${device.state ? 'checked' : ''} 
                               onchange="toggleDevice('${device.name}', this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                `;
                devicesList.appendChild(deviceItem);
            });
        }
    } catch (error) {
        console.error('Error loading devices:', error);
    }
}

async function toggleDevice(deviceName, state) {
    try {
        const action = state ? 'on' : 'off';
        const response = await api.post(`/api/devices/${deviceName}/control`, { action });
        if (response.success) {
            console.log(`${deviceName} turned ${action}`);
        }
    } catch (error) {
        console.error('Error toggling device:', error);
        // Reload devices to restore correct state
        loadDevices();
    }
}

async function loadQuickStats() {
    try {
        const projectResponse = await api.get('/api/projects/active');
        if (projectResponse.success && projectResponse.data) {
            const project = projectResponse.data;
            document.getElementById('activeProject').textContent = project.name;
            
            // Calculate days running
            const startDate = new Date(project.start_date);
            const now = new Date();
            const days = Math.floor((now - startDate) / (1000 * 60 * 60 * 24));
            document.getElementById('daysRunning').textContent = days;
            
            // Get data points count
            const dataResponse = await api.get(`/api/sensors/history?hours=24`);
            if (dataResponse.success) {
                document.getElementById('dataPoints').textContent = dataResponse.count;
            }
        } else {
            document.getElementById('activeProject').textContent = 'None';
            document.getElementById('daysRunning').textContent = '0';
            document.getElementById('dataPoints').textContent = '0';
        }
    } catch (error) {
        console.error('Error loading quick stats:', error);
    }
}

async function loadDashboardChart() {
    try {
        const response = await api.get('/api/sensors/history?hours=24&limit=100');
        if (response.success && response.data.length > 0) {
            const data = response.data.reverse(); // Oldest first
            
            const ctx = document.getElementById('dashboardChart').getContext('2d');
            
            if (dashboardChart) {
                dashboardChart.destroy();
            }
            
            dashboardChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => new Date(d.timestamp).toLocaleTimeString()),
                    datasets: [
                        {
                            label: 'Temperature (°C)',
                            data: data.map(d => d.temperature),
                            borderColor: 'rgb(239, 68, 68)',
                            tension: 0.4,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Humidity (%)',
                            data: data.map(d => d.humidity),
                            borderColor: 'rgb(59, 130, 246)',
                            tension: 0.4,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false,
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Temperature (°C)'
                            }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Humidity (%)'
                            },
                            grid: {
                                drawOnChartArea: false,
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error loading dashboard chart:', error);
    }
}
