<?php
/**
 * API Endpoint: Get Sensor History
 * Returns historical sensor data for charts
 */

require_once __DIR__ . '/../../config/config.php';

header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET');

try {
    $db = getDatabase();
    
    // Get parameters
    $projectId = getParam('project_id');
    $start = getParam('start');
    $end = getParam('end');
    $hours = (int)getParam('hours', 24);
    $limit = min((int)getParam('limit', 500), MAX_ITEMS_PER_PAGE);
    $interval = getParam('interval', 'auto'); // auto, minute, hour, day
    
    // Build date range
    if ($start && $end) {
        $startDate = $start;
        $endDate = $end;
    } else {
        $endDate = date('Y-m-d H:i:s');
        $startDate = date('Y-m-d H:i:s', strtotime("-{$hours} hours"));
    }
    
    // Determine aggregation based on time range
    $timeDiff = strtotime($endDate) - strtotime($startDate);
    if ($interval === 'auto') {
        if ($timeDiff <= 3600) { // 1 hour
            $interval = 'minute';
        } elseif ($timeDiff <= 86400) { // 1 day
            $interval = '5minute';
        } elseif ($timeDiff <= 604800) { // 1 week
            $interval = 'hour';
        } else {
            $interval = 'day';
        }
    }
    
    // Build query based on interval
    $groupBy = match($interval) {
        'minute' => "DATE_FORMAT(timestamp, '%Y-%m-%d %H:%i:00')",
        '5minute' => "DATE_FORMAT(timestamp, '%Y-%m-%d %H:') + FLOOR(MINUTE(timestamp)/5)*5",
        'hour' => "DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00')",
        'day' => "DATE(timestamp)",
        default => "DATE_FORMAT(timestamp, '%Y-%m-%d %H:%i:00')"
    };
    
    $sql = "
        SELECT 
            {$groupBy} as time_bucket,
            AVG(temperature) as temperature,
            AVG(humidity) as humidity,
            AVG(pressure) as pressure,
            AVG(gas_resistance) as gas_resistance,
            MIN(temperature) as temp_min,
            MAX(temperature) as temp_max,
            MIN(humidity) as humidity_min,
            MAX(humidity) as humidity_max
        FROM sensor_logs
        WHERE timestamp BETWEEN :start AND :end
    ";
    
    $params = [':start' => $startDate, ':end' => $endDate];
    
    if ($projectId) {
        $sql .= " AND project_id = :project_id";
        $params[':project_id'] = $projectId;
    }
    
    $sql .= " GROUP BY time_bucket ORDER BY time_bucket ASC LIMIT {$limit}";
    
    $stmt = $db->prepare($sql);
    $stmt->execute($params);
    $data = $stmt->fetchAll();
    
    // Format data for Chart.js
    $formatted = [
        'labels' => [],
        'temperature' => [],
        'humidity' => [],
        'pressure' => [],
        'gas_resistance' => [],
        'temp_range' => [],
        'humidity_range' => []
    ];
    
    foreach ($data as $row) {
        $formatted['labels'][] = $row['time_bucket'];
        $formatted['temperature'][] = round((float)$row['temperature'], 1);
        $formatted['humidity'][] = round((float)$row['humidity'], 1);
        $formatted['pressure'][] = round((float)$row['pressure'], 1);
        $formatted['gas_resistance'][] = round((float)$row['gas_resistance'], 0);
        $formatted['temp_range'][] = [
            round((float)$row['temp_min'], 1),
            round((float)$row['temp_max'], 1)
        ];
        $formatted['humidity_range'][] = [
            round((float)$row['humidity_min'], 1),
            round((float)$row['humidity_max'], 1)
        ];
    }
    
    jsonResponse([
        'success' => true,
        'data' => $formatted,
        'meta' => [
            'start' => $startDate,
            'end' => $endDate,
            'interval' => $interval,
            'points' => count($data)
        ]
    ]);
    
} catch (Exception $e) {
    errorResponse('Failed to fetch sensor history: ' . $e->getMessage(), 500);
}
