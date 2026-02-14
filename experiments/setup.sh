#!/bin/bash
# Setup script for Billy Bass with Gemini on Raspberry Pi 5

echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-pyaudio portaudio19-dev ffmpeg

echo "Installing Python packages..."
pip3 install -r requirements.txt

echo "Setup complete!"
echo ""
echo "Before running, set your Gemini API key:"
echo "export GEMINI_API_KEY='your-api-key-here'"
echo ""
echo "Get your API key from: https://makersuite.google.com/app/apikey"
