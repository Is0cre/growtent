<?php
/**
 * Grow Tent Monitor - Remote Dashboard
 * Main entry point for the LAMP web application
 */

require_once __DIR__ . '/../config/config.php';

// Optional: Check authentication
checkAuth();

// Get current page
$page = $_GET['page'] ?? 'dashboard';
$validPages = ['dashboard', 'history', 'analysis', 'diary', 'timelapse', 'projects'];
if (!in_array($page, $validPages)) {
    $page = 'dashboard';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grow Tent Monitor</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌱</text></svg>">
    <link rel="stylesheet" href="assets/css/styles.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
</head>
<body>
    <!-- Sidebar Navigation -->
    <nav class="sidebar">
        <div class="sidebar-header">
            <span class="logo">🌱</span>
            <h1>Grow Tent</h1>
        </div>
        <ul class="nav-menu">
            <li><a href="?page=dashboard" class="nav-link <?= $page === 'dashboard' ? 'active' : '' ?>" data-page="dashboard">
                <span class="icon">📊</span> Dashboard
            </a></li>
            <li><a href="?page=history" class="nav-link <?= $page === 'history' ? 'active' : '' ?>" data-page="history">
                <span class="icon">📈</span> History
            </a></li>
            <li><a href="?page=analysis" class="nav-link <?= $page === 'analysis' ? 'active' : '' ?>" data-page="analysis">
                <span class="icon">🤖</span> AI Analysis
            </a></li>
            <li><a href="?page=diary" class="nav-link <?= $page === 'diary' ? 'active' : '' ?>" data-page="diary">
                <span class="icon">📔</span> Grow Diary
            </a></li>
            <li><a href="?page=timelapse" class="nav-link <?= $page === 'timelapse' ? 'active' : '' ?>" data-page="timelapse">
                <span class="icon">🎬</span> Time-lapse
            </a></li>
            <li><a href="?page=projects" class="nav-link <?= $page === 'projects' ? 'active' : '' ?>" data-page="projects">
                <span class="icon">📁</span> Projects
            </a></li>
        </ul>
        <div class="sidebar-footer">
            <div class="sync-status" id="syncStatus">
                <span class="status-dot"></span>
                <span class="status-text">Checking...</span>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="main-content">
        <header class="page-header">
            <button class="menu-toggle" id="menuToggle">☰</button>
            <h2 id="pageTitle"><?= ucfirst($page) ?></h2>
            <div class="header-actions">
                <span class="last-update" id="lastUpdate">--</span>
                <button class="btn-refresh" id="refreshBtn" title="Refresh">🔄</button>
            </div>
        </header>

        <!-- Dashboard Page -->
        <div class="page-content <?= $page === 'dashboard' ? 'active' : '' ?>" id="page-dashboard">
            <!-- Project Info Bar -->
            <div class="project-bar" id="projectBar">
                <div class="project-info">
                    <h3 id="projectName">Loading...</h3>
                    <span class="project-meta" id="projectMeta"></span>
                </div>
                <div class="project-status">
                    <span class="status-badge" id="projectStatus">--</span>
                </div>
            </div>

            <!-- Sensor Gauges -->
            <div class="sensor-grid">
                <div class="sensor-card temperature">
                    <div class="sensor-icon">🌡️</div>
                    <div class="sensor-value" id="tempValue">--</div>
                    <div class="sensor-unit">°C</div>
                    <div class="sensor-label">Temperature</div>
                    <canvas id="tempGauge" class="gauge-canvas"></canvas>
                </div>
                <div class="sensor-card humidity">
                    <div class="sensor-icon">💧</div>
                    <div class="sensor-value" id="humidityValue">--</div>
                    <div class="sensor-unit">%</div>
                    <div class="sensor-label">Humidity</div>
                    <canvas id="humidityGauge" class="gauge-canvas"></canvas>
                </div>
                <div class="sensor-card pressure">
                    <div class="sensor-icon">🔽</div>
                    <div class="sensor-value" id="pressureValue">--</div>
                    <div class="sensor-unit">hPa</div>
                    <div class="sensor-label">Pressure</div>
                    <canvas id="pressureGauge" class="gauge-canvas"></canvas>
                </div>
                <div class="sensor-card gas">
                    <div class="sensor-icon">💨</div>
                    <div class="sensor-value" id="gasValue">--</div>
                    <div class="sensor-unit">kΩ</div>
                    <div class="sensor-label">Air Quality</div>
                    <div class="air-quality-badge" id="airQualityBadge">--</div>
                </div>
            </div>

            <!-- Latest Photo & Stats -->
            <div class="dashboard-grid">
                <div class="card latest-photo-card">
                    <h3>📸 Latest Photo</h3>
                    <div class="photo-container">
                        <img id="latestPhoto" src="" alt="Latest grow photo" class="latest-photo">
                        <div class="photo-overlay" id="photoOverlay">
                            <span id="photoTime">--</span>
                        </div>
                    </div>
                </div>
                <div class="card stats-card">
                    <h3>📊 Quick Stats</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-value" id="statPhotos">--</span>
                            <span class="stat-label">Total Photos</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="statDays">--</span>
                            <span class="stat-label">Days Running</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="statHealth">--</span>
                            <span class="stat-label">Health Score</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="statAirQuality">--</span>
                            <span class="stat-label">Air Quality</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Mini Charts -->
            <div class="mini-charts">
                <div class="card">
                    <h4>Temperature (24h)</h4>
                    <canvas id="miniTempChart"></canvas>
                </div>
                <div class="card">
                    <h4>Humidity (24h)</h4>
                    <canvas id="miniHumidityChart"></canvas>
                </div>
            </div>
        </div>

        <!-- History Page -->
        <div class="page-content <?= $page === 'history' ? 'active' : '' ?>" id="page-history">
            <div class="history-controls">
                <div class="date-range">
                    <label>From: <input type="date" id="historyStart"></label>
                    <label>To: <input type="date" id="historyEnd"></label>
                    <button class="btn" id="loadHistoryBtn">Load Data</button>
                </div>
                <div class="quick-ranges">
                    <button class="btn btn-sm" data-hours="6">6h</button>
                    <button class="btn btn-sm" data-hours="24">24h</button>
                    <button class="btn btn-sm" data-hours="168">7d</button>
                    <button class="btn btn-sm" data-hours="720">30d</button>
                </div>
                <button class="btn btn-export" id="exportCsvBtn">📥 Export CSV</button>
            </div>
            <div class="chart-container card">
                <h3>Temperature & Humidity</h3>
                <canvas id="tempHumidityChart"></canvas>
            </div>
            <div class="chart-container card">
                <h3>Pressure</h3>
                <canvas id="pressureChart"></canvas>
            </div>
            <div class="chart-container card">
                <h3>Air Quality (Gas Resistance)</h3>
                <canvas id="gasChart"></canvas>
            </div>
        </div>

        <!-- AI Analysis Page -->
        <div class="page-content <?= $page === 'analysis' ? 'active' : '' ?>" id="page-analysis">
            <div class="analysis-header">
                <div class="card health-trend-card">
                    <h3>🏥 Health Score Trend</h3>
                    <canvas id="healthTrendChart"></canvas>
                </div>
            </div>
            <div class="analysis-latest card" id="latestAnalysis">
                <h3>📋 Latest Analysis</h3>
                <div class="analysis-content">
                    <div class="analysis-photo">
                        <img id="analysisPhoto" src="" alt="Analysis photo">
                    </div>
                    <div class="analysis-details">
                        <div class="health-score-large">
                            <span class="score" id="analysisScore">--</span>
                            <span class="label">Health Score</span>
                        </div>
                        <div class="growth-stage" id="growthStage">--</div>
                        <div class="analysis-text" id="analysisText">Loading...</div>
                        <div class="recommendations" id="recommendations"></div>
                    </div>
                </div>
                <div class="analysis-meta">
                    <span id="analysisDate">--</span>
                    <span id="analysisModel">--</span>
                </div>
            </div>
            <div class="analysis-list card">
                <h3>📚 Analysis History</h3>
                <div class="analysis-items" id="analysisItems"></div>
                <div class="pagination" id="analysisPagination"></div>
            </div>
        </div>

        <!-- Diary Page -->
        <div class="page-content <?= $page === 'diary' ? 'active' : '' ?>" id="page-diary">
            <div class="diary-filters">
                <select id="diaryProjectFilter">
                    <option value="">All Projects</option>
                </select>
                <select id="diaryTypeFilter">
                    <option value="">All Types</option>
                    <option value="note">Notes</option>
                    <option value="photo">Photos</option>
                    <option value="milestone">Milestones</option>
                </select>
            </div>
            <div class="diary-timeline" id="diaryTimeline"></div>
            <div class="pagination" id="diaryPagination"></div>
        </div>

        <!-- Time-lapse Page -->
        <div class="page-content <?= $page === 'timelapse' ? 'active' : '' ?>" id="page-timelapse">
            <div class="timelapse-tabs">
                <button class="tab-btn active" data-tab="videos">🎬 Videos</button>
                <button class="tab-btn" data-tab="images">📷 Images</button>
            </div>
            <div class="timelapse-content">
                <div class="tab-content active" id="tab-videos">
                    <div class="video-grid" id="videoGrid"></div>
                </div>
                <div class="tab-content" id="tab-images">
                    <div class="image-gallery" id="imageGallery"></div>
                </div>
            </div>
            <div class="pagination" id="timelapsePagination"></div>
        </div>

        <!-- Projects Page -->
        <div class="page-content <?= $page === 'projects' ? 'active' : '' ?>" id="page-projects">
            <div class="projects-filters">
                <button class="btn <?= !isset($_GET['status']) ? 'active' : '' ?>" data-status="">All</button>
                <button class="btn <?= ($_GET['status'] ?? '') === 'active' ? 'active' : '' ?>" data-status="active">Active</button>
                <button class="btn <?= ($_GET['status'] ?? '') === 'completed' ? 'active' : '' ?>" data-status="completed">Completed</button>
            </div>
            <div class="projects-grid" id="projectsGrid"></div>
            <div class="pagination" id="projectsPagination"></div>
        </div>
    </main>

    <!-- Lightbox Modal -->
    <div class="lightbox" id="lightbox">
        <button class="lightbox-close" id="lightboxClose">×</button>
        <img id="lightboxImg" src="" alt="">
        <div class="lightbox-caption" id="lightboxCaption"></div>
    </div>

    <!-- Video Player Modal -->
    <div class="video-modal" id="videoModal">
        <div class="video-modal-content">
            <button class="modal-close" id="videoModalClose">×</button>
            <video id="videoPlayer" controls></video>
            <div class="video-info" id="videoInfo"></div>
        </div>
    </div>

    <!-- Loading Overlay -->
    <div class="loading-overlay" id="loadingOverlay">
        <div class="spinner"></div>
    </div>

    <script src="assets/js/app.js"></script>
    <script>
        // Initialize with current page
        document.addEventListener('DOMContentLoaded', () => {
            App.init('<?= $page ?>');
        });
    </script>
</body>
</html>
