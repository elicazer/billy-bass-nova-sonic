#!/bin/bash
# Install Billy Bass as a systemd service

echo "🐟 Installing Billy Bass Service..."

# Get the current directory
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$INSTALL_DIR/billy-bass.service"

# Update the service file with the correct paths
echo "📝 Updating service file paths..."
sed -i "s|/home/eliazer/billy-bass-nova-sonic|$INSTALL_DIR|g" "$SERVICE_FILE"
sed -i "s|User=eliazer|User=$USER|g" "$SERVICE_FILE"

# Copy service file to systemd
echo "📋 Installing service file..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/billy-bass.service

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable the service
echo "✅ Enabling Billy Bass service..."
sudo systemctl enable billy-bass.service

echo ""
echo "✅ Installation complete!"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start billy-bass"
echo "  Stop:    sudo systemctl stop billy-bass"
echo "  Status:  sudo systemctl status billy-bass"
echo "  Logs:    sudo journalctl -u billy-bass -f"
echo "  Disable: sudo systemctl disable billy-bass"
echo ""
echo "The service will now start automatically on boot!"
echo "To start it now, run: sudo systemctl start billy-bass"
