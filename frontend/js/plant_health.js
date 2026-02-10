// Plant health functionality
function loadPlantHealth() {
    // Page is loaded, ready for user actions
}

document.getElementById('analyzeCamera').addEventListener('click', async () => {
    document.getElementById('healthResults').innerHTML = '<div class="loading"><i class="fas fa-spinner"></i> Analyzing...</div>';
    
    try {
        const response = await api.post('/api/plant-health/analyze-camera');
        if (response.success) {
            displayHealthResults(response.data);
        }
    } catch (error) {
        console.error('Error analyzing plant health:', error);
        document.getElementById('healthResults').innerHTML = '<p>Analysis failed. Please try again.</p>';
    }
});

document.getElementById('uploadImageBtn').addEventListener('click', () => {
    document.getElementById('imageUpload').click();
});

document.getElementById('imageUpload').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    document.getElementById('healthResults').innerHTML = '<div class="loading"><i class="fas fa-spinner"></i> Analyzing...</div>';
    
    try {
        const formData = new FormData();
        formData.append('image', file);
        
        const response = await fetch(`${API_BASE}/api/plant-health/analyze`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayHealthResults(result.data);
        }
    } catch (error) {
        console.error('Error analyzing image:', error);
        document.getElementById('healthResults').innerHTML = '<p>Analysis failed. Please try again.</p>';
    }
});

function displayHealthResults(data) {
    const score = data.health_score;
    let scoreClass = 'score-poor';
    let scoreLabel = 'Poor';
    
    if (score >= 85) {
        scoreClass = 'score-excellent';
        scoreLabel = 'Excellent';
    } else if (score >= 70) {
        scoreClass = 'score-good';
        scoreLabel = 'Good';
    } else if (score >= 50) {
        scoreClass = 'score-fair';
        scoreLabel = 'Fair';
    }
    
    const html = `
        <div class="card">
            <div class="card-body health-score">
                <h2>Plant Health Analysis</h2>
                <div class="score-circle ${scoreClass}">
                    ${score.toFixed(0)}
                </div>
                <h3>${scoreLabel} Health</h3>
                <p>${data.analysis}</p>
            </div>
        </div>
        
        <div class="card health-issues">
            <div class="card-header">
                <h3><i class="fas fa-exclamation-triangle"></i> Issues Detected</h3>
            </div>
            <div class="card-body">
                <ul>
                    ${data.issues.map(issue => `<li>${issue}</li>`).join('')}
                </ul>
            </div>
        </div>
        
        <div class="card health-recommendations">
            <div class="card-header">
                <h3><i class="fas fa-lightbulb"></i> Recommendations</h3>
            </div>
            <div class="card-body">
                <ul>
                    ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;
    
    document.getElementById('healthResults').innerHTML = html;
}
