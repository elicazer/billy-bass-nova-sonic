#!/bin/bash
# Billy Bass Startup Script
# Loads environment variables from .env file and starts the animatronic

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🐟 Billy Bass Startup${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo ""
    echo "Please create a .env file with your credentials:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    echo ""
    echo "Then edit .env and add your AWS credentials."
    exit 1
fi

# Load environment variables from .env
echo -e "${YELLOW}📋 Loading configuration from .env...${NC}"
set -a
source .env
set +a

# Verify required credentials
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo -e "${RED}❌ AWS credentials not set in .env file${NC}"
    echo ""
    echo "Please edit .env and set:"
    echo "  AWS_ACCESS_KEY_ID=your_key"
    echo "  AWS_SECRET_ACCESS_KEY=your_secret"
    exit 1
fi

echo -e "${GREEN}✓ Configuration loaded${NC}"
echo "  Region: ${AWS_REGION:-us-east-1}"
echo "  Audio Input: ${AUDIO_INPUT_INDEX:-auto}"
echo "  Audio Output: ${AUDIO_OUTPUT_INDEX:-auto}"
echo "  Mouth Motor: M${MOUTH_MOTOR:-2}"
echo "  Torso Motor: M${TORSO_MOTOR:-1}"
echo ""

# Start Billy Bass
echo -e "${GREEN}🚀 Starting Billy Bass...${NC}"
echo ""
python3 billy_bass_nova_sonic.py
