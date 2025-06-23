from PyQt6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt


class infoWidget(QWidget):
    def __init__(self, label: str, value=None):
        super().__init__()
        layout = QHBoxLayout()
        self.label = QLabel(
            label + ":",
            alignment=Qt.AlignmentFlag.AlignRight,
        )
        self.value = QLabel(
            str(value) if value is not None else "",
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        layout.addWidget(self.label)
        layout.addWidget(self.value)
        self.setLayout(layout)


class InspectorWindow(QWidget):
    def __init__(self, data=None):
        super().__init__()
        self.data = data

        self.setWindowTitle("Inspector")
        layout = QVBoxLayout()
        layout.addWidget(
            infoWidget("Recording", self.data.recording_path if self.data else None)
        )
        layout.addWidget(
            infoWidget("Channel", self.data.channel if self.data else None)
        )
        layout.addWidget(
            infoWidget("# Labels", self.data.n_labels() if self.data else None)
        )
        self.setLayout(layout)

    def update_data(self, data):
        """Set the data to be displayed in the inspector."""
        self.data = data
        if self.data:
            self.layout().itemAt(0).widget().value.setText(
                str(self.data.recording_path) if self.data.recording_path else ""
            )
            self.layout().itemAt(1).widget().value.setText(
                str(self.data.channel) if self.data.channel else ""
            )
            self.layout().itemAt(2).widget().value.setText(str(self.data.n_labels()))
        else:
            self.layout().itemAt(0).widget().value.setText("")
            self.layout().itemAt(1).widget().value.setText("")
