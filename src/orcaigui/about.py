from importlib.resources import files

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class AboutWindow(QWidget):
    """About window for the orcAI GUI."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.logo = QLabel()
        logo = QPixmap(
            str(files("orcaigui.resources").joinpath("orcai-icon.png"))
        ).scaled(
            100,
            100,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.logo.setPixmap(logo)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.about_text = QLabel(
            "orcAI GUI v0.1.0\n\nDeveloped by\nClaude Sonnet 4\nGPT-4o\nand\nDaniel"
        )
        self.about_text.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(self.logo)
        layout.addWidget(self.about_text)
        self.setLayout(layout)
