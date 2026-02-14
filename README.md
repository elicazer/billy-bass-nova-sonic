# Billy Bass AI Animatronic

Turn your Big Mouth Billy Bass into a real-time voice assistant using Amazon Nova Sonic and Raspberry Pi.

## Features

- **Low-latency speech-to-speech** using Amazon Nova Sonic bidirectional streaming
- **Real-time mouth animation** synced to audio output
- **Torso/tail movement** during conversation
- **Button-activated listening** with auto-timeout
- **GPIO shutdown button** for easy power-off
- **Cross-platform development** (Mac demo mode + Raspberry Pi production)

## Hardware Requirements

- Raspberry Pi 5 (or 4)
- [Adafruit DC Motor FeatherWing](https://www.adafruit.com/product/2927) (I2C motor controller)
- Big Mouth Billy Bass (hacked for motor control)
- USB microphone
- USB speaker (or 3.5mm audio out)
- Power supply for motors (separate from Pi)
- Push button for front panel (GPIO 17 to GND)
- Push button for back shutdown (GPIO 27 to GND) - optional

## Motor Wiring

Default configuration (FeatherWing):
- **M2** → Mouth motor
- **M1** → Torso/tail motor

Override with environment variables if needed:
```bash
export MOUTH_MOTOR=2
export TORSO_MOTOR=1
export MOUTH_DIR=-1    # Invert direction if needed
export TORSO_DIR=-1
```

## Button Wiring

### Front Button (Listening Toggle)
- **GPIO 17** → One side of button
- **GND** → Other side of button
- Uses internal pull-up resistor (no external resistor needed)
- Press to start listening, press again to stop

### Back Button (Shutdown) - Optional
- **GPIO 27** → One side of button
- **GND** → Other side of button
- Uses internal pull-up resistor
- Press to safely shutdown the Pi

Configure button pins via environment variables:
```bash
export BUTTON_PIN=17        # Front button (default)
export SHUTDOWN_PIN=27      # Back shutdown button (default)
```

## Setup

### Raspberry Pi

1. **Install dependencies:**
```bash
chmod +x setup_pi.sh
./setup_pi.sh
```

2. **Enable I2C:**
```bash
sudo raspi-config
# Interface Options → I2C → Enable → Reboot
```

3. **Verify I2C connection:**
```bash
sudo i2cdetect -y 1
```
Should show device at `0x60`

4. **Find audio device indexes:**
```bash
arecord -l  # List input devices
aplay -l    # List output devices
```

5. **Configure credentials:**
```bash
cp .env.example .env
nano .env  # Edit with your AWS credentials and audio device indexes
```

6. **Test motors:**
```bash
python3 test_motors.py
```

7. **Run Billy Bass:**
```bash
./start.sh
```

Or run directly with manual environment variables:
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
python3 billy_bass_nova_sonic.py
```

### Mac (Development)

1. **Install dependencies:**
```bash
chmod +x setup_mac.sh
./setup_mac.sh
```

2. **Set AWS credentials:**
```bash
cp .env.example .env
nano .env  # Add your AWS credentials
```

3. **Run in demo mode:**
```bash
./start.sh
```

Or manually:
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
python3 billy_bass_nova_sonic.py
```

Motors will be simulated with console output.

## How It Works

1. **Button activation** — press front button to start listening (Billy says "Hi!")
2. **Continuous audio streaming** — microphone audio streams to Nova Sonic at 16 kHz
3. **Real-time AI processing** — Nova Sonic processes speech and generates responses
4. **Audio output streaming** — response audio streams back at 24 kHz
5. **Synchronized animation** — mouth opens/closes based on audio amplitude, torso moves during speech
6. **Auto-timeout** — after 30 seconds of inactivity, Billy says goodbye and stops listening
7. **Shutdown** — press back button to safely power down the Pi

No separate transcription or TTS steps — everything happens in real-time over a single bidirectional stream.

## Quick Start

1. **Copy and configure environment file:**
```bash
cp .env.example .env
nano .env  # Add your AWS credentials and audio device indexes
```

2. **Make startup script executable:**
```bash
chmod +x start.sh
```

3. **Run Billy Bass:**
```bash
./start.sh
```

The startup script will load your configuration from `.env` and start the animatronic.

## Configuration

### Audio Tuning

Edit `billy_bass_nova_sonic.py`:
```python
MOUTH_MIN_OPEN_PCT = 12      # Deadband to prevent chatter
MOUTH_INTENSITY_MIN = 0.2    # Minimum motor power
MOUTH_INTENSITY_MAX = 0.9    # Maximum motor power
MOUTH_DURATION_MIN = 0.025   # Minimum pulse duration (seconds)
MOUTH_DURATION_MAX = 0.08    # Maximum pulse duration (seconds)
```

### Torso Movement

```python
TORSO_FWD = 0.55             # Forward throttle during speech
TORSO_BACK = -0.55           # Backward throttle to return
TORSO_BACK_SEC = 0.45        # Return duration (seconds)
```

### Voice and Personality

Edit `nova_sonic_client.py`:
```python
voice_id="matthew"  # Options: matthew, joanna, etc.
system_prompt="You are a calm, natural voice..."
```

## Troubleshooting

**No audio output:**
- Check `aplay -l` and set correct `AUDIO_OUTPUT_INDEX`
- Some USB speakers don't support 24 kHz — try a different device
- ALSA warnings about "Unknown PCM" are usually harmless

**Motors don't move:**
- Verify I2C: `sudo i2cdetect -y 1` should show `0x60`
- Check motor power supply is connected
- Run `python3 test_motors.py` to test each motor

**Button doesn't work:**
- Test button: `python3 test_button.py`
- Verify wiring: GPIO 17 to one side, GND to other
- Check GPIO isn't already in use by another process

**Shutdown button requires password:**
- Add to sudoers for passwordless shutdown:
```bash
sudo visudo
# Add this line at the end:
yourusername ALL=(ALL) NOPASSWD: /sbin/shutdown
```

**Motor moves wrong direction:**
- Set `MOUTH_DIR=-1` or `TORSO_DIR=-1` to invert

**AWS credentials error:**
- Verify credentials: `aws sts get-caller-identity`
- Ensure Nova Sonic is available in your region (try `us-east-1`)

**Audio device errors:**
- List devices: `python3 -c "import pyaudio; p=pyaudio.PyAudio(); [print(f'{i}: {p.get_device_info_by_index(i)[\"name\"]}') for i in range(p.get_device_count())]"`
- Set indexes explicitly with `AUDIO_INPUT_INDEX` and `AUDIO_OUTPUT_INDEX`

## Project Structure

```
.
├── billy_bass_nova_sonic.py    # Main script (Nova Sonic + motors)
├── nova_sonic_client.py        # Nova Sonic bidirectional client
├── audio_mouth_controller.py   # Smooth mouth animation controller
├── test_motors.py              # Motor testing utility
├── start.sh                    # Startup script (loads .env)
├── .env.example                # Example configuration file
├── .env                        # Your credentials (create from .env.example)
├── requirements.txt            # Python dependencies
├── setup_pi.sh                 # Raspberry Pi setup
├── setup_mac.sh                # Mac setup
└── experiments/                # Older implementations (Gemini, etc.)
```

## Experiments

The `experiments/` folder contains earlier implementations:
- `billy_bass_cross_platform.py` — Gemini + gTTS (higher latency)
- `billy_bass_nova.py` — Nova + Transcribe + Polly (higher latency)
- `billy_bass_gemini.py` — Original GPIO-based version
- `billy_bass_motor_hat.py` — Motor HAT variant

These are kept for reference but `billy_bass_nova_sonic.py` is the recommended implementation.

## Credits

- Nova Sonic client adapted from [AIRobotAssistant](https://github.com/elicazer/AIRobotAssistant)
- Mouth animation controller from the same project

## License

MIT
