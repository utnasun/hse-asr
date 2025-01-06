import random


class TimeMasking:
    def __init__(self, max_mask_pct=0.1):
        self.max_mask_pct = max_mask_pct

    def __call__(self, spectrogram):
        max_mask = int(spectrogram.size(-1) * self.max_mask_pct)
        mask_start = random.randint(0, spectrogram.size(-1) - max_mask)
        mask_end = mask_start + max_mask
        spectrogram[:, :, mask_start:mask_end] = 0
        return spectrogram
