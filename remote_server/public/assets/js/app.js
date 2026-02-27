/**
 * Grow Tent Monitor - Remote Dashboard
 * Main Application JavaScript
 */

const App = {
    currentPage: 'dashboard',
    refreshInterval: null,
    charts: {},
    
    // Initialize application
    init(page = 'dashboard') {
        this.currentPage = page;
        this.setupEventListeners();
        this.loadPage(page);
        this.startAutoRefresh();
        this.checkSyncStatus();
    },
    
    // Setup event listeners
    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                this.navigate(page);
            });
        });
        
        // Menu toggle
        document.getElementById('menuToggle').addEventListener('click', () => {
            document.querySelector('.sidebar').classList.toggle('open');
        });
        
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadPage(this.currentPage);
        });
        
        // Lightbox
        document.getElementById('lightboxClose').addEventListener('click', () => {
            this.closeLightbox();
        });
        
        document.getElementById('lightbox').addEventListener('click', (e) => {
            if (e.target.id === 'lightbox') this.closeLightbox();
        });
        
        // Video modal
        document.getElementById('videoModalClose').addEventListener('click', () => {
            this.closeVideoModal();
        });
        
        // History controls
        document.getElementById('loadHistoryBtn')?.addEventListener('click', () => {
            this.loadHistory();
        });
        
        document.querySelectorAll('.quick-ranges button').forEach(btn => {
            btn.addEventListener('click', () => {
                this.loadHistory(parseInt(btn.dataset.hours));
            });
        });
        
        document.getElementById('exportCsvBtn')?.addEventListener('click', () => {
            this.exportCsv();
        });
        
        // Time-lapse tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchTab(btn.dataset.tab);
            });
        });
        
        // Project filters
        document.querySelectorAll('.projects-filters .btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.loadProjects(btn.dataset.status);
            });
        });
        
        // Diary filters
        document.getElementById('diaryProjectFilter')?.addEventListener('change', () => {
            this.loadDiary();
        });
        
        document.getElementById('diaryTypeFilter')?.addEventListener('change', () => {
            this.loadDiary();
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeLightbox();
                this.closeVideoModal();
            }
        });
    },
    
    // Navigate to page
    navigate(page) {
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        document.querySelector(`[data-page="${page}"]`).classList.add('active');
        
        document.querySelectorAll('.page-content').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${page}`).classList.add('active');
        
        document.getElementById('pageTitle').textContent = this.capitalize(page);
        
        this.currentPage = page;
        history.pushState({}, '', `?page=${page}`);
        
        this.loadPage(page);
        
        // Close mobile menu
        document.querySelector('.sidebar').classList.remove('open');
    },
    
    // Load page content
    async loadPage(page) {
        this.showLoading();
        
        try {
            switch (page) {
                case 'dashboard':
                    await this.loadDashboard();
                    break;
                case 'history':
                    await this.loadHistory(24);
                    break;
                case 'analysis':
                    await this.loadAnalysis();
                    break;
                case 'diary':
                    await this.loadDiary();
                    break;
                case 'timelapse':
                    await this.loadTimelapse();
                    break;
                case 'projects':
                    await this.loadProjects();
                    break;
            }
            
            this.updateLastUpdate();
        } catch (error) {
            console.error('Error loading page:', error);
            this.showError('Failed to load data');
        }
        
        this.hideLoading();
    },
    
    // Load Dashboard
    async loadDashboard() {
        const response = await fetch('api/current_data.php');
        const result = await response.json();
        
        if (!result.success) throw new Error(result.message);
        
        const data = result.data;
        
        // Update project info
        if (data.project) {
            document.getElementById('projectName').textContent = data.project.name;
            document.getElementById('projectMeta').textContent = 
                `${data.project.plant_type || ''} ${data.project.strain ? '- ' + data.project.strain : ''} | Day ${data.project.days_running}`;
            document.getElementById('projectStatus').textContent = data.project.status;
        } else {
            document.getElementById('projectName').textContent = 'No Active Project';
            document.getElementById('projectMeta').textContent = '';
            document.getElementById('projectStatus').textContent = '--';
        }
        
        // Update sensor values
        if (data.sensors) {
            document.getElementById('tempValue').textContent = data.sensors.temperature;
            document.getElementById('humidityValue').textContent = data.sensors.humidity;
            document.getElementById('pressureValue').textContent = data.sensors.pressure;
            document.getElementById('gasValue').textContent = (data.sensors.gas_resistance / 1000).toFixed(1);
            
            const aqBadge = document.getElementById('airQualityBadge');
            aqBadge.textContent = data.sensors.air_quality || 'Unknown';
            aqBadge.className = 'air-quality-badge ' + (data.sensors.air_quality || '').toLowerCase();
            
            // Draw gauges
            this.drawGauge('tempGauge', data.sensors.temperature, 15, 35, ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444']);
            this.drawGauge('humidityGauge', data.sensors.humidity, 0, 100, ['#ef4444', '#22c55e', '#22c55e', '#3b82f6']);
            this.drawGauge('pressureGauge', data.sensors.pressure, 950, 1050, ['#8b5cf6', '#a855f7']);
        }
        
        // Update stats
        document.getElementById('statPhotos').textContent = data.stats.total_photos;
        document.getElementById('statDays').textContent = data.project?.days_running || '--';
        document.getElementById('statHealth').textContent = data.latest_analysis?.health_score || '--';
        document.getElementById('statAirQuality').textContent = data.sensors?.air_quality || '--';
        
        // Update latest photo
        if (data.stats.latest_photo) {
            const photoEl = document.getElementById('latestPhoto');
            photoEl.src = `data/${data.stats.latest_photo}`;
            photoEl.onclick = () => this.openLightbox(`data/${data.stats.latest_photo}`);
            document.getElementById('photoTime').textContent = this.formatDate(data.stats.latest_photo_time);
        }
        
        // Load mini charts
        await this.loadMiniCharts();
    },
    
    // Draw gauge
    drawGauge(canvasId, value, min, max, colors) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const width = canvas.width = canvas.offsetWidth;
        const height = canvas.height = canvas.offsetHeight;
        
        ctx.clearRect(0, 0, width, height);
        
        const percentage = Math.max(0, Math.min(1, (value - min) / (max - min)));
        const barHeight = 8;
        const barY = height / 2 - barHeight / 2;
        const barRadius = barHeight / 2;
        
        // Background
        ctx.fillStyle = '#334155';
        ctx.beginPath();
        ctx.roundRect(0, barY, width, barHeight, barRadius);
        ctx.fill();
        
        // Gradient fill
        const gradient = ctx.createLinearGradient(0, 0, width, 0);
        colors.forEach((color, i) => {
            gradient.addColorStop(i / (colors.length - 1), color);
        });
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.roundRect(0, barY, width * percentage, barHeight, barRadius);
        ctx.fill();
        
        // Indicator
        const indicatorX = width * percentage;
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(indicatorX, height / 2, 6, 0, Math.PI * 2);
        ctx.fill();
    },
    
    // Load mini charts
    async loadMiniCharts() {
        const response = await fetch('api/sensor_history.php?hours=24');
        const result = await response.json();
        
        if (!result.success) return;
        
        const data = result.data;
        
        // Temperature chart
        this.createMiniChart('miniTempChart', data.labels, data.temperature, '#ef4444', 'Temperature');
        
        // Humidity chart
        this.createMiniChart('miniHumidityChart', data.labels, data.humidity, '#3b82f6', 'Humidity');
    },
    
    // Create mini chart
    createMiniChart(canvasId, labels, data, color, label) {
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: label,
                    data: data,
                    borderColor: color,
                    backgroundColor: color + '20',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { display: false },
                    y: { display: false }
                }
            }
        });
    },
    
    // Load History
    async loadHistory(hours = 24) {
        let url = `api/sensor_history.php?hours=${hours}`;
        
        const start = document.getElementById('historyStart')?.value;
        const end = document.getElementById('historyEnd')?.value;
        
        if (start && end) {
            url = `api/sensor_history.php?start=${start}&end=${end}`;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (!result.success) throw new Error(result.message);
        
        const data = result.data;
        
        // Temperature & Humidity chart
        this.createHistoryChart('tempHumidityChart', data.labels, [
            { label: 'Temperature (°C)', data: data.temperature, color: '#ef4444' },
            { label: 'Humidity (%)', data: data.humidity, color: '#3b82f6' }
        ]);
        
        // Pressure chart
        this.createHistoryChart('pressureChart', data.labels, [
            { label: 'Pressure (hPa)', data: data.pressure, color: '#8b5cf6' }
        ]);
        
        // Gas chart
        this.createHistoryChart('gasChart', data.labels, [
            { label: 'Gas Resistance (Ω)', data: data.gas_resistance, color: '#10b981' }
        ]);
    },
    
    // Create history chart
    createHistoryChart(canvasId, labels, datasets) {
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }
        
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets.map(ds => ({
                    label: ds.label,
                    data: ds.data,
                    borderColor: ds.color,
                    backgroundColor: ds.color + '20',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 1,
                    borderWidth: 2
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { color: '#94a3b8' }
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleColor: '#f8fafc',
                        bodyColor: '#94a3b8',
                        borderColor: '#334155',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#64748b', maxTicksLimit: 10 },
                        grid: { color: '#334155' }
                    },
                    y: {
                        ticks: { color: '#64748b' },
                        grid: { color: '#334155' }
                    }
                }
            }
        });
    },
    
    // Load Analysis
    async loadAnalysis() {
        const response = await fetch('api/analysis.php?limit=20');
        const result = await response.json();
        
        if (!result.success) throw new Error(result.message);
        
        // Health trend chart
        if (result.trend && result.trend.length > 0) {
            this.createHealthTrendChart(result.trend);
        }
        
        // Latest analysis
        if (result.data.length > 0) {
            await this.loadAnalysisDetail(result.data[0].id);
        }
        
        // Analysis list
        this.renderAnalysisList(result.data);
    },
    
    // Create health trend chart
    createHealthTrendChart(trend) {
        if (this.charts['healthTrendChart']) {
            this.charts['healthTrendChart'].destroy();
        }
        
        const ctx = document.getElementById('healthTrendChart');
        if (!ctx) return;
        
        this.charts['healthTrendChart'] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: trend.map(t => t.date),
                datasets: [{
                    label: 'Health Score',
                    data: trend.map(t => t.avg_score),
                    borderColor: '#10b981',
                    backgroundColor: '#10b98120',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    borderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ticks: { color: '#64748b' },
                        grid: { color: '#334155' }
                    },
                    y: {
                        min: 0,
                        max: 100,
                        ticks: { color: '#64748b' },
                        grid: { color: '#334155' }
                    }
                }
            }
        });
    },
    
    // Load single analysis detail
    async loadAnalysisDetail(id) {
        const response = await fetch(`api/analysis.php?id=${id}`);
        const result = await response.json();
        
        if (!result.success) return;
        
        const analysis = result.data;
        
        if (analysis.photo_path) {
            document.getElementById('analysisPhoto').src = `data/${analysis.photo_path}`;
        }
        
        document.getElementById('analysisScore').textContent = analysis.health_score || '--';
        document.getElementById('growthStage').textContent = analysis.growth_stage || 'Unknown';
        document.getElementById('analysisText').textContent = analysis.analysis_text || 'No analysis available';
        document.getElementById('analysisDate').textContent = this.formatDate(analysis.created_at);
        document.getElementById('analysisModel').textContent = analysis.model_used || 'Unknown model';
        
        // Recommendations
        const recsEl = document.getElementById('recommendations');
        if (analysis.recommendations && analysis.recommendations.length > 0) {
            recsEl.innerHTML = `
                <h4>💡 Recommendations</h4>
                <ul>${analysis.recommendations.map(r => `<li>${r}</li>`).join('')}</ul>
            `;
        } else {
            recsEl.innerHTML = '';
        }
    },
    
    // Render analysis list
    renderAnalysisList(analyses) {
        const container = document.getElementById('analysisItems');
        
        if (analyses.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🤖</div><div class="empty-state-text">No analyses yet</div></div>';
            return;
        }
        
        container.innerHTML = analyses.map(a => `
            <div class="analysis-item" onclick="App.loadAnalysisDetail(${a.id})">
                <img src="data/${a.photo_path || 'placeholder.jpg'}" alt="">
                <div>
                    <div style="font-weight: 600;">${a.growth_stage || 'Analysis'}</div>
                    <div style="font-size: 12px; color: #64748b;">${this.formatDate(a.created_at)}</div>
                </div>
                <div class="analysis-item-score">${a.health_score || '--'}</div>
            </div>
        `).join('');
    },
    
    // Load Diary
    async loadDiary(page = 1) {
        let url = `api/diary.php?page=${page}`;
        
        const projectId = document.getElementById('diaryProjectFilter')?.value;
        const entryType = document.getElementById('diaryTypeFilter')?.value;
        
        if (projectId) url += `&project_id=${projectId}`;
        if (entryType) url += `&type=${entryType}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (!result.success) throw new Error(result.message);
        
        this.renderDiaryEntries(result.data);
        this.renderPagination('diaryPagination', result.pagination, (p) => this.loadDiary(p));
        
        // Load projects for filter
        await this.loadProjectsFilter();
    },
    
    // Load projects for filter dropdown
    async loadProjectsFilter() {
        const response = await fetch('api/projects.php?status=all');
        const result = await response.json();
        
        if (!result.success) return;
        
        const select = document.getElementById('diaryProjectFilter');
        if (!select || select.options.length > 1) return;
        
        result.data.forEach(p => {
            const option = document.createElement('option');
            option.value = p.id;
            option.textContent = p.name;
            select.appendChild(option);
        });
    },
    
    // Render diary entries
    renderDiaryEntries(entries) {
        const container = document.getElementById('diaryTimeline');
        
        if (entries.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📔</div><div class="empty-state-text">No diary entries yet</div></div>';
            return;
        }
        
        container.innerHTML = entries.map(e => `
            <div class="diary-entry">
                <div class="diary-entry-header">
                    <div>
                        <div class="diary-entry-title">${e.title || 'Diary Entry'}</div>
                        <div class="diary-entry-date">${this.formatDate(e.created_at)}</div>
                    </div>
                    <span class="diary-entry-type">${e.entry_type}</span>
                </div>
                <div class="diary-entry-content">${e.content || ''}</div>
                ${e.photo_path ? `<img class="diary-entry-photo" src="data/${e.photo_path}" onclick="App.openLightbox('data/${e.photo_path}')">` : ''}
                ${e.tags && e.tags.length > 0 ? `
                    <div class="diary-entry-tags">
                        ${e.tags.map(t => `<span class="diary-tag">${t}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `).join('');
    },
    
    // Load Time-lapse
    async loadTimelapse(type = 'videos', page = 1) {
        const response = await fetch(`api/timelapse.php?type=${type}&page=${page}`);
        const result = await response.json();
        
        if (!result.success) throw new Error(result.message);
        
        if (type === 'videos') {
            this.renderVideos(result.data);
        } else {
            this.renderImages(result.data);
        }
        
        this.renderPagination('timelapsePagination', result.pagination, (p) => this.loadTimelapse(type, p));
    },
    
    // Switch time-lapse tab
    switchTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
        
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        document.getElementById(`tab-${tab}`).classList.add('active');
        
        this.loadTimelapse(tab);
    },
    
    // Render videos
    renderVideos(videos) {
        const container = document.getElementById('videoGrid');
        
        if (videos.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🎬</div><div class="empty-state-text">No time-lapse videos yet</div></div>';
            return;
        }
        
        container.innerHTML = videos.map(v => `
            <div class="video-card" onclick="App.playVideo('data/${v.video_path}', '${v.project_name || 'Time-lapse'}')">
                <div class="video-thumbnail">
                    ${v.thumbnail_path ? `<img src="data/${v.thumbnail_path}" alt="">` : ''}
                    <div class="video-play-icon">▶️</div>
                </div>
                <div class="video-info">
                    <div class="video-title">${v.project_name || 'Time-lapse'}</div>
                    <div class="video-meta">
                        <span>${v.frame_count || 0} frames</span>
                        <span>${v.file_size_formatted}</span>
                        <span>${this.formatDate(v.created_at)}</span>
                    </div>
                </div>
            </div>
        `).join('');
    },
    
    // Render images
    renderImages(images) {
        const container = document.getElementById('imageGallery');
        
        if (images.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📷</div><div class="empty-state-text">No time-lapse images yet</div></div>';
            return;
        }
        
        container.innerHTML = images.map(i => `
            <div class="gallery-item" onclick="App.openLightbox('data/${i.image_path}', '${this.formatDate(i.captured_at)}')">
                <img src="data/${i.thumbnail_path || i.image_path}" alt="">
                <div class="gallery-item-date">${this.formatDate(i.captured_at)}</div>
            </div>
        `).join('');
    },
    
    // Load Projects
    async loadProjects(status = '', page = 1) {
        let url = `api/projects.php?page=${page}`;
        if (status) url += `&status=${status}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (!result.success) throw new Error(result.message);
        
        this.renderProjects(result.data);
        this.renderPagination('projectsPagination', result.pagination, (p) => this.loadProjects(status, p));
        
        // Update active filter button
        document.querySelectorAll('.projects-filters .btn').forEach(b => {
            b.classList.toggle('active', b.dataset.status === status);
        });
    },
    
    // Render projects
    renderProjects(projects) {
        const container = document.getElementById('projectsGrid');
        
        if (projects.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📁</div><div class="empty-state-text">No projects yet</div></div>';
            return;
        }
        
        container.innerHTML = projects.map(p => `
            <div class="project-card">
                <div class="project-card-header">
                    <h3>${p.name}</h3>
                    <div class="project-card-meta">
                        ${p.plant_type || ''}${p.strain ? ' - ' + p.strain : ''} | 
                        Day ${p.days_running}
                    </div>
                </div>
                <div class="project-card-body">
                    <div class="project-stats">
                        <div class="project-stat">
                            <div class="project-stat-value">${p.sensor_readings || 0}</div>
                            <div class="project-stat-label">Readings</div>
                        </div>
                        <div class="project-stat">
                            <div class="project-stat-value">${p.timelapse_images || 0}</div>
                            <div class="project-stat-label">Photos</div>
                        </div>
                        <div class="project-stat">
                            <div class="project-stat-value">${p.diary_entries || 0}</div>
                            <div class="project-stat-label">Diary</div>
                        </div>
                        <div class="project-stat">
                            <div class="project-stat-value">${Math.round(p.avg_health_score) || '--'}</div>
                            <div class="project-stat-label">Health</div>
                        </div>
                    </div>
                </div>
                <div class="project-card-footer">
                    <span class="project-status-badge ${p.status}">${p.status}</span>
                    <span style="font-size: 12px; color: #64748b;">
                        ${this.formatDate(p.start_date)} ${p.end_date ? '- ' + this.formatDate(p.end_date) : ''}
                    </span>
                </div>
            </div>
        `).join('');
    },
    
    // Render pagination
    renderPagination(containerId, pagination, callback) {
        const container = document.getElementById(containerId);
        if (!container || pagination.pages <= 1) {
            if (container) container.innerHTML = '';
            return;
        }
        
        let html = '<button ' + (pagination.page <= 1 ? 'disabled' : '') + ' onclick="' + `App.paginationCallback(${pagination.page - 1})` + '">←</button>';
        
        for (let i = 1; i <= pagination.pages; i++) {
            if (i === 1 || i === pagination.pages || Math.abs(i - pagination.page) <= 2) {
                html += `<button class="${i === pagination.page ? 'active' : ''}" onclick="App.paginationCallback(${i})">${i}</button>`;
            } else if (Math.abs(i - pagination.page) === 3) {
                html += '<button disabled>...</button>';
            }
        }
        
        html += '<button ' + (pagination.page >= pagination.pages ? 'disabled' : '') + ' onclick="' + `App.paginationCallback(${pagination.page + 1})` + '">→</button>';
        
        container.innerHTML = html;
        this.paginationCallback = callback;
    },
    
    // Export CSV
    exportCsv() {
        const start = document.getElementById('historyStart')?.value || '';
        const end = document.getElementById('historyEnd')?.value || '';
        
        let url = 'api/export.php?type=sensors';
        if (start) url += `&start=${start}`;
        if (end) url += `&end=${end}`;
        
        window.location.href = url;
    },
    
    // Open lightbox
    openLightbox(src, caption = '') {
        document.getElementById('lightboxImg').src = src;
        document.getElementById('lightboxCaption').textContent = caption;
        document.getElementById('lightbox').classList.add('active');
    },
    
    // Close lightbox
    closeLightbox() {
        document.getElementById('lightbox').classList.remove('active');
    },
    
    // Play video
    playVideo(src, title = '') {
        const video = document.getElementById('videoPlayer');
        video.src = src;
        video.play();
        document.getElementById('videoInfo').textContent = title;
        document.getElementById('videoModal').classList.add('active');
    },
    
    // Close video modal
    closeVideoModal() {
        const video = document.getElementById('videoPlayer');
        video.pause();
        video.src = '';
        document.getElementById('videoModal').classList.remove('active');
    },
    
    // Check sync status
    async checkSyncStatus() {
        try {
            const response = await fetch('api/current_data.php');
            const result = await response.json();
            
            const statusEl = document.getElementById('syncStatus');
            
            if (result.success && result.data.last_sync) {
                statusEl.classList.add('connected');
                statusEl.classList.remove('error');
                statusEl.querySelector('.status-text').textContent = 
                    `Last sync: ${this.formatTime(result.data.last_sync)}`;
            } else {
                statusEl.classList.remove('connected');
                statusEl.querySelector('.status-text').textContent = 'No sync data';
            }
        } catch (error) {
            const statusEl = document.getElementById('syncStatus');
            statusEl.classList.add('error');
            statusEl.querySelector('.status-text').textContent = 'Connection error';
        }
    },
    
    // Start auto refresh
    startAutoRefresh() {
        if (this.refreshInterval) clearInterval(this.refreshInterval);
        
        this.refreshInterval = setInterval(() => {
            if (this.currentPage === 'dashboard') {
                this.loadDashboard();
            }
            this.checkSyncStatus();
        }, 30000);
    },
    
    // Update last update time
    updateLastUpdate() {
        document.getElementById('lastUpdate').textContent = 
            `Updated: ${this.formatTime(new Date())}`;
    },
    
    // Show loading
    showLoading() {
        document.getElementById('loadingOverlay').classList.add('active');
    },
    
    // Hide loading
    hideLoading() {
        document.getElementById('loadingOverlay').classList.remove('active');
    },
    
    // Show error
    showError(message) {
        console.error(message);
        // Could show a toast notification here
    },
    
    // Utility: Capitalize
    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    },
    
    // Utility: Format date
    formatDate(dateStr) {
        if (!dateStr) return '--';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    // Utility: Format time
    formatTime(dateStr) {
        if (!dateStr) return '--';
        const date = new Date(dateStr);
        return date.toLocaleTimeString('en-GB', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }
};

// Export for global access
window.App = App;
