"""Read structural information from converted H5 files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr


KEY_ATTRS = [
    "source_format",
    "source_path",
    "sample_name",
    "sample_id",
    "temperature_K",
    "photon_energy_eV",
    "polarization",
    "work_function_eV",
    "Region Name",
    "Lens Mode",
    "Pass Energy",
    "Excitation Energy",
]


def summarize_h5(path: str | Path) -> str:
    """Return a human-readable structural summary for an H5 file."""
    path = Path(path)
    lines = [f"File: {path}", f"Size: {_format_size(path.stat().st_size)}", ""]

    try:
        data = xr.load_dataarray(path, engine="h5netcdf")
        lines.append("Readable as: xarray.DataArray")
        lines.extend(_summarize_array(data, indent=""))
        return "\n".join(lines)
    except Exception as dataarray_error:
        lines.append(f"DataArray read: failed ({type(dataarray_error).__name__}: {dataarray_error})")

    try:
        ds = xr.open_dataset(path, engine="h5netcdf")
        try:
            lines.append("")
            lines.append("Readable as: xarray.Dataset")
            lines.extend(_summarize_dataset(ds, indent=""))
            return "\n".join(lines)
        finally:
            ds.close()
    except Exception as dataset_error:
        lines.append(f"Dataset read: failed ({type(dataset_error).__name__}: {dataset_error})")

    try:
        tree = xr.open_datatree(path, engine="h5netcdf")
        lines.append("")
        lines.append("Readable as: xarray.DataTree")
        for node in tree.subtree:
            lines.append(f"Group: {node.path}")
            if node.dataset is not None:
                lines.extend(_summarize_dataset(node.dataset, indent="  "))
        tree.close()
        return "\n".join(lines)
    except Exception as datatree_error:
        lines.append(f"DataTree read: failed ({type(datatree_error).__name__}: {datatree_error})")

    return "\n".join(lines)


def _summarize_dataset(ds: xr.Dataset, *, indent: str) -> list[str]:
    lines: list[str] = []
    if ds.data_vars:
        lines.append(f"{indent}Data variables:")
        for name, arr in ds.data_vars.items():
            lines.append(f"{indent}- {name}")
            lines.extend(_summarize_array(arr, indent=indent + "  ", include_name=False))
    else:
        lines.append(f"{indent}Data variables: none")
    if ds.attrs:
        lines.extend(_summarize_attrs(ds.attrs, indent=indent))
    return lines


def _summarize_array(arr: xr.DataArray, *, indent: str, include_name: bool = True) -> list[str]:
    lines: list[str] = []
    if include_name:
        lines.append(f"{indent}Name: {arr.name}")
    lines.append(f"{indent}Dims: {tuple(str(dim) for dim in arr.dims)}")
    lines.append(f"{indent}Shape: {tuple(int(size) for size in arr.shape)}")
    lines.append(f"{indent}Dtype: {arr.dtype}")
    lines.append(f"{indent}Coordinates:")
    for dim in arr.dims:
        if dim in arr.coords:
            coord = arr.coords[dim]
            lines.append(f"{indent}- {dim}: {_coord_range(coord.values)}")
        else:
            lines.append(f"{indent}- {dim}: no coordinate values")
    lines.extend(_summarize_attrs(arr.attrs, indent=indent))
    return lines


def _summarize_attrs(attrs: dict[str, Any], *, indent: str) -> list[str]:
    lines = [f"{indent}Key attrs:"]
    found = False
    for key in KEY_ATTRS:
        if key in attrs:
            lines.append(f"{indent}- {key}: {_short_value(attrs[key])}")
            found = True
    if not found:
        lines.append(f"{indent}- none")
    extra = [key for key in attrs.keys() if key not in KEY_ATTRS]
    if extra:
        lines.append(f"{indent}Other attrs: {', '.join(str(k) for k in extra[:30])}")
        if len(extra) > 30:
            lines.append(f"{indent}Other attrs continued: {len(extra) - 30} more")
    return lines


def _coord_range(values: Any) -> str:
    arr = np.asarray(values)
    if arr.size == 0:
        return "empty"
    if arr.ndim == 0:
        return _short_value(arr.item())
    first = arr.flat[0]
    last = arr.flat[-1]
    return f"len={arr.size}, first={_short_value(first)}, last={_short_value(last)}"


def _short_value(value: Any) -> str:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    text = str(value)
    return text if len(text) <= 160 else text[:157] + "..."


def _format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{num_bytes} B"
