# 🌱 Grow Tent Automation System

A production-ready Raspberry Pi grow tent automation system with comprehensive monitoring, control, AI-powered analysis, and external server synchronization.

## ✨ Features

### Core Functionality
- **Real-time Monitoring**: BME680 environmental sensor (temperature, humidity, pressure, air quality)
- **Device Control**: 9-channel relay control for lights, fans, pumps, and climate devices
- **Automation Engine**: Intelligent scheduling and threshold-based control
- **Web Interface**: Modern, responsive dashboard accessible on your local network
- **Telegram Bot**: Remote monitoring and control via Telegram commands
- **Data Logging**: SQLite database with historical data and analytics

### Advanced Features
- **Project Management**: Organize grows by project with start/end dates and status tracking
- **Project-Integrated Time-lapse**: Automatic capture per project, resumes after power cuts
- **Grow Diary**: Document your grow with text entries and photos
- **AI Photo Analysis**: Daily OpenAI Vision-powered plant health analysis
- **External Server Sync**: Mirror data to your own server for backup/blogging
- **Background Task Scheduler**: APScheduler-based scheduled tasks
- **Live Camera Feed**: Real-time view of your grow tent

### Version 2.0 Enhancements
- **YAML Configuration**: Easy-to-edit `settings.yaml` and `secrets.yaml` files
- **Web-Based Settings**: Configure everything through the UI (no JSON editing)
- **Service Stability**: Auto-restart, watchdog, improved error handling
- **Rotating Logs**: Log rotation to prevent disk space issues
- **Health Endpoints**: Comprehensive `/api/health` for monitoring

## 📋 Hardware Requirements

### Required Components
- Raspberry Pi 4 Model B (4GB+ recommended)
- 9-Channel Relay HAT (active LOW logic)
- BME680 Environmental Sensor (I²C)
- Raspberry Pi HQ Camera (or compatible camera module)
- MicroSD card (32GB+ recommended)
- 5V power supply for Raspberry Pi

### Camera Requirements
- **libcamera-apps** must be installed for camera functionality
- Uses `rpicam-jpeg` command for image capture
- Install with: `sudo apt install libcamera-apps`

### GPIO Pin Assignments (BCM Numbering) - 9 Relays

| Relay | GPIO Pin | Physical Pin | Device |
|-------|----------|--------------|--------|
| 1 | GPIO 5 | Pin 29 | Lights |
| 2 | GPIO 6 | Pin 31 | Air Pump |
| 3 | GPIO 13 | Pin 33 | Nutrient Pump |
| 4 | GPIO 16 | Pin 36 | Circulatory Fan 1 |
| 5 | GPIO 19 | Pin 35 | Circulatory Fan 2 |
| 6 | GPIO 20 | Pin 38 | Exhaust Fan |
| 7 | GPIO 21 | Pin 40 | Humidifier |
| 8 | GPIO 23 | Pin 16 | Heater |
| 9 | GPIO 24 | Pin 18 | Dehumidifier |

## 🚀 Quick Start

### 1. Clone and Setup
```bash
cd /home/pi
git clone https://github.com/your-repo/grow-tent-automation.git
cd grow_tent_automation
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Secrets
```bash
cp config/secrets.yaml.example config/secrets.yaml
nano config/secrets.yaml
# Add your Telegram bot token, OpenAI API key, etc.
```

### 4. Configure Settings (Optional)
```bash
nano config/settings.yaml
# Adjust GPIO pins, intervals, thresholds, etc.
```

### 5. Run the System
```bash
python backend/main.py
```

Access the web interface at `http://your-pi-ip:8000`

### 6. Install as Service (Recommended)
```bash
# Edit the service file to match your paths
sudo cp systemd/grow-tent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable grow-tent
sudo systemctl start grow-tent
```

## 📁 Project Structure

