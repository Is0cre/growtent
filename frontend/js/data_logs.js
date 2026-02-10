// Data logs functionality
let dataLogsChart = null;

async function loadDataLogs() {
    const hours = document.getElementById('timeRange').value;
    await loadDataChart(hours);
}

document.getElementById('timeRange').addEventListener('change', () => {
    loadDataLogs();
});

async function loadDataChart(hours = 24) {
    try {
        const response = await api.get(`/api/sensors/history?hours=${hours}&limit=500`);
        if (response.success && response.data.length > 0) {
            const data = response.data.reverse();
            
            const ctx = document.getElementById('dataLogsChart').getContext('2d');
            
            if (dataLogsChart) {
                dataLogsChart.destroy();
            }
            
            dataLogsChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => new Date(d.timestamp).toLocaleString()),
                    datasets: [
                        {
                            label: 'Temperature (°C)',
                            data: data.map(d => d.temperature),
                            borderColor: 'rgb(239, 68, 68)',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            tension: 0.4
                        },
                        {
                            label: 'Humidity (%)',
                            data: data.map(d => d.humidity),
                            borderColor: 'rgb(59, 130, 246)',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            tension: 0.4
                        },
                        {
                            label: 'Pressure (hPa)',
                            data: data.map(d => d.pressure),
                            borderColor: 'rgb(16, 185, 129)',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            tension: 0.4,
                            hidden: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            ticks: {
                                maxTicksLimit: 10
                            }
                        }
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error loading data chart:', error);
    }
}

document.getElementById('exportDataBtn').addEventListener('click', async () => {
    const hours = document.getElementById('timeRange').value;
    
    try {
        const response = await api.get(`/api/sensors/history?hours=${hours}&limit=10000`);
        if (response.success && response.data.length > 0) {
            const csv = convertToCSV(response.data);
            downloadCSV(csv, `sensor_data_${hours}h.csv`);
        } else {
            alert('No data to export');
        }
    } catch (error) {
        console.error('Error exporting data:', error);
        alert('Failed to export data');
    }
});

function convertToCSV(data) {
    const headers = ['Timestamp', 'Temperature (°C)', 'Humidity (%)', 'Pressure (hPa)', 'Gas Resistance (Ω)'];
    const rows = data.map(d => [
        d.timestamp,
        d.temperature,
        d.humidity,
        d.pressure,
        d.gas_resistance
    ]);
    
    return [headers, ...rows].map(row => row.join(',')).join('\n');
}

function downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('hidden', '');
    a.setAttribute('href', url);
    a.setAttribute('download', filename);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}
