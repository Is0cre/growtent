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

### OpenAI API
```yaml
openai:
  api_key: "YOUR_API_KEY"        # Get from platform.openai.com
  model: "gpt-4o"                # Vision-capable model
```

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

You can also configure most settings through the Web UI:

1. Navigate to **Settings** in the sidebar
2. Go to **System Settings** tab
3. Edit settings in the user-friendly forms
4. Click **Save** to apply changes

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
