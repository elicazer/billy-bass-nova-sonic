# Billy Bass Setup Guide

## What I Need to Know About Your Setup

Before running the code, please tell me:

### 1. Motor Port Connections
Which motor ports on your HAT did you connect the Billy Bass motors to?

Your HAT should have labeled ports like **M1, M2, M3, M4** or **MA, MB, MC, MD**

- **Mouth motor** is connected to port: ___
- **Tail motor** is connected to port: ___
- **Head motor** is connected to port: ___

### 2. Motor Direction Testing
We need to test which direction makes each motor move correctly:

For the **mouth motor**:
- Does positive throttle (forward) OPEN or CLOSE the mouth?
- Does negative throttle (backward) OPEN or CLOSE the mouth?

### 3. HAT Information
What chip/model is your motor HAT? Look for:
- Brand name (Yahboom, Waveshare, Adafruit, etc.)
- Chip labels on the board (PCA9685, TB6612, DRV8833, etc.)
- Any model number printed on the board

## Quick Start

### Step 1: Install Dependencies
```bash
chmod +x setup.sh
./setup.sh
```

### Step 2: Enable I2C (if not already enabled)
```bash
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable
```

### Step 3: Test I2C Connection
```bash
sudo i2cdetect -y 1
```
You should see a device at address 0x60 or 0x40 (depending on your HAT)

### Step 4: Set Your Gemini API Key
```bash
export GEMINI_API_KEY='your-api-key-here'
```

### Step 5: Configure Motor Ports
Edit `billy_bass_motor_hat.py` and update these lines:
```python
MOUTH_MOTOR = 1  # Change to your mouth motor port (1-4)
TAIL_MOTOR = 2   # Change to your tail motor port (1-4)
HEAD_MOTOR = 3   # Change to your head motor port (1-4)
```

### Step 6: Test Motor Control
Create a simple test script to verify motors work:
```python
from adafruit_motorkit import MotorKit
import time

kit = MotorKit()

# Test motor 1 (adjust number as needed)
print("Testing motor 1 forward...")
kit.motor1.throttle = 0.5
time.sleep(1)
kit.motor1.throttle = 0

print("Testing motor 1 backward...")
kit.motor1.throttle = -0.5
time.sleep(1)
kit.motor1.throttle = 0
```

### Step 7: Run Billy Bass
```bash
python3 billy_bass_motor_hat.py
```

## Common Motor HAT Types

### Adafruit Motor HAT (PCA9685 + TB6612)
- Uses I2C address 0x60
- Library: `adafruit-circuitpython-motorkit`
- 4 DC motor ports

### Waveshare Motor Driver HAT (PCA9685 + TB6612)
- Uses I2C address 0x40
- Compatible with Adafruit library
- 2 DC motor ports

### DFRobot Motor HAT (STM32 + TB6612)
- Uses I2C address 0x10
- Requires custom library

## Troubleshooting

**Motors don't move:**
- Check I2C is enabled: `sudo i2cdetect -y 1`
- Verify power supply is connected to HAT
- Check motor wires are properly connected

**Motors move wrong direction:**
- Swap the motor wires, OR
- Change throttle sign in code (0.5 to -0.5)

**No I2C device detected:**
- Enable I2C in raspi-config
- Check HAT is properly seated on GPIO pins
- Try `sudo i2cdetect -y 0` (older Pi models)

**Import errors:**
- Run: `pip3 install adafruit-circuitpython-motorkit`
- May need: `sudo apt-get install python3-smbus`
