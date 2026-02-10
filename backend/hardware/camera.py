"""Raspberry Pi HQ Camera control using picamera2.

Handles camera initialization, snapshots, and video streaming.
"""
import logging
import io
import time
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

try:
    from picamera2 import Picamera2
    from libcamera import controls
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False
    logging.warning("picamera2 not available. Running in simulation mode.")

from backend.config import CAMERA_RESOLUTION, CAMERA_ROTATION, DATA_DIR

logger = logging.getLogger(__name__)

class CameraController:
    """Raspberry Pi HQ Camera interface."""
    
    def __init__(self, resolution: Tuple[int, int] = CAMERA_RESOLUTION, 
                 rotation: int = CAMERA_ROTATION):
        """Initialize camera controller.
        
        Args:
            resolution: Camera resolution (width, height)
            rotation: Camera rotation in degrees (0, 90, 180, 270)
        """
        self.resolution = resolution
        self.rotation = rotation
        self.camera = None
        self.simulation_mode = not PICAMERA2_AVAILABLE
        self.is_initialized = False
        
        if not self.simulation_mode:
            self._init_camera()
        else:
            logger.warning("Running in SIMULATION MODE - camera not available")
    
    def _init_camera(self):
        """Initialize the camera."""
        try:
            self.camera = Picamera2()
            
            # Configure camera
            config = self.camera.create_still_configuration(
                main={"size": self.resolution},
                transform={
                    "hflip": 0,
                    "vflip": 0
                }
            )
            self.camera.configure(config)
            
            # Start camera
            self.camera.start()
            
            # Allow camera to warm up
            time.sleep(2)
            
            self.is_initialized = True
            logger.info(f"Camera initialized: {self.resolution[0]}x{self.resolution[1]}")
            
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            self.simulation_mode = True
            logger.warning("Falling back to SIMULATION MODE")
    
    def capture_image(self, filepath: Optional[Path] = None) -> Optional[Path]:
        """Capture a still image.
        
        Args:
            filepath: Path to save image. If None, generates timestamped filename.
            
        Returns:
            Path to saved image or None if capture failed
        """
        if not filepath:
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = DATA_DIR / "photos" / f"capture_{timestamp}.jpg"
        
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if self.simulation_mode:
            # Create a placeholder file
            logger.info(f"[SIMULATION] Would capture image to {filepath}")
            # Create a small placeholder image
            try:
                from PIL import Image, ImageDraw, ImageFont
                img = Image.new('RGB', self.resolution, color=(73, 109, 137))
                d = ImageDraw.Draw(img)
                text = f"Simulation\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                d.text((self.resolution[0]//2, self.resolution[1]//2), text, 
                      fill=(255, 255, 255), anchor="mm")
                img.save(filepath)
                return filepath
            except ImportError:
                # If PIL not available, just create empty file
                filepath.touch()
                return filepath
        
        try:
            self.camera.capture_file(str(filepath))
            logger.info(f"Image captured: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error capturing image: {e}")
            return None
    
    def capture_to_stream(self) -> Optional[bytes]:
        """Capture image to bytes (for streaming).
        
        Returns:
            Image as bytes or None if capture failed
        """
        if self.simulation_mode:
            logger.debug("[SIMULATION] Capturing to stream")
            try:
                from PIL import Image, ImageDraw
                import io
                img = Image.new('RGB', (640, 480), color=(73, 109, 137))
                d = ImageDraw.Draw(img)
                text = f"Simulation {datetime.now().strftime('%H:%M:%S')}"
                d.text((320, 240), text, fill=(255, 255, 255), anchor="mm")
                stream = io.BytesIO()
                img.save(stream, format='JPEG')
                return stream.getvalue()
            except ImportError:
                return None
        
        try:
            stream = io.BytesIO()
            self.camera.capture_file(stream, format='jpeg')
            return stream.getvalue()
        except Exception as e:
            logger.error(f"Error capturing to stream: {e}")
            return None
    
    def start_preview(self):
        """Start camera preview (if supported)."""
        if self.simulation_mode:
            logger.info("[SIMULATION] Preview not available")
            return
        
        try:
            # Note: Preview might not work in headless mode
            logger.info("Camera preview started (if display available)")
        except Exception as e:
            logger.warning(f"Preview not available: {e}")
    
    def stop_preview(self):
        """Stop camera preview."""
        if self.simulation_mode:
            return
        
        try:
            logger.info("Camera preview stopped")
        except Exception as e:
            logger.warning(f"Error stopping preview: {e}")
    
    def set_resolution(self, width: int, height: int):
        """Change camera resolution.
        
        Args:
            width: Image width in pixels
            height: Image height in pixels
        """
        self.resolution = (width, height)
        if not self.simulation_mode and self.camera:
            # Reconfigure camera
            self._init_camera()
    
    def cleanup(self):
        """Clean up camera resources."""
        if not self.simulation_mode and self.camera:
            try:
                self.camera.stop()
                self.camera.close()
                logger.info("Camera cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up camera: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
