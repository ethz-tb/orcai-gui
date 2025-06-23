from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from orcAI.io import save_predictions


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

    def n_labels(self) -> int | None:
        if self.predicted_labels is None:
            return None
        return len(self.predicted_labels)

    def delta_t(self) -> float | None:
        """Calculate the time step between consecutive time points."""
        if self.times is None or len(self.times) < 2:
            return 0.0
        return self.times[1] - self.times[0]

    def duration(self) -> float | None:
        """Calculate the duration of the recording in seconds."""
        if self.times is None or len(self.times) == 0:
            return None
        return self.times[-1] - self.times[0]

    def export_labels_as_tsv(self, file_path: Path) -> None:
        """export labels to a TSV file compatible with Audacity."""
        save_predictions(
            predicted_labels=self.predicted_labels[
                self.predicted_labels["label_ok"] == True  # noqa: E712
            ],
            output_path=file_path,
            delta_t=self.delta_t(),
            columns=[
                "start",
                "stop",
                "label",
                "label_checked",
                "label_ok",
                "label_source",
            ],
        )

    def save_as_hdf5(self, file_path: Path) -> None:
        """Save OrcaiData to an HDF5 file."""
        with h5py.File(file_path, "w") as f:
            f.create_dataset("spectrogram", data=self.spectrogram)
            f.create_dataset("frequencies", data=self.frequencies)
            f.create_dataset("times", data=self.times)
            f.create_dataset("pp_spectrogram", data=self.pp_spectrogram)
            f.create_dataset("aggregated_predictions", data=self.aggregated_predictions)
            f.create_dataset("prediction_times", data=self.prediction_times)
            f.create_group("predicted_labels")
            for series_name, series in self.predicted_labels.items():
                f["predicted_labels"].create_dataset(
                    series_name, data=series.to_numpy()
                )
            f.attrs["recording_path"] = str(self.recording_path)
            f.attrs["channel"] = self.channel

    @classmethod
    def load_from_hdf5_file(cls, file_path: Path) -> "OrcaiData":
        """Load OrcaiData from an HDF5 file."""
        with h5py.File(file_path, "r") as f:
            recording_path = Path(f.attrs["recording_path"])
            channel = f.attrs["channel"]
            spectrogram = f["spectrogram"][:]
            frequencies = f["frequencies"][:]
            times = f["times"][:]
            pp_spectrogram = f["pp_spectrogram"][:]
            aggregated_predictions = f["aggregated_predictions"][:]
            prediction_times = f["prediction_times"][:]
            predicted_labels = pd.DataFrame(
                {name: f["predicted_labels"][name][:] for name in f["predicted_labels"]}
            )
            predicted_labels["label"] = predicted_labels["label"].astype("str")
            predicted_labels["label_source"] = predicted_labels["label_source"].astype(
                "str"
            )

        return cls(
            recording_path,
            channel,
            spectrogram,
            frequencies,
            times,
            pp_spectrogram,
            aggregated_predictions,
            prediction_times,
            predicted_labels,
        )
