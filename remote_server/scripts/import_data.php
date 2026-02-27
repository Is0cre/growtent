<?php
/**
 * Grow Tent Monitor - Data Import Script
 * Imports data from SQLite (synced from Pi) to MySQL
 *
 * Usage: php import_data.php
 */

require_once __DIR__ . '/../config/config.php';

class DataImporter {
    private PDO $mysql;
    private PDO $sqlite;
    private int $recordsImported = 0;
    private array $errors = [];
    
    public function __construct() {
        // Load database config
        $configFile = __DIR__ . '/../config/database.local.php';
        if (!file_exists($configFile)) {
            $configFile = __DIR__ . '/../config/database.php';
        }
        $config = require $configFile;
        
        // Connect to MySQL
        $this->mysql = getDatabase();
        
        // Connect to SQLite
        $sqlitePath = $config['sqlite_source'] ?? '/tmp/grow_tent.db';
        if (!file_exists($sqlitePath)) {
            throw new Exception("SQLite database not found: $sqlitePath");
        }
        
        $this->sqlite = new PDO("sqlite:$sqlitePath", null, null, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
        ]);
    }
    
    public function run(): bool {
        $startTime = microtime(true);
        
        echo "Starting data import...\n";
        
        try {
            $this->mysql->beginTransaction();
            
            // Import tables in order (respecting foreign keys)
            $this->importProjects();
            $this->importSensorLogs();
            $this->importDiaryEntries();
            $this->importAiAnalysis();
            $this->importTimelapseImages();
            $this->importTimelapseVideos();
            $this->importDeviceSettings();
            $this->importAlertSettings();
            
            $this->mysql->commit();
            
            // Log sync
            $this->logSync($startTime, 'success');
            
            echo "Import completed successfully. Records imported: {$this->recordsImported}\n";
            return true;
            
        } catch (Exception $e) {
            $this->mysql->rollBack();
            $this->errors[] = $e->getMessage();
            $this->logSync($startTime, 'error', $e->getMessage());
            
            echo "Import failed: " . $e->getMessage() . "\n";
            return false;
        }
    }
    
    private function importProjects(): void {
        echo "  Importing projects...\n";
        
        $stmt = $this->sqlite->query("
            SELECT id, name, plant_type, strain, start_date, end_date, status, notes,
                   timelapse_enabled, timelapse_interval, timelapse_only_with_lights,
                   created_at, updated_at
            FROM projects
        ");
        
        $insertStmt = $this->mysql->prepare("
            INSERT INTO projects 
                (id, name, plant_type, strain, start_date, end_date, status, notes,
                 timelapse_enabled, timelapse_interval, timelapse_only_with_lights,
                 created_at, updated_at)
            VALUES 
                (:id, :name, :plant_type, :strain, :start_date, :end_date, :status, :notes,
                 :timelapse_enabled, :timelapse_interval, :timelapse_only_with_lights,
                 :created_at, :updated_at)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                plant_type = VALUES(plant_type),
                strain = VALUES(strain),
                end_date = VALUES(end_date),
                status = VALUES(status),
                notes = VALUES(notes),
                timelapse_enabled = VALUES(timelapse_enabled),
                timelapse_interval = VALUES(timelapse_interval),
                timelapse_only_with_lights = VALUES(timelapse_only_with_lights),
                updated_at = VALUES(updated_at)
        ");
        
        $count = 0;
        while ($row = $stmt->fetch()) {
            $insertStmt->execute($row);
            $count++;
        }
        
        $this->recordsImported += $count;
        echo "    Imported $count projects\n";
    }
    
    private function importSensorLogs(): void {
        echo "  Importing sensor logs...\n";
        
        // Get last imported timestamp for incremental sync
        $lastTimestamp = $this->mysql->query("
            SELECT MAX(timestamp) as last FROM sensor_logs
        ")->fetch()['last'] ?? '1970-01-01';
        
        $stmt = $this->sqlite->prepare("
            SELECT project_id, temperature, humidity, pressure, gas_resistance, air_quality, timestamp
            FROM sensor_logs
            WHERE timestamp > :last_timestamp
            ORDER BY timestamp ASC
            LIMIT 10000
        ");
        $stmt->execute([':last_timestamp' => $lastTimestamp]);
        
        $insertStmt = $this->mysql->prepare("
            INSERT INTO sensor_logs 
                (project_id, temperature, humidity, pressure, gas_resistance, air_quality, timestamp)
            VALUES 
                (:project_id, :temperature, :humidity, :pressure, :gas_resistance, :air_quality, :timestamp)
        ");
        
        $count = 0;
        while ($row = $stmt->fetch()) {
            $insertStmt->execute($row);
            $count++;
        }
        
        $this->recordsImported += $count;
        echo "    Imported $count sensor logs\n";
    }
    
    private function importDiaryEntries(): void {
        echo "  Importing diary entries...\n";
        
        $stmt = $this->sqlite->query("
            SELECT id, project_id, entry_type, title, content, photo_path, tags, created_at
            FROM diary_entries
        ");
        
        $insertStmt = $this->mysql->prepare("
            INSERT INTO diary_entries 
                (id, project_id, entry_type, title, content, photo_path, tags, created_at)
            VALUES 
                (:id, :project_id, :entry_type, :title, :content, :photo_path, :tags, :created_at)
            ON DUPLICATE KEY UPDATE
                entry_type = VALUES(entry_type),
                title = VALUES(title),
                content = VALUES(content),
                photo_path = VALUES(photo_path),
                tags = VALUES(tags)
        ");
        
        $count = 0;
        while ($row = $stmt->fetch()) {
            $insertStmt->execute($row);
            $count++;
        }
        
        $this->recordsImported += $count;
        echo "    Imported $count diary entries\n";
    }
    
    private function importAiAnalysis(): void {
        echo "  Importing AI analyses...\n";
        
        $stmt = $this->sqlite->query("
            SELECT id, project_id, photo_path, health_score, analysis_text, 
                   recommendations, issues_detected, growth_stage, model_used, 
                   raw_response, created_at
            FROM ai_analysis
        ");
        
        $insertStmt = $this->mysql->prepare("
            INSERT INTO ai_analysis 
                (id, project_id, photo_path, health_score, analysis_text, 
                 recommendations, issues_detected, growth_stage, model_used,
                 raw_response, created_at)
            VALUES 
                (:id, :project_id, :photo_path, :health_score, :analysis_text,
                 :recommendations, :issues_detected, :growth_stage, :model_used,
                 :raw_response, :created_at)
            ON DUPLICATE KEY UPDATE
                health_score = VALUES(health_score),
                analysis_text = VALUES(analysis_text),
                recommendations = VALUES(recommendations),
                issues_detected = VALUES(issues_detected),
                growth_stage = VALUES(growth_stage)
        ");
        
        $count = 0;
        while ($row = $stmt->fetch()) {
            $insertStmt->execute($row);
            $count++;
        }
        
        $this->recordsImported += $count;
        echo "    Imported $count AI analyses\n";
    }
    
    private function importTimelapseImages(): void {
        echo "  Importing time-lapse images...\n";
        
        // Get last imported ID for incremental sync
        $lastId = $this->mysql->query("
            SELECT MAX(id) as last FROM timelapse_images
        ")->fetch()['last'] ?? 0;
        
        $stmt = $this->sqlite->prepare("
            SELECT id, project_id, image_path, thumbnail_path, captured_at, file_size, width, height
            FROM timelapse_images
            WHERE id > :last_id
            ORDER BY id ASC
            LIMIT 10000
        ");
        $stmt->execute([':last_id' => $lastId]);
        
        $insertStmt = $this->mysql->prepare("
            INSERT INTO timelapse_images 
                (id, project_id, image_path, thumbnail_path, captured_at, file_size, width, height)
            VALUES 
                (:id, :project_id, :image_path, :thumbnail_path, :captured_at, :file_size, :width, :height)
        ");
        
        $count = 0;
        while ($row = $stmt->fetch()) {
            $insertStmt->execute($row);
            $count++;
        }
        
        $this->recordsImported += $count;
        echo "    Imported $count time-lapse images\n";
    }
    
    private function importTimelapseVideos(): void {
        echo "  Importing time-lapse videos...\n";
        
        $stmt = $this->sqlite->query("
            SELECT id, project_id, video_path, thumbnail_path, duration, frame_count, 
                   fps, resolution, file_size, created_at
            FROM timelapse_videos
        ");
        
        $insertStmt = $this->mysql->prepare("
            INSERT INTO timelapse_videos 
                (id, project_id, video_path, thumbnail_path, duration, frame_count,
                 fps, resolution, file_size, created_at)
            VALUES 
                (:id, :project_id, :video_path, :thumbnail_path, :duration, :frame_count,
                 :fps, :resolution, :file_size, :created_at)
            ON DUPLICATE KEY UPDATE
                video_path = VALUES(video_path),
                thumbnail_path = VALUES(thumbnail_path),
                duration = VALUES(duration),
                frame_count = VALUES(frame_count),
                file_size = VALUES(file_size)
        ");
        
        $count = 0;
        while ($row = $stmt->fetch()) {
            $insertStmt->execute($row);
            $count++;
        }
        
        $this->recordsImported += $count;
        echo "    Imported $count time-lapse videos\n";
    }
    
    private function importDeviceSettings(): void {
        echo "  Importing device settings...\n";
        
        $stmt = $this->sqlite->query("
            SELECT device_name, device_type, gpio_pin, enabled, auto_mode, 
                   schedule, current_state, updated_at
            FROM device_settings
        ");
        
        $insertStmt = $this->mysql->prepare("
            INSERT INTO device_settings 
                (device_name, device_type, gpio_pin, enabled, auto_mode, 
                 schedule, current_state, updated_at)
            VALUES 
                (:device_name, :device_type, :gpio_pin, :enabled, :auto_mode,
                 :schedule, :current_state, :updated_at)
            ON DUPLICATE KEY UPDATE
                device_type = VALUES(device_type),
                gpio_pin = VALUES(gpio_pin),
                enabled = VALUES(enabled),
                auto_mode = VALUES(auto_mode),
                schedule = VALUES(schedule),
                current_state = VALUES(current_state),
                updated_at = VALUES(updated_at)
        ");
        
        $count = 0;
        while ($row = $stmt->fetch()) {
            $insertStmt->execute($row);
            $count++;
        }
        
        $this->recordsImported += $count;
        echo "    Imported $count device settings\n";
    }
    
    private function importAlertSettings(): void {
        echo "  Importing alert settings...\n";
        
        $stmt = $this->sqlite->query("
            SELECT enabled, temp_min, temp_max, humidity_min, humidity_max,
                   notification_interval, last_notification, updated_at
            FROM alert_settings
            LIMIT 1
        ");
        
        $row = $stmt->fetch();
        if (!$row) return;
        
        $this->mysql->exec("DELETE FROM alert_settings");
        
        $insertStmt = $this->mysql->prepare("
            INSERT INTO alert_settings 
                (enabled, temp_min, temp_max, humidity_min, humidity_max,
                 notification_interval, last_notification, updated_at)
            VALUES 
                (:enabled, :temp_min, :temp_max, :humidity_min, :humidity_max,
                 :notification_interval, :last_notification, :updated_at)
        ");
        
        $insertStmt->execute($row);
        $this->recordsImported++;
        echo "    Imported alert settings\n";
    }
    
    private function logSync(float $startTime, string $status, ?string $error = null): void {
        $duration = round(microtime(true) - $startTime, 2);
        
        $stmt = $this->mysql->prepare("
            INSERT INTO sync_logs 
                (sync_type, status, records_synced, error_message, started_at, completed_at, duration_seconds)
            VALUES 
                ('sqlite_import', :status, :records, :error, :started, NOW(), :duration)
        ");
        
        $stmt->execute([
            ':status' => $status,
            ':records' => $this->recordsImported,
            ':error' => $error,
            ':started' => date('Y-m-d H:i:s', (int)$startTime),
            ':duration' => $duration
        ]);
    }
}

// Run importer
try {
    $importer = new DataImporter();
    $success = $importer->run();
    exit($success ? 0 : 1);
} catch (Exception $e) {
    echo "Fatal error: " . $e->getMessage() . "\n";
    exit(1);
}
