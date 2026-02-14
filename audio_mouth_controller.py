"""
Audio-driven mouth controller adapted from AI Robot Assistant project.
Provides smoothed amplitude → mouth opening mapping for more natural movement.
"""

import numpy as np
from collections import deque


class AudioMouthController:
    """
    Controls mouth movement based on audio amplitude using a sliding window.
    """

    def __init__(
        self,
        sample_rate=16000,
        smoothing_window=3,
        min_threshold=0.015,
        max_threshold=0.25,
        close_speed=0.7,
    ):
        self.sample_rate = sample_rate
        self.smoothing_window = smoothing_window
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.close_speed = close_speed

        self.amplitude_history = deque(maxlen=smoothing_window)
        self.current_opening = 0.0
        self.target_opening = 0.0
        self.is_speaking = False
        self.silence_counter = 0

    def process_audio_chunk(self, audio_bytes):
        """Return mouth opening percentage (0-100) for a chunk of 16-bit PCM."""
        if not audio_bytes:
            return 0.0

        audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
        if audio_data.size == 0:
            return 0.0

        rms = np.sqrt(np.mean(audio_data.astype(float) ** 2))
        normalized_amplitude = rms / 32768.0  # 16-bit max

        self.amplitude_history.append(normalized_amplitude)
        smoothed_amplitude = float(np.mean(self.amplitude_history))

        if smoothed_amplitude < self.min_threshold:
            self.target_opening = 0.0
            self.silence_counter += 1
            self.is_speaking = False
        else:
            normalized = (smoothed_amplitude - self.min_threshold) / (
                self.max_threshold - self.min_threshold
            )
            normalized = max(0.0, min(1.0, normalized))
            self.target_opening = (normalized ** 0.8) * 100.0
            self.silence_counter = 0
            self.is_speaking = self.target_opening > 3

        if self.target_opening < self.current_opening:
            step = (self.current_opening - self.target_opening) * self.close_speed
            self.current_opening = max(self.target_opening, self.current_opening - step)
        else:
            step = (self.target_opening - self.current_opening) * 0.4
            self.current_opening = min(self.target_opening, self.current_opening + step)

        if self.silence_counter > 2:
            self.current_opening = 0.0

        return self.current_opening

    def reset(self):
        """Reset internal state."""
        self.amplitude_history.clear()
        self.current_opening = 0.0
        self.target_opening = 0.0
        self.is_speaking = False
        self.silence_counter = 0
