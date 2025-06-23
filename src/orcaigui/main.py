import sys
from getpass import getuser
from importlib.resources import files
from pathlib import Path

from orcAI.io import load_orcai_model
from PyQt6.QtCore import QSettings, Qt, QThreadPool, pyqtSlot
from PyQt6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from orcaigui.about import AboutWindow
from orcaigui.audio_file_loader import AudioFileLoader, SpectrogramProcessor
from orcaigui.curate_widget import CurateWidget
from orcaigui.dialogs import (
    ChannelSelectDialog,
    ExportLabelsAsDialog,
    SaveProjectAsDialog,
)
from orcaigui.inspector import InspectorWindow
from orcaigui.orcaidata import OrcaiData
from orcaigui.spectrogram_widget import SpectrogramWidget

COLORMAPS = ["inferno", "viridis", "plasma", "magma", "cividis", "Greys"]
N_RECENT_FILES = 5


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.threadpool = QThreadPool()
        self.setWindowTitle("orcAI")

        self.model_dir = files("orcAI.models").joinpath("orcai-v1")
        self.model, self.orcai_parameter, self.shape = load_orcai_model(self.model_dir)
        self.model_name = self.orcai_parameter["name"]

        self.spectrogram_parameter = self.orcai_parameter["spectrogram"]
        self.data = None
        self.project_path = None

        self.inspector_window = InspectorWindow(self.data)

        settings = QSettings()
        self.colormap_name = settings.value("colormap", defaultValue="Greys", type=str)
        self.username = settings.value("username", defaultValue=getuser(), type=str)

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
        self.spectrogram_widget = SpectrogramWidget(
            spectrogram_parameter=self.spectrogram_parameter,
            calls=self.orcai_parameter["calls"],
            colormap_name=self.colormap_name,
        )

        splitter.addWidget(self.spectrogram_widget)

        # Create bottom control widget
        self.curate_widget = CurateWidget(self)
        self.curate_widget.status.connect(self.status.showMessage)
        self.curate_widget.label.connect(self.spectrogram_widget.focus_on_label)
        self.curate_widget.labels_updated.connect(
            self.spectrogram_widget.update_prediction_label
        )

        splitter.addWidget(self.curate_widget)

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

        self.save_project_action = QAction("Save project", self)
        self.save_project_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_project_action.triggered.connect(self.save_project)
        self.file_menu.addAction(self.save_project_action)

        self.save_project_as_action = QAction("Save project as...", self)
        self.save_project_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_project_as_action.triggered.connect(self.save_project_as)
        self.file_menu.addAction(self.save_project_as_action)

        self.file_menu.addSeparator()

        self.export_labels_action = QAction("Export Labels...", self)
        self.export_labels_action.triggered.connect(self.export_labels)
        self.file_menu.addAction(self.export_labels_action)

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
            action.triggered.connect(lambda _, cmap=colormap: self.set_colormap(cmap))
            self.colormap_menu.addAction(action)
            if colormap == self.colormap_name:
                action.setChecked(True)

        # Tools menu
        self.tools_menu = self.menu.addMenu("Tools")
        self.show_inspector_action = QAction("Show Inspector", self)
        self.show_inspector_action.setShortcut(QKeySequence("Ctrl+I"))
        self.show_inspector_action.triggered.connect(self.toggle_inspector_window)
        self.tools_menu.addAction(self.show_inspector_action)

        # Help menu
        self.help_menu = self.menu.addMenu("Help")
        self.about_action = QAction("About orcAI", self)
        self.about_action.triggered.connect(self.show_about_window)
        self.help_menu.addAction(self.about_action)

    def set_colormap(self, cmap):
        """Set the colormap for the spectrogram plot."""
        self.colormap_name = cmap
        settings = QSettings()
        settings.setValue("colormap", self.colormap_name)
        self.spectrogram_widget.set_colormap(colormap_name=self.colormap_name)

    def show_about_window(self):
        """Show the about window."""
        self.about_window = AboutWindow()
        self.about_window.show()

    def open_file_dialog(self):
        """Open file dialog to select an audio recording"""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open Audio Recording or Prokect")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter(
            "WAV Files or OrcAI Project Files (*.wav *.hdf5.orcai)"
        )

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.open_file(Path(selected_files[0]))

    def open_file(self, recording_path: Path):
        self.open_action.setEnabled(False)
        self.recent_files_menu.setEnabled(False)
        if recording_path.suffix == ".orcai":
            results = OrcaiData.load_from_hdf5_file(recording_path)
            self.project_path = recording_path
            self.status.showMessage(f"Project loaded from {recording_path.name}")
            self.spectrogram_processed(results)
        if recording_path.suffix == ".wav":
            self.project_path = None
            file_loader = AudioFileLoader(
                recording_path=recording_path,
                sampling_rate=self.spectrogram_parameter["sampling_rate"],
            )
            file_loader.signals.result.connect(self.audio_file_loaded)
            file_loader.signals.error.connect(self.audio_file_load_error)
            file_loader.signals.progress.connect(self.update_progress)
            self.threadpool.start(file_loader)

    @pyqtSlot(str)
    def update_progress(self, message):
        """Update the status bar with progress messages"""
        self.status.showMessage(message)

    @pyqtSlot(tuple)
    def audio_file_load_error(self, error):
        """Handle errors during audio file loading"""
        _, error_value = error
        self.status.showMessage(f"Error loading audio file: {error_value}")
        self.open_action.setEnabled(True)
        self.recent_files_menu.setEnabled(True)

    @pyqtSlot(dict)
    def audio_file_loaded(self, results):
        wav_file = results["wav_file"]
        n_channels = results["n_channels"]
        self.recording_path = results["recording_path"]

        if n_channels > 1:
            channel_select_dialog = ChannelSelectDialog(n_channels)
            if channel_select_dialog.exec():
                channel = channel_select_dialog.channel_select_box.currentIndex() + 1
            else:
                self.status.showMessage("No channel selected. Operation cancelled.")
                return
        else:
            channel = 1

        spectrogram_processor = SpectrogramProcessor(
            wav_file=wav_file,
            recording_path=self.recording_path,
            channel=channel,
            orcai_parameter=self.orcai_parameter,
            model=self.model,
            shape=self.shape,
        )
        spectrogram_processor.signals.result.connect(self.spectrogram_processed)
        spectrogram_processor.signals.progress.connect(self.update_progress)
        spectrogram_processor.signals.error.connect(self.spectrogram_processing_error)
        self.threadpool.start(spectrogram_processor)

    @pyqtSlot(dict)
    def spectrogram_processed(self, results):
        self.data = results
        self.curate_widget.update_data(self.data)
        self.spectrogram_widget.update_data(
            self.data,
            colormap_name=self.colormap_name,
        )
        self.inspector_window.update_data(self.data)

        self.default_labels_path = self.data.recording_path.with_name(
            f"{self.data.recording_path.stem}_c{self.data.channel}_calls.txt"
        )

        self.setWindowTitle(
            f"orcAI - {self.data.recording_path.name}, Channel {self.data.channel}"
        )
        self.open_action.setEnabled(True)
        self.recent_files_menu.setEnabled(True)
        if self.project_path is None:
            self.update_recent_files(self.data.recording_path)
        else:
            self.update_recent_files(self.project_path)

    @pyqtSlot(tuple)
    def spectrogram_processing_error(self, error):
        """Handle errors during spectrogram processing"""
        _, error_value = error
        self.status.showMessage(f"Error processing spectrogram: {error_value}")
        self.open_action.setEnabled(True)
        self.recent_files_menu.setEnabled(True)

    def update_open_recent_menu(self):
        """Update the recent files menu."""

        self.recent_files_menu.clear()
        settings = QSettings()
        recent_files = settings.value("recentFiles", [], type=list)
        for file_path in recent_files:
            action = QAction(Path(file_path).name, self)
            action.triggered.connect(
                lambda _, path=Path(file_path): self.open_file(recording_path=path)
            )
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

    def save_project(self):
        """Save the current project."""
        if self.data is None:
            self.status.showMessage("No recording loaded")
            return

        if self.project_path is None:
            self.save_project_as()
            return

        self.data.save_to_hdf5_file(self.project_path)
        self.status.showMessage(f"Project saved to {self.project_path.name}")
        return

    def save_project_as(self):
        save_project_as_dialog = SaveProjectAsDialog(parent=self)

        if save_project_as_dialog.exec():
            selected_files = save_project_as_dialog.selectedFiles()
            if selected_files:
                self.project_path = Path(selected_files[0])
                self.save_project()
        return

    def export_labels(self):
        if self.data is None:
            self.status.showMessage("No labels to save")
            return

        export_labels_dialog = ExportLabelsAsDialog(
            default_labels_path=self.default_labels_path, parent=self
        )

        if export_labels_dialog.exec():
            selected_files = export_labels_dialog.selectedFiles()
            if selected_files:
                self.labels_path = Path(selected_files[0])
                self.data.export_labels_as_tsv(self.labels_path)

    def toggle_inspector_window(self):
        if self.inspector_window.isVisible():
            self.inspector_window.hide()
            self.show_inspector_action.setText("Show Inspector")
            return
        self.inspector_window.show()
        self.show_inspector_action.setText("Hide Inspector")


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
