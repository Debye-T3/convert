"""Tab 2: Batch parameter defaults + per-file override table (Excel-like)."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QPushButton, QSplitter, QComboBox, QMenu, QFileDialog, QMessageBox,
    QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction


STANDARD_KEYS = [
    "sample_name", "sample_id",
    "position_x", "position_y", "position_z",
    "position_polar", "position_tilt", "position_azimuth",
    "temperature_K", "photon_energy_eV", "polarization", "slit",
    "work_function_eV",
]

STANDARD_LABELS = [
    "Sample Name", "Sample ID",
    "X", "Y", "Z",
    "Polar", "Tilt", "Azimuth",
    "T (K)", "hv (eV)", "Polarization", "Slit",
    "WF Φ (eV)",
]

FIELD_DEFAULTS = {
    "work_function_eV": "4.2",
}

POLARIZATION_OPTIONS = ["", "p-pol", "s-pol", "circular", "linear", "none"]

CUSTOM_PREFIX = "custom_"


class ParamsTab(QWidget):
    """Batch defaults on the left, per-file overrides on the right.

    Columns are drag-reorderable.  Custom parameter columns can be added /
    removed.  Excel import / template export are supported.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._file_paths = []
        self._overrides = {}          # fp -> {key: value}
        self._hidden_cols = set()     # logical column indices (1-based)
        self._rebuilding = False

        # dynamic field lists (parallel arrays)
        self._field_keys = list(STANDARD_KEYS)
        self._field_labels = list(STANDARD_LABELS)

        # ---- build UI ----
        layout = QVBoxLayout(self)

        title = QLabel("Experiment Parameters")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        self.splitter = QSplitter(Qt.Horizontal)

        # left panel
        self._build_left_panel()
        # right panel
        self._build_right_panel()

        self.splitter.setSizes([360, 600])
        layout.addWidget(self.splitter)

        # nav
        nav = QHBoxLayout()
        nav.addWidget(QPushButton("← Back: Select Files", clicked=self._go_back))
        nav.addStretch()
        nav.addWidget(QPushButton("Next: Preview →", clicked=self._go_next))
        layout.addLayout(nav)

    # ================================================================
    #  left panel — batch defaults
    # ================================================================

    def _build_left_panel(self):
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        form_group = QGroupBox("Batch Defaults")
        self._form_layout = QFormLayout(form_group)
        self._field_widgets = {}
        self._populate_form()
        left_layout.addWidget(form_group)

        # custom fields section
        custom_group = QGroupBox("Custom Fields")
        custom_outer = QVBoxLayout(custom_group)
        self._custom_container = QVBoxLayout()
        self._custom_widgets = {}  # key -> (QLineEdit, QPushButton, QHBoxLayout)
        custom_outer.addLayout(self._custom_container)
        add_btn = QPushButton("+ Add Custom Field")
        add_btn.clicked.connect(self._add_custom_field)
        custom_outer.addWidget(add_btn)
        left_layout.addWidget(custom_group)

        tip = QLabel(
            "Default values apply to all files.\n"
            "Override per-file in the table →\n\n"
            "Right-click table headers to hide columns.\n"
            "Drag columns to reorder."
        )
        tip.setStyleSheet("color: #888; font-size: 10pt; padding: 8px;")
        left_layout.addWidget(tip)
        left_layout.addStretch()

        self.splitter.addWidget(left)

    def _populate_form(self):
        """(Re)build the standard-fields portion of the form."""
        # clear existing rows
        while self._form_layout.rowCount() > 0:
            self._form_layout.removeRow(0)
        self._field_widgets.clear()

        for key, label in zip(STANDARD_KEYS, STANDARD_LABELS):
            if key == "polarization":
                w = QComboBox()
                w.setEditable(True)
                w.addItems(POLARIZATION_OPTIONS)
                w.setCurrentText("")
            else:
                w = QLineEdit()
                w.setPlaceholderText(label)
                if key in FIELD_DEFAULTS:
                    w.setText(FIELD_DEFAULTS[key])
            self._form_layout.addRow(label, w)
            self._field_widgets[key] = w

    # ================================================================
    #  right panel — per-file table
    # ================================================================

    def _build_right_panel(self):
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        table_group = QGroupBox("Per-File Overrides")
        table_layout = QVBoxLayout(table_group)

        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setMinimumSectionSize(50)
        self.table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.horizontalHeader().customContextMenuRequested.connect(
            self._header_context_menu
        )
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setMinimumSectionSize(20)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.setAlternatingRowColors(True)
        self.table.cellChanged.connect(self._on_cell_changed)
        table_layout.addWidget(self.table)

        # buttons under table
        btn_row = QHBoxLayout()

        import_btn = QPushButton("Import from Excel...")
        import_btn.setToolTip(
            "Import per-file parameters from an Excel spreadsheet.\n"
            "First column must contain file names."
        )
        import_btn.clicked.connect(self._import_excel)
        btn_row.addWidget(import_btn)

        export_btn = QPushButton("Export Template")
        export_btn.setToolTip(
            "Export a standardized .xlsx template with the current\n"
            "column layout for batch filling."
        )
        export_btn.clicked.connect(self._export_template)
        btn_row.addWidget(export_btn)

        btn_row.addStretch()
        show_all_btn = QPushButton("Show All Columns")
        show_all_btn.clicked.connect(self._show_all_columns)
        btn_row.addWidget(show_all_btn)
        table_layout.addLayout(btn_row)

        table_tip = QLabel(
            "Click any cell to override. Right-click header to hide. "
            "Drag header to reorder columns."
        )
        table_tip.setStyleSheet("color: #888; font-size: 10pt; padding: 4px;")
        table_layout.addWidget(table_tip)

        right_layout.addWidget(table_group)
        self.splitter.addWidget(right)

    # ================================================================
    #  public API
    # ================================================================

    def set_files(self, file_paths):
        self._file_paths = file_paths
        self._rebuild_table()

    def get_all_params(self):
        """Return batch defaults dict with '_overrides' key."""
        batch = {}
        # standard fields from form
        for key, w in self._field_widgets.items():
            text = (w.currentText().strip() if isinstance(w, QComboBox)
                    else w.text().strip())
            if text:
                try:
                    batch[key] = float(text)
                except ValueError:
                    batch[key] = text
        # custom fields from custom widgets
        for key, (edit, _, _) in self._custom_widgets.items():
            text = edit.text().strip()
            if text:
                try:
                    batch[key] = float(text)
                except ValueError:
                    batch[key] = text
        batch["_overrides"] = dict(self._overrides)
        return batch

    # ================================================================
    #  table management
    # ================================================================

    @property
    def _all_field_keys(self):
        return self._field_keys

    @property
    def _all_field_labels(self):
        return self._field_labels

    def _rebuild_table(self):
        self._rebuilding = True
        keys = self._all_field_keys
        labels = self._all_field_labels
        n_cols = len(keys) + 1  # +1 for File column

        self.table.setColumnCount(n_cols)
        self.table.setHorizontalHeaderLabels(["File"] + list(labels))

        self.table.setRowCount(len(self._file_paths))
        for i, fp in enumerate(self._file_paths):
            name_item = QTableWidgetItem(Path(fp).name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, name_item)
            for j, key in enumerate(keys):
                col = j + 1
                val = self._overrides.get(fp, {}).get(key, "")
                self.table.setItem(i, col, QTableWidgetItem(str(val) if val else ""))

        # apply column visibility (by logical column)
        for col in range(1, self.table.columnCount()):
            self.table.setColumnHidden(col, col in self._hidden_cols)

        self._rebuilding = False

    def _on_cell_changed(self, row, col):
        if self._rebuilding or row >= len(self._file_paths):
            return
        fp = self._file_paths[row]
        key_index = col - 1
        if key_index < 0 or key_index >= len(self._all_field_keys):
            return
        key = self._all_field_keys[key_index]
        item = self.table.item(row, col)
        text = item.text().strip() if item else ""
        if fp not in self._overrides:
            self._overrides[fp] = {}
        if text:
            self._overrides[fp][key] = text
        else:
            self._overrides[fp].pop(key, None)
            if not self._overrides[fp]:
                del self._overrides[fp]

    # ================================================================
    #  column hide / show
    # ================================================================

    def _header_context_menu(self, pos):
        col = self.table.horizontalHeader().logicalIndexAt(pos)
        if col <= 0:   # file name column never hidden
            return
        key_index = col - 1
        is_custom = self._all_field_keys[key_index].startswith(CUSTOM_PREFIX)

        menu = QMenu(self)
        label = self._all_field_labels[key_index]
        hide_action = QAction(f"Hide '{label}'", self)
        hide_action.triggered.connect(lambda: self._hide_column(col))
        menu.addAction(hide_action)

        if is_custom:
            menu.addSeparator()
            remove_action = QAction(f"Remove '{label}'", self)
            remove_action.triggered.connect(lambda: self._remove_custom_field(key_index))
            menu.addAction(remove_action)

        menu.addSeparator()
        show_all = QAction("Show All Columns", self)
        show_all.triggered.connect(self._show_all_columns)
        menu.addAction(show_all)
        menu.exec(self.table.horizontalHeader().mapToGlobal(pos))

    def _hide_column(self, col):
        self._hidden_cols.add(col)
        self.table.setColumnHidden(col, True)

    def _show_all_columns(self):
        self._hidden_cols.clear()
        for col in range(1, self.table.columnCount()):
            self.table.setColumnHidden(col, False)

    # ================================================================
    #  custom fields
    # ================================================================

    def _add_custom_field(self):
        name, ok = QInputDialog.getText(
            self, "Add Custom Field",
            "Field name (e.g. 'K deposition time'):"
        )
        if not ok or not name.strip():
            return
        key = CUSTOM_PREFIX + name.strip().lower().replace(" ", "_")
        label = name.strip()

        # avoid duplicates
        if key in self._field_keys:
            QMessageBox.warning(self, "Duplicate", f"Field '{label}' already exists.")
            return

        self._field_keys.append(key)
        self._field_labels.append(label)

        # add widget row in custom container
        edit = QLineEdit()
        edit.setPlaceholderText(label)
        remove_btn = QPushButton("✕")
        remove_btn.setFixedWidth(28)
        remove_btn.setToolTip(f"Remove '{label}'")
        remove_btn.clicked.connect(lambda: self._remove_custom_field_by_key(key))
        row_layout = QHBoxLayout()
        row_layout.addWidget(edit, 1)
        row_layout.addWidget(remove_btn)
        self._custom_container.addLayout(row_layout)
        self._custom_widgets[key] = (edit, remove_btn, row_layout)

        self._rebuild_table()

    def _remove_custom_field_by_key(self, key):
        """Remove custom field identified by key string."""
        try:
            idx = self._field_keys.index(key)
        except ValueError:
            return
        self._remove_custom_field(idx)

    def _remove_custom_field(self, key_index):
        key = self._field_keys[key_index]
        if not key.startswith(CUSTOM_PREFIX):
            return

        # confirm
        label = self._field_labels[key_index]
        reply = QMessageBox.question(
            self, "Remove Field",
            f"Remove field '{label}' and all its data?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # remove from lists
        self._field_keys.pop(key_index)
        self._field_labels.pop(key_index)

        # clean widget
        if key in self._custom_widgets:
            edit, btn, row = self._custom_widgets.pop(key)
            # remove widgets from layout
            row.removeWidget(edit)
            row.removeWidget(btn)
            edit.deleteLater()
            btn.deleteLater()
            # remove the row layout itself
            while row.count():
                item = row.takeAt(0)
            self._custom_container.removeItem(row)

        # clean overrides referencing this key
        for fp in list(self._overrides.keys()):
            self._overrides[fp].pop(key, None)
            if not self._overrides[fp]:
                del self._overrides[fp]

        self._rebuild_table()

    # ================================================================
    #  Excel import
    # ================================================================

    def _import_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Excel Parameters", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if not path:
            return
        try:
            import openpyxl
        except ImportError:
            QMessageBox.warning(
                self, "Missing Package",
                "The 'openpyxl' package is required to read Excel files.\n"
                "Install it with:  pip install openpyxl"
            )
            return

        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows or len(rows) < 2:
                QMessageBox.warning(self, "Empty File", "No data found in Excel file.")
                wb.close()
                return

            header = [str(c).strip() if c else "" for c in rows[0]]
            # map Excel column -> param key (by label or by key)
            col_to_key = {}
            for ci, h in enumerate(header):
                if ci == 0:
                    continue  # file name column
                # try exact label match first
                matched = False
                for key, label in zip(self._all_field_keys, self._all_field_labels):
                    if h == label or h.lower() == key.lower():
                        col_to_key[ci] = key
                        matched = True
                        break
                if not matched:
                    # try fuzzy: strip units, lowercase
                    for key, label in zip(self._all_field_keys, self._all_field_labels):
                        if h.lower().split("(")[0].strip() == label.lower().split("(")[0].strip():
                            col_to_key[ci] = key
                            break

            file_names = [Path(fp).name for fp in self._file_paths]
            imported = 0
            for row in rows[1:]:
                if not row or not row[0]:
                    continue
                fname = str(row[0]).strip()
                if fname not in file_names:
                    continue
                fp = self._file_paths[file_names.index(fname)]
                overrides = {}
                for ci, key in col_to_key.items():
                    val = row[ci] if ci < len(row) else None
                    if val is not None and str(val).strip():
                        overrides[key] = str(val).strip()
                if overrides:
                    self._overrides[fp] = overrides
                    imported += 1

            wb.close()
            self._rebuild_table()
            QMessageBox.information(
                self, "Import Complete",
                f"Imported parameters for {imported} file(s)."
            )
        except Exception as exc:
            QMessageBox.warning(self, "Import Error", str(exc))

    # ================================================================
    #  Excel template export
    # ================================================================

    def _export_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel Template", "parameters_template.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not path:
            return
        try:
            import openpyxl
        except ImportError:
            QMessageBox.warning(
                self, "Missing Package",
                "The 'openpyxl' package is required.\n"
                "Install it with:  pip install openpyxl"
            )
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Parameters"

        # Get headers in visual order
        hdr = self.table.horizontalHeader()
        n_cols = self.table.columnCount()
        vis_order = sorted(range(n_cols), key=lambda c: hdr.visualIndex(c))

        header_row = []
        for logical_col in vis_order:
            if self.table.isColumnHidden(logical_col):
                continue
            label = self._all_field_labels[logical_col - 1] if logical_col > 0 else "File"
            header_row.append(label)
        ws.append(header_row)

        # example row
        example = ["sample_data_001.txt"]
        for logical_col in vis_order:
            if logical_col == 0:
                continue
            if self.table.isColumnHidden(logical_col):
                continue
            key = self._all_field_keys[logical_col - 1]
            # provide hint value for some known keys
            hints = {
                "sample_name": "MySample", "sample_id": "001",
                "photon_energy_eV": "21.2", "work_function_eV": "4.2",
                "temperature_K": "300", "polarization": "p-pol",
            }
            example.append(hints.get(key, ""))
        ws.append(example)

        # set column widths
        for i, _ in enumerate(header_row, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 16

        wb.save(path)
        QMessageBox.information(
            self, "Template Exported",
            f"Template saved to:\n{path}\n\n"
            "Fill in parameters for each file and use 'Import from Excel' to load."
        )

    # ================================================================
    #  navigation
    # ================================================================

    def _go_back(self):
        w = self.window()
        if w and hasattr(w, "tabs"):
            w.tabs.setCurrentIndex(0)

    def _go_next(self):
        w = self.window()
        if w and hasattr(w, "tabs"):
            w.tabs.setCurrentIndex(2)
