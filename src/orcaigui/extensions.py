from orcAI.auxiliary import seconds_to_hms
from PyQt6.QtWidgets import (
    QFileDialog,
)
from pyqtgraph import AxisItem


class hhmmssAxisItem(AxisItem):
    def tickStrings(self, values, scale, spacing):
        """Format tick labels as HH:MM:SS"""
        return [seconds_to_hms(v * scale) for v in values]


class SaveLabelsAsDialog(QFileDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Labels As")
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setNameFilter("txt files (*.txt)")
        self.setDefaultSuffix("txt")
        self.selectFile(
            str(
                parent.recording_path.with_name(
                    f"{parent.recording_path.stem}_c{parent.channel}_calls.txt"
                )
            )
        )
