"""ConvertWorker — QThread that runs conversion without blocking the GUI."""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from converter.engine import convert_file, merge_params


def _opt_float(params, key):
    """Extract an optional float from params dict; returns None if absent/invalid."""
    val = params.get(key)
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


class ConvertWorker(QThread):
    """Worker thread that runs batch conversion."""

    progress = Signal(int, str)
    file_done = Signal(str, bool, str)
    all_done = Signal(int, int)

    def __init__(self, file_paths, batch_params, output_dir, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.batch_params = batch_params
        self.output_dir = Path(output_dir)

    def run(self):
        success = 0
        fail = 0
        for i, file_path in enumerate(self.file_paths):
            path = Path(file_path)
            self.progress.emit(i, f"Converting {path.name}...")
            try:
                file_overrides = self.batch_params.get("_overrides", {}).get(str(path), {})
                params = merge_params(self.batch_params, file_overrides)

                result = convert_file(
                    path, self.output_dir, params,
                    preview_enabled=False,
                    preview_settings=None,
                    pxt_channel=int(params.get("pxt_channel", 0)),
                    pxt_subtract_dark=bool(params.get("pxt_subtract_dark", False)),
                    pxt_energy_offset=_opt_float(params, "pxt_energy_offset"),
                    pxt_energy_step=_opt_float(params, "pxt_energy_step"),
                    pxt_angle_offset=_opt_float(params, "pxt_angle_offset"),
                    pxt_angle_step=_opt_float(params, "pxt_angle_step"),
                )

                self.file_done.emit(result["output_path"], True, result["message"])
                success += 1

            except Exception as exc:
                fail += 1
                self.file_done.emit(str(path), False, f"[FAIL] {path.name}: {exc}")

        self.all_done.emit(success, fail)
