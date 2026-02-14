#!/usr/bin/env python3
"""Test audio input to see if microphone is working"""

import pyaudio
import numpy as np
import time

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

p = pyaudio.PyAudio()

# List devices
print("Available audio devices:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"  [{i}] {info['name']} (in:{info['maxInputChannels']}, out:{info['maxOutputChannels']})")

print("\nTesting microphone input...")
print("Device 9: MacBook Pro Microphone")
print("Speak into your microphone for 5 seconds...\n")

try:
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=9,
        frames_per_buffer=CHUNK
    )
    
    for i in range(0, int(RATE / CHUNK * 5)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        amplitude = np.abs(audio_data).mean()
        
        # Show amplitude bar
        bar_length = int(amplitude / 100)
        bar = "█" * bar_length
        print(f"\rAmplitude: {amplitude:6.0f} {bar:50s}", end="", flush=True)
        
        time.sleep(0.01)
    
    stream.stop_stream()
    stream.close()
    print("\n\n✓ Microphone test complete!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    p.terminate()
