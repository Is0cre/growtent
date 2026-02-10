// Camera functionality
async function loadCamera() {
    await loadPhotos();
}

document.getElementById('captureSnapshot').addEventListener('click', async () => {
    try {
        const response = await api.get('/api/camera/snapshot');
        if (response.success) {
            showNotification('Snapshot captured!');
            loadPhotos();
        }
    } catch (error) {
        console.error('Error capturing snapshot:', error);
        alert('Failed to capture snapshot');
    }
});

async function loadPhotos() {
    try {
        const response = await api.get('/api/camera/photos');
        if (response.success) {
            const gallery = document.getElementById('photoGallery');
            gallery.innerHTML = '<h2>Recent Photos</h2>';
            
            if (response.data.length === 0) {
                gallery.innerHTML += '<p>No photos yet.</p>';
                return;
            }
            
            const grid = document.createElement('div');
            grid.className = 'photo-gallery';
            
            response.data.forEach(photo => {
                const item = document.createElement('div');
                item.className = 'photo-item';
                item.innerHTML = `<img src="/${photo.path}" alt="${photo.filename}" 
                                       onclick="showImageModal('/${photo.path}')">`;
                grid.appendChild(item);
            });
            
            gallery.appendChild(grid);
        }
    } catch (error) {
        console.error('Error loading photos:', error);
    }
}
