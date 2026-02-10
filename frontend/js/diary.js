// Diary functionality
async function loadDiary() {
    try {
        const response = await api.get('/api/diary/');
        if (response.success) {
            const diaryEntries = document.getElementById('diaryEntries');
            diaryEntries.innerHTML = '';
            
            if (response.data.length === 0) {
                diaryEntries.innerHTML = '<p>No diary entries yet. Start documenting your grow!</p>';
                return;
            }
            
            response.data.forEach(entry => {
                const entryDiv = document.createElement('div');
                entryDiv.className = 'diary-entry';
                
                const photos = entry.photos && entry.photos.length > 0 
                    ? `<div class="diary-photos">
                        ${entry.photos.map(photo => 
                            `<img src="/${photo}" alt="Diary photo" onclick="showImageModal('/${photo}')">`
                        ).join('')}
                       </div>`
                    : '';
                
                entryDiv.innerHTML = `
                    <div class="diary-entry-header">
                        <div>
                            <h3>${entry.title}</h3>
                            <small>${formatDate(entry.timestamp)}</small>
                        </div>
                        <button class="btn btn-danger" onclick="deleteDiaryEntry(${entry.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    <p>${entry.text}</p>
                    ${photos}
                `;
                
                diaryEntries.appendChild(entryDiv);
            });
        }
    } catch (error) {
        console.error('Error loading diary:', error);
    }
}

document.getElementById('newEntryBtn').addEventListener('click', () => {
    showModal(`
        <h2>New Diary Entry</h2>
        <div class="form-group">
            <label>Title</label>
            <input type="text" id="entryTitle" placeholder="Day 15: First flowers">
        </div>
        <div class="form-group">
            <label>Notes</label>
            <textarea id="entryText" rows="6" placeholder="Describe what you observe..."></textarea>
        </div>
        <div class="form-group">
            <label>Photos (optional)</label>
            <input type="file" id="entryPhotos" multiple accept="image/*">
        </div>
        <button class="btn btn-primary" onclick="createDiaryEntry()">Save Entry</button>
    `);
});

async function createDiaryEntry() {
    const title = document.getElementById('entryTitle').value;
    const text = document.getElementById('entryText').value;
    const photosInput = document.getElementById('entryPhotos');
    
    if (!title || !text) {
        alert('Please fill in title and notes');
        return;
    }
    
    try {
        // Get active project
        const projectResponse = await api.get('/api/projects/active');
        if (!projectResponse.success || !projectResponse.data) {
            alert('No active project. Please create a project first.');
            return;
        }
        
        const formData = new FormData();
        formData.append('project_id', projectResponse.data.id);
        formData.append('title', title);
        formData.append('text', text);
        
        if (photosInput.files.length > 0) {
            for (let file of photosInput.files) {
                formData.append('photos', file);
            }
        }
        
        const response = await fetch(`${API_BASE}/api/diary/`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            hideModal();
            showNotification('Diary entry created!');
            loadDiary();
        }
    } catch (error) {
        console.error('Error creating diary entry:', error);
        alert('Failed to create entry');
    }
}

async function deleteDiaryEntry(entryId) {
    if (!confirm('Delete this diary entry?')) return;
    
    try {
        const response = await api.delete(`/api/diary/${entryId}`);
        if (response.success) {
            showNotification('Entry deleted');
            loadDiary();
        }
    } catch (error) {
        console.error('Error deleting entry:', error);
        alert('Failed to delete entry');
    }
}

function showImageModal(imageSrc) {
    showModal(`<img src="${imageSrc}" style="max-width:100%; border-radius:8px;">`);
}
