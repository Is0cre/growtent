// Timelapse functionality
async function loadTimelapse() {
    await loadTimelapseStatus();
    await loadTimelapseVideos();
}

async function loadTimelapseStatus() {
    try {
        const response = await api.get('/api/timelapse/status');
        if (response.success && response.data) {
            document.getElementById('timelapseStatus').textContent = 
                response.data.enabled ? 'Capturing' : 'Stopped';
            document.getElementById('imageCount').textContent = response.data.image_count;
            document.getElementById('timelapseInterval').value = response.data.interval;
        }
    } catch (error) {
        console.error('Error loading timelapse status:', error);
    }
}

document.getElementById('startTimelapse').addEventListener('click', async () => {
    const interval = parseInt(document.getElementById('timelapseInterval').value);
    
    try {
        const response = await api.post(`/api/timelapse/start?interval=${interval}`);
        if (response.success) {
            showNotification('Time-lapse capture started!');
            loadTimelapseStatus();
        }
    } catch (error) {
        console.error('Error starting timelapse:', error);
        alert('Failed to start timelapse');
    }
});

document.getElementById('stopTimelapse').addEventListener('click', async () => {
    try {
        const response = await api.post('/api/timelapse/stop');
        if (response.success) {
            showNotification('Time-lapse capture stopped');
            loadTimelapseStatus();
        }
    } catch (error) {
        console.error('Error stopping timelapse:', error);
        alert('Failed to stop timelapse');
    }
});

document.getElementById('generateVideo').addEventListener('click', async () => {
    const fps = 30;
    
    if (!confirm(`Generate time-lapse video at ${fps} FPS? This may take a few minutes.`)) {
        return;
    }
    
    try {
        const response = await api.post(`/api/timelapse/generate?fps=${fps}`);
        if (response.success) {
            showNotification('Video generation started! Check back in a few minutes.');
            setTimeout(loadTimelapseVideos, 5000);
        }
    } catch (error) {
        console.error('Error generating video:', error);
        alert('Failed to generate video');
    }
});

async function loadTimelapseVideos() {
    try {
        const response = await api.get('/api/timelapse/videos');
        if (response.success) {
            const container = document.getElementById('timelapseVideos');
            container.innerHTML = '<h2>Generated Videos</h2>';
            
            if (response.data.length === 0) {
                container.innerHTML += '<p>No videos generated yet.</p>';
                return;
            }
            
            response.data.forEach(video => {
                const videoCard = document.createElement('div');
                videoCard.className = 'card';
                videoCard.innerHTML = `
                    <div class="card-body">
                        <h3>${video.filename}</h3>
                        <p>Size: ${(video.size / 1024 / 1024).toFixed(2)} MB</p>
                        <p>Created: ${new Date(video.created).toLocaleString()}</p>
                        <a href="/api/timelapse/videos/${video.filename}" 
                           class="btn btn-primary" download>
                            <i class="fas fa-download"></i> Download
                        </a>
                    </div>
                `;
                container.appendChild(videoCard);
            });
        }
    } catch (error) {
        console.error('Error loading videos:', error);
    }
}
