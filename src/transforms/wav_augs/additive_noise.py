import random

import torch


class AdditiveNoise:
    def __init__(self, noise_level=(0.01, 0.05)):
        self.noise_level = noise_level

    def __call__(self, waveform):
        noise = torch.randn_like(waveform) * random.uniform(*self.noise_level)
        return waveform + noise
