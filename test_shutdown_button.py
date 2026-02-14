#!/usr/bin/env python3
"""
Test shutdown button functionality
Wire button: GPIO 3 to GND
"""

import os
import time

SHUTDOWN_PIN = int(os.getenv("SHUTDOWN_PIN", "27"))

try:
    from gpiozero import Button
    print(f"Testing shutdown button on GPIO {SHUTDOWN_PIN}")
    print("Wire button: one side to GPIO 27, other side to GND")
    print("Press button to test (Ctrl+C to exit)")
    print()
    
    def on_press():
        print("🔴 SHUTDOWN button pressed!")
        print("In production, this would run: sudo shutdown -h now")
        print()
    
    button = Button(SHUTDOWN_PIN, pull_up=True, bounce_time=0.2)
    button.when_pressed = on_press
    
    print("✓ Button ready - waiting for press...")
    
    while True:
        time.sleep(0.1)
        
except ImportError:
    print("⚠️  gpiozero not available (running on Mac?)")
    print("This test only works on Raspberry Pi")
except KeyboardInterrupt:
    print("\n✓ Test complete")
except Exception as e:
    print(f"❌ Error: {e}")
