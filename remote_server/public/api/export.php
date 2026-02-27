<?php
/**
 * API Endpoint: Export Data to CSV
 */

require_once __DIR__ . '/../../config/config.php';

try {
    $db = getDatabase();
    
    $type = getParam('type', 'sensors'); // sensors, diary, analysis
    $projectId = getParam('project_id');
    $start = getParam('start');
    $end = getParam('end');
    
    // Set headers for CSV download
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="grow_tent_' . $type . '_' . date('Y-m-d') . '.csv"');
    header('Cache-Control: no-cache, no-store, must-revalidate');
    
    $output = fopen('php://output', 'w');
    
    // Add UTF-8 BOM for Excel compatibility
    fprintf($output, chr(0xEF).chr(0xBB).chr(0xBF));
    
    switch ($type) {
        case 'sensors':
            // Headers
            fputcsv($output, ['Timestamp', 'Temperature (°C)', 'Humidity (%)', 'Pressure (hPa)', 'Gas Resistance (Ω)', 'Air Quality', 'Project ID']);
            
            $where = "1=1";
            $params = [];
            
            if ($projectId) {
                $where .= " AND project_id = :project_id";
                $params[':project_id'] = $projectId;
            }
            if ($start) {
                $where .= " AND timestamp >= :start";
                $params[':start'] = $start;
            }
            if ($end) {
                $where .= " AND timestamp <= :end";
                $params[':end'] = $end;
            }
            
            $stmt = $db->prepare("
                SELECT timestamp, temperature, humidity, pressure, gas_resistance, air_quality, project_id
                FROM sensor_logs
                WHERE {$where}
                ORDER BY timestamp ASC
            ");
            $stmt->execute($params);
            
            while ($row = $stmt->fetch()) {
                fputcsv($output, [
                    $row['timestamp'],
                    $row['temperature'],
                    $row['humidity'],
                    $row['pressure'],
                    $row['gas_resistance'],
                    $row['air_quality'],
                    $row['project_id']
                ]);
            }
            break;
            
        case 'diary':
            fputcsv($output, ['Date', 'Type', 'Title', 'Content', 'Photo', 'Tags', 'Project ID']);
            
            $where = "1=1";
            $params = [];
            
            if ($projectId) {
                $where .= " AND project_id = :project_id";
                $params[':project_id'] = $projectId;
            }
            
            $stmt = $db->prepare("
                SELECT created_at, entry_type, title, content, photo_path, tags, project_id
                FROM diary_entries
                WHERE {$where}
                ORDER BY created_at ASC
            ");
            $stmt->execute($params);
            
            while ($row = $stmt->fetch()) {
                fputcsv($output, [
                    $row['created_at'],
                    $row['entry_type'],
                    $row['title'],
                    $row['content'],
                    $row['photo_path'],
                    $row['tags'],
                    $row['project_id']
                ]);
            }
            break;
            
        case 'analysis':
            fputcsv($output, ['Date', 'Health Score', 'Growth Stage', 'Photo', 'Analysis', 'Recommendations', 'Model', 'Project ID']);
            
            $where = "1=1";
            $params = [];
            
            if ($projectId) {
                $where .= " AND project_id = :project_id";
                $params[':project_id'] = $projectId;
            }
            
            $stmt = $db->prepare("
                SELECT created_at, health_score, growth_stage, photo_path, analysis_text, recommendations, model_used, project_id
                FROM ai_analysis
                WHERE {$where}
                ORDER BY created_at ASC
            ");
            $stmt->execute($params);
            
            while ($row = $stmt->fetch()) {
                fputcsv($output, [
                    $row['created_at'],
                    $row['health_score'],
                    $row['growth_stage'],
                    $row['photo_path'],
                    $row['analysis_text'],
                    $row['recommendations'],
                    $row['model_used'],
                    $row['project_id']
                ]);
            }
            break;
            
        default:
            fclose($output);
            errorResponse('Invalid export type', 400);
    }
    
    fclose($output);
    exit;
    
} catch (Exception $e) {
    errorResponse('Export failed: ' . $e->getMessage(), 500);
}
