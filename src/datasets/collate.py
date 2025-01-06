import logging
from typing import Dict, List

import torch
from torch.nn import functional as F

logger = logging.getLogger(__name__)


def collate_fn(dataset_items: List[Dict], padding_values: Dict[str, int] = None):
    """
    Collate and pad fields in dataset items.

    Args:
        dataset_items (List[Dict]): List of dataset items (dictionaries) containing fields to collate.
        padding_values (Dict[str, int]): Dictionary specifying padding values for specific keys.
            Defaults to 0 for unspecified keys.

    Returns:
        Dict: Collated and padded batch.
    """
    if padding_values is None:
        padding_values = {}

    result_batch = {}

    for key in ("text", "audio_path"):
        result_batch[key] = [el[key] for el in dataset_items]

    for key in ("audio", "spectrogram", "text_encoded"):
        tensors = [el[key] for el in dataset_items]
        lengths = [tensor.shape[-1] for tensor in tensors]

        result_batch[key + "_length"] = torch.tensor(lengths)

        fill_with = padding_values.get(key, 0)

        max_length = max(lengths)
        padded_tensors = [
            F.pad(tensor, (0, max_length - tensor.shape[-1]), value=fill_with)
            for tensor in tensors
        ]
        result_batch[key] = torch.cat(padded_tensors)

    return result_batch
