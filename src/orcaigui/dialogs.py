from PyQt6.QtWidgets import (
    QFileDialog,
)


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
