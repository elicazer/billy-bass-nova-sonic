#!/usr/bin/env python3
"""
Billy Bass with Amazon Nova (Bedrock) + Amazon Transcribe + Polly
Mac-friendly demo mode for motors; uses AWS for AI/voice.
"""

import os
import sys
import json
import time
import wave
import asyncio
import tempfile
import platform
os.environ.setdefault("BLINKA_FORCECHIP_ID", "GENERIC_LINUX")

import numpy as np
import pyaudio
import boto3
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
import re
from audio_mouth_controller import AudioMouthController

# Detect platform
IS_MAC = platform.system() == "Darwin"
IS_PI = platform.system() == "Linux" and "arm" in platform.machine().lower()

print(f"Running on: {platform.system()} ({platform.machine()})")

# Try to import motor control libraries
MOTOR_LIB = None
try:
    from adafruit_motorkit import MotorKit
    MOTOR_LIB = "adafruit"
    print("✓ Adafruit MotorKit library found")
except Exception as e:
    # Blinka can raise NotImplementedError on non-Pi platforms
    print(f"⚠ Adafruit MotorKit unavailable ({e.__class__.__name__}: {e}) - will run in demo mode")

# Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
NOVA_MODEL_ID = os.getenv("NOVA_MODEL_ID", "amazon.nova-pro-v1:0")
# Default to an older-male voice; override via POLLY_VOICE_ID if desired
POLLY_VOICE_ID = os.getenv("POLLY_VOICE_ID", "Matthew")

# Motor port assignments (FeatherWing wiring: M2 mouth, M1 torso)
MOUTH_MOTOR = 2  # Connected to A2/B2
TAIL_MOTOR = 1   # Connected to A1/B1 (tail and torso)
HEAD_MOTOR = None

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 10
THRESHOLD = 500
SILENCE_THRESHOLD = 300
MIN_SPEECH_SECONDS = 0.8
SILENCE_TIMEOUT_SECONDS = 1.5
WAIT_AFTER_SPEAK = 1.0
# Mouth safety tuning
MOUTH_MIN_OPEN_PCT = 12      # deadband to prevent chatter
MOUTH_INTENSITY_MIN = 0.20   # lower bound for pulse intensity
MOUTH_INTENSITY_MAX = 0.75   # upper bound to avoid slamming
MOUTH_DURATION_MIN = 0.020   # seconds
MOUTH_DURATION_MAX = 0.055   # seconds
MOUTH_DUTY_WINDOW_SEC = 3.0  # rolling window to measure duty
MOUTH_MAX_DUTY = 0.45        # max fraction of time motor may be powered in window

# Demo mode settings
DEMO_MODE = MOTOR_LIB is None


class MockMotor:
    """Mock motor for testing without hardware"""

    def __init__(self, name):
        self.name = name
        self.throttle = 0

    def __setattr__(self, name, value):
        if name == "throttle":
            if value != 0:
                print(f"  🔧 {self.__dict__.get('name', 'Motor')} throttle: {value}")
        super().__setattr__(name, value)


class _TranscriptHandler(TranscriptResultStreamHandler):
    """Collects final transcripts from Transcribe events."""

    def __init__(self, output_stream):
        super().__init__(output_stream)
        self.parts = []

    async def handle_transcript_event(self, event: TranscriptEvent):
        for result in event.transcript.results:
            if result.is_partial:
                continue
            for alt in result.alternatives:
                self.parts.append(alt.transcript)


