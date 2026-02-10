"""Plant health analysis API endpoints."""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import base64
import json

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from backend.config import DATA_DIR

router = APIRouter(prefix="/api/plant-health", tags=["plant-health"])

class HealthAnalysisResponse(BaseModel):
    health_score: float  # 0-100
    issues: list
    recommendations: list
    analysis: str

@router.post("/analyze")
async def analyze_plant_health(image: UploadFile = File(...)):
    """Analyze plant health from an uploaded image."""
    try:
        # Read image
        image_data = await image.read()
        
        # Save image temporarily
        temp_dir = DATA_DIR / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / image.filename
        
        with open(temp_path, 'wb') as f:
            f.write(image_data)
        
        # Perform analysis
        result = await _analyze_image(temp_path, image_data)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-camera")
async def analyze_from_camera():
    """Analyze plant health using current camera snapshot."""
    try:
        from backend.api.camera import automation_engine
        
        if not automation_engine:
            raise HTTPException(status_code=503, detail="Automation engine not available")
        
        # Capture image
        photo_path = automation_engine.capture_photo()
        
        if not photo_path or not Path(photo_path).exists():
            raise HTTPException(status_code=500, detail="Failed to capture image")
        
        # Read image
        with open(photo_path, 'rb') as f:
            image_data = f.read()
        
        # Perform analysis
        result = await _analyze_image(Path(photo_path), image_data)
        
        return {
            "success": True,
            "data": result,
            "image_path": str(Path(photo_path).relative_to(DATA_DIR.parent))
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _analyze_image(image_path: Path, image_data: bytes) -> dict:
    """Analyze plant health from image data.
    
    Uses OpenAI Vision API if available, otherwise uses simple heuristics.
    """
    import os
    
    # Try OpenAI Vision API first
    api_key = os.getenv('OPENAI_API_KEY')
    if OPENAI_AVAILABLE and api_key:
        try:
            return await _analyze_with_openai(image_data)
        except Exception as e:
            print(f"OpenAI analysis failed: {e}")
            # Fall back to simple analysis
    
    # Simple color-based analysis (fallback)
    return _simple_color_analysis(image_path)

async def _analyze_with_openai(image_data: bytes) -> dict:
    """Analyze image using OpenAI Vision API."""
    import os
    
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Encode image to base64
    image_b64 = base64.b64encode(image_data).decode('utf-8')
    
    # Create prompt
    prompt = """
    Analyze this plant image and provide a health assessment in JSON format with:
    - health_score: A number from 0-100 (100 being perfect health)
    - issues: Array of any problems detected (e.g., "yellowing leaves", "nutrient deficiency")
    - recommendations: Array of suggested actions
    - analysis: Brief text description of overall plant health
    
    Focus on:
    - Leaf color and condition
    - Signs of pests or disease
    - Growth patterns
    - Nutrient deficiencies
    - Water stress
    """
    
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=500
    )
    
    # Parse response
    content = response.choices[0].message.content
    
    # Try to extract JSON from response
    try:
        # Look for JSON in the response
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = content[start_idx:end_idx]
            result = json.loads(json_str)
            return result
    except:
        pass
    
    # If JSON parsing failed, create structured response from text
    return {
        "health_score": 75.0,  # Default score
        "issues": ["Unable to perform detailed analysis"],
        "recommendations": ["Visual inspection recommended"],
        "analysis": content
    }

def _simple_color_analysis(image_path: Path) -> dict:
    """Simple color-based health analysis (fallback method)."""
    try:
        from PIL import Image
        import numpy as np
        
        # Load image
        img = Image.open(image_path)
        img = img.convert('RGB')
        
        # Get pixels
        pixels = np.array(img)
        
        # Calculate average color
        avg_color = pixels.mean(axis=(0, 1))
        r, g, b = avg_color
        
        # Simple health heuristics based on color
        health_score = 70.0
        issues = []
        recommendations = []
        
        # Check for green color (healthy plants should be green)
        green_ratio = g / (r + g + b + 1)
        if green_ratio < 0.3:
            health_score -= 20
            issues.append("Low green color - possible chlorosis")
            recommendations.append("Check nitrogen levels")
        elif green_ratio > 0.4:
            health_score += 10
        
        # Check for yellowing (high red, low green)
        if r > g and r > b:
            health_score -= 15
            issues.append("Possible yellowing or nutrient deficiency")
            recommendations.append("Consider adding nutrients")
        
        # Check brightness (pale = unhealthy)
        brightness = (r + g + b) / 3
        if brightness > 200:
            health_score -= 10
            issues.append("Leaves appear pale")
            recommendations.append("Monitor light levels and nutrients")
        
        # Cap health score
        health_score = max(0, min(100, health_score))
        
        if not issues:
            issues = ["No obvious issues detected"]
        if not recommendations:
            recommendations = ["Continue current care routine"]
        
        analysis = f"Based on color analysis: Average green ratio is {green_ratio:.2f}. "
        analysis += f"Health score: {health_score:.1f}/100. "
        if health_score > 80:
            analysis += "Plant appears healthy."
        elif health_score > 60:
            analysis += "Plant shows some signs of stress."
        else:
            analysis += "Plant may need attention."
        
        return {
            "health_score": health_score,
            "issues": issues,
            "recommendations": recommendations,
            "analysis": analysis
        }
        
    except ImportError:
        # PIL not available
        return {
            "health_score": 75.0,
            "issues": ["Image analysis library not available"],
            "recommendations": ["Install Pillow for image analysis: pip install Pillow"],
            "analysis": "Unable to perform automated analysis. Manual inspection recommended."
        }
    except Exception as e:
        return {
            "health_score": 70.0,
            "issues": [f"Analysis error: {str(e)}"],
            "recommendations": ["Manual inspection recommended"],
            "analysis": "Unable to complete automated analysis."
        }
