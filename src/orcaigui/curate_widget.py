from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class CurateWidget(QFrame):
    """Widget for curating labels in the spectrogram."""

    status = pyqtSignal(str)
    label = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.predicted_labels = None

        self.current_label = 0
        self.n_labels = 0

        self.curate_buttons = {
            "first": self._create_button_and_label(
                "First", "Go to the first label", self.go_to_first_label, "", 0
            ),
            "previous": self._create_button_and_label(
                "Previous",
                "Go to the previous label",
                self.go_to_previous_label,
                "",
                1,
            ),
            "check": self._create_button_and_label(
                "✅", "Mark as correct.", self.mark_as_correct, "", 2
            ),
            "wrong": self._create_button_and_label(
                "❌", "Mark as incorrect.", self.mark_as_incorrect, "", 3
            ),
            "next": self._create_button_and_label(
                "Next", "Go to the next label", self.go_to_next_label, "", 4
            ),
            "last": self._create_button_and_label(
                "Last", "Go to the last label", self.go_to_last_label, "", 5
            ),
        }
        curate_layout = QVBoxLayout()
        curate_button_layout = QGridLayout()
        for value in self.curate_buttons.values():
            curate_button_layout.addWidget(value["button"], 0, value["col"])
            curate_button_layout.addWidget(value["label"], 1, value["col"])

        curate_layout.addLayout(curate_button_layout)

        self.current_label_label = QLabel(
            f"Current label: {self.current_label} / {self.n_labels}",
            alignment=Qt.AlignmentFlag.AlignLeft,
        )

        curate_layout.addWidget(self.current_label_label)

        self.setLayout(curate_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(50)
        self.update_predicted_labels(self.predicted_labels)

    def _create_button_and_label(self, button_text, tooltip, callback, label="", col=0):
        button = QPushButton(button_text)
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        return {"button": button, "label": label, "col": col}

    def update_predicted_labels(self, predicted_labels):
        """Update the widget with the current label and predicted labels."""
        self.predicted_labels = predicted_labels
        self.current_label = 0
        self.n_labels = len(predicted_labels) if predicted_labels is not None else 0
        self.update_buttons()
        self.update_label_texts()

    def update_buttons(self):
        """Update the state of the navigation buttons based on the current label."""

        if self.predicted_labels is None or self.n_labels == 0:
            for value in self.curate_buttons.values():
                value["button"].setEnabled(False)
                value["label"].setText("")
        else:
            self.curate_buttons["first"]["button"].setEnabled(self.current_label >= 0)
            self.curate_buttons["previous"]["button"].setEnabled(self.current_label > 0)
            self.curate_buttons["next"]["button"].setEnabled(
                self.current_label < self.n_labels - 1
            )
            self.curate_buttons["last"]["button"].setEnabled(
                self.current_label < self.n_labels - 1
            )
            self.curate_buttons["check"]["button"].setEnabled(
                not self.current_label < 0
            )
            self.curate_buttons["wrong"]["button"].setEnabled(
                not self.current_label < 0
            )

    def update_label_texts(self):
        """Update the label texts in the bottom control widget."""
        if self.predicted_labels is None or self.predicted_labels.empty:
            return

        label = self.predicted_labels.iloc[self.current_label]

        label_texts = {
            "first": f"{self.predicted_labels.index[0] + 1}: {self.predicted_labels.iloc[0].label}",
            "previous": f"{self.predicted_labels.index[max(0, self.current_label - 1)] + 1}: {self.predicted_labels.iloc[max(0, self.current_label - 1)].label}",
            "check": f"{self.predicted_labels.index[self.current_label] + 1}: {label.label}",
            "wrong": f"{self.predicted_labels.index[self.current_label] + 1}: {label.label}",
            "next": f"{self.predicted_labels.index[min(len(self.predicted_labels) - 1, self.current_label + 1)] + 1}: {self.predicted_labels.iloc[min(len(self.predicted_labels) - 1, self.current_label + 1)].label}",
            "last": f"{self.predicted_labels.index[-1] + 1}: {self.predicted_labels.iloc[-1].label}",
        }

        for key, value in label_texts.items():
            if key in self.curate_buttons:
                self.curate_buttons[key]["label"].setText(value)

        self.current_label_label.setText(
            f"Current label: {self.current_label + 1} / {self.n_labels} - {label.label}"
        )

    def mark_as_correct(self):
        """Mark the current label as correct."""
        # TODO: Implement logic to mark the current label as correct
        self.status.emit("Not implemented yet")
        self.go_to_next_label()

    def mark_as_incorrect(self):
        """Mark the current label as incorrect."""
        # TODO: Implement logic to mark the current label as incorrect
        self.status.emit("Not implemented yet")
        self.go_to_next_label()

    def go_to_first_label(self):
        """Go to the first label in the spectrogram."""
        if self.predicted_labels is None or self.predicted_labels.empty:
            self.status.emit("No labels available")
            return
        self.current_label = 0
        self.go_to_label()

    def go_to_previous_label(self):
        """Go to the previous label in the spectrogram."""
        if self.predicted_labels is None or self.predicted_labels.empty:
            self.status.emit("No labels available")
            return
        if self.current_label < 1:
            self.status.emit("Already at the first label")
            return
        self.current_label -= 1
        self.go_to_label()

    def go_to_next_label(self):
        """Go to the next label in the spectrogram."""
        if self.predicted_labels is None or self.predicted_labels.empty:
            self.status.emit("No labels available")
            return
        if self.current_label >= len(self.predicted_labels) - 1:
            self.status.emit("Already at the last label")
            return
        self.current_label += 1
        self.go_to_label()

    def go_to_last_label(self):
        """Go to the last label in the spectrogram."""
        if self.predicted_labels is None or self.predicted_labels.empty:
            self.status.emit("No labels available")
            return
        self.current_label = len(self.predicted_labels) - 1
        self.go_to_label()

    def go_to_label(self):
        """Go to a specific label index."""
        self.label.emit(self.current_label)
        self.update_label_texts()
        self.update_buttons()
