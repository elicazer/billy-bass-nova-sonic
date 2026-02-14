#!/usr/bin/env python3
"""
Billy Bass with Gemini AI - Cross Platform Version
Works on Mac (development/testing) and Raspberry Pi (production)
"""

import os
import sys
import time
import wave
import pyaudio
import numpy as np
import google.generativeai as genai
from gtts import gTTS
import tempfile
import platform
import re
os.environ.setdefault("BLINKA_FORCECHIP_ID", "GENERIC_LINUX")

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
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Motor port assignments (FeatherWing: M2 = mouth, M1 = torso/tail)
MOUTH_MOTOR = 2  # Connected to A2/B2
TAIL_MOTOR = 1   # Connected to A1/B1 (torso/tail)
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
WAIT_AFTER_SPEAK = 1.0  # Cooldown so TTS doesn't get re-recorded
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

class BillyBass:
    def __init__(self):
        print(f"\n{'='*50}")
        print(f"Billy Bass Initialization")
        print(f"{'='*50}")
        print(f"Platform: {platform.system()}")
        print(f"Motor Library: {MOTOR_LIB or 'DEMO MODE'}")
        print(f"Demo Mode: {DEMO_MODE}")
        
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
        
        # Initialize Gemini
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-3-flash-preview')
            self.chat = self.model.start_chat(history=[])
            print("✓ Gemini AI initialized")
        else:
            print("⚠ GEMINI_API_KEY not set - AI features disabled")
            self.model = None
            self.chat = None
        
        # Audio
        try:
            self.audio = pyaudio.PyAudio()
            print("✓ Audio initialized")
            self._list_audio_devices()
        except Exception as e:
            print(f"⚠ Audio initialization failed: {e}")
            self.audio = None

        # Mouth controller for smoother movement
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
                4: self.kit.motor4
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
        # Compute duty in window
        duty_used = sum(d for _, d in self._duty_window)
        if duty_used >= MOUTH_MAX_DUTY * MOUTH_DUTY_WINDOW_SEC:
            # Skip pulse to respect duty cap
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

        # Record duty (duration counts as "on" time)
        self._duty_window.append((time.time(), duration))

    def _apply_mouth_opening(self, opening):
        """Map opening percentage (0-100) to motor pulses."""
        # Opening <8% treated as closed to reduce chatter
        if opening < MOUTH_MIN_OPEN_PCT:
            self._pulse_mouth("close", intensity=0.35, duration=0.03)
            self._last_opening = 0
            return

        # Scale intensity with opening (more opening -> stronger pulse)
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
                frames_per_buffer=CHUNK
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
        
        # Save to temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        
        return temp_file.name
    
    def get_gemini_response(self, audio_file):
        """Get response from Gemini using native audio"""
        if not self.model:
            return "Gemini AI is not configured. Please set GEMINI_API_KEY environment variable."
        
        print("🤔 Thinking...")
        
        try:
            # Upload audio file
            audio_file_obj = genai.upload_file(audio_file)
            
            # Use a fresh chat each turn so deleted files aren't referenced from history
            chat = self.model.start_chat(history=[])
            
            # Send to Gemini with audio
            response = chat.send_message([
                "You are a friendly, natural-sounding voice assistant for an animatronic display. "
                "Respond conversationally in 1-2 sentences. Avoid emojis, sound effects, stage directions, or fish jokes.",
                audio_file_obj
            ])
            
            # Clean up uploaded file
            genai.delete_file(audio_file_obj.name)
            
            return self._sanitize_text(response.text)
        except Exception as e:
            print(f"⚠ Gemini error: {e}")
            return "Sorry, I had trouble understanding that!"
    
    def speak(self, text):
        """Convert text to speech and animate"""
        text = self._sanitize_text(text)
        print(f"🐟 Billy says: {text}")
        
        # Generate speech
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            temp_file = fp.name
        
        try:
            tts = gTTS(text=text, lang='en')
            tts.save(temp_file)
        except Exception as e:
            print(f"⚠ TTS error: {e}")
            return
        
        # Convert to WAV for processing
        wav_file = temp_file.replace('.mp3', '.wav')
        
        # Use ffmpeg if available, otherwise skip animation
        if os.system(f'which ffmpeg > /dev/null 2>&1') == 0:
            os.system(f'ffmpeg -i {temp_file} -acodec pcm_s16le -ar {RATE} {wav_file} -y -loglevel quiet')
            
            # Play audio and animate mouth
            if self.audio:
                try:
                    with wave.open(wav_file, 'rb') as wf:
                        stream = self.audio.open(
                            format=self.audio.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True
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
        else:
            print("⚠ ffmpeg not found - skipping audio playback")
            print("  Install with: brew install ffmpeg (Mac) or sudo apt install ffmpeg (Pi)")
        
        os.remove(temp_file)

    @staticmethod
    def _sanitize_text(text):
        """Remove emojis and common emoticon markers for cleaner, natural TTS."""
        if not text:
            return ""
        text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
        text = re.sub(r'[:;]-?[)D\(Pp]', '', text)
        text = ' '.join(text.split())
        return text.strip()
    
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
        print("🐟 Billy Bass is ready!")
        print("Commands:")
        print("  - Speak to talk to Billy")
        print("  - Press Ctrl+C to quit")
        print("  - Type 'test' to test motors")
        print()
        
        try:
            while True:
                # Record audio
                audio_file = self.record_audio()
                
                if audio_file:
                    # Get Gemini response using native audio
                    response = self.get_gemini_response(audio_file)
                    
                    # Clean up recorded audio
                    os.remove(audio_file)
                    
                    # Speak and animate
                    self.speak(response)
                
                time.sleep(WAIT_AFTER_SPEAK)
                
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if MOTOR_LIB == "adafruit" and hasattr(self, 'mouth'):
            if self.mouth:
                self.mouth.throttle = 0
            if self.tail:
                self.tail.throttle = 0
            if self.head:
                self.head.throttle = 0
        
        if self.audio:
            self.audio.terminate()
        
        print("✓ Cleanup complete")

if __name__ == "__main__":
    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        billy = BillyBass()
        billy.test_motors()
    else:
        billy = BillyBass()
        billy.run()