class BillyBassNova:
    def __init__(self):
        print(f"\n{'='*50}")
        print(f"Billy Bass (Amazon Nova) Initialization")
        print(f"{'='*50}")
        print(f"Platform: {platform.system()}")
        print(f"Motor Library: {MOTOR_LIB or 'DEMO MODE'}")
        print(f"Demo Mode: {DEMO_MODE}")
        print(f"AWS Region: {AWS_REGION}")

        # Initialize motors
        if MOTOR_LIB == "adafruit":
            try:
                self.kit = MotorKit()
                self.mouth = self._get_motor(MOUTH_MOTOR)
                self.tail = self._get_motor(TAIL_MOTOR) if TAIL_MOTOR else None
                self.head = self._get_motor(HEAD_MOTOR) if HEAD_MOTOR else None
                print("✓ Motors initialized")
            except Exception as e:
                print(f"⚠ Motor initialization failed: {e}")
                print("  Falling back to demo mode")
                self._init_demo_motors()
        else:
            self._init_demo_motors()

        # AWS clients
        try:
            self.bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)
            self.polly = boto3.client("polly", region_name=AWS_REGION)
            print("✓ AWS clients initialized (Bedrock, Polly)")
        except Exception as e:
            print(f"⚠ AWS client init failed: {e}")
            self.bedrock = None
            self.polly = None

        # Audio
        try:
            self.audio = pyaudio.PyAudio()
            print("✓ Audio initialized")
            self._list_audio_devices()
        except Exception as e:
            print(f"⚠ Audio initialization failed: {e}")
            self.audio = None

        # Mouth controller for smoother animation
        self.mouth_controller = AudioMouthController(sample_rate=RATE)
        self._last_opening = 0.0
        self._duty_window = []

        print(f"{'='*50}\n")

    def _init_demo_motors(self):
        """Initialize mock motors for demo mode"""
        self.mouth = MockMotor("Mouth")
        self.tail = MockMotor("Tail") if TAIL_MOTOR else None
        self.head = MockMotor("Head") if HEAD_MOTOR else None
        print("✓ Demo motors initialized")

    def _list_audio_devices(self):
        """List available audio devices"""
        if not self.audio:
            return
        print("\nAvailable audio devices:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            print(f"  [{i}] {info['name']} (in:{info['maxInputChannels']}, out:{info['maxOutputChannels']})")

    def _get_motor(self, port):
        """Get motor object by port number"""
        if MOTOR_LIB == "adafruit":
            motors = {
                1: self.kit.motor1,
                2: self.kit.motor2,
                3: self.kit.motor3,
                4: self.kit.motor4,
            }
            return motors.get(port)
        return None

    def close_mouth(self):
        """Close the mouth"""
        if self.mouth:
            if MOTOR_LIB == "adafruit":
                self.mouth.throttle = 0.5
                time.sleep(0.1)
                self.mouth.throttle = 0
            else:
                self.mouth.throttle = 0.5
                time.sleep(0.05)
                self.mouth.throttle = 0

    def open_mouth(self):
        """Open the mouth"""
        if self.mouth:
            if MOTOR_LIB == "adafruit":
                self.mouth.throttle = -0.5
                time.sleep(0.1)
                self.mouth.throttle = 0
            else:
                self.mouth.throttle = -0.5
                time.sleep(0.05)
                self.mouth.throttle = 0

    def _pulse_mouth(self, direction, intensity=0.5, duration=0.04):
        """Apply a short throttle pulse; direction='open' or 'close'."""
        if not self.mouth:
            return

        now = time.time()
        # Drop old duty samples
        self._duty_window = [(t, d) for (t, d) in self._duty_window if now - t <= MOUTH_DUTY_WINDOW_SEC]
        duty_used = sum(d for _, d in self._duty_window)
        if duty_used >= MOUTH_MAX_DUTY * MOUTH_DUTY_WINDOW_SEC:
            return

        intensity = max(0.1, min(1.0, intensity))
        val = -intensity if direction == "open" else intensity
        if MOTOR_LIB == "adafruit":
            self.mouth.throttle = val
            time.sleep(duration)
            self.mouth.throttle = 0
        else:
            self.mouth.throttle = val
            time.sleep(duration / 2)
            self.mouth.throttle = 0

        self._duty_window.append((time.time(), duration))

    def _apply_mouth_opening(self, opening):
        """Map opening percentage (0-100) to motor pulses."""
        if opening < MOUTH_MIN_OPEN_PCT:
            self._pulse_mouth("close", intensity=0.35, duration=0.03)
            self._last_opening = 0
            return

        intensity = MOUTH_INTENSITY_MIN + (opening / 100) * (MOUTH_INTENSITY_MAX - MOUTH_INTENSITY_MIN)
        duration = MOUTH_DURATION_MIN + (opening / 100) * (MOUTH_DURATION_MAX - MOUTH_DURATION_MIN)
        self._pulse_mouth("open", intensity=intensity, duration=duration)
        self._last_opening = opening

    def animate_mouth(self, audio_data, sample_rate):
        """Animate mouth based on audio amplitude"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        chunk_size = int(sample_rate * 0.05)
        for i in range(0, len(audio_array), chunk_size):
            chunk = audio_array[i:i+chunk_size]
            amplitude = np.abs(chunk).mean()
            if amplitude > THRESHOLD:
                self.open_mouth()
            else:
                self.close_mouth()
            time.sleep(0.05)
        self.close_mouth()

    def record_audio(self):
        """Record audio from microphone"""
        if not self.audio:
            print("⚠ Audio not available")
            return None

        print("🎤 Listening... (speak now)")
        try:
            stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
            )
        except Exception as e:
            print(f"⚠ Could not open audio stream: {e}")
            return None

        frames = []
        silent_chunks = 0
        recording = False
        speech_chunks = 0
        min_speech_chunks = int((RATE / CHUNK) * MIN_SPEECH_SECONDS)
        silence_limit_chunks = int((RATE / CHUNK) * SILENCE_TIMEOUT_SECONDS)

        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                audio_data = np.frombuffer(data, dtype=np.int16)
                amplitude = np.abs(audio_data).mean()
                if amplitude > SILENCE_THRESHOLD:
                    recording = True
                    speech_chunks += 1
                    silent_chunks = 0
                elif recording and speech_chunks >= min_speech_chunks:
                    silent_chunks += 1
                    if silent_chunks > silence_limit_chunks:
                        break
            except Exception as e:
                print(f"⚠ Error reading audio: {e}")
                break

        stream.stop_stream()
        stream.close()

        if not recording:
            print("⚠ No speech detected")
            return None

        print("✓ Audio recorded")

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        with wave.open(temp_file.name, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(frames))
        return temp_file.name

    async def _transcribe_async(self, wav_file):
        """Stream audio to Amazon Transcribe and return transcript text."""
        client = TranscribeStreamingClient(region=AWS_REGION)
        stream = await client.start_stream_transcription(
            language_code="en-US",
            media_sample_rate_hz=RATE,
            media_encoding="pcm",
        )

        async def write_chunks():
            with wave.open(wav_file, "rb") as wf:
                data = wf.readframes(CHUNK)
                while data:
                    await stream.input_stream.send_audio_event(audio_chunk=data)
                    data = wf.readframes(CHUNK)
            await stream.input_stream.end_stream()

        handler = _TranscriptHandler(stream.output_stream)
        await asyncio.gather(write_chunks(), handler.handle_events())
        return " ".join(handler.parts).strip()

    def transcribe_audio(self, wav_file):
        """Sync wrapper for Transcribe streaming."""
        try:
            return asyncio.run(self._transcribe_async(wav_file))
        except Exception as e:
            print(f"⚠ Transcribe error: {e}")
            return ""

    def get_nova_response(self, text_prompt):
        """Get response text from Amazon Nova via Bedrock."""
        if not self.bedrock:
            return "Nova is not configured. Check AWS credentials/region."
        print("🤔 Thinking (Nova)...")
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"text": "You are a friendly, natural-sounding voice assistant for an animatronic display. "
                                 "Respond conversationally in 1-2 sentences. Avoid emojis, sound effects, or stage directions."},
                        {"text": text_prompt},
                    ],
                }
            ],
            "inferenceConfig": {"temperature": 0.7, "maxTokens": 256, "topP": 0.9},
        }
        try:
            resp = self.bedrock.invoke_model(
                modelId=NOVA_MODEL_ID,
                body=json.dumps(payload),
                contentType="application/json",
                accept="application/json",
            )
            body = resp.get("body")
            if hasattr(body, "read"):
                body = body.read()
            data = json.loads(body)
            # Bedrock message response format
            msg = data.get("output", {}).get("message", {})
            parts = msg.get("content", [])
            for part in parts:
                if "text" in part:
                    return part["text"]
            # Fallback to legacy text field if present
            return data.get("outputText", "Sorry, I could not think of a reply.")
        except Exception as e:
            print(f"⚠ Nova error: {e}")
            return "Sorry, Nova had an issue responding."

    def synthesize_voice(self, text):
        """Convert text to speech with Polly and animate."""
        text = self._sanitize_text(text)
        if not self.polly:
            print("⚠ Polly not available")
            return
        try:
            resp = self.polly.synthesize_speech(
                Text=text,
                VoiceId=POLLY_VOICE_ID,
                OutputFormat="pcm",
                SampleRate=str(RATE),
            )
            audio_bytes = resp["AudioStream"].read()
        except Exception as e:
            print(f"⚠ Polly error: {e}")
            return

        # Write PCM to WAV for playback/animation
        wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        with wave.open(wav_file, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(RATE)
            wf.writeframes(audio_bytes)

        # Play and animate
        if self.audio:
            try:
                with wave.open(wav_file, "rb") as wf:
                    stream = self.audio.open(
                        format=self.audio.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True,
                    )
                    data = wf.readframes(CHUNK)
                    while data:
                        stream.write(data)
                        opening = self.mouth_controller.process_audio_chunk(data)
                        self._apply_mouth_opening(opening)
                        data = wf.readframes(CHUNK)
                    stream.stop_stream()
                    stream.close()
                self.close_mouth()
                self.mouth_controller.reset()
            except Exception as e:
                print(f"⚠ Audio playback error: {e}")
        os.remove(wav_file)

    def test_motors(self):
        """Test motor movements"""
        print("\n🔧 Testing motors...")
        print("Watch the motors move!\n")

        print("Testing mouth - OPEN")
        self.open_mouth()
        time.sleep(1)

        print("Testing mouth - CLOSE")
        self.close_mouth()
        time.sleep(1)

        if self.tail:
            print("Testing tail - FORWARD")
            if MOTOR_LIB == "adafruit":
                self.tail.throttle = 0.5
                time.sleep(1)
                self.tail.throttle = 0
            else:
                self.tail.throttle = 0.5
                time.sleep(0.5)
                self.tail.throttle = 0

            print("Testing tail - BACKWARD")
            if MOTOR_LIB == "adafruit":
                self.tail.throttle = -0.5
                time.sleep(1)
                self.tail.throttle = 0
            else:
                self.tail.throttle = -0.5
                time.sleep(0.5)
                self.tail.throttle = 0

        print("✓ Motor test complete\n")

    def run(self):
        """Main loop"""
        print("🐟 Billy Bass (Nova) is ready!")
        print("Commands:")
        print("  - Speak to talk to Billy")
        print("  - Press Ctrl+C to quit")
        print("  - Type 'test' to test motors")
        print()

        try:
            while True:
                audio_file = self.record_audio()
                if audio_file:
                    transcript = self.transcribe_audio(audio_file)
                    os.remove(audio_file)
                    if not transcript:
                        print("⚠ No transcript received")
                        continue
                    response = self.get_nova_response(transcript)
                    self.synthesize_voice(response)
                time.sleep(WAIT_AFTER_SPEAK)
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        if MOTOR_LIB == "adafruit" and hasattr(self, "mouth"):
            if self.mouth:
                self.mouth.throttle = 0
            if self.tail:
                self.tail.throttle = 0
            if self.head:
                self.head.throttle = 0
        if self.audio:
            self.audio.terminate()
        print("✓ Cleanup complete")

    @staticmethod
    def _sanitize_text(text):
        """Remove emojis and common emoticon markers for cleaner, natural TTS."""
        if not text:
            return ""
        text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
        text = re.sub(r'[:;]-?[)D\(Pp]', '', text)
        text = ' '.join(text.split())
        return text.strip()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        billy = BillyBassNova()
        billy.test_motors()
    else:
        billy = BillyBassNova()
        billy.run()
