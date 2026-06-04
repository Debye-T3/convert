"""Tab 3: conversion with progress, log, output folder, and H5 results."""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QProgressBar, QFileDialog, QLineEdit, QGroupBox,
    QMessageBox, QListWidget, QListWidgetItem,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from gui.convert_worker import ConvertWorker


class ConvertTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._results = []
        self._failures = []

        layout = QVBoxLayout(self)

        title = QLabel("Convert")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        self.summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout(self.summary_group)
        self.summary_label = QLabel("No files selected.")
        summary_layout.addWidget(self.summary_label)
        layout.addWidget(self.summary_group)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output folder:"))
        self.out_dir_edit = QLineEdit("data/converted_h5/")
        out_row.addWidget(self.out_dir_edit, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output)
        out_row.addWidget(browse_btn)
        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        self.open_folder_btn.setEnabled(False)
        out_row.addWidget(self.open_folder_btn)
        layout.addLayout(out_row)

        self.start_btn = QPushButton("Start Conversion")
        self.start_btn.setStyleSheet(
            "background-color: #27ae60; color: white; font-size: 12pt; padding: 8px 24px;"
        )
        self.start_btn.clicked.connect(self._start_conversion)
        layout.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("")
        layout.addWidget(self.progress_label)

        results_label = QLabel("Converted H5 files:")
        layout.addWidget(results_label)
        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(100)
        self.results_list.itemDoubleClicked.connect(self._on_result_double_clicked)
        layout.addWidget(self.results_list)

        log_label = QLabel("Log:")
        layout.addWidget(log_label)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(
            "background-color: #1a1a2e; color: #a0ffa0; font-family: Consolas, monospace; font-size: 10pt;"
        )
        self.log_view.document().setMaximumBlockCount(500)
        layout.addWidget(self.log_view, 1)

        nav = QHBoxLayout()
        back_btn = QPushButton("← Back: Parameters")
        back_btn.clicked.connect(lambda: self._nav_to(1))
        nav.addWidget(back_btn)
        nav.addStretch()
        info_btn = QPushButton("Next: H5 Info →")
        info_btn.clicked.connect(lambda: self._nav_to(3))
        nav.addWidget(info_btn)
        layout.addLayout(nav)

    def _browse_output(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if d:
            self.out_dir_edit.setText(d)
            self._sync_h5_info_tab()

    def _open_output_folder(self):
        out_dir = self.out_dir_edit.text().strip() or "data/converted_h5/"
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(out_dir)))

    def _start_conversion(self):
        w = self.window()
        if not w or not hasattr(w, "file_tab"):
            return
        file_paths = w.file_tab.get_files()
        if not file_paths:
            QMessageBox.warning(self, "No Files", "Please add files in the Select Files tab.")
            return

        params = w.params_tab.get_all_params()
        output_dir = self.out_dir_edit.text().strip() or "data/converted_h5/"

        self._results.clear()
        self._failures.clear()
        self.results_list.clear()
        self.log_view.clear()

        self._log(f"Starting conversion of {len(file_paths)} file(s)...")
        self._log(f"Output: {output_dir}")
        self._log("Preview: disabled")
        self._log("-" * 40)

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(file_paths))
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)

        self._worker = ConvertWorker(file_paths, params, output_dir)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _on_progress(self, idx, msg):
        self.progress_bar.setValue(idx)
        self.progress_label.setText(msg)

    def _on_file_done(self, path, success, msg):
        color = "#a0ffa0" if success else "#ff6666"
        for line in msg.split("\n"):
            self._log(line, color)

        if success:
            from pathlib import Path
            out_path = Path(path)
            self._results.append(str(out_path))
            display_name = out_path.stem
            item = QListWidgetItem(f"{display_name}  ✓")
            item.setToolTip(f"HDF5: {out_path}")
            self.results_list.addItem(item)
        else:
            self._failures.append(msg)

    def _on_all_done(self, success, fail):
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_label.setText(f"Done — {success} success, {fail} failed")
        self.start_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(True)
        self._log(f"\n{'=' * 40}")
        self._log(f"Conversion complete: {success} success, {fail} failed")
        self._sync_h5_info_tab()
        if fail == 0 and success > 0:
            QMessageBox.information(
                self, "Done",
                f"All {success} file(s) converted successfully.\n\n"
                f"Output folder:\n{os.path.abspath(self.out_dir_edit.text().strip())}"
            )
        elif fail > 0:
            detail = "\n".join(self._failures[:10])
            if len(self._failures) > 10:
                detail += f"\n... and {len(self._failures) - 10} more."
            QMessageBox.warning(
                self, "Conversion Finished with Failures",
                f"{success} file(s) converted, {fail} failed.\n\n{detail}"
            )

    def _on_result_double_clicked(self, item):
        idx = self.results_list.row(item)
        if idx < 0 or idx >= len(self._results):
            return
        h5_path = self._results[idx]
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(h5_path)))

    def _log(self, text, color="#a0ffa0"):
        self.log_view.append(f"<span style='color:{color};'>{text}</span>")

    def _nav_to(self, idx):
        w = self.window()
        if w and hasattr(w, "tabs"):
            w.tabs.setCurrentIndex(idx)

    def _sync_h5_info_tab(self):
        w = self.window()
        if w and hasattr(w, "h5_info_tab"):
            output_dir = self.out_dir_edit.text().strip() or "data/converted_h5/"
            w.h5_info_tab.set_output_dir(output_dir)
