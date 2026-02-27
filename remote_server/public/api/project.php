<?php
/**
 * API Endpoint: Get Single Project Details
 */

require_once __DIR__ . '/../../config/config.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');

try {
    $db = getDatabase();
    
    $id = getParam('id');
    
    if (!$id) {
        errorResponse('Project ID is required', 400);
    }
    
    // Get project details
    $stmt = $db->prepare("
        SELECT 
            p.*,
            DATEDIFF(COALESCE(p.end_date, NOW()), p.start_date) as days_running
        FROM projects p
        WHERE p.id = :id
    ");
    $stmt->execute([':id' => $id]);
    $project = $stmt->fetch();
    
    if (!$project) {
        errorResponse('Project not found', 404);
    }
    
    // Get statistics
    $stats = [];
    
    // Sensor readings count and averages
    $stmt = $db->prepare("
        SELECT 
            COUNT(*) as total_readings,
            AVG(temperature) as avg_temp,
            MIN(temperature) as min_temp,
            MAX(temperature) as max_temp,
            AVG(humidity) as avg_humidity,
            MIN(humidity) as min_humidity,
            MAX(humidity) as max_humidity
        FROM sensor_logs 
        WHERE project_id = :id
    ");
    $stmt->execute([':id' => $id]);
    $stats['sensors'] = $stmt->fetch();
    
    // Diary entries
    $stmt = $db->prepare("SELECT COUNT(*) as count FROM diary_entries WHERE project_id = :id");
    $stmt->execute([':id' => $id]);
    $stats['diary_entries'] = $stmt->fetch()['count'];
    
    // Time-lapse images
    $stmt = $db->prepare("SELECT COUNT(*) as count FROM timelapse_images WHERE project_id = :id");
    $stmt->execute([':id' => $id]);
    $stats['timelapse_images'] = $stmt->fetch()['count'];
    
    // Time-lapse videos
    $stmt = $db->prepare("SELECT COUNT(*) as count FROM timelapse_videos WHERE project_id = :id");
    $stmt->execute([':id' => $id]);
    $stats['timelapse_videos'] = $stmt->fetch()['count'];
    
    // AI analyses
    $stmt = $db->prepare("
        SELECT 
            COUNT(*) as total,
            AVG(health_score) as avg_score,
            MAX(health_score) as best_score,
            MIN(health_score) as worst_score
        FROM ai_analysis 
        WHERE project_id = :id
    ");
    $stmt->execute([':id' => $id]);
    $stats['ai_analysis'] = $stmt->fetch();
    
    // Latest photo
    $stmt = $db->prepare("
        SELECT image_path, captured_at 
        FROM timelapse_images 
        WHERE project_id = :id 
        ORDER BY captured_at DESC 
        LIMIT 1
    ");
    $stmt->execute([':id' => $id]);
    $stats['latest_photo'] = $stmt->fetch();
    
    jsonResponse([
        'success' => true,
        'data' => [
            'project' => $project,
            'statistics' => $stats
        ]
    ]);
    
} catch (Exception $e) {
    errorResponse('Failed to fetch project: ' . $e->getMessage(), 500);
}
