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

# Try to import button support
try:
    from gpiozero import Button
    BUTTON_AVAILABLE = True
except Exception:
    BUTTON_AVAILABLE = False
    print("⚠️  GPIO button not available (running on Mac?)")

# Motor config (env overridable)
MOUTH_MOTOR = int(os.getenv("MOUTH_MOTOR", "2"))
TORSO_MOTOR = int(os.getenv("TORSO_MOTOR", os.getenv("TAIL_MOTOR", "1")))

# Button config
BUTTON_PIN = int(os.getenv("BUTTON_PIN", "17"))  # GPIO pin for front button
SHUTDOWN_PIN = int(os.getenv("SHUTDOWN_PIN", "27"))  # GPIO pin for back switch
INACTIVITY_TIMEOUT = 30  # seconds

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
            model_id='amazon.nova-2-sonic-v1:0',  # Nova 2 Sonic
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
        self.listening_active = False
        self.last_activity_time = time.time()
        self.pending_text = None  # Text to speak from button press
        
        # Setup front button if available
        if BUTTON_AVAILABLE:
            self.button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.1)
            self.button.when_pressed = self.on_button_press
            print(f"✓ Front button configured on GPIO {BUTTON_PIN} (press to toggle listening)")
            
            # Setup shutdown button (back switch)
            try:
                self.shutdown_button = Button(SHUTDOWN_PIN, pull_up=True, bounce_time=0.2)
                self.shutdown_button.when_pressed = self.on_shutdown_press
                print(f"✓ Shutdown button configured on GPIO {SHUTDOWN_PIN} (press to shutdown Pi)")
            except Exception as e:
                print(f"⚠️  Shutdown button setup failed: {e}")
                self.shutdown_button = None
        else:
            self.button = None
            self.shutdown_button = None
            self.listening_active = True  # Always active on Mac
            print("⚠️  No button - listening always active")

    def on_button_press(self):
        """Front button pressed - toggle listening (called from GPIO thread)"""
        if self.listening_active:
            print("🔘 Button pressed - STOPPING listening")
            self.listening_active = False
            if self.audio_capture_task:
                self.audio_capture_task.cancel()
                self.audio_capture_task = None
            # Queue goodbye message
            self.pending_text = "Goodbye! Press the button if you need me again."
        else:
            print("🔘 Button pressed - STARTING listening")
            self.listening_active = True
            self.last_activity_time = time.time()
            # Queue greeting message
            self.pending_text = "Hi! My name is Billy. How can I help you today?"
    
    def on_shutdown_press(self):
        """Back shutdown button pressed - shutdown the Pi (called from GPIO thread)"""
        import subprocess
        print("🔴 SHUTDOWN button pressed - powering down Pi...")
        try:
            # Run shutdown command
            subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
        except Exception as e:
            print(f"⚠️  Shutdown failed: {e}")
            print("Make sure the script has sudo permissions or add to sudoers:")
    
    async def say_text(self, text: str):
        """Make Billy speak using text input (crossmodal)"""
        try:
            # Send text content to make Billy speak
            content_name = f"text_{time.time()}"
            
            # Start text content as USER (not ASSISTANT)
            text_content_start = f'''
            {{
                "event": {{
                    "contentStart": {{
                        "promptName": "{self.client.prompt_name}",
                        "contentName": "{content_name}",
                        "type": "TEXT",
                        "interactive": false,
                        "role": "USER",
                        "textInputConfiguration": {{
                            "mediaType": "text/plain"
                        }}
                    }}
                }}
            }}
            '''
            await self.client.send_event(text_content_start)
            
            # Send text as a prompt to respond to
            text_input = f'''
            {{
                "event": {{
                    "textInput": {{
                        "promptName": "{self.client.prompt_name}",
                        "contentName": "{content_name}",
                        "content": "Say this exact phrase: {text}"
                    }}
                }}
            }}
            '''
            await self.client.send_event(text_input)
            
            # End text content
            text_content_end = f'''
            {{
                "event": {{
                    "contentEnd": {{
                        "promptName": "{self.client.prompt_name}",
                        "contentName": "{content_name}"
                    }}
                }}
            }}
            '''
            await self.client.send_event(text_content_end)
        except Exception as e:
            print(f"⚠️  Error sending text: {e}")

    def on_audio_chunk(self, chunk: bytes):
        # Drive mouth during playback
        opening = self.billy.mouth_controller.process_audio_chunk(chunk)
        self.billy.drive_mouth(opening)
        
        # Torso up when speaking starts
        if not self.speaking:
            self.billy.torso_start()
            self.speaking = True
        
        # Update activity time
        self.last_activity_time = time.time()

    async def run(self):
        await self.client.start_session()

        self.audio_play_task = asyncio.create_task(self.client.play_audio())
        
        # Only start capture if button pressed or no button available
        if self.listening_active:
            self.audio_capture_task = asyncio.create_task(self.client.capture_audio())
        
        # Simple idle wag
        asyncio.create_task(self.idle_wag())

        try:
            while True:
                # Check if tasks are still alive
                if self.audio_play_task and self.audio_play_task.done():
                    print("⚠️  Audio playback task died, restarting...")
                    self.audio_play_task = asyncio.create_task(self.client.play_audio())
                
                if self.audio_capture_task and self.audio_capture_task.done() and self.listening_active:
                    print("⚠️  Audio capture task died, restarting...")
                    self.audio_capture_task = asyncio.create_task(self.client.capture_audio())
                
                # Check for pending text to speak
                if self.pending_text:
                    text = self.pending_text
                    self.pending_text = None
                    await self.say_text(text)
                
                # Check for inactivity timeout
                if self.listening_active and BUTTON_AVAILABLE:
                    if time.time() - self.last_activity_time > INACTIVITY_TIMEOUT:
                        print(f"⏱️  Inactivity timeout ({INACTIVITY_TIMEOUT}s) - deactivating listening")
                        self.listening_active = False
                        if self.audio_capture_task:
                            self.audio_capture_task.cancel()
                            self.audio_capture_task = None
                        # Say goodbye
                        await self.say_text("I haven't heard from you in a while. Goodbye for now!")
                
                # Start capture if button was pressed and not already capturing
                if self.listening_active and not self.audio_capture_task:
                    print("🎤 Starting audio capture...")
                    self.audio_capture_task = asyncio.create_task(self.client.capture_audio())
                
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
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.client.end_session()
            if self.audio_play_task:
                self.audio_play_task.cancel()
            if self.audio_capture_task:
                self.audio_capture_task.cancel()
            if self.button:
                self.button.close()
            if self.shutdown_button:
                self.shutdown_button.close()
            self.billy.stop_all()
            print("✓ Cleanup complete")
    
    async def idle_wag(self):
        """Wag tail when idle and listening is active"""
        try:
            while True:
                await asyncio.sleep(3.0)
                # Only wag if listening is active and not speaking
                if self.listening_active and not self.speaking and self.billy.torso:
                    self.billy.torso.throttle = 0.3 * TORSO_DIR
                    await asyncio.sleep(0.15)
                    self.billy.torso.throttle = -0.3 * TORSO_DIR
                    await asyncio.sleep(0.15)
                    self.billy.torso.throttle = 0
        except Exception as e:
            print(f"⚠️  Idle wag error: {e}")


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
