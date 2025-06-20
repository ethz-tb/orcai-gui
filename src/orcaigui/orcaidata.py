from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class OrcaiData:
    recording_path: Path
    channel: int
    spectrogram: np.ndarray
    frequencies: np.ndarray
    times: np.ndarray
    pp_spectrogram: np.ndarray
    aggregated_predictions: np.ndarray
    prediction_times: np.ndarray
    predicted_labels: pd.DataFrame

    def save_to_hdf5_file(self):
        pass
