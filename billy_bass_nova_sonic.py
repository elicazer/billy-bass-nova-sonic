#!/usr/bin/env python3
"""
Billy Bass + Amazon Nova Sonic

Real-time speech-to-speech animatronic using Amazon Nova Sonic bidirectional streaming.
Mic streams 16 kHz PCM → Nova Sonic → 24 kHz PCM output with synchronized mouth/torso animation.

This is the primary implementation. See experiments/ for earlier Gemini and Nova+Transcribe versions.
"""

import asyncio
import os
import time
from pathlib import Path

import numpy as np
import pyaudio

os.environ.setdefault("BLINKA_FORCECHIP_ID", "GENERIC_LINUX")

# Import the working client from AIRobotAssistant (copied into this repo)
from nova_sonic_client import NovaSonicClient, INPUT_SAMPLE_RATE, OUTPUT_SAMPLE_RATE, CHUNK_SIZE, FORMAT, CHANNELS

from audio_mouth_controller import AudioMouthController

try:
    from adafruit_motorkit import MotorKit
    MOTOR_LIB = "adafruit"
except Exception:
    MOTOR_LIB = None

# Motor config (env overridable)
MOUTH_MOTOR = int(os.getenv("MOUTH_MOTOR", "2"))
TORSO_MOTOR = int(os.getenv("TORSO_MOTOR", os.getenv("TAIL_MOTOR", "1")))

# Direction tweaks (set to -1 to invert)
MOUTH_DIR = int(os.getenv("MOUTH_DIR", "1"))
TORSO_DIR = int(os.getenv("TORSO_DIR", "1"))

MOUTH_MIN_OPEN_PCT = 12
MOUTH_INTENSITY_MIN = 0.2
MOUTH_INTENSITY_MAX = 0.9
MOUTH_DURATION_MIN = 0.025
MOUTH_DURATION_MAX = 0.08

TORSO_FWD = float(os.getenv("TORSO_THROTTLE_FWD", "0.55"))
TORSO_BACK = float(os.getenv("TORSO_THROTTLE_BACK", "-0.55"))
TORSO_BACK_SEC = float(os.getenv("TORSO_BACK_SEC", "0.45"))

# Audio devices (set indexes if you know them)
INPUT_DEVICE_INDEX = os.getenv("AUDIO_INPUT_INDEX")
OUTPUT_DEVICE_INDEX = os.getenv("AUDIO_OUTPUT_INDEX")


class MockMotor:
    def __init__(self, name):
        self.name = name
        self.throttle = 0

    def __setattr__(self, name, value):
        if name == "throttle" and value != 0:
            print(f"  🔧 {self.__dict__.get('name', 'Motor')} throttle: {value}")
        super().__setattr__(name, value)


class Billy:
    def __init__(self):
        self.mouth_controller = AudioMouthController(sample_rate=OUTPUT_SAMPLE_RATE)
        self.torso_active = False

        if MOTOR_LIB == "adafruit":
            try:
                self.kit = MotorKit()
                self.mouth = {1: self.kit.motor1, 2: self.kit.motor2, 3: self.kit.motor3, 4: self.kit.motor4}.get(MOUTH_MOTOR)
                self.torso = {1: self.kit.motor1, 2: self.kit.motor2, 3: self.kit.motor3, 4: self.kit.motor4}.get(TORSO_MOTOR)
                print("✓ Motors initialized")
            except Exception as e:
                print(f"⚠ Motor init failed: {e} — demo mode")
                self.mouth = MockMotor("Mouth")
                self.torso = MockMotor("Torso")
        else:
            self.mouth = MockMotor("Mouth")
            self.torso = MockMotor("Torso")

    def drive_mouth(self, opening):
        if not self.mouth:
            return
        if opening < MOUTH_MIN_OPEN_PCT:
            self.mouth.throttle = 0.35 * MOUTH_DIR
            time.sleep(0.03)
            self.mouth.throttle = 0
            return
        intensity = MOUTH_INTENSITY_MIN + (opening / 100) * (MOUTH_INTENSITY_MAX - MOUTH_INTENSITY_MIN)
        duration = MOUTH_DURATION_MIN + (opening / 100) * (MOUTH_DURATION_MAX - MOUTH_DURATION_MIN)
        self.mouth.throttle = -intensity * MOUTH_DIR
        time.sleep(duration)
        self.mouth.throttle = 0

    def torso_start(self):
        if not self.torso:
            print("⚠️  No torso motor!")
            return
        try:
            self.torso.throttle = TORSO_FWD * TORSO_DIR
            self.torso_active = True
            print(f"✅ torso_active set to True")
        except Exception as e:
            print(f"❌ torso_start failed: {e}")

    def torso_end(self):
        """Return torso to rest position"""
        if not self.torso:
            return
        try:
            self.torso.throttle = TORSO_BACK * TORSO_DIR
        except Exception:
            pass
        self.torso_active = False
    
    def torso_stop(self):
        """Stop torso motor"""
        if not self.torso:
            return
        try:
            self.torso.throttle = 0
        except Exception:
            pass

    def stop_all(self):
        for m in (self.mouth, self.torso):
            try:
                if m:
                    m.throttle = 0
            except Exception:
                pass


