<?php
/**
 * API Endpoint: Get Time-lapse Data
 */

require_once __DIR__ . '/../../config/config.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');

try {
    $db = getDatabase();
    
    $projectId = getParam('project_id');
    $type = getParam('type', 'videos'); // videos or images
    $page = max(1, (int)getParam('page', 1));
    $limit = min((int)getParam('limit', ITEMS_PER_PAGE), MAX_ITEMS_PER_PAGE);
    $offset = ($page - 1) * $limit;
    
    if ($type === 'videos') {
        // Get videos
        $where = "1=1";
        $params = [];
        
        if ($projectId) {
            $where .= " AND v.project_id = :project_id";
            $params[':project_id'] = $projectId;
        }
        
        $countStmt = $db->prepare("SELECT COUNT(*) as total FROM timelapse_videos v WHERE {$where}");
        $countStmt->execute($params);
        $total = $countStmt->fetch()['total'];
        
        $sql = "
            SELECT 
                v.*,
                p.name as project_name
            FROM timelapse_videos v
            LEFT JOIN projects p ON v.project_id = p.id
            WHERE {$where}
            ORDER BY v.created_at DESC
            LIMIT {$limit} OFFSET {$offset}
        ";
        
        $stmt = $db->prepare($sql);
        $stmt->execute($params);
        $items = $stmt->fetchAll();
        
        // Format file sizes
        foreach ($items as &$item) {
            $item['file_size_formatted'] = formatBytes((int)$item['file_size']);
        }
        
    } else {
        // Get images
        $where = "1=1";
        $params = [];
        
        if ($projectId) {
            $where .= " AND i.project_id = :project_id";
            $params[':project_id'] = $projectId;
        }
        
        $countStmt = $db->prepare("SELECT COUNT(*) as total FROM timelapse_images i WHERE {$where}");
        $countStmt->execute($params);
        $total = $countStmt->fetch()['total'];
        
        $sql = "
            SELECT 
                i.*,
                p.name as project_name
            FROM timelapse_images i
            LEFT JOIN projects p ON i.project_id = p.id
            WHERE {$where}
            ORDER BY i.captured_at DESC
            LIMIT {$limit} OFFSET {$offset}
        ";
        
        $stmt = $db->prepare($sql);
        $stmt->execute($params);
        $items = $stmt->fetchAll();
    }
    
    jsonResponse([
        'success' => true,
        'type' => $type,
        'data' => $items,
        'pagination' => [
            'page' => $page,
            'limit' => $limit,
            'total' => (int)$total,
            'pages' => ceil($total / $limit)
        ]
    ]);
    
} catch (Exception $e) {
    errorResponse('Failed to fetch timelapse data: ' . $e->getMessage(), 500);
}
