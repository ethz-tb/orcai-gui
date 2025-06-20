from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QVBoxLayout,
)


class ChannelSelectDialog(QDialog):
    def __init__(self, n_channels: int):
        super().__init__()

        self.setWindowTitle("Select Channel")
        message = QLabel("Multiple channels detected. Please select a channel:")

        self.channel_select_box = QComboBox()
        self.channel_select_box.addItems(
            [f"Channel {i + 1}" for i in range(n_channels)]
        )

        QBtn = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()

        layout.addWidget(message)
        layout.addWidget(self.channel_select_box)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class ExportLabelsAsDialog(QFileDialog):
    def __init__(self, default_labels_path: str | Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Labels")
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setNameFilter("txt files (*.txt)")
        self.setDefaultSuffix("txt")
        self.selectFile(str(default_labels_path))


class ExportProjectAsDialog(QFileDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Project as")
        self.setFileMode(QFileDialog.FileMode.AnyFile)
        self.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.setNameFilter("orcai project files (*.orcai)")
        self.setDefaultSuffix("orcai")
