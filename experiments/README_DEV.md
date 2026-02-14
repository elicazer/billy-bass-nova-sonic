# Billy Bass - Development Guide

Cross-platform development setup for Mac and Raspberry Pi.

## Quick Start

### On Mac (Development)

1. **Install dependencies:**
```bash
chmod +x setup_mac.sh
./setup_mac.sh
```

2. **Set Gemini API key:**
```bash
export GEMINI_API_KEY='your-api-key-here'
```

3. **Test without hardware (demo mode):**
```bash
python3 billy_bass_cross_platform.py test
```

4. **Test with USB-C to I2C adapter:**
   - Connect your motor HAT via USB-C to I2C adapter
   - The code will auto-detect the hardware
   - Run: `python3 billy_bass_cross_platform.py test`

### On Raspberry Pi (Production)

1. **Install dependencies:**
```bash
chmod +x setup_pi.sh
./setup_pi.sh
```

2. **Enable I2C (if not done by setup):**
```bash
sudo raspi-config
# Interface Options → I2C → Enable → Reboot
```

3. **Check I2C connection:**
```bash
sudo i2cdetect -y 1
```
Should show device at 0x60 or 0x40

4. **Set Gemini API key:**
```bash
export GEMINI_API_KEY='your-api-key-here'
```

5. **Test motors:**
```bash
python3 billy_bass_cross_platform.py test
```

6. **Run Billy Bass:**
```bash
python3 billy_bass_cross_platform.py
```

## Features

### Auto-Detection
- Automatically detects Mac vs Pi
- Falls back to demo mode if hardware not available
- Shows detailed initialization info

### Demo Mode
- Works without motor hardware
- Prints motor commands to console
- Perfect for testing logic on Mac

### Cross-Platform Audio
- Lists available audio devices
- Works with built-in mic or USB audio
- Handles audio errors gracefully

### Motor Control
- Motor 1 (A1/B1) = Mouth
- Motor 2 (A2/B2) = Tail/Torso
- Configurable throttle and timing

## Development Workflow

1. **Develop on Mac:**
   - Write code in your editor
   - Test in demo mode
   - Test audio/Gemini features

2. **Test with I2C adapter (optional):**
   - Connect motor HAT via USB-C to I2C
   - Test actual motor movements
   - Verify timing and directions

3. **Deploy to Pi:**
   - Copy files: `scp *.py pi@raspberrypi.local:~/billy_bass/`
   - SSH in: `ssh pi@raspberrypi.local`
   - Run setup: `./setup_pi.sh`
   - Test: `python3 billy_bass_cross_platform.py test`

## Troubleshooting

### Mac Issues

**PyAudio won't install:**
```bash
brew install portaudio
pip3 install pyaudio
```

**No audio devices found:**
- Check System Preferences → Sound
- Grant microphone permissions to Terminal

**I2C adapter not detected:**
- Check USB connection
- May need specific drivers for your adapter

### Pi Issues

**I2C not working:**
```bash
sudo raspi-config nonint do_i2c 0
sudo reboot
sudo i2cdetect -y 1
```

**Motor library import error:**
```bash
pip3 install adafruit-circuitpython-motorkit adafruit-blinka
```

**Audio device error:**
```bash
arecord -l  # List recording devices
aplay -l    # List playback devices
```

**Motors move wrong direction:**
Edit the code and swap throttle signs:
```python
# Change this:
self.mouth.throttle = 0.5
# To this:
self.mouth.throttle = -0.5
```

## File Structure

```
billy_bass/
├── billy_bass_cross_platform.py  # Main cross-platform code
├── requirements_dev.txt           # Python dependencies
├── setup_mac.sh                   # Mac setup script
├── setup_pi.sh                    # Pi setup script
├── README_DEV.md                  # This file
└── test_motors.py                 # Simple motor test (optional)
```

## Testing Checklist

- [ ] Code runs on Mac in demo mode
- [ ] Audio recording works
- [ ] Gemini API responds
- [ ] TTS generates speech
- [ ] Motors move correctly (if hardware connected)
- [ ] Code runs on Pi
- [ ] I2C detected on Pi
- [ ] Motors move on Pi
- [ ] Full conversation works

## Notes

- The code automatically detects your platform
- Demo mode activates when motor hardware isn't found
- All motor commands are logged in demo mode
- Audio features work independently of motor hardware
- Gemini API key must be set for AI features
