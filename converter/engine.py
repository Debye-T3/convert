"""Conversion engine - pure-Python orchestrator. No Qt dependency."""

from pathlib import Path
from typing import Any, Dict, Optional

from converter.readers.txt_reader import read_txt
from converter.readers.pxt_reader import read_pxt
from converter.readers.da30_zip_reader import load_zip
from converter.xarray_io import (
    apply_metadata,
    axes_for_preview,
    first_2d_dataarray,
    legacy_result_to_dataarray,
    normalize_da30_dims,
    unique_output_path,
    write_xarray_h5,
)
from converter.preview import generate_preview


MANUAL_PARAM_KEYS = [
    "sample_name", "sample_id",
    "position_x", "position_y", "position_z",
    "position_polar", "position_tilt", "position_azimuth",
    "temperature_K", "photon_energy_eV", "polarization", "slit",
    "work_function_eV",
]


def detect_format(path: Path) -> str:
    """Detect file format from extension."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return "txt"
    elif suffix == ".pxt":
        return "pxt"
    elif suffix == ".pxp":
        return "pxp"
    elif suffix == ".zip":
        return "zip"
    raise ValueError(f"Unsupported file extension: {suffix}")


def merge_params(batch_defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Merge batch defaults with per-file overrides. Override wins if non-empty."""
    merged = {key: value for key, value in batch_defaults.items() if not key.startswith("_")}
    for key, value in overrides.items():
        if value is not None and value != "":
            merged[key] = value
    return merged


def read_as_xarray(path: Path, *, pxt_channel: int = 0,
                   pxt_subtract_dark: bool = False,
                   pxt_energy_offset: Optional[float] = None,
                   pxt_energy_step: Optional[float] = None,
                   pxt_angle_offset: Optional[float] = None,
                   pxt_angle_step: Optional[float] = None):
    """Read a supported source file as an xarray object."""
    fmt = detect_format(path)
    if fmt == "txt":
        return normalize_da30_dims(legacy_result_to_dataarray(read_txt(path), name=path.stem))
    if fmt == "zip":
        return normalize_da30_dims(load_zip(path))
    if fmt in {"pxt", "pxp"}:
        try:
            from converter.readers.igor_reader import load_experiment
            return normalize_da30_dims(load_experiment(path, recursive=True))
        except Exception:
            if fmt != "pxt":
                raise
            result = read_pxt(
                path,
                channel=pxt_channel,
                subtract_dark=pxt_subtract_dark,
                energy_offset_override=pxt_energy_offset,
                energy_step_override=pxt_energy_step,
                angle_offset_override=pxt_angle_offset,
                angle_step_override=pxt_angle_step,
            )
            return normalize_da30_dims(legacy_result_to_dataarray(result, name=path.stem))
    raise ValueError(f"Unknown format: {fmt}")


def convert_file(
    path: Path,
    output_dir: Path,
    params: Dict[str, Any],
    *,
    preview_enabled: bool = False,
    preview_settings: Optional[Dict[str, Any]] = None,
    preview_base_dir: Optional[Path] = None,
    pxt_channel: int = 0,
    pxt_subtract_dark: bool = False,
    pxt_energy_offset: Optional[float] = None,
    pxt_energy_step: Optional[float] = None,
    pxt_angle_offset: Optional[float] = None,
    pxt_angle_step: Optional[float] = None,
) -> Dict[str, Any]:
    """Convert a single file to HDF5. Returns dict with status info.

    Args:
        path: source file path
        output_dir: directory for .h5 output
        params: merged manual + SES params
        preview_enabled: whether to generate preview PNG
        preview_settings: dict with cmap, pmin, pmax, use_log
        preview_base_dir: base dir for preview output (defaults to output_dir)
        pxt_channel: PXT channel index (0-based, -1 for auto)
        pxt_subtract_dark: subtract adjacent channel as dark reference
        pxt_energy_offset: override energy offset from PXT header
        pxt_energy_step: override energy step from PXT header
        pxt_angle_offset: override angle offset from PXT header
        pxt_angle_step: override angle step from PXT header

    Returns:
        dict with keys: success (bool), message (str), output_path (str or None)
    """
    fmt = detect_format(path)
    data = read_as_xarray(
        path,
        pxt_channel=pxt_channel,
        pxt_subtract_dark=pxt_subtract_dark,
        pxt_energy_offset=pxt_energy_offset,
        pxt_energy_step=pxt_energy_step,
        pxt_angle_offset=pxt_angle_offset,
        pxt_angle_step=pxt_angle_step,
    )
    data = apply_metadata(data, source_format=fmt, source_path=path, manual_params=params)

    out_path = unique_output_path(output_dir, path.stem, ".h5")
    write_xarray_h5(data, out_path)
    region_kind = "multi region" if hasattr(data, "children") and len(getattr(data, "children", {})) else "single region"

    messages = [f"[OK] {path.name} -> {out_path} ({region_kind})"]

    if preview_enabled:
        try:
            preview_arr = first_2d_dataarray(data)
            spectrum, energy, thetax = axes_for_preview(preview_arr)
            p_settings = preview_settings or {}
            prev_dir = preview_base_dir or output_dir
            prev_path = prev_dir / (path.stem + ".png")
            generate_preview(
                spectrum, energy, thetax, prev_path,
                cmap=p_settings.get("cmap", "inferno"),
                pmin=p_settings.get("pmin", 1.0),
                pmax=p_settings.get("pmax", 99.5),
                use_log=p_settings.get("use_log", True),
            )
            messages.append(f"  Preview saved -> {prev_path}")
        except Exception as exc:
            messages.append(f"  Preview failed: {exc}")

    return {"success": True, "message": "\n".join(messages), "output_path": str(out_path)}
