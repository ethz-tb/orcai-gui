from pathlib import Path

import numpy as np
from librosa import load
from orcAI.predict import (
    compute_aggregated_predictions,
    compute_binary_predictions,
    compute_labels,
)
from orcAI.spectrogram import (
    calculate_spectrogram,
    preprocess_spectrogram,
)
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal


class AudioFileLoaderSignals(QObject):
    """Signals for the AudioFileLoader class."""

    result = pyqtSignal(dict)
    progress = pyqtSignal(str)


class AudioFileLoader(QRunnable):
    def __init__(self, recording_path: Path, sampling_rate: float):
        super().__init__()
        self.signals = AudioFileLoaderSignals()
        self.recording_path = recording_path
        self.sampling_rate = sampling_rate

    def run(self):
        try:
            self.signals.progress.emit(
                f"(1/5) Loading & resampling {self.recording_path.name}..."
            )
            wav_file, _ = load(
                self.recording_path,
                sr=self.sampling_rate,
                mono=False,
            )
            n_channels = wav_file.ndim
        except Exception as e:
            self.signals.result.emit({"error": (type(e), e, e.__traceback__)})
        else:
            self.signals.result.emit(
                {
                    "recording_path": self.recording_path,
                    "wav_file": wav_file,
                    "n_channels": n_channels,
                }
            )


class SpectrogramProcessor(QRunnable):
    def __init__(
        self,
        wav_file: np.ndarray,
        recording_path: Path,
        orcai_parameter: dict,
        model,
        shape: dict,
    ):
        super().__init__()
        self.signals = AudioFileLoaderSignals()
        self.orcai_parameter = orcai_parameter
        self.shape = shape
        self.wav_file = wav_file
        self.recording_path = recording_path
        self.model = model

    def run(self):
        self.signals.progress.emit("(2/5) Calculating spectrogram...")
        try:
            spectrogram, frequencies, times = calculate_spectrogram(
                self.wav_file,
                channel=1,
                spectrogram_parameter=self.orcai_parameter["spectrogram"],
            )
        except Exception as e:
            self.signals.error.emit((type(e), e, e.__traceback__))

        self.signals.progress.emit("(3/5) Preprocessing spectrogram...")

        try:
            pp_spectrogram = preprocess_spectrogram(
                spectrogram, frequencies, self.orcai_parameter["spectrogram"]
            )
        except Exception as e:
            self.signals.result.emit({"error": (type(e), e, e.__traceback__)})
            return

        self.signals.progress.emit("(4/5) Computing predictions...")
        try:
            aggregated_predictions, overlap_count = compute_aggregated_predictions(
                recording_path=self.recording_path,
                spectrogram=pp_spectrogram,
                model=self.model,
                orcai_parameter=self.orcai_parameter,
                shape=self.shape,
            )

            prediction_times = np.arange(0, len(aggregated_predictions)) * (
                2 ** len(self.orcai_parameter["model"]["filters"])
            )
        except Exception as e:
            self.signals.result.emit({"error": (type(e), e, e.__traceback__)})
            return

        self.signals.progress.emit("5/5 Computing labels...")
        try:
            row_starts, row_stops, label_names = compute_binary_predictions(
                aggregated_predictions=aggregated_predictions,
                overlap_count=overlap_count,
                calls=self.orcai_parameter["calls"],
                threshold=0.5,
            )
            predicted_labels = compute_labels(
                row_starts,
                row_stops,
                label_names,
                time_steps_per_output_step=2
                ** len(self.orcai_parameter["model"]["filters"]),
                label_suffix="*",
            )
            predicted_labels["label_source"] = f"auto:{self.orcai_parameter['name']}"
            predicted_labels["label_checked"] = False
            predicted_labels["label_ok"] = True
        except Exception as e:
            self.signals.result.emit({"error": (type(e), e, e.__traceback__)})
            return

        self.signals.progress.emit(f"Loaded file {self.recording_path.name}")
        self.signals.result.emit(
            {
                "spectrogram": spectrogram,
                "frequencies": frequencies,
                "times": times,
                "pp_spectrogram": pp_spectrogram,
                "aggregated_predictions": aggregated_predictions,
                "prediction_times": prediction_times,
                "predicted_labels": predicted_labels,
            }
        )