class BillyNova:
    def __init__(self):
        self.billy = Billy()
        self.client = NovaSonicClient(
            region=os.getenv("AWS_REGION", "us-east-1"),
            voice_id="matthew",
            input_device_index=int(INPUT_DEVICE_INDEX) if INPUT_DEVICE_INDEX else None,
            output_device_index=int(OUTPUT_DEVICE_INDEX) if OUTPUT_DEVICE_INDEX else None,
            system_prompt="You are Billy Bass, a talking fish mounted on a wall. You're helpful and conversational, but keep responses brief - one or two sentences max. You're aware you're a fish, but don't constantly mention it unless relevant. Be natural and friendly."
        )
        self.client.on_audio_chunk = self.on_audio_chunk
        self.client.on_audio_output = None
        self.client.on_assistant_text = lambda txt: None
        self.audio_play_task = None
        self.audio_capture_task = None
        self.speaking = False

    def on_audio_chunk(self, chunk: bytes):
        # Drive mouth during playback
        opening = self.billy.mouth_controller.process_audio_chunk(chunk)
        self.billy.drive_mouth(opening)
        
        # Torso up when speaking starts
        if not self.speaking:
            self.billy.torso_start()
            self.speaking = True

    async def run(self):
        await self.client.start_session()

        self.audio_play_task = asyncio.create_task(self.client.play_audio())
        self.audio_capture_task = asyncio.create_task(self.client.capture_audio())
        
        # Simple idle wag
        asyncio.create_task(self.idle_wag())

        try:
            while True:
                # Check if audio playback is happening
                if self.speaking and self.client.audio_queue.empty():
                    await asyncio.sleep(1.0)  # Wait 1 second after audio stops
                    if self.client.audio_queue.empty():  # Still empty
                        self.billy.torso_end()
                        await asyncio.sleep(TORSO_BACK_SEC)
                        self.billy.torso_stop()
                        self.speaking = False
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            await self.client.end_session()
            if self.audio_play_task:
                self.audio_play_task.cancel()
            if self.audio_capture_task:
                self.audio_capture_task.cancel()
            self.billy.stop_all()
            print("✓ Cleanup complete")
    
    async def idle_wag(self):
        """Wag tail when idle"""
        while True:
            await asyncio.sleep(3.0)
            if not self.speaking and self.billy.torso:
                self.billy.torso.throttle = 0.3 * TORSO_DIR
                await asyncio.sleep(0.15)
                self.billy.torso.throttle = -0.3 * TORSO_DIR
                await asyncio.sleep(0.15)
                self.billy.torso.throttle = 0


def main():
    # Ensure AWS creds exist
    missing = [v for v in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY") if not os.getenv(v)]
    if missing:
        print(f"⚠ Missing AWS creds: {', '.join(missing)}")
        return
    bn = BillyNova()
    asyncio.run(bn.run())


if __name__ == "__main__":
    main()
