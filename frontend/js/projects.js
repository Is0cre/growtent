// Projects functionality
async function loadProjects() {
    try {
        const response = await api.get('/api/projects/');
        if (response.success) {
            const projectsList = document.getElementById('projectsList');
            projectsList.innerHTML = '';
            
            if (response.data.length === 0) {
                projectsList.innerHTML = '<p>No projects yet. Create your first project!</p>';
                return;
            }
            
            response.data.forEach(project => {
                const projectCard = document.createElement('div');
                projectCard.className = `project-card ${project.status === 'active' ? 'active' : ''}`;
                
                const startDate = new Date(project.start_date).toLocaleDateString();
                const endDate = project.end_date ? new Date(project.end_date).toLocaleDateString() : 'Ongoing';
                
                // Timelapse status indicator
                let timelapseStatus = '';
                if (project.status === 'active') {
                    if (project.timelapse_enabled) {
                        const smartMode = project.timelapse_only_with_lights ? ' (smart)' : '';
                        timelapseStatus = `<span class="timelapse-badge active">📷 Time-lapse ON${smartMode}</span>`;
                    } else {
                        timelapseStatus = '<span class="timelapse-badge">📷 Time-lapse OFF</span>';
                    }
                }
                
                projectCard.innerHTML = `
                    <h3>${project.name} ${project.status === 'active' ? '<span style="color:var(--primary-color)">●</span>' : ''}</h3>
                    <p>${project.notes || 'No description'}</p>
                    <div class="project-meta">
                        ${timelapseStatus}
                        <small>Images: ${project.timelapse_count || 0}</small>
                    </div>
                    <div style="margin-top:15px; display:flex; justify-content:space-between; align-items:center;">
                        <small>Started: ${startDate} | Ended: ${endDate}</small>
                        ${project.status === 'active' ? 
                            `<button class="btn btn-danger" onclick="endProject(${project.id})">End Project</button>` : 
                            ''}
                    </div>
                `;
                
                projectsList.appendChild(projectCard);
            });
        }
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

document.getElementById('newProjectBtn').addEventListener('click', () => {
    showModal(`
        <h2>Create New Project</h2>
        <div class="form-group">
            <label>Project Name</label>
            <input type="text" id="projectName" placeholder="e.g., Tomato Grow 2024">
        </div>
        <div class="form-group">
            <label>Notes</label>
            <textarea id="projectNotes" rows="3" placeholder="Optional notes about this grow..."></textarea>
        </div>
        
        <div class="section-divider">
            <h3>📷 Time-lapse Settings</h3>
        </div>
        
        <div class="form-group toggle-group">
            <label class="toggle-switch">
                <input type="checkbox" id="enableTimelapse" checked>
                <span class="toggle-slider"></span>
            </label>
            <span class="toggle-label">Enable time-lapse for this project</span>
        </div>
        
        <div id="timelapseOptions" class="timelapse-options">
            <div class="form-group">
                <label>Capture Interval</label>
                <select id="timelapseInterval">
                    <option value="300">Every 5 minutes</option>
                    <option value="600" selected>Every 10 minutes</option>
                    <option value="900">Every 15 minutes</option>
                    <option value="1800">Every 30 minutes</option>
                    <option value="3600">Every hour</option>
                </select>
            </div>
            
            <div class="form-group toggle-group">
                <label class="toggle-switch">
                    <input type="checkbox" id="onlyWithLights" checked>
                    <span class="toggle-slider"></span>
                </label>
                <span class="toggle-label">
                    <strong>Smart mode:</strong> Only capture when lights are ON
                    <small class="hint">Skips captures during dark periods to save storage</small>
                </span>
            </div>
        </div>
        
        <button class="btn btn-primary" onclick="createProject()">Create Project</button>
    `);
    
    // Toggle timelapse options visibility
    document.getElementById('enableTimelapse').addEventListener('change', (e) => {
        const options = document.getElementById('timelapseOptions');
        options.style.display = e.target.checked ? 'block' : 'none';
    });
});

async function createProject() {
    const name = document.getElementById('projectName').value;
    const notes = document.getElementById('projectNotes').value;
    const timelapseEnabled = document.getElementById('enableTimelapse').checked;
    const timelapseInterval = parseInt(document.getElementById('timelapseInterval').value);
    const onlyWithLights = document.getElementById('onlyWithLights').checked;
    
    if (!name) {
        alert('Please enter a project name');
        return;
    }
    
    try {
        const response = await api.post('/api/projects/', { 
            name, 
            notes,
            timelapse_enabled: timelapseEnabled,
            timelapse_interval: timelapseInterval,
            timelapse_only_with_lights: onlyWithLights
        });
        if (response.success) {
            hideModal();
            showNotification(response.message || 'Project created successfully!');
            loadProjects();
        }
    } catch (error) {
        console.error('Error creating project:', error);
        alert('Failed to create project');
    }
}

async function endProject(projectId) {
    if (!confirm('Are you sure you want to end this project? This will stop time-lapse capture and optionally generate a video.')) {
        return;
    }
    
    try {
        const response = await api.post(`/api/projects/${projectId}/end`);
        if (response.success) {
            showNotification(response.message || 'Project ended');
            loadProjects();
        }
    } catch (error) {
        console.error('Error ending project:', error);
        alert('Failed to end project');
    }
}
