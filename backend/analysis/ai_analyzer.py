"""AI Photo Analysis Module using OpenAI Vision API.

Provides automated plant health analysis using GPT-4 Vision.
"""
import logging
import base64
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class AIAnalysisError(Exception):
    """Custom exception for AI analysis errors."""
    pass


class AIAnalyzer:
    """Handles AI-powered plant photo analysis using OpenAI Vision API."""
    
    def __init__(self, config: Dict[str, Any], secrets: Dict[str, Any]):
        """Initialize the AI analyzer.
        
        Args:
            config: Settings configuration dictionary
            secrets: Secrets configuration dictionary
        """
        self.config = config.get('ai_analysis', {})
        self.secrets = secrets.get('openai', {})
        
        self.api_key = self.secrets.get('api_key', '')
        self.model = self.secrets.get('model', 'gpt-4o')
        self.enabled = bool(self.api_key) and self.config.get('enabled', False)
        
        self.default_prompt = self.config.get('analysis_prompt', '''
Analyze this cannabis/plant photo. Assess:
1. Overall plant health (score 1-10)
2. Growth stage (seedling, vegetative, flowering, etc.)
3. Any visible issues (nutrient deficiency, pests, diseases, stress signs)
4. Color and appearance assessment
5. Recommendations for improvement

Provide a structured response with these sections.
''')
        
        self.send_to_telegram = self.config.get('send_to_telegram', True)
        self.send_to_external = self.config.get('send_to_external_server', True)
        
        logger.info(f"AI Analyzer initialized. Enabled: {self.enabled}")
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded image string
        """
        path = Path(image_path)
        if not path.exists():
            raise AIAnalysisError(f"Image not found: {image_path}")
        
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def _get_image_media_type(self, image_path: str) -> str:
        """Get the media type for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Media type string (e.g., 'image/jpeg')
        """
        path = Path(image_path)
        ext = path.suffix.lower()
        media_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return media_types.get(ext, 'image/jpeg')
    
    def _parse_health_score(self, analysis_text: str) -> Optional[int]:
        """Extract health score from analysis text.
        
        Args:
            analysis_text: The analysis text from OpenAI
            
        Returns:
            Health score (1-10) or None if not found
        """
        # Look for patterns like "health: 7", "score: 8/10", "7/10", etc.
        patterns = [
            r'health[:\s]+(?:score)?[:\s]*([0-9]+)(?:/10)?',
            r'score[:\s]*([0-9]+)(?:/10)?',
            r'([0-9]+)/10',
            r'health rating[:\s]*([0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis_text.lower())
            if match:
                score = int(match.group(1))
                if 1 <= score <= 10:
                    return score
        
        return None
    
    def _parse_recommendations(self, analysis_text: str) -> str:
        """Extract recommendations section from analysis text.
        
        Args:
            analysis_text: The analysis text from OpenAI
            
        Returns:
            Recommendations text
        """
        # Try to find recommendations section
        patterns = [
            r'(?:recommendations?|suggestions?)[:\s]*(.+?)(?=\n\n|\Z)',
            r'(?:5\.\s*)?recommendations?[:\s]*(.+?)(?=\n\n|\Z)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, analysis_text.lower(), re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def analyze_photo(self, image_path: str, 
                      custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Analyze a plant photo using OpenAI Vision API.
        
        Args:
            image_path: Path to the image file
            custom_prompt: Custom analysis prompt (optional)
            
        Returns:
            Dictionary containing analysis results
        """
        if not self.enabled:
            raise AIAnalysisError("AI analysis is not enabled or API key not configured")
        
        if not self.api_key:
            raise AIAnalysisError("OpenAI API key not configured")
        
        try:
            # Import openai here to avoid import errors if not installed
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            # Encode image
            base64_image = self._encode_image(image_path)
            media_type = self._get_image_media_type(image_path)
            
            # Use custom prompt or default
            prompt = custom_prompt or self.default_prompt
            
            # Make API request
            logger.info(f"Sending image for analysis: {image_path}")
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500
            )
            
            # Extract analysis text
            analysis_text = response.choices[0].message.content
            
            # Parse health score and recommendations
            health_score = self._parse_health_score(analysis_text)
            recommendations = self._parse_recommendations(analysis_text)
            
            result = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'photo_path': str(image_path),
                'analysis_text': analysis_text,
                'health_score': health_score,
                'recommendations': recommendations,
                'model': self.model,
                'tokens_used': response.usage.total_tokens if response.usage else None
            }
            
            logger.info(f"Analysis completed. Health score: {health_score}")
            return result
            
        except openai.APIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            logger.error(error_msg)
            raise AIAnalysisError(error_msg)
            
        except openai.RateLimitError:
            error_msg = "OpenAI rate limit exceeded. Please try again later."
            logger.error(error_msg)
            raise AIAnalysisError(error_msg)
            
        except Exception as e:
            error_msg = f"Analysis failed: {str(e)}"
            logger.error(error_msg)
            raise AIAnalysisError(error_msg)
    
    def format_telegram_message(self, analysis: Dict[str, Any], 
                                project_name: str = "") -> str:
        """Format analysis result for Telegram notification.
        
        Args:
            analysis: Analysis result dictionary
            project_name: Name of the project
            
        Returns:
            Formatted message string
        """
        health_score = analysis.get('health_score')
        score_emoji = self._get_score_emoji(health_score)
        
        message = f"🌿 *Daily Plant Analysis*\n\n"
        
        if project_name:
            message += f"📁 Project: {project_name}\n"
        
        message += f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        
        if health_score:
            message += f"{score_emoji} Health Score: {health_score}/10\n\n"
        
        # Truncate analysis text for Telegram (max ~4000 chars)
        analysis_text = analysis.get('analysis_text', '')
        if len(analysis_text) > 3000:
            analysis_text = analysis_text[:3000] + "...\n\n[Truncated for Telegram]"
        
        message += f"📋 *Analysis:*\n{analysis_text}"
        
        return message
    
    def _get_score_emoji(self, score: Optional[int]) -> str:
        """Get emoji based on health score."""
        if score is None:
            return "❓"
        if score >= 8:
            return "🌟"
        if score >= 6:
            return "✅"
        if score >= 4:
            return "⚠️"
        return "🚨"
    
    def create_daily_report(self, analyses: list, 
                            project_name: str = "") -> str:
        """Create a daily summary report from multiple analyses.
        
        Args:
            analyses: List of analysis dictionaries
            project_name: Name of the project
            
        Returns:
            Formatted daily report
        """
        if not analyses:
            return "No analyses available for today."
        
        report = f"# Daily Plant Health Report\n\n"
        report += f"**Date:** {datetime.now().strftime('%Y-%m-%d')}\n"
        
        if project_name:
            report += f"**Project:** {project_name}\n\n"
        
        # Calculate average health score
        scores = [a.get('health_score') for a in analyses if a.get('health_score')]
        if scores:
            avg_score = sum(scores) / len(scores)
            report += f"**Average Health Score:** {avg_score:.1f}/10\n\n"
        
        report += "## Analysis Results\n\n"
        
        for i, analysis in enumerate(analyses, 1):
            timestamp = analysis.get('timestamp', 'Unknown')
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp).strftime('%H:%M')
                except:
                    pass
            
            report += f"### Analysis #{i} ({timestamp})\n\n"
            report += f"**Health Score:** {analysis.get('health_score', 'N/A')}/10\n\n"
            report += f"{analysis.get('analysis_text', 'No analysis available')}\n\n"
            report += "---\n\n"
        
        return report


# Singleton instance
_ai_analyzer: Optional[AIAnalyzer] = None


def get_ai_analyzer() -> Optional[AIAnalyzer]:
    """Get the global AI analyzer instance."""
    return _ai_analyzer


def init_ai_analyzer(config: Dict[str, Any], secrets: Dict[str, Any]) -> AIAnalyzer:
    """Initialize the global AI analyzer instance.
    
    Args:
        config: Settings configuration
        secrets: Secrets configuration
        
    Returns:
        Initialized AIAnalyzer instance
    """
    global _ai_analyzer
    _ai_analyzer = AIAnalyzer(config, secrets)
    return _ai_analyzer
