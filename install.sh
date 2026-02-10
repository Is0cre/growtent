#!/bin/bash
# Grow Tent Automation Installation Script

set -e

echo "🌱 Grow Tent Automation - Installation Script"
echo "============================================="
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    echo "   The system will run in simulation mode for hardware"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if running as pi user
if [ "$USER" != "pi" ] && [ "$USER" != "root" ]; then
    echo "⚠️  Warning: Not running as 'pi' user. Service file may need adjustment."
fi

echo "📦 Step 1: Installing system dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-venv git i2c-tools ffmpeg

echo ""
echo "🔧 Step 2: Enabling I2C and Camera interfaces..."
echo "Please enable I2C and Camera in raspi-config if not already enabled"
read -p "Press Enter to continue..."

echo ""
echo "🐍 Step 3: Creating Python virtual environment..."
if [ -d "venv" ]; then
    echo "   Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "   ✓ Virtual environment created"
fi

echo ""
echo "📚 Step 4: Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "   ✓ Dependencies installed"

echo ""
echo "⚙️  Step 5: Configuration setup..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "   ✓ Created .env file"
    echo ""
    echo "   ⚠️  IMPORTANT: Edit .env file with your Telegram credentials:"
    echo "      nano .env"
    echo ""
    read -p "   Press Enter when you've configured .env..."
else
    echo "   .env file already exists, skipping..."
fi

if [ ! -f "config/config.yaml" ]; then
    cp config/config.yaml.example config/config.yaml
    echo "   ✓ Created config.yaml"
else
    echo "   config.yaml already exists, skipping..."
fi

echo ""
echo "📁 Step 6: Creating data directories..."
mkdir -p data/photos data/timelapse data/videos data/temp logs
echo "   ✓ Directories created"

echo ""
echo "🔍 Step 7: Verifying hardware..."
echo "   Checking I2C devices..."
if command -v i2cdetect &> /dev/null; then
    sudo i2cdetect -y 1 || echo "   No I2C devices detected (normal if not connected yet)"
else
    echo "   i2cdetect not available"
fi

echo ""
echo "🎯 Step 8: Testing installation..."
echo "   Starting test run (press Ctrl+C to stop)..."
echo ""
cd backend
python main.py &
SERVER_PID=$!
sleep 5

if ps -p $SERVER_PID > /dev/null; then
    echo "   ✓ Server started successfully!"
    echo ""
    echo "   Access the web interface at:"
    echo "   http://$(hostname -I | awk '{print $1}'):8000"
    echo ""
    read -p "   Press Enter to stop test server..."
    kill $SERVER_PID
else
    echo "   ❌ Server failed to start. Check logs for errors."
fi

echo ""
echo "🚀 Step 9: Setting up systemd service..."
echo "   Do you want to install the systemd service for auto-start?"
read -p "   This requires sudo access (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Update service file with correct user
    sed "s/User=pi/User=$USER/g" systemd/grow-tent.service | \
        sed "s|/home/pi|$HOME|g" | \
        sudo tee /etc/systemd/system/grow-tent.service > /dev/null
    
    sudo systemctl daemon-reload
    sudo systemctl enable grow-tent.service
    sudo systemctl start grow-tent.service
    
    echo "   ✓ Service installed and started"
    echo ""
    echo "   Service commands:"
    echo "   - Status:  sudo systemctl status grow-tent"
    echo "   - Stop:    sudo systemctl stop grow-tent"
    echo "   - Restart: sudo systemctl restart grow-tent"
    echo "   - Logs:    sudo journalctl -u grow-tent -f"
else
    echo "   Skipping service installation"
    echo "   You can manually run: cd backend && python main.py"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Verify Telegram bot configuration in .env"
echo "   2. Connect your hardware (sensors, relays, camera)"
echo "   3. Access web interface at http://$(hostname -I | awk '{print $1}'):8000"
echo "   4. Create your first project and start growing! 🌱"
echo ""
echo "📖 For detailed documentation, see README.md"
echo ""
