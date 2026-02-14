#!/usr/bin/env python3
"""
Billy Bass with Gemini AI - Motor HAT Version
Animates a Big Mouth Billy Bass using Raspberry Pi 5 with Motor Driver HAT
"""

import os
import time
import wave
import pyaudio
import numpy as np
import google.generativeai as genai
from gtts import gTTS
import tempfile

# Try to import motor control libraries
try:
    from adafruit_motorkit import MotorKit
    MOTOR_LIB = "adafruit"
except ImportError:
    try:
        from gpiozero import Motor
        MOTOR_LIB = "gpiozero"
    except ImportError:
        print("No motor library found!")
        MOTOR_LIB = None

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Motor port assignments (adjust these to match your wiring)
# Motor 1 (A1/B1) = Mouth
# Motor 2 (A2/B2) = Tail/Torso
MOUTH_MOTOR = 1  # Connected to A1/B1
TAIL_MOTOR = 2   # Connected to A2/B2 (tail and torso on same motor)
HEAD_MOTOR = None  # Not connected

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5
THRESHOLD = 500
SILENCE_THRESHOLD = 300

class BillyBass:
    def __init__(self):
        print(f"Using motor library: {MOTOR_LIB}")
        
        # Initialize motors based on available library
        if MOTOR_LIB == "adafruit":
            self.kit = MotorKit()
            self.mouth = self._get_motor(MOUTH_MOTOR)
            self.tail = self._get_motor(TAIL_MOTOR) if TAIL_MOTOR else None
            self.head = self._get_motor(HEAD_MOTOR) if HEAD_MOTOR else None
        else:
            print("Warning: No motor control available. Running in demo mode.")
            self.mouth = None
            self.tail = None
            self.head = None
        
        # Initialize Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-3-flash-preview')
        self.chat = self.model.start_chat(history=[])
        
        # Audio
        self.audio = pyaudio.PyAudio()
        
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
        if self.mouth and MOTOR_LIB == "adafruit":
            self.mouth.throttle = 0.5
            time.sleep(0.1)
            self.mouth.throttle = 0
        
    def open_mouth(self):
        """Open the mouth"""
        if self.mouth and MOTOR_LIB == "adafruit":
            self.mouth.throttle = -0.5
            time.sleep(0.1)
            self.mouth.throttle = 0
    
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
        print("Listening... (speak now)")
        
        stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        frames = []
        silent_chunks = 0
        recording = False
        
        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)
            
            audio_data = np.frombuffer(data, dtype=np.int16)
            amplitude = np.abs(audio_data).mean()
            
            if amplitude > SILENCE_THRESHOLD:
                recording = True
                silent_chunks = 0
            elif recording:
                silent_chunks += 1
                if silent_chunks > int(RATE / CHUNK * 1):
                    break
        
        stream.stop_stream()
        stream.close()
        
        if not recording:
            print("No speech detected")
            return None
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        
        return temp_file.name
    
    def get_gemini_response(self, audio_file):
        """Get response from Gemini using native audio"""
        print("Thinking...")
        
        audio_file_obj = genai.upload_file(audio_file)
        
        response = self.chat.send_message([
            "Listen to this audio and respond naturally as a talking fish.",
            audio_file_obj
        ])
        
        genai.delete_file(audio_file_obj.name)
        
        return response.text
    
    def speak(self, text):
        """Convert text to speech and animate"""
        print(f"Billy says: {text}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            temp_file = fp.name
        
        tts = gTTS(text=text, lang='en')
        tts.save(temp_file)
        
        wav_file = temp_file.replace('.mp3', '.wav')
        os.system(f'ffmpeg -i {temp_file} -acodec pcm_s16le -ar {RATE} {wav_file} -y -loglevel quiet')
        
        with wave.open(wav_file, 'rb') as wf:
            stream = self.audio.open(
                format=self.audio.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )
            
            data = wf.readframes(CHUNK)
            audio_data = b''
            
            while data:
                stream.write(data)
                audio_data += data
                data = wf.readframes(CHUNK)
            
            stream.stop_stream()
            stream.close()
        
        with wave.open(wav_file, 'rb') as wf:
            audio_data = wf.readframes(wf.getnframes())
            self.animate_mouth(audio_data, wf.getframerate())
        
        os.remove(temp_file)
        os.remove(wav_file)
    
    def run(self):
        """Main loop"""
        print("Billy Bass is ready! Say something...")
        
        try:
            while True:
                audio_file = self.record_audio()
                
                if audio_file:
                    response = self.get_gemini_response(audio_file)
                    os.remove(audio_file)
                    self.speak(response)
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if self.mouth and MOTOR_LIB == "adafruit":
            self.mouth.throttle = 0
        if self.tail and MOTOR_LIB == "adafruit":
            self.tail.throttle = 0
        if self.head and MOTOR_LIB == "adafruit":
            self.head.throttle = 0
        self.audio.terminate()

if __name__ == "__main__":
    billy = BillyBass()
    billy.run()
