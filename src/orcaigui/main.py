import sys
from importlib.resources import files
from pathlib import Path

import pyqtgraph as pg
from orcAI.io import load_orcai_model
from PyQt6.QtCore import (
    QSettings,
    Qt,
    QThreadPool,
)
from PyQt6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from orcaigui.about import AboutWindow
from orcaigui.io import AudioFileLoader
from orcaigui.pgaxis import hhmmssAxisItem

COLORMAPS = ["inferno", "viridis", "plasma", "magma", "cividis", "Greys"]
N_RECENT_FILES = 5


def _create_button_and_label(button_text, tooltip, callback, label="", col=0):
    button = QPushButton(button_text)
    button.setToolTip(tooltip)
    button.clicked.connect(callback)
    label = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
    return {"button": button, "label": label, "col": col}


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.threadpool = QThreadPool()
        self.setWindowTitle("orcAI")

        settings = QSettings()
        self.colormap = settings.value("colormap", defaultValue="Greys", type=str)

        self.model_dir = files("orcAI.models").joinpath("orcai-v1")
        self.model, self.orcai_parameter, self.shape = load_orcai_model(self.model_dir)

        self.spectrogram_parameter = self.orcai_parameter["spectrogram"]
        self.spectrogram = None
        self.file_path = None
        self.current_label = -1
        self.predicted_labels = None

        # Menu
        self.create_menus()

        # Status Bar
        self.status = self.statusBar()
        self.status.showMessage("No recording loaded")

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)

        # Create top widget for spectrogram plot

        self.initilize_plots()

        self.update_plots()

        splitter.addWidget(self.plot_widget)

        # Create bottom control widget
        bottom_widget = self.create_bottom_widget()
        splitter.addWidget(bottom_widget)

        # Set initial splitter sizes (70% for plot, 30% for bottom)
        splitter.setSizes([750, 250])

    def create_menus(self):
        self.menu = self.menuBar()
        # File menu
        self.file_menu = self.menu.addMenu("File")

        self.open_action = QAction("Open", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_file_dialog)
        self.file_menu.addAction(self.open_action)

        self.recent_files_menu = self.file_menu.addMenu("Open recent")
        self.update_open_recent_menu()

        self.file_menu.addSeparator()

        self.window_close_action = QAction("Close Window", self)
        self.window_close_action.setShortcut(QKeySequence.StandardKey.Close)
        self.window_close_action.triggered.connect(self.close)
        self.file_menu.addAction(self.window_close_action)

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)

        # View Menu
        self.spectrogram_menu = self.menu.addMenu("Spectrogram")
        self.colormap_menu = self.spectrogram_menu.addMenu("Colormap")

        self.colormap_group = QActionGroup(self)
        self.colormap_group.setExclusive(True)

        for colormap in COLORMAPS:
            action = QAction(colormap, self.colormap_group, checkable=True)
            action.setData(colormap)
            action.triggered.connect(lambda cmap=colormap: self.setColormap(cmap))
            self.colormap_menu.addAction(action)
            if colormap == self.colormap:
                action.setChecked(True)

        # Help menu
        self.help_menu = self.menu.addMenu("Help")
        self.about_action = QAction("About orcAI", self)
        self.about_action.triggered.connect(self.show_about_window)
        self.help_menu.addAction(self.about_action)

    def setColormap(self, colormap):
        """Set the colormap for the spectrogram plot."""
        self.colormap = colormap
        settings = QSettings()
        settings.setValue("colormap", colormap)
        self.update_plots()

    def show_about_window(self):
        """Show the about window."""
        self.about_window = AboutWindow()
        self.about_window.setWindowTitle("About orcAI")
        self.about_window.resize(300, 200)
        self.about_window.show()

    def initilize_plots(self):
        y_axis_style = {
            "tickTextWidth": 15,
            "autoExpandTextSpace": False,
            "autoReduceTextSpace": False,
        }
        self.maxXRange = 1500

        navigation_x_axis = hhmmssAxisItem(orientation="bottom")
        navigation_x_axis.setScale(
            self.spectrogram_parameter["n_overlap"]
            / self.spectrogram_parameter["sampling_rate"]
        )
        navigation_y_axis = pg.AxisItem(orientation="left")
        navigation_y_axis.setLabel("Frequency", units="Hz")
        navigation_y_axis.setRange(0, 1.0)
        navigation_y_axis.setStyle(**y_axis_style)
        self.navigation_plot = pg.PlotItem(
            axisItems={
                "bottom": navigation_x_axis,
                "left": navigation_y_axis,
            },
            enableMenu=False,
        )
        self.navigation_plot.hideAxis("left")
        self.navigation_plot.hideAxis("bottom")
        self.navigation_plot.setMaximumHeight(25)
        self.navigation_plot.setMouseEnabled(x=False, y=False)
        vb = self.navigation_plot.getViewBox()
        vb.setBackgroundColor((50, 50, 50))

        self.navigation_plot.hideButtons()

        spectrogram_y_axis = pg.AxisItem(orientation="left")
        spectrogram_y_axis.setLabel("Frequency", units="Hz")
        spectrogram_y_axis.setRange(0, self.spectrogram_parameter["n_overlap"] + 1)
        spectrogram_y_axis.setScale(
            (self.spectrogram_parameter["sampling_rate"] / 2)
            / self.spectrogram_parameter["n_overlap"]
        )
        spectrogram_y_axis.setStyle(**y_axis_style)

        spectrogram_x_axis = hhmmssAxisItem(orientation="bottom")
        spectrogram_x_axis.setScale(
            self.spectrogram_parameter["n_overlap"]
            / self.spectrogram_parameter["sampling_rate"]
        )

        self.spectrogram_plot = pg.PlotItem(
            axisItems={
                "bottom": spectrogram_x_axis,
                "left": spectrogram_y_axis,
            }
        )
        self.spectrogram_plot.setMouseEnabled(x=False, y=False)
        self.spectrogram_plot.setLimits(xMin=0)
        self.spectrogram_plot.hideAxis("bottom")
        self.spectrogram_plot.hideButtons()

        prediction_x_axis = hhmmssAxisItem(orientation="bottom")
        prediction_x_axis.setScale(
            self.spectrogram_parameter["n_overlap"]
            / self.spectrogram_parameter["sampling_rate"]
        )

        prediction_y_axis = pg.AxisItem(orientation="left")
        prediction_y_axis.setLabel("Probability")
        prediction_y_axis.setRange(-0.3, 1.0)
        prediction_y_axis.setTicks(
            [
                [
                    (0.0, "0"),
                    (0.5, "0.5"),
                    (1.0, "1"),
                ],
                [],
            ]
        )
        prediction_y_axis.setStyle(**y_axis_style)

        self.prediction_plot = pg.PlotItem(
            axisItems={
                "bottom": prediction_x_axis,
                "left": prediction_y_axis,
            }
        )
        self.prediction_plot.setMouseEnabled(x=False, y=False)
        self.prediction_plot.setLabel("left", "Probability")
        self.prediction_plot.setLimits(xMin=0)
        self.prediction_plot.setXLink(self.spectrogram_plot)
        self.prediction_plot.setMaximumHeight(100)
        self.prediction_plot.hideButtons()

        self.plot_widget = pg.GraphicsLayoutWidget()

        self.plot_widget.addItem(self.spectrogram_plot, row=0, col=0)
        self.plot_widget.addItem(self.prediction_plot, row=1, col=0)
        self.legend_box = self.plot_widget.addViewBox(
            row=2, col=0, enableMouse=False, lockAspect=False
        )
        self.legend = pg.LegendItem(colCount=self.shape["num_labels"])
        self.legend.setParentItem(self.legend_box)
        self.legend.anchor((0.5, 0.5), (0.5, 0.5))
        self.legend.mouseDragEvent = lambda *args, **kwargs: None
        self.legend.hoverEvent = lambda *args, **kwargs: None
        # legend.sampleType.mouseClickEvent = lambda *args, **kwargs: None
        self.legend_box.setMaximumHeight(10)
        self.plot_widget.addItem(self.navigation_plot, row=3, col=0)

    def create_bottom_widget(self):
        self.curate_buttons = {
            "first": _create_button_and_label(
                "First", "Go to the first label", self.go_to_first_label, "", 0
            ),
            "previous": _create_button_and_label(
                "Previous",
                "Go to the previous label",
                self.go_to_previous_label,
                "",
                1,
            ),
            "check": _create_button_and_label(
                "✅", "Mark as correct.", self.mark_as_correct, "", 2
            ),
            "wrong": _create_button_and_label(
                "❌", "Mark as incorrect.", self.mark_as_incorrect, "", 3
            ),
            "next": _create_button_and_label(
                "Next", "Go to the next label", self.go_to_next_label, "", 4
            ),
            "last": _create_button_and_label(
                "Last", "Go to the last label", self.go_to_last_label, "", 5
            ),
        }
        bottom_layout = QGridLayout()
        for value in self.curate_buttons.values():
            bottom_layout.addWidget(value["button"], 0, value["col"])
            bottom_layout.addWidget(value["label"], 1, value["col"])

        bottom_widget = QFrame()
        bottom_widget.setLayout(bottom_layout)
        bottom_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        bottom_widget.setMinimumHeight(50)
        self.update_buttons()

        return bottom_widget

    def mark_as_correct(self):
        """Mark the current label as correct."""
        # TODO: Implement logic to mark the current label as correct
        self.status.showMessage("Not implemented yet")
        self.go_to_next_label()

    def mark_as_incorrect(self):
        """Mark the current label as incorrect."""
        # TODO: Implement logic to mark the current label as incorrect
        self.status.showMessage("Not implemented yet")
        self.go_to_next_label()

    def go_to_first_label(self):
        """Go to the first label in the spectrogram."""
        if self.predicted_labels is None or self.predicted_labels.empty:
            self.status.showMessage("No labels available")
            return
        self.current_label = 0
        self.focus_on_label(self.current_label)

    def go_to_previous_label(self):
        """Go to the previous label in the spectrogram."""
        if self.predicted_labels is None or self.predicted_labels.empty:
            self.status.showMessage("No labels available")
            return
        if self.current_label < 1:
            self.status.showMessage("Already at the first label")
            return
        self.current_label -= 1
        self.focus_on_label(self.current_label)

    def go_to_next_label(self):
        """Go to the next label in the spectrogram."""
        if self.predicted_labels is None or self.predicted_labels.empty:
            self.status.showMessage("No labels available")
            return
        if self.current_label >= len(self.predicted_labels) - 1:
            self.status.showMessage("Already at the last label")
            return
        self.current_label += 1
        self.focus_on_label(self.current_label)
        pass

    def go_to_last_label(self):
        """Go to the last label in the spectrogram."""
        if self.predicted_labels is None or self.predicted_labels.empty:
            self.status.showMessage("No labels available")
            return
        self.current_label = len(self.predicted_labels) - 1
        self.focus_on_label(self.current_label)

    def focus_on_label(self, label_index):
        """Focus on a specific label in the spectrogram."""
        if self.predicted_labels is None or self.predicted_labels.empty:
            self.status.showMessage("No labels available")
            return
        if label_index < 0 or label_index >= len(self.predicted_labels):
            self.status.showMessage("Invalid label index")
            return

        label = self.predicted_labels.iloc[label_index]
        start, stop = label.start, label.stop
        self.navigation_region.setRegion([start * 0.95, stop * 1.05])
        self.update_buttons()
        self.update_label_texts()

    def update_buttons(self):
        """Update the state of the navigation buttons based on the current label."""

        if self.predicted_labels is None:
            for value in self.curate_buttons.values():
                value["button"].setEnabled(False)
                value["label"].setText("")
        else:
            self.curate_buttons["first"]["button"].setEnabled(
                self.current_label > 0 or self.current_label == -1
            )
            self.curate_buttons["previous"]["button"].setEnabled(self.current_label > 0)
            self.curate_buttons["next"]["button"].setEnabled(
                self.current_label < len(self.predicted_labels) - 1
            )
            self.curate_buttons["last"]["button"].setEnabled(
                self.current_label < len(self.predicted_labels) - 1
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

    def open_file_dialog(self):
        """Open file dialog to select an audio recording"""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open Audio Recording")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("WAV Files (*.wav)")

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.open_file(Path(selected_files[0]))

    def open_file(self, file_path: Path):
        self.open_action.setEnabled(False)
        self.recent_files_menu.setEnabled(False)
        audioFileLoader = AudioFileLoader(
            file_path=file_path,
            model=self.model,
            orcai_parameter=self.orcai_parameter,
            shape=self.shape,
        )
        audioFileLoader.signals.result.connect(self.audio_file_loaded)
        audioFileLoader.signals.progress.connect(self.update_progress)
        self.threadpool.start(audioFileLoader)

    def update_open_recent_menu(self):
        """Update the recent files menu."""

        self.recent_files_menu.clear()
        settings = QSettings()
        recent_files = settings.value("recentFiles", [], type=list)
        for file_path in recent_files:
            action = QAction(Path(file_path).name, self)
            action.triggered.connect(lambda: self.open_file(file_path=Path(file_path)))
            self.recent_files_menu.addAction(action)

        self.recent_files_menu.addSeparator()
        action_clear_recents = QAction("Clear Menu", self)
        self.recent_files_menu.addAction(action_clear_recents)
        action_clear_recents.triggered.connect(
            lambda: self.update_recent_files(clear=True)
        )
        action_clear_recents.setEnabled(
            len(recent_files) > 0,
        )

    def update_recent_files(self, file_path: Path = None, clear: bool = False):
        """update recent files"""
        settings = QSettings()
        if clear:
            settings.setValue("recentFiles", [])
            self.update_open_recent_menu()
            return
        recent_files = settings.value("recentFiles", [], type=list)
        if file_path is not None:
            file_path = str(file_path)
            if file_path in recent_files:
                recent_files.remove(file_path)
            recent_files.insert(0, file_path)
        recent_files = recent_files[:N_RECENT_FILES]

        settings.setValue("recentFiles", recent_files)
        self.update_open_recent_menu()

    def update_progress(self, message):
        """Update the status bar with progress messages"""
        self.status.showMessage(message)

    def audio_file_loaded(self, results):
        self.spectrogram, self.frequencies, self.times = (
            results["spectrogram"],
            results["frequencies"],
            results["times"],
        )
        self.pp_spectrogram = results["pp_spectrogram"]
        self.aggregated_predictions = results["aggregated_predictions"]
        self.prediction_times = results["prediction_times"]
        self.predicted_labels = results["predicted_labels"]

        if self.spectrogram is not None:
            self.file_path = results["file_path"]
            self.setWindowTitle(f"orcAI - {self.file_path.name}")
            self.update_plots()
            self.update_buttons()
            self.update_label_texts()
            self.open_action.setEnabled(True)
            self.recent_files_menu.setEnabled(True)
            self.update_recent_files(self.file_path)

    def update_plots(self):
        """Update the spectrogram plot with current data"""

        if self.spectrogram is None:
            self.status.showMessage("No spectrogram data available")
            return

        plot_xMax = len(self.times) * 1.05
        plot_xRange = [
            0,
            plot_xMax if len(self.times) <= self.maxXRange else self.maxXRange,
        ]

        img = pg.ImageItem()
        img.setImage(self.spectrogram.T)

        lut = pg.colormap.get(self.colormap, source="matplotlib").getLookupTable()
        img.setLookupTable(lut)

        self.spectrogram_plot.clear()
        self.spectrogram_plot.addItem(img)
        self.spectrogram_plot.setLimits(xMin=0, xMax=plot_xMax)
        self.spectrogram_plot.setRange(xRange=plot_xRange)

        self.prediction_plot.clear()
        self.navigation_plot.clear()
        self.navigation_plot.setLimits(xMin=0, xMax=plot_xMax)
        self.navigation_plot.setRange(xRange=[0, plot_xMax])
        self.navigation_region = pg.LinearRegionItem(
            values=plot_xRange,
            bounds=[0, plot_xMax],
            brush=pg.mkBrush(255, 255, 255, 50),
            movable=True,
        )
        self.navigation_region.sigRegionChangeFinished.connect(self.update_plot_region)
        self.navigation_plot.addItem(
            self.navigation_region,
        )

        self.legend.clear()
        for i, call in enumerate(self.orcai_parameter["calls"]):
            self.prediction_plot.plot(
                x=self.prediction_times,
                y=self.aggregated_predictions[:, i],
                pen=pg.mkPen(
                    self.get_call_color(call),
                ),
                name=self.orcai_parameter["calls"][i],
            )
            self.legend.addItem(self.prediction_plot.items[-1], call)

        for label in self.predicted_labels.itertuples():
            self.prediction_plot.addItem(
                pg.BarGraphItem(
                    x0=label.start,
                    x1=label.stop,
                    y0=0.25,
                    y1=0.75,
                    brush=pg.mkBrush(
                        self.get_call_color(label.label, alpha=100),
                    ),
                    pen=pg.mkPen(self.get_call_color(label.label, alpha=200)),
                )
            )
            self.navigation_plot.addItem(
                pg.BarGraphItem(
                    x0=label.start,
                    x1=label.stop,
                    y0=0.25,
                    y1=0.75,
                    brush=pg.mkBrush(
                        self.get_call_color(label.label, alpha=100),
                    ),
                    pen=pg.mkPen(self.get_call_color(label.label, alpha=200)),
                )
            )
            call_label = pg.TextItem(
                text=label.label,
                color=self.get_call_color(label.label, alpha=200),
                anchor=(0.5, 0.5),
            )
            self.prediction_plot.addItem(call_label)
            call_label.setPos(
                (label.start + label.stop) / 2,
                0.5,
            )

        self.prediction_plot.setLimits(xMin=0, xMax=plot_xMax)
        self.prediction_plot.setRange(xRange=plot_xRange, yRange=[-0.3, 1.0])
        self.prediction_plot.showGrid(x=True, y=True)
        self.update_label_texts()

    def update_plot_region(self):
        """Update the spectrogram and prediction plots based on the selected region"""
        region = self.navigation_region.getRegion()

        self.spectrogram_plot.setRange(xRange=region, disableAutoRange=True)
        self.prediction_plot.setRange(xRange=region, disableAutoRange=True)

    def get_call_color(self, call, alpha=255):
        call = call.replace("*", "")
        i = self.orcai_parameter["calls"].index(call)
        if i < 0:
            raise ValueError(f"Call '{call}' not found in orcAI parameters.")

        return pg.intColor(i, alpha=alpha, hues=len(self.orcai_parameter["calls"]))


def predict_gui():
    app = QApplication(sys.argv)

    app.setApplicationName("orcAI")
    app.setApplicationDisplayName("orcAI")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("Theoretical Biology @ ETH Zurich")
    app.setOrganizationDomain("tb.ethz.ch")

    icon = QIcon(str(files("orcaigui.resources").joinpath("orcai-icon.png")))
    app.setWindowIcon(icon)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    predict_gui()
