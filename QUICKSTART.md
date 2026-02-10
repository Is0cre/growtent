# 🚀 Quick Start Guide

Get your grow tent automation system up and running in minutes!

## Prerequisites

- Raspberry Pi 4 (connected to your network)
- MicroSD card with Raspberry Pi OS installed
- SSH or physical access to the Pi

## Installation (One Command)

```bash
git clone <your-repo-url> grow_tent_automation
cd grow_tent_automation
./install.sh
```

The installation script will:
1. Install system dependencies
2. Create Python virtual environment
3. Install Python packages
4. Set up configuration files
5. Create data directories
6. Test the installation
7. Optionally install systemd service

## Quick Configuration

### 1. Get Telegram Bot Token

1. Open Telegram, search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow instructions
3. Copy the bot token

### 2. Get Your Telegram Chat ID

1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find your `chat.id` in the JSON response

### 3. Configure Environment

```bash
nano .env
```

Update these values:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Running the System

### Option 1: Manual Run
```bash
./run.sh
```

### Option 2: As a Service (Auto-start on boot)
```bash
sudo systemctl start grow-tent
sudo systemctl enable grow-tent  # Start on boot
```

## Access the Web Interface

Open your browser and navigate to:
```
http://<raspberry-pi-ip>:8000
```

Find your Pi's IP:
```bash
hostname -I
```

## Test Hardware

Before connecting real devices, test in simulation mode:

```bash
./test_hardware.py
```

This will verify:
- ✅ GPIO/Relay control
- ✅ BME680 sensor reading
- ✅ Camera functionality

## First Steps in the Web Interface

1. **Create a Project**
   - Navigate to "Projects" page
   - Click "New Project"
   - Name your grow (e.g., "Tomatoes 2024")

2. **Configure Devices**
   - Go to "Settings" page
   - Adjust schedules for each device
   - Set temperature/humidity thresholds

3. **Monitor Dashboard**
   - Real-time sensor data
   - Device controls
   - Live camera feed

4. **Start Time-lapse** (Optional)
   - Go to "Time-lapse" page
   - Set interval (e.g., 300 seconds = 5 minutes)
   - Click "Start Capture"

## Telegram Bot Commands

Send these commands to your bot:

- `/status` - Current readings and device states
- `/devices` - List all devices
- `/on lights` - Turn lights on
- `/off pump` - Turn pump off
- `/photo` - Get snapshot
- `/alerts` - View alert settings

## Common Issues

### Can't access web interface
```bash
# Check if service is running
sudo systemctl status grow-tent

# Check Pi's IP
hostname -I

# Allow port in firewall
sudo ufw allow 8000/tcp
```

### Sensor not detected
```bash
# Enable I2C
sudo raspi-config
# Interface Options → I2C → Enable

# Check I2C devices
sudo i2cdetect -y 1
```

### Camera not working
```bash
# Enable camera
sudo raspi-config
# Interface Options → Camera → Enable

# Test camera
libcamera-still -o test.jpg
```

## File Structure

```
grow_tent_automation/
├── install.sh          # Installation script
├── run.sh              # Quick run script
├── test_hardware.py    # Hardware testing
├── requirements.txt    # Python dependencies
├── .env                # Your configuration
├── README.md           # Full documentation
├── backend/            # Python backend
├── frontend/           # Web interface
├── data/               # Database and photos
└── logs/               # Application logs
```

## Service Management

```bash
# Start
sudo systemctl start grow-tent

# Stop
sudo systemctl stop grow-tent

# Restart
sudo systemctl restart grow-tent

# View logs
sudo journalctl -u grow-tent -f

# Check status
sudo systemctl status grow-tent
```

## Default Device Settings

- **Lights**: On 06:00-22:00 (16 hours)
- **Exhaust Fan**: 15 min/hour + auto (temp > 28°C or humidity > 75%)
- **Circulatory Fans**: Always on
- **Humidifier**: Auto (humidity < 50%)
- **Dehumidifier**: Auto (humidity > 70%)
- **Heater**: Auto (temp < 18°C)
- **Pump**: 5 min at 08:00 and 20:00

All settings can be customized in the web interface!

## Need Help?

1. Check full documentation: `README.md`
2. View logs: `tail -f logs/grow_tent.log`
3. Test hardware: `./test_hardware.py`
4. Check service status: `sudo systemctl status grow-tent`

## Safety Note

⚠️ **Important**: 
- Start with LOW power devices for testing
- Verify relay wiring before connecting high-power equipment
- Use proper electrical safety equipment
- Consider using safety relays and circuit breakers
- Never leave high-power devices unattended during initial testing

## Next Steps

Once everything is working:

1. ✅ Fine-tune device schedules in Settings
2. ✅ Configure alert thresholds
3. ✅ Start documenting in Grow Diary
4. ✅ Set up time-lapse for your grow
5. ✅ Use plant health analysis to monitor progress

Happy growing! 🌱

---

**Note**: The web interface runs on the Raspberry Pi. Access it from any device on your network using the Pi's IP address.
