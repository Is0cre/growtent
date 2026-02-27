"""AI Photo Analysis Module using OpenRouter API.

Provides automated plant health analysis using various vision models via OpenRouter.
OpenRouter provides access to multiple AI models including GPT-4, Claude, and more.
"""
import logging
import base64
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# OpenRouter configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Popular vision models available on OpenRouter
OPENROUTER_VISION_MODELS = {
    "anthropic/claude-3.5-sonnet": "Claude 3.5 Sonnet (recommended)",
    "anthropic/claude-3-opus": "Claude 3 Opus",
    "anthropic/claude-3-haiku": "Claude 3 Haiku (fast)",
    "openai/gpt-4o": "GPT-4o",
    "openai/gpt-4-vision-preview": "GPT-4 Vision",
    "google/gemini-pro-vision": "Gemini Pro Vision",
    "meta-llama/llama-3.2-90b-vision-instruct": "Llama 3.2 90B Vision",
}


class AIAnalysisError(Exception):
    """Custom exception for AI analysis errors."""
    pass


class AIAnalyzer:
    """Handles AI-powered plant photo analysis using OpenRouter API."""
    
    def __init__(self, config: Dict[str, Any], secrets: Dict[str, Any]):
        """Initialize the AI analyzer.
        
        Args:
            config: Settings configuration dictionary
            secrets: Secrets configuration dictionary
        """
        self.config = config.get('ai_analysis', {})
        self.secrets = secrets.get('openrouter', {})
        
        # Support legacy openai config for backwards compatibility
        if not self.secrets:
            self.secrets = secrets.get('openai', {})
        
        self.api_key = self.secrets.get('api_key', '')
        self.model = self.secrets.get('model', 'anthropic/claude-3.5-sonnet')
        self.enabled = bool(self.api_key) and self.config.get('enabled', False)
        
        # Site info for OpenRouter headers
        self.site_url = self.config.get('site_url', 'https://grow-tent-automation.local')
        self.site_name = self.config.get('site_name', 'Grow Tent Automation')
        
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
        
        logger.info(f"AI Analyzer initialized (OpenRouter). Enabled: {self.enabled}, Model: {self.model}")
    
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
            analysis_text: The analysis text from AI
            
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
            analysis_text: The analysis text from AI
            
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
        """Analyze a plant photo using OpenRouter API.
        
        Args:
            image_path: Path to the image file
            custom_prompt: Custom analysis prompt (optional)
            
        Returns:
            Dictionary containing analysis results
        """
        if not self.enabled:
            raise AIAnalysisError("AI analysis is not enabled or API key not configured")
        
        if not self.api_key:
            raise AIAnalysisError("OpenRouter API key not configured")
        
        try:
            # Import openai here to avoid import errors if not installed
            import openai
            
            # Configure OpenRouter client
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=OPENROUTER_BASE_URL,
                default_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.site_name
                }
            )
            
            # Encode image
            base64_image = self._encode_image(image_path)
            media_type = self._get_image_media_type(image_path)
            
            # Use custom prompt or default
            prompt = custom_prompt or self.default_prompt
            
            # Make API request
            logger.info(f"Sending image for analysis via OpenRouter: {image_path} (model: {self.model})")
            
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
            error_msg = f"OpenRouter API error: {str(e)}"
            logger.error(error_msg)
            raise AIAnalysisError(error_msg)
            
        except openai.RateLimitError:
            error_msg = "OpenRouter rate limit exceeded. Please try again later."
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
        message += f"🤖 Model: {analysis.get('model', 'N/A')}\n"
        
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
    
    def get_available_models(self) -> Dict[str, str]:
        """Get dictionary of available vision models.
        
        Returns:
            Dictionary of model_id: display_name
        """
        return OPENROUTER_VISION_MODELS.copy()


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
