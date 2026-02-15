#!/usr/bin/env python3
"""
Test script for shutdown button on GPIO 3 (or configured pin)
Wire: One wire to GPIO 3, other to GND
GPIO 3 has special wake-on-low feature for Pi
"""

import os
import time

try:
    from gpiozero import Button
    GPIO_AVAILABLE = True
except ImportError:
    print("❌ gpiozero not available - install with: pip3 install gpiozero")
    exit(1)

# Get shutdown pin from env or use default
SHUTDOWN_PIN = int(os.getenv("SHUTDOWN_PIN", "27"))

print(f"🔴 Testing shutdown button on GPIO {SHUTDOWN_PIN}")
print(f"📌 Wiring: GPIO {SHUTDOWN_PIN} → Switch → GND")
print("⚠️  This will actually shutdown the Pi when pressed!")
print("\nPress Ctrl+C to exit test without triggering shutdown\n")

def on_shutdown():
    print("\n🔴 SHUTDOWN BUTTON PRESSED!")
    print("In production, this would run: sudo shutdown -h now")
    print("(Not executing in test mode)")
    # Uncomment below to actually test shutdown:
    # import subprocess
    # subprocess.run(['sudo', 'shutdown', '-h', 'now'])

try:
    button = Button(SHUTDOWN_PIN, pull_up=True, bounce_time=0.2)
    button.when_pressed = on_shutdown
    
    print("✓ Button initialized - waiting for press...")
    print("  (Button should be OPEN/not pressed right now)")
    
    while True:
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n\n✓ Test stopped")
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure gpiozero is installed: pip3 install gpiozero")
    print("2. Check wiring: One wire to GPIO pin, other to GND")
    print("3. Try a different GPIO pin if this one doesn't work")
