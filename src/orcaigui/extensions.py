from orcAI.auxiliary import seconds_to_hms
from PyQt6.QtWidgets import QCheckBox, QFileDialog, QVBoxLayout
from pyqtgraph import AxisItem


class hhmmssAxisItem(AxisItem):
    def tickStrings(self, values, scale, spacing):
        """Format tick labels as HH:MM:SS"""
        return [seconds_to_hms(v * scale) for v in values]


class SaveLabelsDialog(QFileDialog):
    """A dialog for saving labels to a file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Labels to Folder")
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setFileMode(QFileDialog.FileMode.Directory)

        extraOptions = QVBoxLayout()
        checkbox_save_probabilities = QCheckBox("Save probabilities", self)
        checkbox_save_probabilities.setToolTip(
            "If checked, the probabilities will be saved to a seperate file."
        )
        extraOptions.addWidget(checkbox_save_probabilities)
        self.setLayout(extraOptions)
