-- Grow Tent Automation - MySQL Database Schema
-- Compatible with data synced from Raspberry Pi SQLite database

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS grow_tent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE grow_tent;

-- --------------------------------------------------------
-- Table: projects
-- --------------------------------------------------------
DROP TABLE IF EXISTS `projects`;
CREATE TABLE `projects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL,
    `plant_type` VARCHAR(100),
    `strain` VARCHAR(100),
    `start_date` DATETIME NOT NULL,
    `end_date` DATETIME,
    `status` VARCHAR(50) DEFAULT 'active',
    `notes` TEXT,
    `timelapse_enabled` TINYINT(1) DEFAULT 1,
    `timelapse_interval` INT DEFAULT 3600,
    `timelapse_only_with_lights` TINYINT(1) DEFAULT 1,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_status` (`status`),
    INDEX `idx_start_date` (`start_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: sensor_logs
-- --------------------------------------------------------
DROP TABLE IF EXISTS `sensor_logs`;
CREATE TABLE `sensor_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `project_id` INT,
    `temperature` DECIMAL(5,2),
    `humidity` DECIMAL(5,2),
    `pressure` DECIMAL(7,2),
    `gas_resistance` DECIMAL(10,2),
    `air_quality` VARCHAR(50),
    `timestamp` DATETIME NOT NULL,
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_timestamp` (`timestamp`),
    INDEX `idx_project_timestamp` (`project_id`, `timestamp`),
    FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: diary_entries
-- --------------------------------------------------------
DROP TABLE IF EXISTS `diary_entries`;
CREATE TABLE `diary_entries` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `project_id` INT NOT NULL,
    `entry_type` VARCHAR(50) DEFAULT 'note',
    `title` VARCHAR(255),
    `content` TEXT,
    `photo_path` VARCHAR(500),
    `tags` TEXT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_entry_type` (`entry_type`),
    INDEX `idx_created_at` (`created_at`),
    FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: ai_analysis
-- --------------------------------------------------------
DROP TABLE IF EXISTS `ai_analysis`;
CREATE TABLE `ai_analysis` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `project_id` INT,
    `photo_path` VARCHAR(500),
    `health_score` INT,
    `analysis_text` TEXT,
    `recommendations` TEXT,
    `issues_detected` TEXT,
    `growth_stage` VARCHAR(100),
    `model_used` VARCHAR(100),
    `raw_response` TEXT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_health_score` (`health_score`),
    INDEX `idx_created_at` (`created_at`),
    FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: timelapse_images
-- --------------------------------------------------------
DROP TABLE IF EXISTS `timelapse_images`;
CREATE TABLE `timelapse_images` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `project_id` INT NOT NULL,
    `image_path` VARCHAR(500) NOT NULL,
    `thumbnail_path` VARCHAR(500),
    `captured_at` DATETIME NOT NULL,
    `file_size` INT,
    `width` INT,
    `height` INT,
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_captured_at` (`captured_at`),
    FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: timelapse_videos
-- --------------------------------------------------------
DROP TABLE IF EXISTS `timelapse_videos`;
CREATE TABLE `timelapse_videos` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `project_id` INT NOT NULL,
    `video_path` VARCHAR(500) NOT NULL,
    `thumbnail_path` VARCHAR(500),
    `duration` INT,
    `frame_count` INT,
    `fps` INT DEFAULT 30,
    `resolution` VARCHAR(50),
    `file_size` BIGINT,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_project_id` (`project_id`),
    FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: device_settings
-- --------------------------------------------------------
DROP TABLE IF EXISTS `device_settings`;
CREATE TABLE `device_settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `device_name` VARCHAR(100) NOT NULL,
    `device_type` VARCHAR(50),
    `gpio_pin` INT,
    `enabled` TINYINT(1) DEFAULT 1,
    `auto_mode` TINYINT(1) DEFAULT 0,
    `schedule` TEXT,
    `current_state` TINYINT(1) DEFAULT 0,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `idx_device_name` (`device_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: alert_settings
-- --------------------------------------------------------
DROP TABLE IF EXISTS `alert_settings`;
CREATE TABLE `alert_settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `enabled` TINYINT(1) DEFAULT 1,
    `temp_min` DECIMAL(5,2) DEFAULT 18.00,
    `temp_max` DECIMAL(5,2) DEFAULT 30.00,
    `humidity_min` DECIMAL(5,2) DEFAULT 40.00,
    `humidity_max` DECIMAL(5,2) DEFAULT 70.00,
    `notification_interval` INT DEFAULT 3600,
    `last_notification` DATETIME,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: sync_logs
-- --------------------------------------------------------
DROP TABLE IF EXISTS `sync_logs`;
CREATE TABLE `sync_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `sync_type` VARCHAR(50) NOT NULL,
    `status` VARCHAR(50) NOT NULL,
    `records_synced` INT DEFAULT 0,
    `error_message` TEXT,
    `started_at` DATETIME,
    `completed_at` DATETIME,
    `duration_seconds` DECIMAL(10,2),
    INDEX `idx_sync_type` (`sync_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_started_at` (`started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Table: system_settings
-- --------------------------------------------------------
DROP TABLE IF EXISTS `system_settings`;
CREATE TABLE `system_settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `setting_key` VARCHAR(100) NOT NULL,
    `setting_value` TEXT,
    `setting_type` VARCHAR(50) DEFAULT 'string',
    `description` VARCHAR(500),
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `idx_setting_key` (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------
-- Insert default settings
-- --------------------------------------------------------
INSERT INTO `alert_settings` (`enabled`, `temp_min`, `temp_max`, `humidity_min`, `humidity_max`) 
VALUES (1, 18.00, 30.00, 40.00, 70.00);

INSERT INTO `system_settings` (`setting_key`, `setting_value`, `setting_type`, `description`) VALUES
('last_sync_time', NULL, 'datetime', 'Last successful sync from Pi'),
('sync_interval', '300', 'integer', 'Sync interval in seconds'),
('timezone', 'Europe/Malta', 'string', 'Server timezone'),
('data_retention_days', '365', 'integer', 'Days to retain sensor data');

SET FOREIGN_KEY_CHECKS = 1;
