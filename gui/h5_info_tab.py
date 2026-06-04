"""Tab 4: inspect converted H5 structure without plotting."""

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from converter.h5_info import summarize_h5


class H5InfoTab(QWidget):
    """Read and display xarray/ERLab-relevant H5 structure."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._output_dir = Path("data/converted_h5/")

        layout = QVBoxLayout(self)

        title = QLabel("H5 Info")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        controls = QHBoxLayout()
        self.dir_label = QLabel(str(self._output_dir))
        controls.addWidget(QLabel("Folder:"))
        controls.addWidget(self.dir_label, 1)

        browse_dir = QPushButton("Browse Folder...")
        browse_dir.clicked.connect(self._browse_folder)
        controls.addWidget(browse_dir)

        open_file = QPushButton("Open H5...")
        open_file.clicked.connect(self._open_file)
        controls.addWidget(open_file)

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        controls.addWidget(refresh)
        layout.addLayout(controls)

        body = QHBoxLayout()
        self.file_list = QListWidget()
        self.file_list.itemSelectionChanged.connect(self._on_selection_changed)
        body.addWidget(self.file_list, 1)

        self.info_view = QTextEdit()
        self.info_view.setReadOnly(True)
        self.info_view.setStyleSheet("font-family: Consolas, monospace; font-size: 10pt;")
        body.addWidget(self.info_view, 3)
        layout.addLayout(body, 1)

        nav = QHBoxLayout()
        back_btn = QPushButton("← Back: Convert")
        back_btn.clicked.connect(lambda: self._nav_to(2))
        nav.addWidget(back_btn)
        nav.addStretch()
        layout.addLayout(nav)

        self.refresh()

    def set_output_dir(self, output_dir):
        self._output_dir = Path(output_dir)
        self.dir_label.setText(str(self._output_dir))
        self.refresh()

    def refresh(self):
        self.file_list.clear()
        folder = self._output_dir
        if not folder.exists():
            self.info_view.setPlainText(f"Folder does not exist:\n{folder}")
            return
        for path in sorted(folder.glob("*.h5")):
            item = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            item.setData(0x0100, str(path))
            self.file_list.addItem(item)
        if self.file_list.count() == 0:
            self.info_view.setPlainText(f"No .h5 files found in:\n{folder}")

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select H5 Output Folder", str(self._output_dir))
        if folder:
            self.set_output_dir(folder)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open H5 File", str(self._output_dir), "H5 Files (*.h5);;All Files (*)"
        )
        if path:
            self._show_file(Path(path))

    def _on_selection_changed(self):
        items = self.file_list.selectedItems()
        if not items:
            return
        path = items[0].data(0x0100)
        self._show_file(Path(path))

    def _show_file(self, path: Path):
        try:
            self.info_view.setPlainText(summarize_h5(path))
        except Exception as exc:
            QMessageBox.warning(self, "H5 Read Error", f"Could not read {path.name}:\n\n{exc}")

    def _nav_to(self, idx):
        w = self.window()
        if w and hasattr(w, "tabs"):
            w.tabs.setCurrentIndex(idx)
