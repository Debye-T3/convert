"""Tab 3: Preview with colormap picker and contrast sliders."""

from pathlib import Path

import matplotlib
matplotlib.use("QtAgg")

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.colors import LogNorm

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QCheckBox, QSlider, QGroupBox, QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from converter.readers.txt_reader import read_txt
from converter.readers.pxt_reader import read_pxt
from converter.preview import compute_contrast
from converter.engine import detect_format


COLORMAPS = ["inferno", "viridis", "plasma", "gray", "jet", "turbo"]


class PreviewTab(QWidget):
    preview_enabled_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_paths = []
        self._current_data = None
        self._current_energy = None
        self._current_angle = None

        layout = QVBoxLayout(self)

        title = QLabel("Preview")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        # Controls row
        ctrl_row = QHBoxLayout()

        ctrl_row.addWidget(QLabel("File:"))
        self.file_combo = QComboBox()
        self.file_combo.currentIndexChanged.connect(self._on_file_selected)
        ctrl_row.addWidget(self.file_combo)

        ctrl_row.addSpacing(16)

        ctrl_row.addWidget(QLabel("Colormap:"))
        self.cmap_combo = QComboBox()
        self.cmap_combo.addItems(COLORMAPS)
        self.cmap_combo.currentTextChanged.connect(lambda: self._refresh_preview())
        ctrl_row.addWidget(self.cmap_combo)

        self.log_cb = QCheckBox("Log scale")
        self.log_cb.setChecked(True)
        self.log_cb.stateChanged.connect(lambda: self._refresh_preview())
        ctrl_row.addWidget(self.log_cb)

        self.save_preview_cb = QCheckBox("Save with conversion")
        self.save_preview_cb.setChecked(True)
        self.save_preview_cb.stateChanged.connect(
            lambda s: self.preview_enabled_changed.emit(s == Qt.Checked.value)
        )
        ctrl_row.addWidget(self.save_preview_cb)

        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        # Main area: canvas + contrast
        main_row = QHBoxLayout()

        self.canvas = FigureCanvas(Figure(figsize=(7, 5)))
        self.ax = self.canvas.figure.add_subplot(111)
        main_row.addWidget(self.canvas, 1)

        contrast_group = QGroupBox("Contrast")
        contrast_layout = QVBoxLayout(contrast_group)

        contrast_layout.addWidget(QLabel("vmin percentile:"))
        self.vmin_slider = QSlider(Qt.Horizontal)
        self.vmin_slider.setRange(0, 10)
        self.vmin_slider.setValue(1)
        self.vmin_label = QLabel("1%")
        self.vmin_slider.valueChanged.connect(
            lambda v: (self.vmin_label.setText(f"{v}%"), self._refresh_preview())
        )
        contrast_layout.addWidget(self.vmin_slider)
        contrast_layout.addWidget(self.vmin_label)

        contrast_layout.addWidget(QLabel("vmax percentile:"))
        self.vmax_slider = QSlider(Qt.Horizontal)
        self.vmax_slider.setRange(90, 100)
        self.vmax_slider.setValue(99)
        self.vmax_label = QLabel("99%")
        self.vmax_slider.valueChanged.connect(
            lambda v: (self.vmax_label.setText(f"{v}%"), self._refresh_preview())
        )
        contrast_layout.addWidget(self.vmax_slider)
        contrast_layout.addWidget(self.vmax_label)

        contrast_layout.addStretch()
        main_row.addWidget(contrast_group)

        layout.addLayout(main_row)

        nav = QHBoxLayout()
        back_btn = QPushButton("← Back: Parameters")
        back_btn.clicked.connect(lambda: self._nav_to(1))
        next_btn = QPushButton("Next: Convert →")
        next_btn.clicked.connect(lambda: self._nav_to(3))
        nav.addWidget(back_btn)
        nav.addStretch()
        nav.addWidget(next_btn)
        layout.addLayout(nav)

    def set_files(self, file_paths):
        self._file_paths = file_paths
        self.file_combo.clear()
        for fp in file_paths:
            self.file_combo.addItem(Path(fp).name, fp)
        if file_paths:
            self._on_file_selected(0)

    def _on_file_selected(self, index):
        if index < 0 or not self._file_paths:
            return
        fp = self._file_paths[index]
        path = Path(fp)
        try:
            fmt = detect_format(path)
            if fmt == "txt":
                data = read_txt(path)
            elif fmt == "pxt":
                data = read_pxt(path)
            elif fmt == "bin":
                QMessageBox.information(
                    self, "Binary File",
                    f"{path.name}\n\n"
                    "Raw .bin files require manual shape input.\n"
                    "Use the Convert tab to specify dimensions."
                )
                return
            else:
                return
            self._current_data = data["spectrum"]
            self._current_energy = data["energy"]
            self._current_angle = data["thetax"]
            self._refresh_preview()
        except Exception as exc:
            import traceback
            detail = traceback.format_exc()
            QMessageBox.warning(
                self, "Preview Error",
                f"Could not read {path.name}:\n\n{exc}\n\n"
                f"Traceback:\n{detail}"
            )

    def _refresh_preview(self):
        if self._current_data is None:
            return
        self.canvas.figure.clear()
        self.ax = self.canvas.figure.add_subplot(111)

        data = np.clip(self._current_data, a_min=0.0, a_max=None)
        use_log = self.log_cb.isChecked()
        cmap = self.cmap_combo.currentText()
        pmin = self.vmin_slider.value()
        pmax = self.vmax_slider.value()
        e_axis = self._current_energy
        k_axis = self._current_angle
        x_label = "Angle [deg]"

        extent = [
            float(k_axis[0]), float(k_axis[-1]),
            float(e_axis[0]), float(e_axis[-1]),
        ]

        norm = None
        if use_log:
            vmin, vmax = compute_contrast(data, pmin, pmax)
            norm = LogNorm(vmin=vmin, vmax=vmax)

        kwargs = {"origin": "lower", "aspect": "auto", "cmap": cmap, "extent": extent}
        if norm is not None:
            kwargs["norm"] = norm
        im = self.ax.imshow(data, **kwargs)
        self.canvas.figure.colorbar(im, ax=self.ax)
        title = "ARPES Spectrum"
        if use_log:
            title += " (log)"
        self.ax.set_title(title)
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel("Energy [eV]")
        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def get_settings(self):
        return {
            "cmap": self.cmap_combo.currentText(),
            "pmin": float(self.vmin_slider.value()),
            "pmax": float(self.vmax_slider.value()),
            "use_log": self.log_cb.isChecked(),
        }

    def is_preview_enabled(self):
        return self.save_preview_cb.isChecked()

    def _nav_to(self, idx):
        w = self.window()
        if w and hasattr(w, "tabs"):
            w.tabs.setCurrentIndex(idx)
