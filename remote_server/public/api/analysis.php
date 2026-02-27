<?php
/**
 * API Endpoint: Get AI Analysis Reports
 */

require_once __DIR__ . '/../../config/config.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');

try {
    $db = getDatabase();
    
    $projectId = getParam('project_id');
    $id = getParam('id'); // Get single analysis
    $page = max(1, (int)getParam('page', 1));
    $limit = min((int)getParam('limit', ITEMS_PER_PAGE), MAX_ITEMS_PER_PAGE);
    $offset = ($page - 1) * $limit;
    
    // Single analysis
    if ($id) {
        $stmt = $db->prepare("
            SELECT 
                a.*,
                p.name as project_name
            FROM ai_analysis a
            LEFT JOIN projects p ON a.project_id = p.id
            WHERE a.id = :id
        ");
        $stmt->execute([':id' => $id]);
        $analysis = $stmt->fetch();
        
        if (!$analysis) {
            errorResponse('Analysis not found', 404);
        }
        
        // Parse JSON fields
        $analysis['recommendations'] = json_decode($analysis['recommendations'], true) ?: [];
        $analysis['issues_detected'] = json_decode($analysis['issues_detected'], true) ?: [];
        
        jsonResponse([
            'success' => true,
            'data' => $analysis
        ]);
        return;
    }
    
    // List analyses
    $where = "1=1";
    $params = [];
    
    if ($projectId) {
        $where .= " AND a.project_id = :project_id";
        $params[':project_id'] = $projectId;
    }
    
    // Get total count
    $countStmt = $db->prepare("SELECT COUNT(*) as total FROM ai_analysis a WHERE {$where}");
    $countStmt->execute($params);
    $total = $countStmt->fetch()['total'];
    
    // Get analyses
    $sql = "
        SELECT 
            a.id,
            a.project_id,
            a.photo_path,
            a.health_score,
            a.growth_stage,
            a.model_used,
            a.created_at,
            p.name as project_name
        FROM ai_analysis a
        LEFT JOIN projects p ON a.project_id = p.id
        WHERE {$where}
        ORDER BY a.created_at DESC
        LIMIT {$limit} OFFSET {$offset}
    ";
    
    $stmt = $db->prepare($sql);
    $stmt->execute($params);
    $analyses = $stmt->fetchAll();
    
    // Get health score trend
    $trendSql = "
        SELECT 
            DATE(created_at) as date,
            AVG(health_score) as avg_score,
            COUNT(*) as count
        FROM ai_analysis
        WHERE project_id IS NOT NULL
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 30
    ";
    $trend = $db->query($trendSql)->fetchAll();
    
    jsonResponse([
        'success' => true,
        'data' => $analyses,
        'trend' => array_reverse($trend),
        'pagination' => [
            'page' => $page,
            'limit' => $limit,
            'total' => (int)$total,
            'pages' => ceil($total / $limit)
        ]
    ]);
    
} catch (Exception $e) {
    errorResponse('Failed to fetch analyses: ' . $e->getMessage(), 500);
}
