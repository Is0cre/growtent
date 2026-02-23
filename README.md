# 🌱 Grow Tent Automation System

A production-ready Raspberry Pi grow tent automation system with comprehensive monitoring, control, and analysis features.

## ✨ Features

### Core Functionality
- **Real-time Monitoring**: BME680 environmental sensor (temperature, humidity, pressure, air quality)
- **Device Control**: 9-channel relay control for lights, fans, pumps, and climate devices
- **Automation Engine**: Intelligent scheduling and threshold-based control
- **Web Interface**: Modern, responsive dashboard accessible on your local network
- **Telegram Bot**: Remote monitoring and control via Telegram commands
- **Data Logging**: SQLite database with historical data and analytics

### Advanced Features
- **Project Management**: Organize grows by project with start/end dates
- **Grow Diary**: Document your grow with text entries and photos
- **Time-lapse**: Automatic image capture and video generation
- **Plant Health Analysis**: AI-powered plant health assessment from camera images
- **Data Export**: Export sensor data to CSV for analysis
- **Live Camera Feed**: Real-time view of your grow tent

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

### BME680 Sensor Connections (I²C)
- **VCC** → 3.3V (Pin 1 or 17)
- **GND** → GND (Any ground pin)
- **SDA** → GPIO 2 (Pin 3)
- **SCL** → GPIO 3 (Pin 5)

## 🚀 Installation

### 1. Prepare Raspberry Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-pip python3-venv git i2c-tools ffmpeg

# Install camera support (REQUIRED for camera functionality)
sudo apt install -y libcamera-apps

# Enable I²C and Camera
sudo raspi-config
# Navigate to: Interfacing Options → I2C → Enable
# Navigate to: Interfacing Options → Camera → Enable
# Reboot when prompted
```

### 2. Verify Hardware

```bash
# Test I²C devices (should show BME680 at 0x76 or 0x77)
sudo i2cdetect -y 1

# Test camera with rpicam-jpeg
rpicam-jpeg -o test.jpg --width 1920 --height 1080

# List available cameras
libcamera-hello --list-cameras
```

### 3. Clone and Setup

```bash
# Clone repository
cd ~
git clone <repository-url> grow_tent_automation
cd grow_tent_automation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configuration

```bash
# Create environment file
cp .env.example .env
nano .env
```

Edit `.env` with your settings:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
OPENAI_API_KEY=your_openai_key_here  # Optional
```

**Getting Telegram Bot Token:**
1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow instructions
3. Copy the token provided
4. Send a message to your bot
5. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` to get your chat ID

### 5. Test Run

```bash
# Activate virtual environment
source venv/bin/activate

# Run the application
cd backend
python main.py
```

Open your browser and navigate to:
- **Web UI**: `http://raspberry-pi-ip:8000`
- **API Docs**: `http://raspberry-pi-ip:8000/docs`

## 🔧 Systemd Service (Auto-start on Boot)

### 1. Create Service File

```bash
sudo nano /etc/systemd/system/grow-tent.service
```

Paste the following (adjust paths if needed):

```ini
[Unit]
Description=Grow Tent Automation System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/grow_tent_automation
Environment="PATH=/home/pi/grow_tent_automation/venv/bin"
EnvironmentFile=/home/pi/grow_tent_automation/.env
ExecStart=/home/pi/grow_tent_automation/venv/bin/python backend/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable grow-tent.service

# Start service now
sudo systemctl start grow-tent.service

# Check status
sudo systemctl status grow-tent.service

# View logs
sudo journalctl -u grow-tent.service -f
```

### 3. Service Management

```bash
# Stop service
sudo systemctl stop grow-tent.service

# Restart service
sudo systemctl restart grow-tent.service

# Disable auto-start
sudo systemctl disable grow-tent.service
```

## 📱 Telegram Bot Commands

Once configured, interact with your grow tent via Telegram:

- `/start` - Show available commands
- `/status` - Get current sensor readings and device states
- `/devices` - List all devices and their states
- `/on <device>` - Turn device on (e.g., `/on lights`)
- `/off <device>` - Turn device off (e.g., `/off nutrient_pump`)
- `/alerts` - View current alert settings
- `/photo` - Get current camera snapshot

**Device names**: `lights`, `air_pump`, `nutrient_pump`, `circulatory_fan_1`, `circulatory_fan_2`, `exhaust_fan`, `humidifier`, `heater`, `dehumidifier`

## 💻 Web Interface Usage

### Dashboard
- View real-time sensor data (temperature, humidity, pressure, air quality)
- Monitor all 9 device states with on/off toggles
- Live camera feed
- Recent trends chart

### Projects
- Create new grow projects
- Track start/end dates
- View historical projects
- End active projects

### Data Logs
- Time-series charts for all sensor data
- Select time range (1h, 6h, 24h, 7d)
- Export data to CSV

### Grow Diary
- Add text entries with photos
- Timeline view of all entries
- Edit and delete entries
- Photo gallery

### Settings
- Configure device schedules (on/off times)
- Set environmental thresholds (temp/humidity triggers)
- Configure alert thresholds
- Choose control modes:
  - **Schedule**: Time-based control
  - **Threshold**: Environmental trigger control
  - **Auto**: Combination of schedule and thresholds
  - **Manual**: No automatic control

### Time-lapse
- Start/stop automatic image capture
- Set capture interval (seconds)
- Generate MP4 videos from captured images
- Download generated time-lapse videos

### Plant Health
- Analyze plant health from camera or uploaded images
- Get health score (0-100)
- Detect issues (nutrient deficiency, pests, diseases)
- Receive recommendations

