<?php
/**
 * API Endpoint: Get Diary Entries
 */

require_once __DIR__ . '/../../config/config.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');

try {
    $db = getDatabase();
    
    $projectId = getParam('project_id');
    $entryType = getParam('type'); // note, photo, milestone, etc.
    $page = max(1, (int)getParam('page', 1));
    $limit = min((int)getParam('limit', ITEMS_PER_PAGE), MAX_ITEMS_PER_PAGE);
    $offset = ($page - 1) * $limit;
    
    // Build query
    $where = "1=1";
    $params = [];
    
    if ($projectId) {
        $where .= " AND project_id = :project_id";
        $params[':project_id'] = $projectId;
    }
    
    if ($entryType) {
        $where .= " AND entry_type = :entry_type";
        $params[':entry_type'] = $entryType;
    }
    
    // Get total count
    $countStmt = $db->prepare("SELECT COUNT(*) as total FROM diary_entries WHERE {$where}");
    $countStmt->execute($params);
    $total = $countStmt->fetch()['total'];
    
    // Get entries with project info
    $sql = "
        SELECT 
            d.*,
            p.name as project_name
        FROM diary_entries d
        LEFT JOIN projects p ON d.project_id = p.id
        WHERE {$where}
        ORDER BY d.created_at DESC
        LIMIT {$limit} OFFSET {$offset}
    ";
    
    $stmt = $db->prepare($sql);
    $stmt->execute($params);
    $entries = $stmt->fetchAll();
    
    // Parse tags JSON if present
    foreach ($entries as &$entry) {
        if ($entry['tags']) {
            $entry['tags'] = json_decode($entry['tags'], true) ?: [];
        } else {
            $entry['tags'] = [];
        }
    }
    
    jsonResponse([
        'success' => true,
        'data' => $entries,
        'pagination' => [
            'page' => $page,
            'limit' => $limit,
            'total' => (int)$total,
            'pages' => ceil($total / $limit)
        ]
    ]);
    
} catch (Exception $e) {
    errorResponse('Failed to fetch diary entries: ' . $e->getMessage(), 500);
}
