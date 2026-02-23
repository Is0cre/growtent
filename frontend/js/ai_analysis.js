/**
 * AI Analysis page functionality
 */

// Load AI analysis status on page load
async function loadAIAnalysisStatus() {
    try {
        const response = await fetch('/api/analysis/status');
        const data = await response.json();
        
        if (data.success) {
            const status = data.data;
            
            document.getElementById('aiStatusEnabled').textContent = 
                status.enabled ? 'Enabled' : 'Disabled';
            document.getElementById('aiStatusEnabled').className = 
                status.enabled ? 'value status-enabled' : 'value status-disabled';
            
            document.getElementById('aiStatusLastAnalysis').textContent = 
                status.latest_analysis ? new Date(status.latest_analysis).toLocaleString() : 'Never';
            
            document.getElementById('aiStatusHealthScore').textContent = 
                status.latest_health_score ? `${status.latest_health_score}/10` : '--';
            
            document.getElementById('aiStatusTotal').textContent = 
                status.total_analyses || 0;
        }
    } catch (error) {
        console.error('Error loading AI status:', error);
    }
}

// Load analysis history
async function loadAnalysisHistory() {
    try {
        const response = await fetch('/api/analysis/?limit=20');
        const data = await response.json();
        
        const container = document.getElementById('analysisHistory');
        
        if (!data.success || !data.data || data.data.length === 0) {
            container.innerHTML = '<p class="no-data">No analyses yet. Click "Analyze Now" to run your first analysis.</p>';
            return;
        }
        
        container.innerHTML = data.data.map(analysis => `
            <div class="analysis-item">
                <div class="analysis-header">
                    <span class="analysis-date">${new Date(analysis.timestamp).toLocaleString()}</span>
                    <span class="health-score ${getScoreClass(analysis.health_score)}">
                        Health: ${analysis.health_score || 'N/A'}/10
                    </span>
                </div>
                <div class="analysis-content">
                    ${analysis.photo_path ? `<img src="/data/${analysis.photo_path.replace('data/', '')}" alt="Analysis photo" class="analysis-photo" onerror="this.style.display='none'">` : ''}
                    <div class="analysis-text">
                        ${formatAnalysisText(analysis.analysis_text)}
                    </div>
                </div>
                ${analysis.recommendations ? `
                    <div class="analysis-recommendations">
                        <strong>Recommendations:</strong> ${analysis.recommendations}
                    </div>
                ` : ''}
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading analysis history:', error);
        document.getElementById('analysisHistory').innerHTML = 
            '<p class="error">Error loading analyses</p>';
    }
}

function getScoreClass(score) {
    if (!score) return '';
    if (score >= 8) return 'score-good';
    if (score >= 6) return 'score-ok';
    if (score >= 4) return 'score-warning';
    return 'score-bad';
}

function formatAnalysisText(text) {
    if (!text) return '';
    // Truncate long text and add formatting
    const maxLength = 500;
    let formatted = text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    // Convert newlines to <br>
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
}

// Analyze now button
document.getElementById('analyzeNowBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('analyzeNowBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
    
    try {
        const response = await fetch('/api/analysis/now', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Analysis started! Results will appear shortly.', 'success');
            // Refresh data after a delay
            setTimeout(() => {
                loadAIAnalysisStatus();
                loadAnalysisHistory();
            }, 5000);
        } else {
            showNotification(data.detail || 'Analysis failed', 'error');
        }
    } catch (error) {
        console.error('Error starting analysis:', error);
        showNotification('Failed to start analysis', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-robot"></i> Analyze Now';
    }
});

// Initialize when page becomes visible
function initAIAnalysisPage() {
    loadAIAnalysisStatus();
    loadAnalysisHistory();
}

// Auto-refresh when page is shown
const aiAnalysisObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.target.id === 'page-ai-analysis' && 
            mutation.target.classList.contains('active')) {
            initAIAnalysisPage();
        }
    });
});

const aiAnalysisPage = document.getElementById('page-ai-analysis');
if (aiAnalysisPage) {
    aiAnalysisObserver.observe(aiAnalysisPage, { attributes: true, attributeFilter: ['class'] });
}