### Camera
- View live feed
- Capture manual snapshots
- Browse photo gallery

## 🔄 Device Control Logic

### Lights
- **Default**: On from 06:00 to 22:00 (16 hours)
- **Mode**: Schedule-based
- Customize on/off times in Settings

### Exhaust Fan
- **Default**: 15 minutes every hour + threshold triggers
- **Mode**: Auto (schedule + thresholds)
- **Thresholds**: Turns on if temp > 28°C or humidity > 75%

### Circulatory Fan 1 & 2
- **Default**: Always on
- **Mode**: Schedule-based
- Two independently controllable fans

### Humidifier
- **Default**: Threshold-based
- **Mode**: Threshold
- **Threshold**: Turns on if humidity < 50%

### Dehumidifier
- **Default**: Threshold-based
- **Mode**: Threshold
- **Threshold**: Turns on if humidity > 70%

### Heater
- **Default**: Threshold-based
- **Mode**: Threshold
- **Threshold**: Turns on if temp < 18°C

### Nutrient Pump
- **Default**: 5 minutes at 08:00 and 20:00
- **Mode**: Schedule-based
- Customize watering times in Settings

### Air Pump
- **Default**: Always on for oxygenation
- **Mode**: Schedule-based
- Critical for hydroponic systems

## 🔍 Troubleshooting

### Sensor Not Detected

```bash
# Check I²C connection
sudo i2cdetect -y 1

# Try alternate I²C address in config (0x76 or 0x77)
```

### Camera Not Working

```bash
# Verify libcamera-apps is installed
sudo apt install libcamera-apps

# Test camera with rpicam-jpeg
rpicam-jpeg -o test.jpg --width 1920 --height 1080

# Verify camera is enabled
sudo raspi-config
# Interface Options → Camera → Enable

# Check camera permissions
sudo usermod -aG video $USER
```

### GPIO Errors

```bash
# Reset GPIO
sudo rmmod gpiomem
sudo modprobe gpiomem

# Check permissions
sudo usermod -aG gpio $USER
```

### Service Won't Start

```bash
# Check logs
sudo journalctl -u grow-tent.service -n 50

# Check file permissions
ls -la /home/pi/grow_tent_automation

# Verify virtual environment
source venv/bin/activate
python -c "import fastapi, RPi.GPIO, bme680"
```

### Web Interface Not Accessible

```bash
# Check if service is running
sudo systemctl status grow-tent.service

# Check firewall
sudo ufw status
sudo ufw allow 8000/tcp

# Find Pi's IP address
hostname -I
```

### Telegram Bot Not Responding

- Verify bot token in `.env` file
- Check chat ID is correct
- Ensure Pi has internet connection
- Check service logs for errors

## 📊 Database Backup

```bash
# Backup database
cp data/database.db data/database_backup_$(date +%Y%m%d).db

# Restore from backup
cp data/database_backup_YYYYMMDD.db data/database.db
```

## 🔐 Security Considerations

- **Network**: Recommended to use on a private network
- **Authentication**: Consider adding password protection for web interface
- **Telegram**: Only you can control via Telegram (using your chat ID)
- **Firewall**: Configure firewall rules if exposed to internet
- **Updates**: Keep system and dependencies updated

## 📈 Performance Tips

- **Database**: Vacuum periodically: `sqlite3 data/database.db "VACUUM;"`
- **Logs**: Rotate logs regularly to save space
- **Photos**: Clean old photos/videos periodically
- **SD Card**: Use high-quality SD card for better I/O performance

## 🛠️ Development

### Project Structure
```
grow_tent_automation/
├── backend/
│   ├── api/              # FastAPI endpoints
│   ├── automation/       # Automation engine
│   ├── hardware/         # Hardware controllers
│   ├── telegram_bot/     # Telegram bot
│   ├── utils/            # Utilities
│   ├── config.py         # Configuration
│   ├── database.py       # Database models
│   └── main.py           # Main application
├── frontend/
│   ├── css/             # Styles
│   ├── js/              # JavaScript modules
│   └── index.html       # Main HTML
├── data/                # Data storage
├── config/              # Configuration files
├── logs/                # Log files
└── requirements.txt     # Python dependencies
```

### Running Tests
```bash
source venv/bin/activate
python test_hardware.py
```

### API Documentation
- FastAPI automatically generates API docs
- Access at: `http://raspberry-pi-ip:8000/docs`

## 📝 Changelog

### Version 1.1.0 (Current)
- Updated to 9-relay system with new device names
- Camera now uses rpicam-jpeg command via subprocess
- Split circulatory fans into two independent controls
- Renamed pump to nutrient_pump
- Added air_pump for oxygenation
- Improved device display names throughout UI

### Version 1.0.0 (Initial Release)
- Complete grow tent automation system
- Web interface with 8 functional pages
- Telegram bot integration
- Time-lapse functionality
- Plant health analysis
- Project management
- Comprehensive device control

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues, questions, or feature requests:
- Check the troubleshooting section
- Review system logs
- Check API documentation at `/docs`

## 🎯 Roadmap

Future enhancements:
- [ ] Mobile app (iOS/Android)
- [ ] Multi-tent support
- [ ] Advanced analytics and predictions
- [ ] Integration with weather APIs
- [ ] Automated nutrient dosing
- [ ] pH/EC monitoring
- [ ] Cloud backup and sync

---

**Note**: This localhost refers to localhost of the Raspberry Pi where the application is running, not your local machine. To access the interface, you need to use the Raspberry Pi's IP address from any device on your network (e.g., `http://192.168.1.100:8000`).

Made with 🌱 for growers by growers.
