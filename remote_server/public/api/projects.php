<?php
/**
 * API Endpoint: Get All Projects
 */

require_once __DIR__ . '/../../config/config.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');

try {
    $db = getDatabase();
    
    $status = getParam('status'); // active, completed, all
    $page = max(1, (int)getParam('page', 1));
    $limit = min((int)getParam('limit', ITEMS_PER_PAGE), MAX_ITEMS_PER_PAGE);
    $offset = ($page - 1) * $limit;
    
    // Build query
    $where = "1=1";
    $params = [];
    
    if ($status && $status !== 'all') {
        $where .= " AND status = :status";
        $params[':status'] = $status;
    }
    
    // Get total count
    $countStmt = $db->prepare("SELECT COUNT(*) as total FROM projects WHERE {$where}");
    $countStmt->execute($params);
    $total = $countStmt->fetch()['total'];
    
    // Get projects with stats
    $sql = "
        SELECT 
            p.*,
            DATEDIFF(COALESCE(p.end_date, NOW()), p.start_date) as days_running,
            (SELECT COUNT(*) FROM sensor_logs WHERE project_id = p.id) as sensor_readings,
            (SELECT COUNT(*) FROM diary_entries WHERE project_id = p.id) as diary_entries,
            (SELECT COUNT(*) FROM timelapse_images WHERE project_id = p.id) as timelapse_images,
            (SELECT COUNT(*) FROM ai_analysis WHERE project_id = p.id) as ai_analyses,
            (SELECT AVG(health_score) FROM ai_analysis WHERE project_id = p.id) as avg_health_score
        FROM projects p
        WHERE {$where}
        ORDER BY p.start_date DESC
        LIMIT {$limit} OFFSET {$offset}
    ";
    
    $stmt = $db->prepare($sql);
    $stmt->execute($params);
    $projects = $stmt->fetchAll();
    
    jsonResponse([
        'success' => true,
        'data' => $projects,
        'pagination' => [
            'page' => $page,
            'limit' => $limit,
            'total' => (int)$total,
            'pages' => ceil($total / $limit)
        ]
    ]);
    
} catch (Exception $e) {
    errorResponse('Failed to fetch projects: ' . $e->getMessage(), 500);
}
