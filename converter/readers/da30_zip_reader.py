"""Minimal ERLab-style DA30 zip reader.

Adapted from ERLab's Scienta Omicron DA30 loader. The implementation here is
kept local so the converter can read ``Spectrum_*.ini`` + ``Spectrum_*.bin``
archives without importing the full ERLab package.
"""

from __future__ import annotations

import configparser
import os
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr


class InvalidDA30ZipError(Exception):
    """Raised when the file is not a valid DA30 zip export."""


class CasePreservingConfigParser(configparser.ConfigParser):
    """ConfigParser that preserves key case."""

    def optionxform(self, optionstr):
        return str(optionstr)


def _parse_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
    return value


def _parse_ini_string(content: str) -> dict[str, dict[str, Any]]:
    parser = CasePreservingConfigParser(strict=False)
    parser.read_string(content)
    return {
        section: {key: _parse_value(value) for key, value in parser.items(section)}
        for section in parser.sections()
    }


def parse_ini(filename: str | os.PathLike) -> dict[str, dict[str, Any]]:
    with open(filename, encoding="utf-8") as handle:
        return _parse_ini_string(handle.read())


def _get_zip_regions(names: list[str]) -> list[str]:
    return [name[9:-4] for name in names if name.startswith("Spectrum_") and name.endswith(".bin")]


def _read_zip_array(zf: zipfile.ZipFile, member: str) -> np.ndarray:
    return np.frombuffer(zf.read(member), dtype=np.float32)


def _load_zip_content(
    regions: list[str],
    *,
    read_ini: Callable[[str], dict[str, dict[str, Any]]],
    read_bin: Callable[[str], np.ndarray],
    without_values: bool,
) -> list[xr.DataArray]:
    arrays: list[xr.DataArray] = []
    for region in regions:
        region_info = read_ini(f"Spectrum_{region}.ini")["spectrum"]
        attrs: dict[str, Any] = {}
        for section in read_ini(f"{region}.ini").values():
            attrs.update(section)

        shape: list[int] = []
        coords: dict[str, np.ndarray] = {}
        for dim_key in ("depth", "height", "width"):
            n = int(region_info[dim_key])
            offset = float(region_info[f"{dim_key}offset"])
            delta = float(region_info[f"{dim_key}delta"])
            label = str(region_info[f"{dim_key}label"])
            shape.append(n)
            coords[label] = np.linspace(offset, offset + (n - 1) * delta, n)

        values = (
            np.zeros(shape, dtype=np.float32)
            if without_values
            else read_bin(f"Spectrum_{region}.bin").reshape(shape)
        )
        arrays.append(
            xr.DataArray(
                values.astype(np.float32, copy=False),
                coords=coords,
                name=str(region_info["name"]),
                attrs=attrs,
            )
        )
    return arrays


def load_zip(filename: str | os.PathLike, *, without_values: bool = False) -> xr.DataArray | xr.DataTree:
    """Load a DA30 zip file or unzipped DA30 directory."""
    filename = Path(filename)
    zipped = not filename.is_dir()

    if zipped:
        with zipfile.ZipFile(filename, mode="r", allowZip64=False) as zf:
            names = zf.namelist()
            regions = _get_zip_regions(names)
            if not regions:
                raise InvalidDA30ZipError(f"{filename} does not appear to be a valid DA30 zip file.")
            arrays = _load_zip_content(
                regions,
                read_ini=lambda name: _parse_ini_string(zf.read(name).decode("utf-8")),
                read_bin=lambda name: _read_zip_array(zf, name),
                without_values=without_values,
            )
    else:
        names = os.listdir(filename)
        regions = _get_zip_regions(names)
        if not regions:
            raise InvalidDA30ZipError(f"{filename} does not appear to be a valid DA30 directory.")
        arrays = _load_zip_content(
            regions,
            read_ini=lambda name: parse_ini(filename / name),
            read_bin=lambda name: np.fromfile(filename / name, dtype=np.float32),
            without_values=without_values,
        )

    if len(arrays) == 1:
        return arrays[0]
    return xr.DataTree.from_dict({str(arr.name): arr.to_dataset(promote_attrs=True) for arr in arrays})
