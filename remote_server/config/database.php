<?php
/**
 * Database Configuration
 * 
 * Copy this file to database.local.php and update with your credentials
 * for local development.
 */

return [
    'host' => getenv('DB_HOST') ?: 'localhost',
    'port' => getenv('DB_PORT') ?: 3306,
    'database' => getenv('DB_NAME') ?: 'grow_tent',
    'username' => getenv('DB_USER') ?: 'grow_tent_user',
    'password' => getenv('DB_PASS') ?: 'change_this_password',
    'charset' => 'utf8mb4',
    'collation' => 'utf8mb4_unicode_ci',
    
    // Connection options
    'options' => [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
        PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci"
    ],
    
    // SQLite source (for imports)
    'sqlite_source' => '/tmp/grow_tent.db'
];
