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
print("\nMotor 2 (M2) = Mouth motor")
print("Motor 1 (M1) = Tail/Torso motor")
print("\nWatch the motors and note which direction they move!\n")

# Test Motor 2 (Mouth)
print("Testing Motor 2 (Mouth) - FORWARD (positive throttle)...")
kit.motor2.throttle = 1.0
time.sleep(1)
kit.motor2.throttle = 0
print("Did the mouth OPEN or CLOSE? (write this down)")
time.sleep(2)

print("\nTesting Motor 2 (Mouth) - BACKWARD (negative throttle)...")
kit.motor2.throttle = -1.0
time.sleep(1)
kit.motor2.throttle = 0
print("Did the mouth OPEN or CLOSE? (write this down)")
time.sleep(2)

# Test Motor 1 (Tail/Torso)
print("\nTesting Motor 1 (Tail/Torso) - FORWARD (FULL POWER)...")
kit.motor1.throttle = 1.0
time.sleep(2)
kit.motor1.throttle = 0
print("Did the tail/torso move OUT? (should lean forward)")
time.sleep(2)

print("\nTesting Motor 1 (Tail/Torso) - BACKWARD (FULL POWER)...")
kit.motor1.throttle = -1.0
time.sleep(2)
kit.motor1.throttle = 0
print("Did the tail/torso move BACK IN? (should return to rest)")
time.sleep(2)

print("\n" + "=" * 50)
print("Test complete!")
print("\nNow tell me:")
print("1. Does FORWARD (0.5) or BACKWARD (-0.5) OPEN the mouth?")
print("2. Does FORWARD (0.5) or BACKWARD (-0.5) CLOSE the mouth?")
print("\nI'll update the code based on your answer!")
