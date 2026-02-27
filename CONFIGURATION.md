# Configuration Guide

This guide explains all configuration options for the Grow Tent Automation System.

## Configuration Files

The system uses two YAML configuration files:

### 1. `config/settings.yaml` - Non-sensitive Settings
This file contains all general settings and can be safely committed to git.

### 2. `config/secrets.yaml` - Sensitive Data
This file contains API keys, tokens, and passwords. **NEVER commit this file to git.**

Copy the example file to get started:
```bash
cp config/secrets.yaml.example config/secrets.yaml
```

---

## Settings Configuration (`config/settings.yaml`)

### GPIO Pin Configuration
```yaml
gpio_pins:
  lights: 5           # GPIO pin for grow lights
  air_pump: 6         # Air pump for oxygenation
  nutrient_pump: 13   # Nutrient solution pump
  circulatory_fan_1: 16
  circulatory_fan_2: 19
  exhaust_fan: 20
  humidifier: 21
  heater: 23
  dehumidifier: 24
```

### Sensor Settings
```yaml
sensor:
  i2c_address: 0x76     # BME680 I2C address (try 0x77 if not working)
  read_interval: 30     # Seconds between sensor readings
  log_interval: 60      # Seconds between database logs
```

### Camera Settings
```yaml
camera:
  resolution:
    width: 1920
    height: 1080
  rotation: 0           # 0, 90, 180, or 270 degrees
```

### Time-lapse Settings
```yaml
timelapse:
  default_interval: 300          # Capture every 5 minutes (seconds)
  default_fps: 30                # Frames per second for generated video
  auto_start_on_project: true    # Auto-start timelapse when project created
```

**Smart Time-lapse:**
When creating a new project, you can enable "Smart Mode" which only captures images when the lights are ON. This saves storage space by skipping captures during dark periods.

**UI Features:**
- Visual interval slider (1 minute to 1 hour)
- Toggle switches for enabling/disabling features
- Time picker for scheduling

### Alert Thresholds
```yaml
alerts:
  enabled: true
  temperature:
    min: 15.0    # Alert if below this (°C)
    max: 32.0    # Alert if above this (°C)
  humidity:
    min: 40.0    # Alert if below this (%)
    max: 80.0    # Alert if above this (%)
  notification_interval: 300    # Seconds between repeated alerts
```

### External Server Sync Settings
```yaml
external_sync:
  enabled: false              # Enable/disable sync
  sync_interval: 300          # Sync every 5 minutes (seconds)
  sync_photos: true           # Sync latest photos
  sync_sensor_data: true      # Sync sensor readings
  sync_project_info: true     # Sync project information
  sync_analysis_reports: true # Sync AI analysis reports
  retry_attempts: 3           # Retry failed syncs
  retry_delay: 30             # Seconds between retries
  endpoints:
    photos: "/photos/upload"
    sensor_data: "/sensor-data"
    project_info: "/projects"
    analysis_reports: "/reports"
```

### AI Analysis Settings
```yaml
ai_analysis:
  enabled: false                   # Enable/disable AI analysis
  daily_schedule_time: "12:00"     # Time to run daily analysis (24h format)
  analysis_prompt: |
    Analyze this cannabis/plant photo...
  send_to_telegram: true           # Send results to Telegram
  send_to_external_server: true    # Sync to external server
```

### Scheduler Settings
```yaml
scheduler:
  enabled: true
  daily_report_time: "08:00"    # Time to generate daily report
  persist_state: true           # Save state for restart recovery
```

### Logging Settings
```yaml
logging:
  level: "INFO"                 # DEBUG, INFO, WARNING, ERROR, CRITICAL
  max_file_size: 10485760       # 10 MB per log file
  backup_count: 5               # Keep 5 backup log files
  log_to_console: true
  log_to_file: true
```

---

## Secrets Configuration (`config/secrets.yaml`)

### Telegram Bot
```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"    # Get from @BotFather
  chat_id: "YOUR_CHAT_ID"        # Your chat ID
```

To get your Telegram credentials:
1. Message @BotFather to create a bot and get the token
2. Message @userinfobot to get your chat ID

### OpenRouter API (for AI Plant Analysis)
```yaml
openrouter:
  api_key: "YOUR_API_KEY"                    # Get from openrouter.ai
  model: "anthropic/claude-3.5-sonnet"       # Vision-capable model
```

**Available Vision Models:**
- `anthropic/claude-3.5-sonnet` - Recommended, excellent accuracy
- `anthropic/claude-3-opus` - Most capable, higher cost
- `anthropic/claude-3-haiku` - Fast and affordable
- `openai/gpt-4o` - OpenAI's latest vision model
- `openai/gpt-4-vision-preview` - GPT-4 Vision
- `google/gemini-pro-vision` - Google's vision model
- `meta-llama/llama-3.2-90b-vision-instruct` - Llama 3.2 Vision

### External Server
```yaml
external_server:
  enabled: false
  url: "https://your-server.com/api"
  auth_type: "api_key"           # api_key, bearer, basic, none
  api_key: "YOUR_API_KEY"        # For api_key auth
  bearer_token: "YOUR_TOKEN"     # For bearer auth
  basic_username: ""             # For basic auth
  basic_password: ""             # For basic auth
```

---

## Web-Based Configuration

You can configure most settings through the enhanced Web UI:

### System Settings Page
1. Navigate to **System Settings** in the sidebar
2. Use the tabbed interface for different setting categories
3. Edit settings using the visual controls
4. Click **Save** to apply changes

### Enhanced UI Controls

The settings page features modern, visual controls:

**Toggle Switches:**
- Enable/disable features with a single click
- Visual feedback for on/off states
- Used for: Alerts, Time-lapse, Telegram notifications, etc.

**Slider Controls:**
- Temperature range: Slide to set min/max thresholds
- Humidity range: Slide to set min/max thresholds
- Time-lapse interval: Visual slider from 1 min to 1 hour
- Shows current value with colored indicators

**Time Pickers:**
- Native HTML5 time input for schedule settings
- 24-hour format for daily analysis time
- Easy selection with hour/minute controls

**Model Selector:**
- Dropdown menu for AI vision models
- Shows model name and description
- Updates dynamically from OpenRouter

### Project Creation Wizard

When creating a new project:
1. Enter project name and notes
2. **Time-lapse Options:**
   - Toggle to enable/disable time-lapse
   - Interval selector (5, 10, 15, 30 min, 1 hour)
   - Smart mode toggle (only capture when lights ON)
3. Click Create to start your grow

---

## Environment Variables (Alternative)

You can also use environment variables for secrets:

```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export OPENAI_API_KEY="your_api_key"
```

The system will fall back to environment variables if not found in `secrets.yaml`.

---

## Configuration Precedence

1. `secrets.yaml` (highest priority for sensitive data)
2. Environment variables
3. `settings.yaml`
4. Default values in code

---

## Reload Configuration

After editing YAML files, reload without restart:

```bash
# Via API
curl -X POST http://localhost:8000/api/system-settings/reload

# Or restart the service
sudo systemctl restart grow-tent
```

---

## Security Best Practices

1. **Never commit `secrets.yaml` to git**
2. Set restrictive file permissions: `chmod 600 config/secrets.yaml`
3. Use strong, unique API keys
4. Regularly rotate sensitive credentials
5. Use HTTPS for external server sync
