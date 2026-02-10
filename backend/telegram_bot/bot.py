"""Telegram bot for remote monitoring and control.

Provides commands:
- /status - Get current sensor readings and device states
- /devices - List all devices and their states
- /on <device> - Turn device on
- /off <device> - Turn device off
- /alerts - View current alert settings
- /photo - Get current camera snapshot
"""
import logging
import asyncio
from typing import Optional
from pathlib import Path

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("python-telegram-bot not available")

from backend.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GPIO_PINS

logger = logging.getLogger(__name__)

class TelegramBot:
    """Telegram bot for grow tent automation."""
    
    def __init__(self, automation_engine):
        """Initialize Telegram bot.
        
        Args:
            automation_engine: Reference to AutomationEngine instance
        """
        self.engine = automation_engine
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.application: Optional[Application] = None
        self.running = False
        
        if not TELEGRAM_AVAILABLE:
            logger.warning("Telegram bot disabled - library not available")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "🌱 *Grow Tent Automation Bot*\n\n"
            "Available commands:\n"
            "/status - Current sensor readings and device states\n"
            "/devices - List all devices\n"
            "/on <device> - Turn device on\n"
            "/off <device> - Turn device off\n"
            "/alerts - View alert settings\n"
            "/photo - Get camera snapshot\n\n"
            "Device names: " + ", ".join([d for d in GPIO_PINS.keys() if d != 'unused']),
            parse_mode='Markdown'
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - show sensor readings and device states."""
        try:
            # Get sensor data
            sensor_data = self.engine.get_sensor_data()
            
            # Get device states
            device_states = self.engine.get_device_states()
            
            # Format message
            message = "📊 *Current Status*\n\n"
            
            if sensor_data:
                message += "🌡️ *Environment*\n"
                message += f"Temperature: {sensor_data['temperature']:.1f}°C\n"
                message += f"Humidity: {sensor_data['humidity']:.1f}%\n"
                message += f"Pressure: {sensor_data['pressure']:.1f} hPa\n"
                message += f"Gas: {sensor_data['gas_resistance']:.0f} Ω\n\n"
            else:
                message += "⚠️ No sensor data available\n\n"
            
            message += "🔌 *Devices*\n"
            for device, state in device_states.items():
                if device != 'unused':
                    status = "✅ ON" if state else "❌ OFF"
                    device_display = device.replace('_', ' ').title()
                    message += f"{device_display}: {status}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text(f"Error getting status: {e}")
    
    async def devices_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /devices command - list all devices."""
        try:
            device_states = self.engine.get_device_states()
            
            message = "🔌 *Device List*\n\n"
            for device, state in device_states.items():
                if device != 'unused':
                    status = "✅ ON" if state else "❌ OFF"
                    device_display = device.replace('_', ' ').title()
                    message += f"• {device_display}: {status}\n"
            
            message += "\nUse /on <device> or /off <device> to control"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in devices command: {e}")
            await update.message.reply_text(f"Error getting devices: {e}")
    
    async def on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /on command - turn device on."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "Usage: /on <device>\n"
                    "Available devices: " + ", ".join([d for d in GPIO_PINS.keys() if d != 'unused'])
                )
                return
            
            device_name = context.args[0].lower()
            
            if device_name not in GPIO_PINS or device_name == 'unused':
                await update.message.reply_text(f"Unknown device: {device_name}")
                return
            
            success = self.engine.turn_device_on(device_name)
            
            if success:
                device_display = device_name.replace('_', ' ').title()
                await update.message.reply_text(f"✅ Turned ON {device_display}")
            else:
                await update.message.reply_text(f"❌ Failed to turn on {device_name}")
            
        except Exception as e:
            logger.error(f"Error in on command: {e}")
            await update.message.reply_text(f"Error: {e}")
    
    async def off_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /off command - turn device off."""
        try:
            if not context.args:
                await update.message.reply_text(
                    "Usage: /off <device>\n"
                    "Available devices: " + ", ".join([d for d in GPIO_PINS.keys() if d != 'unused'])
                )
                return
            
            device_name = context.args[0].lower()
            
            if device_name not in GPIO_PINS or device_name == 'unused':
                await update.message.reply_text(f"Unknown device: {device_name}")
                return
            
            success = self.engine.turn_device_off(device_name)
            
            if success:
                device_display = device_name.replace('_', ' ').title()
                await update.message.reply_text(f"❌ Turned OFF {device_display}")
            else:
                await update.message.reply_text(f"❌ Failed to turn off {device_name}")
            
        except Exception as e:
            logger.error(f"Error in off command: {e}")
            await update.message.reply_text(f"Error: {e}")
    
    async def alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alerts command - show alert settings."""
        try:
            from backend.database import db
            alert_settings = db.get_alert_settings()
            
            if not alert_settings:
                await update.message.reply_text("No alert settings configured")
                return
            
            enabled = "✅ Enabled" if alert_settings.get('enabled') else "❌ Disabled"
            
            message = f"🔔 *Alert Settings*\n\n"
            message += f"Status: {enabled}\n\n"
            message += f"Temperature:\n"
            message += f"  Min: {alert_settings.get('temp_min', 'N/A')}°C\n"
            message += f"  Max: {alert_settings.get('temp_max', 'N/A')}°C\n\n"
            message += f"Humidity:\n"
            message += f"  Min: {alert_settings.get('humidity_min', 'N/A')}%\n"
            message += f"  Max: {alert_settings.get('humidity_max', 'N/A')}%\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in alerts command: {e}")
            await update.message.reply_text(f"Error: {e}")
    
    async def photo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /photo command - capture and send photo."""
        try:
            await update.message.reply_text("📸 Capturing photo...")
            
            photo_path = self.engine.capture_photo()
            
            if photo_path and Path(photo_path).exists():
                with open(photo_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=f"📷 Grow tent snapshot"
                    )
            else:
                await update.message.reply_text("❌ Failed to capture photo")
            
        except Exception as e:
            logger.error(f"Error in photo command: {e}")
            await update.message.reply_text(f"Error: {e}")
    
    async def send_message(self, message: str):
        """Send a message to the configured chat.
        
        Args:
            message: Message to send
        """
        try:
            if self.application and self.running:
                await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
    
    async def send_alert(self, alert_message: str):
        """Send an alert message.
        
        Args:
            alert_message: Alert message to send
        """
        message = f"⚠️ *ALERT*\n\n{alert_message}"
        await self.send_message(message)
    
    def start(self):
        """Start the Telegram bot."""
        if not TELEGRAM_AVAILABLE:
            logger.warning("Cannot start Telegram bot - library not available")
            return
        
        if not self.bot_token:
            logger.warning("Cannot start Telegram bot - no token configured")
            return
        
        try:
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("devices", self.devices_command))
            self.application.add_handler(CommandHandler("on", self.on_command))
            self.application.add_handler(CommandHandler("off", self.off_command))
            self.application.add_handler(CommandHandler("alerts", self.alerts_command))
            self.application.add_handler(CommandHandler("photo", self.photo_command))
            
            # Start bot in separate thread
            self.running = True
            
            logger.info("Telegram bot started")
            
            # Run bot
            self.application.run_polling()
            
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")
    
    def stop(self):
        """Stop the Telegram bot."""
        self.running = False
        if self.application:
            try:
                logger.info("Stopping Telegram bot...")
                # The polling will stop when the application is shut down
            except Exception as e:
                logger.error(f"Error stopping Telegram bot: {e}")
