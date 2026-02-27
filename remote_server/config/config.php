<?php
/**
 * General Application Configuration
 */

// Error reporting (disable in production)
if (getenv('APP_ENV') === 'development') {
    error_reporting(E_ALL);
    ini_set('display_errors', 1);
} else {
    error_reporting(0);
    ini_set('display_errors', 0);
}

// Timezone
date_default_timezone_set('Europe/Malta');

// Application paths
define('BASE_PATH', dirname(__DIR__));
define('PUBLIC_PATH', BASE_PATH . '/public');
define('DATA_PATH', PUBLIC_PATH . '/data');
define('PHOTOS_PATH', DATA_PATH . '/photos');
define('TIMELAPSE_PATH', DATA_PATH . '/timelapse');
define('DIARY_PATH', DATA_PATH . '/diary');

// URLs (update for your domain)
define('BASE_URL', getenv('BASE_URL') ?: 'http://localhost');
define('DATA_URL', BASE_URL . '/data');

// API settings
define('API_VERSION', '1.0');
define('ITEMS_PER_PAGE', 50);
define('MAX_ITEMS_PER_PAGE', 500);

// Auto-refresh settings (in seconds)
define('DASHBOARD_REFRESH_INTERVAL', 30);
define('SENSOR_HISTORY_HOURS', 24);

// Security
define('REQUIRE_AUTH', false);  // Set to true to enable HTTP Basic Auth
define('AUTH_REALM', 'Grow Tent Monitor');

// Rsync settings
define('PI_USER', 'matthias');
define('PI_HOST', 'grow-tent');
define('PI_DATA_PATH', '/home/matthias/grow_tent_automation/data');

/**
 * Get database connection
 */
function getDatabase(): PDO {
    static $pdo = null;
    
    if ($pdo === null) {
        // Load local config if exists, otherwise use default
        $configFile = __DIR__ . '/database.local.php';
        if (!file_exists($configFile)) {
            $configFile = __DIR__ . '/database.php';
        }
        $config = require $configFile;
        
        $dsn = sprintf(
            'mysql:host=%s;port=%d;dbname=%s;charset=%s',
            $config['host'],
            $config['port'],
            $config['database'],
            $config['charset']
        );
        
        try {
            $pdo = new PDO($dsn, $config['username'], $config['password'], $config['options']);
        } catch (PDOException $e) {
            http_response_code(500);
            die(json_encode(['error' => 'Database connection failed', 'message' => $e->getMessage()]));
        }
    }
    
    return $pdo;
}

/**
 * Send JSON response
 */
function jsonResponse($data, int $statusCode = 200): void {
    http_response_code($statusCode);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-cache, no-store, must-revalidate');
    echo json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * Handle errors as JSON
 */
function errorResponse(string $message, int $statusCode = 400): void {
    jsonResponse(['error' => true, 'message' => $message], $statusCode);
}

/**
 * Get query parameter with default
 */
function getParam(string $name, $default = null) {
    return $_GET[$name] ?? $_POST[$name] ?? $default;
}

/**
 * Sanitize path to prevent directory traversal
 */
function sanitizePath(string $path): string {
    return preg_replace('/\.\.\//', '', $path);
}

/**
 * Format bytes to human readable
 */
function formatBytes(int $bytes, int $precision = 2): string {
    $units = ['B', 'KB', 'MB', 'GB', 'TB'];
    $bytes = max($bytes, 0);
    $pow = floor(($bytes ? log($bytes) : 0) / log(1024));
    $pow = min($pow, count($units) - 1);
    return round($bytes / pow(1024, $pow), $precision) . ' ' . $units[$pow];
}

/**
 * Check for basic auth if enabled
 */
function checkAuth(): void {
    if (!REQUIRE_AUTH) return;
    
    $htpasswd = BASE_PATH . '/.htpasswd';
    if (!file_exists($htpasswd)) return;
    
    if (!isset($_SERVER['PHP_AUTH_USER'])) {
        header('WWW-Authenticate: Basic realm="' . AUTH_REALM . '"');
        http_response_code(401);
        die('Authentication required');
    }
    
    // Simple htpasswd check (for production, use proper Apache auth)
    $users = file($htpasswd, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($users as $user) {
        list($username, $hash) = explode(':', $user, 2);
        if ($username === $_SERVER['PHP_AUTH_USER']) {
            if (password_verify($_SERVER['PHP_AUTH_PW'], $hash)) {
                return;
            }
        }
    }
    
    header('WWW-Authenticate: Basic realm="' . AUTH_REALM . '"');
    http_response_code(401);
    die('Invalid credentials');
}
