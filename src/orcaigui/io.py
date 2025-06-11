import numpy as np
from orcAI.predict import (
    compute_aggregated_predictions,
    compute_binary_predictions,
    compute_labels,
)
from orcAI.spectrogram import (
    calculate_spectrogram,
    preprocess_spectrogram,
)
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


class AudioFileLoaderSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(dict)
    progress = pyqtSignal(str)


class AudioFileLoader(QRunnable):
    def __init__(self, file_path, orcai_parameter, model, shape):
        super().__init__()
        self.signals = AudioFileLoaderSignals()
        self.orcai_parameter = orcai_parameter
        self.shape = shape
        self.file_path = file_path
        self.model = model

    @pyqtSlot()
    def run(self):
        self.signals.progress.emit("(1/4) Calculating spectrogram...")
        try:
            spectrogram, frequencies, times = calculate_spectrogram(
                self.file_path,
                channel=1,
                spectrogram_parameter=self.orcai_parameter["spectrogram"],
            )
        except Exception as e:
            print(e)
            self.signals.error.emit((type(e), e, e.__traceback__))

        self.signals.progress.emit("(2/4) Preprocessing spectrogram...")

        try:
            pp_spectrogram = preprocess_spectrogram(
                spectrogram, frequencies, self.orcai_parameter["spectrogram"]
            )
        except Exception as e:
            print(e)
            self.signals.error.emit((type(e), e, e.__traceback__))

        self.signals.progress.emit("(3/4) Computing predictions...")
        try:
            aggregated_predictions, overlap_count = compute_aggregated_predictions(
                recording_path=self.file_path,
                spectrogram=pp_spectrogram,
                model=self.model,
                orcai_parameter=self.orcai_parameter,
                shape=self.shape,
            )

            prediction_times = np.arange(0, len(aggregated_predictions)) * (
                2 ** len(self.orcai_parameter["model"]["filters"])
            )
        except Exception as e:
            print(e)
            self.signals.error.emit((type(e), e, e.__traceback__))

        self.signals.progress.emit("4/4 Computing labels...")
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
                delta_t=1,
                label_suffix="*",
            )
        except Exception as e:
            print(e)
            self.signals.error.emit((type(e), e, e.__traceback__))

        self.signals.progress.emit(f"Loaded file {self.file_path.name}")
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
