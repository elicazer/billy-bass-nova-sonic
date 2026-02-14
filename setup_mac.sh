#!/bin/bash
# Setup script for Billy Bass on Mac

echo "🍎 Setting up Billy Bass on Mac..."
echo ""

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install from https://brew.sh"
    exit 1
fi

echo "✓ Homebrew found"

# Install system dependencies
echo ""
echo "Installing system dependencies..."
brew install portaudio ffmpeg

# Install Python packages
echo ""
echo "Installing Python packages..."
pip3 install -r requirements_dev.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Before running, set your Gemini API key:"
echo "  export GEMINI_API_KEY='your-api-key-here'"
echo ""
echo "Or add to ~/.zshrc:"
echo "  echo \"export GEMINI_API_KEY='your-key'\" >> ~/.zshrc"
echo "  source ~/.zshrc"
echo ""
echo "To test motors:"
echo "  python3 billy_bass_cross_platform.py test"
echo ""
echo "To run Billy Bass:"
echo "  python3 billy_bass_cross_platform.py"
