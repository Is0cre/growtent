<?php
/**
 * API Endpoint: Get Current Sensor Data
 * Returns the latest sensor readings and system status
 */

require_once __DIR__ . '/../../config/config.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');

try {
    $db = getDatabase();
    
    // Get active project
    $project = $db->query("
        SELECT id, name, plant_type, strain, start_date, status,
               timelapse_enabled, timelapse_interval,
               DATEDIFF(NOW(), start_date) as days_running
        FROM projects 
        WHERE status = 'active' 
        ORDER BY start_date DESC 
        LIMIT 1
    ")->fetch();
    
    // Get latest sensor reading
    $sensor = $db->query("
        SELECT temperature, humidity, pressure, gas_resistance, air_quality, timestamp
        FROM sensor_logs 
        ORDER BY timestamp DESC 
        LIMIT 1
    ")->fetch();
    
    // Get latest AI analysis
    $analysis = $db->query("
        SELECT id, health_score, growth_stage, created_at
        FROM ai_analysis 
        ORDER BY created_at DESC 
        LIMIT 1
    ")->fetch();
    
    // Get photo count
    $photoCount = $db->query("
        SELECT COUNT(*) as count FROM timelapse_images
    ")->fetch()['count'];
    
    // Get latest photo
    $latestPhoto = $db->query("
        SELECT image_path, captured_at 
        FROM timelapse_images 
        ORDER BY captured_at DESC 
        LIMIT 1
    ")->fetch();
    
    // Get last sync time
    $lastSync = $db->query("
        SELECT completed_at FROM sync_logs 
        WHERE status = 'success' 
        ORDER BY completed_at DESC 
        LIMIT 1
    ")->fetch();
    
    jsonResponse([
        'success' => true,
        'data' => [
            'project' => $project ?: null,
            'sensors' => $sensor ? [
                'temperature' => round((float)$sensor['temperature'], 1),
                'humidity' => round((float)$sensor['humidity'], 1),
                'pressure' => round((float)$sensor['pressure'], 1),
                'gas_resistance' => round((float)$sensor['gas_resistance'], 0),
                'air_quality' => $sensor['air_quality'],
                'timestamp' => $sensor['timestamp']
            ] : null,
            'latest_analysis' => $analysis,
            'stats' => [
                'total_photos' => (int)$photoCount,
                'latest_photo' => $latestPhoto ? $latestPhoto['image_path'] : null,
                'latest_photo_time' => $latestPhoto ? $latestPhoto['captured_at'] : null
            ],
            'last_sync' => $lastSync ? $lastSync['completed_at'] : null,
            'server_time' => date('Y-m-d H:i:s')
        ]
    ]);
    
} catch (Exception $e) {
    errorResponse('Failed to fetch current data: ' . $e->getMessage(), 500);
}
