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
                
                projectCard.innerHTML = `
                    <h3>${project.name} ${project.status === 'active' ? '<span style="color:var(--primary-color)">●</span>' : ''}</h3>
                    <p>${project.notes || 'No description'}</p>
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
            <textarea id="projectNotes" rows="4" placeholder="Optional notes about this grow..."></textarea>
        </div>
        <button class="btn btn-primary" onclick="createProject()">Create Project</button>
    `);
});

async function createProject() {
    const name = document.getElementById('projectName').value;
    const notes = document.getElementById('projectNotes').value;
    
    if (!name) {
        alert('Please enter a project name');
        return;
    }
    
    try {
        const response = await api.post('/api/projects/', { name, notes });
        if (response.success) {
            hideModal();
            showNotification('Project created successfully!');
            loadProjects();
        }
    } catch (error) {
        console.error('Error creating project:', error);
        alert('Failed to create project');
    }
}

async function endProject(projectId) {
    if (!confirm('Are you sure you want to end this project?')) {
        return;
    }
    
    try {
        const response = await api.post(`/api/projects/${projectId}/end`);
        if (response.success) {
            showNotification('Project ended');
            loadProjects();
        }
    } catch (error) {
        console.error('Error ending project:', error);
        alert('Failed to end project');
    }
}
