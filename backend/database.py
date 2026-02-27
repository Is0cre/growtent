"""Database models and setup for grow tent automation."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import threading
import logging

from backend.config import DATABASE_PATH

logger = logging.getLogger(__name__)


class Database:
    """Thread-safe database manager."""
    
    _local = threading.local()
    
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        try:
            yield self._local.conn
        except Exception as e:
            self._local.conn.rollback()
            raise e
    
    def init_database(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Projects table (with timelapse state fields)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    start_date TIMESTAMP NOT NULL,
                    end_date TIMESTAMP,
                    notes TEXT,
                    status TEXT DEFAULT 'active',
                    timelapse_enabled INTEGER DEFAULT 1,
                    timelapse_interval INTEGER DEFAULT 300,
                    timelapse_last_capture TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add timelapse columns if they don't exist (migration)
            try:
                cursor.execute("ALTER TABLE projects ADD COLUMN timelapse_enabled INTEGER DEFAULT 1")
            except sqlite3.OperationalError:
                pass  # Column already exists
            try:
                cursor.execute("ALTER TABLE projects ADD COLUMN timelapse_interval INTEGER DEFAULT 300")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE projects ADD COLUMN timelapse_last_capture TIMESTAMP")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE projects ADD COLUMN timelapse_only_with_lights INTEGER DEFAULT 1")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # Sensor logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sensor_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    timestamp TIMESTAMP NOT NULL,
                    temperature REAL,
                    humidity REAL,
                    pressure REAL,
                    gas_resistance REAL,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sensor_logs_timestamp 
                ON sensor_logs(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sensor_logs_project 
                ON sensor_logs(project_id)
            """)
            
            # Diary entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS diary_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    title TEXT,
                    text TEXT,
                    photos TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            # Device settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_settings (
                    device_name TEXT PRIMARY KEY,
                    schedule_json TEXT,
                    thresholds_json TEXT,
                    enabled INTEGER DEFAULT 1,
                    mode TEXT DEFAULT 'schedule',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Alert settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    temp_min REAL,
                    temp_max REAL,
                    humidity_min REAL,
                    humidity_max REAL,
                    enabled INTEGER DEFAULT 1,
                    notification_interval INTEGER DEFAULT 300,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Time-lapse images table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS timelapse_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    timestamp TIMESTAMP NOT NULL,
                    filepath TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            # System settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Device states table (for tracking current states)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_states (
                    device_name TEXT PRIMARY KEY,
                    state INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # AI Analysis table (NEW)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    timestamp TIMESTAMP NOT NULL,
                    photo_path TEXT,
                    analysis_text TEXT,
                    health_score INTEGER,
                    recommendations TEXT,
                    model TEXT,
                    tokens_used INTEGER,
                    synced_to_external INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_project 
                ON ai_analysis(project_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_timestamp 
                ON ai_analysis(timestamp)
            """)
            
            # Sync log table (NEW)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT,
                    error_message TEXT,
                    items_synced INTEGER DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_log_timestamp 
                ON sync_log(timestamp)
            """)
            
            # Scheduled tasks table (NEW - for APScheduler persistence)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_value TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    last_run TIMESTAMP,
                    next_run TIMESTAMP,
                    run_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Database schema initialized")
    
    # Project methods
    def create_project(self, name: str, notes: str = "", 
                      timelapse_enabled: bool = True,
                      timelapse_interval: int = 300,
                      timelapse_only_with_lights: bool = True) -> int:
        """Create a new project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO projects (name, start_date, notes, status, 
                                     timelapse_enabled, timelapse_interval, timelapse_only_with_lights)
                VALUES (?, ?, ?, 'active', ?, ?, ?)
            """, (name, datetime.now(), notes, 
                  1 if timelapse_enabled else 0, timelapse_interval,
                  1 if timelapse_only_with_lights else 0))
            conn.commit()
            return cursor.lastrowid
    
    def get_active_project(self) -> Optional[Dict[str, Any]]:
        """Get the currently active project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM projects WHERE status = 'active' 
                ORDER BY start_date DESC LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Get all projects."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY start_date DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_project(self, project_id: int, **kwargs) -> bool:
        """Update project details."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            allowed_fields = ['name', 'notes', 'status', 'end_date',
                            'timelapse_enabled', 'timelapse_interval',
                            'timelapse_last_capture', 'timelapse_only_with_lights']
            updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            if not updates:
                return False
            
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [project_id]
            
            cursor.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0
    
    def end_project(self, project_id: int) -> bool:
        """End a project."""
        return self.update_project(
            project_id, 
            status='completed', 
            end_date=datetime.now(),
            timelapse_enabled=0
        )
    
    def archive_project(self, project_id: int) -> bool:
        """Archive a project."""
        return self.update_project(project_id, status='archived')
    
    def update_timelapse_capture(self, project_id: int) -> bool:
        """Update the last timelapse capture time for a project."""
        return self.update_project(
            project_id, 
            timelapse_last_capture=datetime.now()
        )
    
    def get_projects_needing_timelapse(self) -> List[Dict[str, Any]]:
        """Get active projects that need timelapse capture."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM projects 
                WHERE status = 'active' AND timelapse_enabled = 1
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    # Sensor log methods
    def log_sensor_data(self, project_id: Optional[int], temperature: float, 
                       humidity: float, pressure: float, gas_resistance: float) -> int:
        """Log sensor data."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sensor_logs 
                (project_id, timestamp, temperature, humidity, pressure, gas_resistance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (project_id, datetime.now(), temperature, humidity, pressure, gas_resistance))
            conn.commit()
            return cursor.lastrowid
    
    def get_latest_sensor_data(self) -> Optional[Dict[str, Any]]:
        """Get the most recent sensor reading."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sensor_logs ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_sensor_data(self, project_id: Optional[int] = None, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       limit: int = 1000) -> List[Dict[str, Any]]:
        """Get sensor data with optional filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM sensor_logs WHERE 1=1"
            params = []
            
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # Device settings methods
    def get_device_settings(self, device_name: str) -> Optional[Dict[str, Any]]:
        """Get device settings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM device_settings WHERE device_name = ?", 
                (device_name,)
            )
            row = cursor.fetchone()
            if row:
                settings = dict(row)
                # Parse JSON fields
                if settings.get('schedule_json'):
                    settings['schedule'] = json.loads(settings['schedule_json'])
                if settings.get('thresholds_json'):
                    settings['thresholds'] = json.loads(settings['thresholds_json'])
                return settings
            return None
    
    def save_device_settings(self, device_name: str, settings: Dict[str, Any]) -> bool:
        """Save device settings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            schedule_json = json.dumps(settings.get('schedule', []))
            thresholds_json = json.dumps(settings.get('thresholds', {}))
            enabled = 1 if settings.get('enabled', True) else 0
            mode = settings.get('mode', 'schedule')
            
            cursor.execute("""
                INSERT OR REPLACE INTO device_settings 
                (device_name, schedule_json, thresholds_json, enabled, mode, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (device_name, schedule_json, thresholds_json, enabled, mode, datetime.now()))
            conn.commit()
            return True
    
    def get_all_device_settings(self) -> Dict[str, Dict[str, Any]]:
        """Get all device settings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM device_settings")
            result = {}
            for row in cursor.fetchall():
                settings = dict(row)
                device_name = settings['device_name']
                if settings.get('schedule_json'):
                    settings['schedule'] = json.loads(settings['schedule_json'])
                if settings.get('thresholds_json'):
                    settings['thresholds'] = json.loads(settings['thresholds_json'])
                result[device_name] = settings
            return result
    
    # Alert settings methods
    def get_alert_settings(self) -> Dict[str, Any]:
        """Get alert settings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alert_settings WHERE id = 1")
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def save_alert_settings(self, settings: Dict[str, Any]) -> bool:
        """Save alert settings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO alert_settings 
                (id, temp_min, temp_max, humidity_min, humidity_max, enabled, 
                 notification_interval, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """, (
                settings.get('temp_min'),
                settings.get('temp_max'),
                settings.get('humidity_min'),
                settings.get('humidity_max'),
                1 if settings.get('enabled', True) else 0,
                settings.get('notification_interval', 300),
                datetime.now()
            ))
            conn.commit()
            return True
    
    # Diary methods
    def create_diary_entry(self, project_id: int, title: str, text: str, 
                          photos: List[str] = None) -> int:
        """Create a diary entry."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            photos_json = json.dumps(photos or [])
            cursor.execute("""
                INSERT INTO diary_entries (project_id, timestamp, title, text, photos)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, datetime.now(), title, text, photos_json))
            conn.commit()
            return cursor.lastrowid
    
    def get_diary_entries(self, project_id: int) -> List[Dict[str, Any]]:
        """Get diary entries for a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM diary_entries 
                WHERE project_id = ? 
                ORDER BY timestamp DESC
            """, (project_id,))
            entries = []
            for row in cursor.fetchall():
                entry = dict(row)
                if entry.get('photos'):
                    entry['photos'] = json.loads(entry['photos'])
                entries.append(entry)
            return entries
    
    def update_diary_entry(self, entry_id: int, title: str = None, 
                          text: str = None, photos: List[str] = None) -> bool:
        """Update a diary entry."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if text is not None:
                updates.append("text = ?")
                params.append(text)
            if photos is not None:
                updates.append("photos = ?")
                params.append(json.dumps(photos))
            
            if not updates:
                return False
            
            params.append(entry_id)
            cursor.execute(f"UPDATE diary_entries SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_diary_entry(self, entry_id: int) -> bool:
        """Delete a diary entry."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # Time-lapse methods
    def save_timelapse_image(self, project_id: Optional[int], filepath: str) -> int:
        """Save time-lapse image record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO timelapse_images (project_id, timestamp, filepath)
                VALUES (?, ?, ?)
            """, (project_id, datetime.now(), filepath))
            conn.commit()
            return cursor.lastrowid
    
    def get_timelapse_images(self, project_id: int) -> List[Dict[str, Any]]:
        """Get time-lapse images for a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM timelapse_images 
                WHERE project_id = ? 
                ORDER BY timestamp ASC
            """, (project_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_timelapse_image_count(self, project_id: int) -> int:
        """Get count of timelapse images for a project."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM timelapse_images WHERE project_id = ?",
                (project_id,)
            )
            row = cursor.fetchone()
            return row['count'] if row else 0
    
    # System settings methods
    def get_system_setting(self, key: str) -> Optional[str]:
        """Get a system setting."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else None
    
    def set_system_setting(self, key: str, value: str) -> bool:
        """Set a system setting."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now()))
            conn.commit()
            return True
    
    # Device state methods
    def update_device_state(self, device_name: str, state: int) -> bool:
        """Update device state."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO device_states (device_name, state, last_updated)
                VALUES (?, ?, ?)
            """, (device_name, state, datetime.now()))
            conn.commit()
            return True
    
    def get_device_state(self, device_name: str) -> Optional[int]:
        """Get device state."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT state FROM device_states WHERE device_name = ?", 
                (device_name,)
            )
            row = cursor.fetchone()
            return row['state'] if row else None
    
    def get_all_device_states(self) -> Dict[str, int]:
        """Get all device states."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT device_name, state FROM device_states")
            return {row['device_name']: row['state'] for row in cursor.fetchall()}
    
    # AI Analysis methods (NEW)
    def save_ai_analysis(self, project_id: Optional[int], photo_path: str,
                        analysis_text: str, health_score: Optional[int] = None,
                        recommendations: str = "", model: str = "",
                        tokens_used: Optional[int] = None) -> int:
        """Save AI analysis result."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_analysis 
                (project_id, timestamp, photo_path, analysis_text, health_score,
                 recommendations, model, tokens_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, datetime.now(), photo_path, analysis_text,
                  health_score, recommendations, model, tokens_used))
            conn.commit()
            return cursor.lastrowid
    
    def get_ai_analysis(self, analysis_id: int) -> Optional[Dict[str, Any]]:
        """Get AI analysis by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ai_analysis WHERE id = ?", (analysis_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_ai_analyses(self, project_id: Optional[int] = None,
                       limit: int = 50) -> List[Dict[str, Any]]:
        """Get AI analyses with optional project filter."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if project_id:
                cursor.execute("""
                    SELECT * FROM ai_analysis 
                    WHERE project_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (project_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM ai_analysis 
                    ORDER BY timestamp DESC LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_latest_ai_analysis(self, project_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get the most recent AI analysis."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if project_id:
                cursor.execute("""
                    SELECT * FROM ai_analysis 
                    WHERE project_id = ?
                    ORDER BY timestamp DESC LIMIT 1
                """, (project_id,))
            else:
                cursor.execute("""
                    SELECT * FROM ai_analysis 
                    ORDER BY timestamp DESC LIMIT 1
                """)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def mark_analysis_synced(self, analysis_id: int) -> bool:
        """Mark an analysis as synced to external server."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE ai_analysis SET synced_to_external = 1 WHERE id = ?
            """, (analysis_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # Sync log methods (NEW)
    def log_sync(self, sync_type: str, status: str, details: str = "",
                error_message: str = "", items_synced: int = 0) -> int:
        """Log a sync operation."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_log 
                (sync_type, status, details, error_message, items_synced)
                VALUES (?, ?, ?, ?, ?)
            """, (sync_type, status, details, error_message, items_synced))
            conn.commit()
            return cursor.lastrowid
    
    def get_sync_logs(self, sync_type: Optional[str] = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
        """Get sync logs with optional type filter."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if sync_type:
                cursor.execute("""
                    SELECT * FROM sync_log 
                    WHERE sync_type = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (sync_type, limit))
            else:
                cursor.execute("""
                    SELECT * FROM sync_log 
                    ORDER BY timestamp DESC LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_last_successful_sync(self, sync_type: str) -> Optional[Dict[str, Any]]:
        """Get the last successful sync for a type."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sync_log 
                WHERE sync_type = ? AND status = 'success'
                ORDER BY timestamp DESC LIMIT 1
            """, (sync_type,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # Scheduled tasks methods (NEW)
    def save_scheduled_task(self, task_id: str, task_name: str,
                           schedule_type: str, schedule_value: str,
                           enabled: bool = True) -> bool:
        """Save or update a scheduled task."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO scheduled_tasks 
                (id, task_name, schedule_type, schedule_value, enabled)
                VALUES (?, ?, ?, ?, ?)
            """, (task_id, task_name, schedule_type, schedule_value,
                  1 if enabled else 0))
            conn.commit()
            return True
    
    def get_scheduled_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a scheduled task by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get all scheduled tasks."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scheduled_tasks ORDER BY task_name")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_task_run_time(self, task_id: str, 
                            next_run: Optional[datetime] = None) -> bool:
        """Update task last run time and optionally next run."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if next_run:
                cursor.execute("""
                    UPDATE scheduled_tasks 
                    SET last_run = ?, next_run = ?, run_count = run_count + 1
                    WHERE id = ?
                """, (datetime.now(), next_run, task_id))
            else:
                cursor.execute("""
                    UPDATE scheduled_tasks 
                    SET last_run = ?, run_count = run_count + 1
                    WHERE id = ?
                """, (datetime.now(), task_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def toggle_scheduled_task(self, task_id: str, enabled: bool) -> bool:
        """Enable or disable a scheduled task."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE scheduled_tasks SET enabled = ? WHERE id = ?
            """, (1 if enabled else 0, task_id))
            conn.commit()
            return cursor.rowcount > 0


# Global database instance
db = Database()
