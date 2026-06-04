"""xarray conversion and HDF5 writing helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np
import xarray as xr


STANDARD_PARAM_KEYS = {
    "sample_name",
    "sample_id",
    "position_x",
    "position_y",
    "position_z",
    "position_polar",
    "position_tilt",
    "position_azimuth",
    "temperature_K",
    "photon_energy_eV",
    "polarization",
    "slit",
    "work_function_eV",
}


def unique_output_path(output_dir: Path, stem: str, suffix: str = ".h5") -> Path:
    """Return a non-existing output path using ``stem``, appending a counter if needed."""
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = output_dir / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    idx = 1
    while True:
        candidate = output_dir / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def sanitize_attrs(attrs: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only non-empty scalar/string attrs that h5netcdf can serialize."""
    clean: dict[str, Any] = {}
    for key, value in attrs.items():
        if key.startswith("_") or value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, (str, int, float, bool)):
            clean[str(key)] = int(value) if isinstance(value, bool) else value
        elif isinstance(value, Path):
            clean[str(key)] = str(value)
        else:
            clean[str(key)] = str(value)
    return clean


def legacy_result_to_dataarray(result: Mapping[str, Any], *, name: str) -> xr.DataArray:
    """Convert the existing reader dict shape to an xarray DataArray."""
    spectrum = np.asarray(result["spectrum"], dtype=np.float32)
    energy = np.asarray(result["energy"], dtype=np.float32)
    thetax = np.asarray(result["thetax"], dtype=np.float32)
    attrs = sanitize_attrs(result.get("ses_params", {}))
    return xr.DataArray(
        spectrum,
        dims=("eV", "alpha"),
        coords={"eV": energy, "alpha": thetax},
        name=name,
        attrs=attrs,
    )


def normalize_da30_dims(data: xr.DataArray | xr.Dataset | xr.DataTree) -> xr.DataArray | xr.Dataset | xr.DataTree:
    """Rename common DA30 dimension labels to ERLab-style names."""
    def _rename(obj: xr.DataArray | xr.Dataset) -> xr.DataArray | xr.Dataset:
        mapping = {}
        for dim in obj.dims:
            canonical = _canonical_dim_name(str(dim))
            if canonical is not None and canonical not in obj.dims:
                mapping[dim] = canonical
        return obj.rename(mapping) if mapping else obj

    if isinstance(data, xr.DataTree):
        updated = data.copy(deep=False)
        for node in updated.subtree:
            if node.dataset is not None:
                node.dataset = _rename(node.dataset)
        return updated
    return _rename(data)


def _canonical_dim_name(dim: str) -> str | None:
    normalized = dim.strip().lower()
    if normalized in {"ev", "energy [ev]", "kinetic energy [ev]"}:
        return "eV"
    if normalized in {"alpha", "thetax [deg]", "y-scale [deg]", "angle [deg]"}:
        return "alpha"
    if normalized in {"beta", "thetay [deg]"}:
        return "beta"
    return None


def apply_metadata(
    data: xr.DataArray | xr.Dataset | xr.DataTree,
    *,
    source_format: str,
    source_path: Path,
    manual_params: Mapping[str, Any],
) -> xr.DataArray | xr.Dataset | xr.DataTree:
    """Apply source and user metadata to arrays/datasets in xarray objects."""
    source_attrs = {
        "source_format": source_format,
        "source_path": str(source_path),
    }
    manual_attrs = sanitize_attrs(manual_params)

    def _apply(obj: xr.DataArray | xr.Dataset) -> xr.DataArray | xr.Dataset:
        merged = sanitize_attrs(obj.attrs)
        merged.update(source_attrs)
        merged.update(manual_attrs)
        out = obj.copy()
        out.attrs = merged
        return out

    if isinstance(data, xr.DataTree):
        updated = data.copy(deep=False)
        for node in updated.subtree:
            if node.dataset is not None:
                ds = node.dataset.copy()
                ds.attrs = {**sanitize_attrs(ds.attrs), **source_attrs, **manual_attrs}
                for name in ds.data_vars:
                    ds[name].attrs = {
                        **sanitize_attrs(ds[name].attrs),
                        **source_attrs,
                        **manual_attrs,
                    }
                node.dataset = ds
        return updated
    if isinstance(data, (xr.DataArray, xr.Dataset)):
        return _apply(data)
    raise TypeError(f"Unsupported xarray object: {type(data)!r}")


def write_xarray_h5(data: xr.DataArray | xr.Dataset | xr.DataTree, destination: Path) -> None:
    """Write xarray data in ERLab/xarray-compatible h5netcdf form."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        import netCDF4  # noqa: F401
    except ImportError:
        pass
    else:
        data.to_netcdf(destination, engine="netcdf4")
        return
    try:
        data.to_netcdf(destination, engine="h5netcdf")
    except ValueError:
        data.to_netcdf(destination, engine="h5netcdf", invalid_netcdf=True)


def first_2d_dataarray(data: xr.DataArray | xr.Dataset | xr.DataTree) -> xr.DataArray:
    """Return the first 2D DataArray, slicing leading dimensions when needed."""
    arrays: list[xr.DataArray] = []
    if isinstance(data, xr.DataArray):
        arrays = [data]
    elif isinstance(data, xr.Dataset):
        arrays = list(data.data_vars.values())
    elif isinstance(data, xr.DataTree):
        for node in data.subtree:
            if node.dataset is not None:
                arrays.extend(node.dataset.data_vars.values())
    else:
        raise TypeError(f"Unsupported xarray object: {type(data)!r}")

    for arr in arrays:
        if arr.ndim == 2:
            return arr
    for arr in arrays:
        if arr.ndim > 2:
            indexers = {dim: 0 for dim in arr.dims[:-2]}
            return arr.isel(indexers)
    if arrays:
        raise ValueError("No plottable 2D data found in xarray object.")
    raise ValueError("No data variables found in xarray object.")


def axes_for_preview(arr: xr.DataArray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return spectrum, y-axis and x-axis arrays for the existing preview code."""
    if arr.ndim != 2:
        arr = first_2d_dataarray(arr)

    energy_dim = _find_dim(arr, ("ev", "energy", "kinetic"))
    angle_dim = _find_dim(arr, ("alpha", "theta", "angle", "scale", "deg"))
    if energy_dim and angle_dim and energy_dim != angle_dim:
        arr = arr.transpose(energy_dim, angle_dim)
    y_dim, x_dim = arr.dims
    y = np.asarray(arr.coords[y_dim].values if y_dim in arr.coords else np.arange(arr.shape[0]))
    x = np.asarray(arr.coords[x_dim].values if x_dim in arr.coords else np.arange(arr.shape[1]))
    return np.asarray(arr.values, dtype=np.float32), y.astype(np.float32), x.astype(np.float32)


def _find_dim(arr: xr.DataArray, tokens: tuple[str, ...]) -> str | None:
    for dim in arr.dims:
        name = dim.lower()
        if any(token in name for token in tokens):
            return dim
        coord = arr.coords.get(dim)
        if coord is not None:
            units = str(coord.attrs.get("units", "")).lower()
            if any(token in units for token in tokens):
                return dim
    return None
