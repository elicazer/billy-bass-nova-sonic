#!/usr/bin/env python3
"""
Billy Bass with Gemini AI
Animates a Big Mouth Billy Bass using Raspberry Pi 5 and Gemini 3 Flash API
"""

import os
import time
import wave
import pyaudio
import numpy as np
from gpiozero import Motor
import google.generativeai as genai
from gtts import gTTS
from pathlib import Path
import tempfile

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Set this in your environment
MOUTH_MOTOR_PINS = (17, 27)  # GPIO pins for mouth motor (forward, backward)
TAIL_MOTOR_PINS = (22, 23)   # GPIO pins for tail motor (optional)
HEAD_MOTOR_PINS = (24, 25)   # GPIO pins for head motor (optional)

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # 16kHz for better compatibility with Gemini
RECORD_SECONDS = 5  # Max recording time
THRESHOLD = 500  # Amplitude threshold for mouth movement
SILENCE_THRESHOLD = 300  # Threshold to detect end of speech

class BillyBass:
    def __init__(self):
        # Initialize motors
        self.mouth = Motor(forward=MOUTH_MOTOR_PINS[0], backward=MOUTH_MOTOR_PINS[1])
        self.tail = Motor(forward=TAIL_MOTOR_PINS[0], backward=TAIL_MOTOR_PINS[1])
        self.head = Motor(forward=HEAD_MOTOR_PINS[0], backward=HEAD_MOTOR_PINS[1])
        
        # Initialize Gemini with 3 Flash Preview
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-3-flash-preview')
        self.chat = self.model.start_chat(history=[])
        
        # Audio player
        self.audio = pyaudio.PyAudio()
        
    def close_mouth(self):
        """Close the mouth"""
        self.mouth.forward(0.5)
        time.sleep(0.1)
        self.mouth.stop()
        
    def open_mouth(self):
        """Open the mouth"""
        self.mouth.backward(0.5)
        time.sleep(0.1)
        self.mouth.stop()
        
    def animate_mouth(self, audio_data, sample_rate):
        """Animate mouth based on audio amplitude"""
        # Convert audio data to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate amplitude in chunks
        chunk_size = int(sample_rate * 0.05)  # 50ms chunks
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
        """Record audio from microphone until silence detected"""
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
            
            # Check amplitude to detect speech
            audio_data = np.frombuffer(data, dtype=np.int16)
            amplitude = np.abs(audio_data).mean()
            
            if amplitude > SILENCE_THRESHOLD:
                recording = True
                silent_chunks = 0
            elif recording:
                silent_chunks += 1
                # Stop if 1 second of silence after speech
                if silent_chunks > int(RATE / CHUNK * 1):
                    break
        
        stream.stop_stream()
        stream.close()
        
        if not recording:
            print("No speech detected")
            return None
        
        # Save to temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
        
        return temp_file.name
    
    def get_gemini_response(self, audio_file):
        """Get response from Gemini using native audio input"""
        print("Thinking...")
        
        # Upload audio file
        audio_file_obj = genai.upload_file(audio_file)
        
        # Send to Gemini with audio
        response = self.chat.send_message([
            "Listen to this audio and respond naturally as a talking fish.",
            audio_file_obj
        ])
        
        # Clean up uploaded file
        genai.delete_file(audio_file_obj.name)
        
        return response.text
    
    def speak(self, text):
        """Convert text to speech and animate"""
        print(f"Billy says: {text}")
        
        # Generate speech
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            temp_file = fp.name
        
        tts = gTTS(text=text, lang='en')
        tts.save(temp_file)
        
        # Convert to WAV for processing
        wav_file = temp_file.replace('.mp3', '.wav')
        os.system(f'ffmpeg -i {temp_file} -acodec pcm_s16le -ar {RATE} {wav_file} -y -loglevel quiet')
        
        # Play audio and animate mouth
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
        
        # Animate mouth based on audio
        with wave.open(wav_file, 'rb') as wf:
            audio_data = wf.readframes(wf.getnframes())
            self.animate_mouth(audio_data, wf.getframerate())
        
        # Cleanup
        os.remove(temp_file)
        os.remove(wav_file)
    
    def run(self):
        """Main loop"""
        print("Billy Bass is ready! Say something...")
        
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
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.mouth.close()
        self.tail.close()
        self.head.close()
        self.audio.terminate()

if __name__ == "__main__":
    billy = BillyBass()
    billy.run()