```
grow_tent_automation/
├── backend/
│   ├── api/                    # FastAPI endpoints
│   │   ├── projects.py         # Project management
│   │   ├── sensors.py          # Sensor data
│   │   ├── devices.py          # Device control
│   │   ├── timelapse.py        # Time-lapse management
│   │   ├── analysis.py         # AI analysis endpoints
│   │   ├── sync.py             # External sync endpoints
│   │   └── system_settings.py  # Configuration endpoints
│   ├── analysis/
│   │   └── ai_analyzer.py      # OpenAI Vision integration
│   ├── automation/
│   │   ├── engine.py           # Main automation loop
│   │   └── scheduler.py        # Device scheduling logic
│   ├── hardware/
│   │   ├── relay.py            # Relay control
│   │   ├── sensor.py           # BME680 sensor
│   │   └── camera.py           # Camera control
│   ├── telegram_bot/
│   │   └── bot.py              # Telegram bot
│   ├── config.py               # Configuration loader
│   ├── database.py             # SQLite database
│   ├── external_sync.py        # External server sync
│   ├── task_scheduler.py       # APScheduler integration
│   └── main.py                 # FastAPI application
├── config/
│   ├── settings.yaml           # Non-sensitive settings
│   ├── settings.yaml.example   # Settings template
│   ├── secrets.yaml            # Sensitive data (not in git)
│   └── secrets.yaml.example    # Secrets template
├── frontend/
│   ├── index.html              # Main HTML
│   ├── css/                    # Stylesheets
│   └── js/                     # JavaScript
├── data/                       # Runtime data (not in git)
│   ├── database.db             # SQLite database
│   ├── photos/                 # Captured photos
│   ├── projects/               # Project-specific data
│   └── videos/                 # Generated time-lapses
├── logs/                       # Log files (not in git)
├── systemd/
│   └── grow-tent.service       # Systemd service file
├── requirements.txt
├── README.md
├── CONFIGURATION.md            # Configuration guide
├── API.md                      # External API documentation
└── QUICKSTART.md               # Quick setup guide
```

## 🔧 Configuration

See [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration options.

### Quick Configuration Overview

**Non-sensitive settings** (`config/settings.yaml`):
- GPIO pin assignments
- Sensor intervals
- Time-lapse settings
- Alert thresholds
- External sync settings
- AI analysis settings

**Sensitive data** (`config/secrets.yaml`):
- Telegram bot token and chat ID
- OpenAI API key
- External server URL and credentials

## 🌐 External Server Sync

The system can sync data to your own server for:
- Photo backups
- Sensor data logging
- Project information
- AI analysis reports

See [API.md](API.md) for the API specification your server should implement.

## 🤖 AI Plant Analysis

The system uses OpenAI's GPT-4 Vision to analyze plant photos daily:
- Health score (1-10)
- Growth stage assessment
- Issue detection (deficiencies, pests, diseases)
- Recommendations

Configure your OpenAI API key in `config/secrets.yaml` and enable in settings.

## 📱 Telegram Commands

- `/start` - Welcome message
- `/status` - Current sensor readings
- `/photo` - Capture and send photo
- `/lights on/off` - Control lights
- `/devices` - Show device states
- `/sync` - Trigger external sync
- `/analyze` - Run AI analysis now
- `/help` - Show all commands

## 🔄 Service Management

```bash
# Start service
sudo systemctl start grow-tent

# Stop service
sudo systemctl stop grow-tent

# Restart service
sudo systemctl restart grow-tent

# Check status
sudo systemctl status grow-tent

# View logs
sudo journalctl -u grow-tent -f
```

## 🛠 Troubleshooting

### Service won't start
1. Check logs: `sudo journalctl -u grow-tent -e`
2. Verify paths in service file
3. Check Python virtual environment
4. Ensure hardware is connected

### Sensor not reading
1. Check I2C: `sudo i2cdetect -y 1`
2. Verify BME680 address (0x76 or 0x77)
3. Check wiring connections

### Camera not working
1. Test with: `rpicam-jpeg -o test.jpg`
2. Install libcamera-apps if missing
3. Check camera cable connection

### External sync failing
1. Test connection in UI: Settings → External Sync → Test Connection
2. Check server URL and authentication
3. Review sync logs: `/api/sync/logs`

### AI analysis not working
1. Verify OpenAI API key in secrets.yaml
2. Check API key has GPT-4 Vision access
3. Ensure a photo is available

## 🔒 Security Notes

1. Never commit `config/secrets.yaml` to git
2. Use HTTPS for external server sync
3. Change default settings for production
4. Restrict network access as needed
5. Regularly update dependencies

## 📄 License

MIT License - See LICENSE file for details.

## 🙏 Contributing

Contributions welcome! Please read CONTRIBUTING.md before submitting PRs.

## 📚 Additional Documentation

- [CONFIGURATION.md](CONFIGURATION.md) - Detailed configuration guide
- [API.md](API.md) - External server API specification
- [QUICKSTART.md](QUICKSTART.md) - Quick setup guide
