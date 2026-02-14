#!/usr/bin/env python3
"""Test the button on GPIO 17"""

from gpiozero import Button
import time

print("Button Test - GPIO 17")
print("Press the button to test...")
print("Press Ctrl+C to exit\n")

# Try with pull_up=True (button connects to GND)
button = Button(17, pull_up=True, bounce_time=0.1)

def on_press():
    print("✓ Button PRESSED!")

def on_release():
    print("  Button released")

button.when_pressed = on_press
button.when_released = on_release

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nTest stopped")
    button.close()
