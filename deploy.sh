#!/bin/bash
# Deploy Billy Bass to Raspberry Pi via SSH

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Billy Bass Deployment Script${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please create .env with your credentials before deploying."
    exit 1
fi

# Get Pi hostname/IP
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: ./deploy.sh [pi-hostname-or-ip]${NC}"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh raspberrypi.local"
    echo "  ./deploy.sh pi@raspberrypi.local"
    echo "  ./deploy.sh 192.168.1.100"
    echo ""
    read -p "Enter Pi hostname or IP: " PI_HOST
else
    PI_HOST=$1
fi

# Add pi@ prefix if not present
if [[ ! "$PI_HOST" =~ "@" ]]; then
    PI_HOST="pi@$PI_HOST"
fi

echo -e "${YELLOW}📡 Connecting to $PI_HOST...${NC}"

# Test SSH connection
if ! ssh -o ConnectTimeout=5 "$PI_HOST" "echo 'Connection successful'" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to $PI_HOST${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check Pi is powered on and connected to network"
    echo "  2. Verify hostname/IP is correct"
    echo "  3. Ensure SSH is enabled on Pi"
    echo "  4. Try: ssh $PI_HOST"
    exit 1
fi

echo -e "${GREEN}✓ Connected to Pi${NC}"
echo ""

# Create directory on Pi
echo -e "${YELLOW}📁 Creating billy_bass directory on Pi...${NC}"
ssh "$PI_HOST" "mkdir -p ~/billy_bass"

# Copy files
echo -e "${YELLOW}📦 Copying files to Pi...${NC}"
echo "  - Python scripts"
scp -q billy_bass_nova_sonic.py nova_sonic_client.py audio_mouth_controller.py test_motors.py "$PI_HOST:~/billy_bass/"

echo "  - Configuration files"
scp -q .env requirements.txt "$PI_HOST:~/billy_bass/"

echo "  - Setup scripts"
scp -q setup_pi.sh start.sh "$PI_HOST:~/billy_bass/"

echo -e "${GREEN}✓ Files copied${NC}"
echo ""

# Make scripts executable
echo -e "${YELLOW}🔧 Setting permissions...${NC}"
ssh "$PI_HOST" "cd ~/billy_bass && chmod +x setup_pi.sh start.sh"

echo -e "${GREEN}✓ Deployment complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. SSH into your Pi:"
echo "     ssh $PI_HOST"
echo ""
echo "  2. Run setup (first time only):"
echo "     cd ~/billy_bass"
echo "     ./setup_pi.sh"
echo ""
echo "  3. Find audio device indexes:"
echo "     arecord -l  # Input devices"
echo "     aplay -l    # Output devices"
echo ""
echo "  4. Update .env with correct audio indexes:"
echo "     nano .env"
echo ""
echo "  5. Test motors:"
echo "     python3 test_motors.py"
echo ""
echo "  6. Run Billy Bass:"
echo "     ./start.sh"
echo ""
