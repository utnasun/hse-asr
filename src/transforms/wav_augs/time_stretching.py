import random

import torchaudio


class TimeStretching:
    def __init__(self, rate_range=(0.8, 1.2)):
        self.rate_range = rate_range

    def __call__(self, waveform, sample_rate=16000):
        rate = random.uniform(*self.rate_range)
        new_sample_rate = int(sample_rate * rate)

        stretched_waveform = torchaudio.functional.resample(
            waveform, orig_freq=sample_rate, new_freq=new_sample_rate
        )
        return stretched_waveform
