"""External Server Sync Module for Grow Tent Automation.

Handles synchronization of data to external servers including:
- Latest camera photos
- Sensor data (temperature, humidity, pressure, gas readings)
- Project information and status
- Daily analysis reports
"""
import logging
import base64
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ExternalSyncError(Exception):
    """Custom exception for external sync errors."""
    pass


class ExternalSyncModule:
    """Handles data synchronization to external servers."""
    
    def __init__(self, config: Dict[str, Any], secrets: Dict[str, Any]):
        """Initialize the external sync module.
        
        Args:
            config: Settings configuration dictionary
            secrets: Secrets configuration dictionary
        """
        self.config = config.get('external_sync', {})
        self.secrets = secrets.get('external_server', {})
        
        self.enabled = self.secrets.get('enabled', False) and self.config.get('enabled', False)
        self.base_url = self.secrets.get('url', '').rstrip('/')
        self.auth_type = self.secrets.get('auth_type', 'none')
        
        # Authentication credentials
        self.api_key = self.secrets.get('api_key', '')
        self.bearer_token = self.secrets.get('bearer_token', '')
        self.basic_username = self.secrets.get('basic_username', '')
        self.basic_password = self.secrets.get('basic_password', '')
        
        # Sync settings
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay', 30)
        self.endpoints = self.config.get('endpoints', {})
        
        # Create session with retry logic
        self.session = self._create_session()
        
        logger.info(f"External sync module initialized. Enabled: {self.enabled}")
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.retry_attempts,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth type."""
        headers = {'Content-Type': 'application/json'}
        
        if self.auth_type == 'api_key':
            headers['X-API-Key'] = self.api_key
        elif self.auth_type == 'bearer':
            headers['Authorization'] = f'Bearer {self.bearer_token}'
        elif self.auth_type == 'basic':
            import base64
            credentials = base64.b64encode(
                f"{self.basic_username}:{self.basic_password}".encode()
            ).decode()
            headers['Authorization'] = f'Basic {credentials}'
        
        return headers
    
    def _make_request(self, method: str, endpoint: str, 
                      data: Optional[Dict] = None,
                      files: Optional[Dict] = None,
                      timeout: int = 30) -> Dict[str, Any]:
        """Make an HTTP request to the external server.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: JSON data to send
            files: Files to upload
            timeout: Request timeout in seconds
            
        Returns:
            Response data as dictionary
            
        Raises:
            ExternalSyncError: If request fails
        """
        if not self.enabled:
            raise ExternalSyncError("External sync is not enabled")
        
        if not self.base_url:
            raise ExternalSyncError("External server URL not configured")
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_auth_headers()
        
        # Remove Content-Type for file uploads
        if files:
            del headers['Content-Type']
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data if not files else None,
                files=files,
                headers=headers,
                timeout=timeout
            )
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                return response.json()
            except ValueError:
                return {'success': True, 'message': response.text}
                
        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after {timeout}s: {url}"
            logger.error(error_msg)
            raise ExternalSyncError(error_msg)
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error to {url}: {str(e)}"
            logger.error(error_msg)
            raise ExternalSyncError(error_msg)
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise ExternalSyncError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            raise ExternalSyncError(error_msg)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to external server.
        
        Returns:
            Dictionary with connection status
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'External sync is not enabled',
                'connected': False
            }
        
        if not self.base_url:
            return {
                'success': False,
                'error': 'External server URL not configured',
                'connected': False
            }
        
        try:
            # Try a simple GET request to base URL
            headers = self._get_auth_headers()
            response = self.session.get(
                self.base_url,
                headers=headers,
                timeout=10
            )
            
            return {
                'success': True,
                'connected': True,
                'status_code': response.status_code,
                'message': 'Connection successful'
            }
            
        except Exception as e:
            return {
                'success': False,
                'connected': False,
                'error': str(e)
            }
    
    def sync_photo(self, photo_path: str, project_id: Optional[int] = None,
                   photo_type: str = 'latest') -> Dict[str, Any]:
        """Sync a photo to the external server.
        
        Args:
            photo_path: Path to the photo file
            project_id: Associated project ID
            photo_type: Type of photo (latest, timelapse, diary)
            
        Returns:
            Sync result dictionary
        """
        if not self.config.get('sync_photos', True):
            return {'success': False, 'error': 'Photo sync is disabled'}
        
        photo_path = Path(photo_path)
        if not photo_path.exists():
            raise ExternalSyncError(f"Photo file not found: {photo_path}")
        
        endpoint = self.endpoints.get('photos', '/photos/upload')
        
        try:
            with open(photo_path, 'rb') as f:
                files = {
                    'photo': (photo_path.name, f, 'image/jpeg')
                }
                
                # Add metadata as form fields
                data = {
                    'project_id': str(project_id) if project_id else '',
                    'photo_type': photo_type,
                    'timestamp': datetime.now().isoformat(),
                    'filename': photo_path.name
                }
                
                # Need to send as multipart form
                url = f"{self.base_url}{endpoint}"
                headers = self._get_auth_headers()
                del headers['Content-Type']  # Let requests set multipart header
                
                response = self.session.post(
                    url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60
                )
                
                response.raise_for_status()
                
                logger.info(f"Photo synced successfully: {photo_path.name}")
                return {
                    'success': True,
                    'message': 'Photo synced successfully',
                    'filename': photo_path.name
                }
                
        except Exception as e:
            logger.error(f"Failed to sync photo: {e}")
            raise ExternalSyncError(f"Failed to sync photo: {e}")
    
    def sync_sensor_data(self, sensor_data: Dict[str, Any],
                         project_id: Optional[int] = None) -> Dict[str, Any]:
        """Sync sensor data to external server.
        
        Args:
            sensor_data: Dictionary containing sensor readings
            project_id: Associated project ID
            
        Returns:
            Sync result dictionary
        """
        if not self.config.get('sync_sensor_data', True):
            return {'success': False, 'error': 'Sensor data sync is disabled'}
        
        endpoint = self.endpoints.get('sensor_data', '/sensor-data')
        
        payload = {
            'project_id': project_id,
            'timestamp': datetime.now().isoformat(),
            'temperature': sensor_data.get('temperature'),
            'humidity': sensor_data.get('humidity'),
            'pressure': sensor_data.get('pressure'),
            'gas_resistance': sensor_data.get('gas_resistance')
        }
        
        result = self._make_request('POST', endpoint, data=payload)
        logger.info("Sensor data synced successfully")
        return {
            'success': True,
            'message': 'Sensor data synced successfully',
            'data': result
        }
    
    def sync_project_info(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Sync project information to external server.
        
        Args:
            project: Project data dictionary
            
        Returns:
            Sync result dictionary
        """
        if not self.config.get('sync_project_info', True):
            return {'success': False, 'error': 'Project sync is disabled'}
        
        endpoint = self.endpoints.get('project_info', '/projects')
        
        payload = {
            'id': project.get('id'),
            'name': project.get('name'),
            'start_date': project.get('start_date'),
            'end_date': project.get('end_date'),
            'status': project.get('status'),
            'notes': project.get('notes'),
            'timestamp': datetime.now().isoformat()
        }
        
        result = self._make_request('POST', endpoint, data=payload)
        logger.info(f"Project info synced: {project.get('name')}")
        return {
            'success': True,
            'message': 'Project info synced successfully',
            'data': result
        }
    
    def sync_analysis_report(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Sync AI analysis report to external server.
        
        Args:
            analysis: Analysis data dictionary
            
        Returns:
            Sync result dictionary
        """
        if not self.config.get('sync_analysis_reports', True):
            return {'success': False, 'error': 'Analysis report sync is disabled'}
        
        endpoint = self.endpoints.get('analysis_reports', '/reports')
        
        payload = {
            'id': analysis.get('id'),
            'project_id': analysis.get('project_id'),
            'timestamp': analysis.get('timestamp'),
            'analysis_text': analysis.get('analysis_text'),
            'health_score': analysis.get('health_score'),
            'recommendations': analysis.get('recommendations'),
            'photo_url': analysis.get('photo_path'),
            'sync_timestamp': datetime.now().isoformat()
        }
        
        result = self._make_request('POST', endpoint, data=payload)
        logger.info(f"Analysis report synced: ID {analysis.get('id')}")
        return {
            'success': True,
            'message': 'Analysis report synced successfully',
            'data': result
        }
    
    def sync_all(self, sensor_data: Optional[Dict] = None,
                 project: Optional[Dict] = None,
                 photo_path: Optional[str] = None,
                 analysis: Optional[Dict] = None) -> Dict[str, Any]:
        """Sync all available data to external server.
        
        Args:
            sensor_data: Current sensor readings
            project: Active project data
            photo_path: Path to latest photo
            analysis: Latest AI analysis
            
        Returns:
            Dictionary with sync results for each data type
        """
        results = {}
        
        if sensor_data and project:
            try:
                results['sensor_data'] = self.sync_sensor_data(
                    sensor_data, project.get('id')
                )
            except ExternalSyncError as e:
                results['sensor_data'] = {'success': False, 'error': str(e)}
        
        if project:
            try:
                results['project_info'] = self.sync_project_info(project)
            except ExternalSyncError as e:
                results['project_info'] = {'success': False, 'error': str(e)}
        
        if photo_path and project:
            try:
                results['photo'] = self.sync_photo(
                    photo_path, project.get('id'), 'latest'
                )
            except ExternalSyncError as e:
                results['photo'] = {'success': False, 'error': str(e)}
        
        if analysis:
            try:
                results['analysis'] = self.sync_analysis_report(analysis)
            except ExternalSyncError as e:
                results['analysis'] = {'success': False, 'error': str(e)}
        
        # Determine overall success
        success_count = sum(1 for r in results.values() if r.get('success'))
        total_count = len(results)
        
        return {
            'success': success_count == total_count,
            'synced': success_count,
            'total': total_count,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }


# Singleton instance (initialized later with config)
_sync_module: Optional[ExternalSyncModule] = None


def get_sync_module() -> Optional[ExternalSyncModule]:
    """Get the global sync module instance."""
    return _sync_module


def init_sync_module(config: Dict[str, Any], secrets: Dict[str, Any]) -> ExternalSyncModule:
    """Initialize the global sync module instance.
    
    Args:
        config: Settings configuration
        secrets: Secrets configuration
        
    Returns:
        Initialized ExternalSyncModule instance
    """
    global _sync_module
    _sync_module = ExternalSyncModule(config, secrets)
    return _sync_module
