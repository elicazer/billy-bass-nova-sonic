# Experiments

This folder contains earlier implementations and development iterations of the Billy Bass project.

## Files

### Earlier AI Implementations

- **`billy_bass_cross_platform.py`** — Gemini + gTTS implementation with cross-platform support (Mac/Pi). Uses record → transcribe → generate → speak pipeline. Higher latency than Nova Sonic but simpler setup.

- **`billy_bass_nova.py`** — Amazon Nova (text model) + Transcribe + Polly. Still uses the record → transcribe → generate → speak pipeline. Higher latency than Nova Sonic.

- **`billy_bass_gemini.py`** — Original implementation using GPIO pins directly via `gpiozero`. Legacy motor control approach.

- **`billy_bass_motor_hat.py`** — Gemini implementation adapted for Adafruit Motor HAT. Early MotorKit version.

### Documentation

- **`README_DEV.md`** — Development guide for cross-platform workflow
- **`SETUP_GUIDE.md`** — Detailed setup instructions for various motor HATs
- **`setup.sh`** — Generic setup script (superseded by `setup_pi.sh` and `setup_mac.sh`)

### Dependencies

- **`requirements_dev.txt`** — Earlier dependency list (now consolidated into main `requirements.txt`)

## Why These Were Archived

The main implementation (`billy_bass_nova_sonic.py`) uses Amazon Nova Sonic's bidirectional streaming for significantly lower latency. These earlier implementations are kept for:

1. **Reference** — showing the evolution of the project
2. **Alternative AI backends** — if you prefer Gemini over AWS
3. **Simpler setups** — some of these have fewer dependencies
4. **Learning** — comparing different approaches to the same problem

## Running Experiments

These scripts should still work if you have the right dependencies:

```bash
# Gemini cross-platform version
export GEMINI_API_KEY=your_key
python3 experiments/billy_bass_cross_platform.py

# Nova + Transcribe + Polly version
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
python3 experiments/billy_bass_nova.py
```

Note: You may need to adjust import paths or copy utility files into the experiments folder.
