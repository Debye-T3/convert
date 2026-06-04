"""Main window with QTabWidget containing the converter workflow tabs."""

from PySide6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from gui.file_tab import FileTab
from gui.params_tab import ParamsTab
from gui.convert_tab import ConvertTab
from gui.h5_info_tab import H5InfoTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARPES Data Converter")
        self.resize(960, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.file_tab = FileTab()
        self.params_tab = ParamsTab()
        self.convert_tab = ConvertTab()
        self.h5_info_tab = H5InfoTab()

        self.tabs.addTab(self.file_tab, "1. Select Files")
        self.tabs.addTab(self.params_tab, "2. Parameters")
        self.tabs.addTab(self.convert_tab, "3. Convert")
        self.tabs.addTab(self.h5_info_tab, "4. H5 Info")

        self.file_tab.files_changed.connect(self._on_files_changed)

    def _on_files_changed(self, file_paths):
        self.params_tab.set_files(file_paths)
