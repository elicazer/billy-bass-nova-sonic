#!/bin/bash
# Setup script for Billy Bass on Raspberry Pi

echo "🥧 Setting up Billy Bass on Raspberry Pi..."
echo ""

# Update system
echo "Updating system..."
sudo apt-get update

# Install system dependencies
echo ""
echo "Installing system dependencies..."
sudo apt-get install -y python3-pip python3-pyaudio portaudio19-dev ffmpeg i2c-tools

# Install Python packages
echo ""
echo "Installing Python packages..."
pip3 install -r requirements_dev.txt

# Enable I2C
echo ""
echo "Checking I2C..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "Enabling I2C..."
    sudo raspi-config nonint do_i2c 0
    echo "⚠️  Please reboot after setup: sudo reboot"
else
    echo "✓ I2C already enabled"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Before running, set your Gemini API key:"
echo "  export GEMINI_API_KEY='your-api-key-here'"
echo ""
echo "Or add to ~/.bashrc:"
echo "  echo \"export GEMINI_API_KEY='your-key'\" >> ~/.bashrc"
echo "  source ~/.bashrc"
echo ""
echo "To check I2C devices:"
echo "  sudo i2cdetect -y 1"
echo ""
echo "To test motors:"
echo "  python3 billy_bass_cross_platform.py test"
echo ""
echo "To run Billy Bass:"
echo "  python3 billy_bass_cross_platform.py"
