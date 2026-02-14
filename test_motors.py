#!/usr/bin/env python3
"""
Test script for Billy Bass motors
Use this to verify motor connections and directions
"""

from adafruit_motorkit import MotorKit
import time

kit = MotorKit()

print("Billy Bass Motor Test")
print("=" * 50)
print("\nMotor 1 (A1/B1) = Mouth motor")
print("Motor 2 (A2/B2) = Tail/Torso motor")
print("\nWatch the motors and note which direction they move!\n")

# Test Motor 1 (Mouth)
print("Testing Motor 1 (Mouth) - FORWARD (positive throttle)...")
kit.motor1.throttle = 0.5
time.sleep(1)
kit.motor1.throttle = 0
print("Did the mouth OPEN or CLOSE? (write this down)")
time.sleep(2)

print("\nTesting Motor 1 (Mouth) - BACKWARD (negative throttle)...")
kit.motor1.throttle = -0.5
time.sleep(1)
kit.motor1.throttle = 0
print("Did the mouth OPEN or CLOSE? (write this down)")
time.sleep(2)

# Test Motor 2 (Tail/Torso)
print("\nTesting Motor 2 (Tail/Torso) - FORWARD...")
kit.motor2.throttle = 0.5
time.sleep(1)
kit.motor2.throttle = 0
print("Did the tail/torso move? Which direction?")
time.sleep(2)

print("\nTesting Motor 2 (Tail/Torso) - BACKWARD...")
kit.motor2.throttle = -0.5
time.sleep(1)
kit.motor2.throttle = 0
print("Did the tail/torso move? Which direction?")
time.sleep(2)

print("\n" + "=" * 50)
print("Test complete!")
print("\nNow tell me:")
print("1. Does FORWARD (0.5) or BACKWARD (-0.5) OPEN the mouth?")
print("2. Does FORWARD (0.5) or BACKWARD (-0.5) CLOSE the mouth?")
print("\nI'll update the code based on your answer!")
