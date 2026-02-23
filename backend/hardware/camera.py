"""Raspberry Pi HQ Camera control using rpicam-jpeg command.

Handles camera initialization, snapshots, and video streaming via subprocess.
Uses the rpicam-jpeg command which is part of libcamera-apps.
"""
import logging
import subprocess
import time
import shutil
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import threading

from backend.config import CAMERA_RESOLUTION, CAMERA_ROTATION, DATA_DIR

logger = logging.getLogger(__name__)

class CameraController:
    """Raspberry Pi HQ Camera interface using rpicam-jpeg command."""
    
    def __init__(self, resolution: Tuple[int, int] = CAMERA_RESOLUTION, 
                 rotation: int = CAMERA_ROTATION):
        """Initialize camera controller.
        
        Args:
            resolution: Camera resolution (width, height)
            rotation: Camera rotation in degrees (0, 90, 180, 270)
        """
        self.resolution = resolution
        self.rotation = rotation
        self.simulation_mode = False
        self.is_initialized = False
        self._lock = threading.Lock()
        
        # Latest snapshot path for live feed
        self.latest_snapshot_path = DATA_DIR / "photos" / "latest_snapshot.jpg"
        
        # Check if rpicam-jpeg is available
        self._check_camera_available()
    
    def _check_camera_available(self):
        """Check if rpicam-jpeg command is available."""
        try:
            # Check if rpicam-jpeg exists
            result = subprocess.run(
                ["which", "rpicam-jpeg"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self.is_initialized = True
                self.simulation_mode = False
                logger.info(f"Camera initialized using rpicam-jpeg: {self.resolution[0]}x{self.resolution[1]}")
            else:
                # Try fallback to libcamera-jpeg
                result = subprocess.run(
                    ["which", "libcamera-jpeg"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.is_initialized = True
                    self.simulation_mode = False
                    self._use_libcamera_jpeg = True
                    logger.info(f"Camera initialized using libcamera-jpeg (fallback): {self.resolution[0]}x{self.resolution[1]}")
                else:
                    self.simulation_mode = True
                    logger.warning("rpicam-jpeg not available. Running in SIMULATION MODE")
                    logger.warning("Install libcamera-apps: sudo apt install libcamera-apps")
        except Exception as e:
            self.simulation_mode = True
            logger.warning(f"Camera initialization failed: {e}. Running in SIMULATION MODE")
    
    def _get_camera_command(self) -> str:
        """Get the camera command to use."""
        if hasattr(self, '_use_libcamera_jpeg') and self._use_libcamera_jpeg:
            return "libcamera-jpeg"
        return "rpicam-jpeg"
    
    def capture_image(self, filepath: Optional[Path] = None) -> Optional[Path]:
        """Capture a still image using rpicam-jpeg.
        
        Args:
            filepath: Path to save image. If None, generates timestamped filename.
            
        Returns:
            Path to saved image or None if capture failed
        """
        if not filepath:
            # Generate timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = DATA_DIR / "photos" / f"capture_{timestamp}.jpg"
        
        # Ensure filepath is a Path object
        filepath = Path(filepath)
        
        # Ensure directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if self.simulation_mode:
            return self._create_simulation_image(filepath)
        
        with self._lock:
            try:
                cmd = self._get_camera_command()
                
                # Build command with arguments
                command = [
                    cmd,
                    "-o", str(filepath),
                    "--width", str(self.resolution[0]),
                    "--height", str(self.resolution[1]),
                    "-n",  # No preview
                    "-t", "1"  # Minimum timeout (1ms, will capture immediately)
                ]
                
                # Add rotation if needed
                if self.rotation == 180:
                    command.extend(["--hflip", "--vflip"])
                elif self.rotation == 90:
                    command.extend(["--rotation", "90"])
                elif self.rotation == 270:
                    command.extend(["--rotation", "270"])
                
                logger.debug(f"Running camera command: {' '.join(command)}")
                
                # Execute capture
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=30  # 30 second timeout
                )
                
                if result.returncode != 0:
                    logger.error(f"Camera capture failed: {result.stderr}")
                    return self._create_simulation_image(filepath)
                
                if filepath.exists():
                    logger.info(f"Image captured: {filepath}")
                    
                    # Update latest snapshot
                    self._update_latest_snapshot(filepath)
                    
                    return filepath
                else:
                    logger.error("Capture succeeded but file not found")
                    return None
                    
            except subprocess.TimeoutExpired:
                logger.error("Camera capture timed out")
                return self._create_simulation_image(filepath)
            except Exception as e:
                logger.error(f"Error capturing image: {e}")
                return self._create_simulation_image(filepath)
    
    def _update_latest_snapshot(self, source_path: Path):
        """Update the latest snapshot file for live feed.
        
        Args:
            source_path: Path to the source image
        """
        try:
            self.latest_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, self.latest_snapshot_path)
        except Exception as e:
            logger.warning(f"Failed to update latest snapshot: {e}")
    
    def _create_simulation_image(self, filepath: Path) -> Optional[Path]:
        """Create a simulation/placeholder image.
        
        Args:
            filepath: Path to save the image
            
        Returns:
            Path to saved image or None if failed
        """
        logger.info(f"[SIMULATION] Creating placeholder image at {filepath}")
        try:
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', self.resolution, color=(73, 109, 137))
            d = ImageDraw.Draw(img)
            
            # Add text
            text = f"Simulation Mode\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nCamera not available"
            
            # Try to use a larger font
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            except:
                font = ImageFont.load_default()
            
            # Calculate text position (center)
            bbox = d.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (self.resolution[0] - text_width) // 2
            y = (self.resolution[1] - text_height) // 2
            
            d.text((x, y), text, fill=(255, 255, 255), font=font, align="center")
            
            # Add border
            d.rectangle([10, 10, self.resolution[0]-10, self.resolution[1]-10], 
                       outline=(255, 165, 0), width=5)
            
            img.save(filepath, quality=90)
            return filepath
        except ImportError:
            # If PIL not available, just create empty file
            logger.warning("PIL not available, creating empty placeholder")
            filepath.touch()
            return filepath
        except Exception as e:
            logger.error(f"Failed to create simulation image: {e}")
            return None
    
    def capture_to_stream(self) -> Optional[bytes]:
        """Capture image to bytes (for streaming/live feed).
        
        Returns:
            Image as bytes or None if capture failed
        """
        # For live feed, capture to temporary file and read bytes
        import tempfile
        
        if self.simulation_mode:
            return self._create_simulation_stream()
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            captured = self.capture_image(tmp_path)
            if captured and captured.exists():
                with open(captured, 'rb') as f:
                    return f.read()
            return None
        finally:
            # Clean up temp file
            try:
                tmp_path.unlink()
            except:
                pass
    
    def _create_simulation_stream(self) -> Optional[bytes]:
        """Create simulation image as bytes.
        
        Returns:
            Image bytes or None if failed
        """
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
    
    def get_latest_snapshot(self) -> Optional[Path]:
        """Get path to the latest snapshot for live feed.
        
        Returns:
            Path to latest snapshot or None if not available
        """
        if self.latest_snapshot_path.exists():
            return self.latest_snapshot_path
        return None
    
    def capture_for_live_feed(self) -> Optional[Path]:
        """Capture a new image for the live feed.
        
        Returns:
            Path to the captured image
        """
        return self.capture_image(self.latest_snapshot_path)
    
    def start_preview(self):
        """Start camera preview (not supported with rpicam-jpeg)."""
        logger.info("Preview not supported with rpicam-jpeg command")
    
    def stop_preview(self):
        """Stop camera preview."""
        pass
    
    def set_resolution(self, width: int, height: int):
        """Change camera resolution.
        
        Args:
            width: Image width in pixels
            height: Image height in pixels
        """
        self.resolution = (width, height)
        logger.info(f"Resolution changed to {width}x{height}")
    
    def cleanup(self):
        """Clean up camera resources."""
        # No persistent resources with subprocess approach
        logger.info("Camera controller cleaned up")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
