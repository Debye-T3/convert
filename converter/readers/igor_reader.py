"""Minimal Igor experiment reader for DA30 ``.pxt``/``.pxp`` files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import igor2.binarywave
import igor2.packed
import igor2.record
import numpy as np
import xarray as xr


DEFAULT_DIMS = ["W", "X", "Y", "Z"]
MAXDIM = 4


def _decode(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="ignore")
    return str(value)


def _native(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values)
    if arr.dtype.byteorder not in (">", "<"):
        return arr
    return arr.byteswap().view(arr.dtype.newbyteorder("="))


def _parse_note(note: bytes) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    for line in note.decode(errors="ignore").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        try:
            attrs[key] = int(value)
            continue
        except ValueError:
            pass
        try:
            attrs[key] = float(value)
            continue
        except ValueError:
            pass
        attrs[key] = value
    return attrs


def load_wave(wave: dict | igor2.record.WaveRecord | str | os.PathLike) -> xr.DataArray:
    """Load one Igor wave into a DataArray."""
    wave_dict = wave.wave if isinstance(wave, igor2.record.WaveRecord) else wave
    if isinstance(wave_dict, (str, os.PathLike)):
        wave_dict = igor2.binarywave.load(wave_dict)

    data = wave_dict["wave"]
    version = wave_dict["version"]
    bin_header = data["bin_header"]
    wave_header = data["wave_header"]
    dim_labels = [""] * MAXDIM

    if version <= 3:
        shape = [wave_header["npnts"]] + [0] * (MAXDIM - 1)
        scale_a = [wave_header["hsA"]] + [0] * (MAXDIM - 1)
        scale_b = [wave_header["hsB"]] + [0] * (MAXDIM - 1)
        axis_units = [_decode(wave_header["xUnits"])] + [""] * (MAXDIM - 1)
    else:
        shape = wave_header["nDim"]
        scale_a = wave_header["sfA"]
        scale_b = wave_header["sfB"]
        axis_units = [""] * MAXDIM
        if version >= 5:
            unit_sizes = bin_header["dimEUnitsSize"]
            cursor = 0
            for idx, size in enumerate(unit_sizes):
                if size:
                    axis_units[idx] = _decode(data["dimension_units"][cursor : cursor + size])
                cursor += size
            for idx, size in enumerate(bin_header["dimLabelsSize"]):
                if size:
                    dim_labels[idx] = _decode(b"".join(data["labels"][idx]))
        else:
            axis_units[0] = _decode(data["dimension_units"])

    coords: dict[str, Any] = {}
    for idx, (step, start, count) in enumerate(zip(scale_a, scale_b, shape)):
        count = int(count)
        if count == 0:
            continue
        dim = dim_labels[idx]
        unit = axis_units[idx]
        if dim == "":
            if unit == "":
                dim = DEFAULT_DIMS[idx]
            else:
                dim, unit = unit, ""
        values = np.linspace(float(start), float(start) + float(step) * (count - 1), count)
        coords[dim] = xr.DataArray(values, dims=(dim,), attrs={"units": unit}) if unit else values

    name = _decode(wave_header["bname"]).strip() or "wave"
    attrs = _parse_note(data.get("note", b""))
    return xr.DataArray(_native(data["wData"]), dims=coords.keys(), coords=coords, attrs=attrs, name=name)


def load_experiment(filename: str | os.PathLike, *, recursive: bool = True) -> xr.DataArray | xr.DataTree:
    """Load waves from a ``.pxt`` or ``.pxp`` Igor experiment."""
    experiment = None
    for byte_order in (">", "=", "<"):
        try:
            _, experiment = igor2.packed.load(filename, initial_byte_order=byte_order)
            break
        except ValueError:
            continue
    if experiment is None:
        raise OSError("Failed to load Igor experiment file.")

    def unpack(contents: dict, parent: str = "") -> dict[str, xr.DataArray]:
        waves: dict[str, xr.DataArray] = {}
        for raw_name, record in contents.items():
            decoded = _decode(raw_name)
            name = f"{parent}/{decoded}" if parent else decoded
            if isinstance(record, igor2.record.WaveRecord):
                arr = load_wave(record)
                arr.name = arr.name or decoded
                waves[name] = arr
            elif isinstance(record, dict) and recursive:
                waves.update(unpack(record, name))
        return waves

    waves = unpack(experiment["root"])
    if not waves:
        raise ValueError(f"No Igor waves found in {Path(filename).name}.")
    if len(waves) == 1:
        return next(iter(waves.values()))
    return xr.DataTree.from_dict({name.replace("/", "_"): arr.to_dataset(promote_attrs=True) for name, arr in waves.items()})
