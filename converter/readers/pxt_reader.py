"""Scienta DA30 PXT binary and raw .bin cube parser."""

import math
import struct
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np


def load_bin(path: Path, shape: Tuple[int, ...], dtype: str) -> np.ndarray:
    """Load a raw binary cube with given shape and dtype."""
    dtype_obj = np.dtype(dtype)
    expected_bytes = math.prod(shape) * dtype_obj.itemsize
    actual_bytes = path.stat().st_size
    if expected_bytes != actual_bytes:
        raise ValueError(
            f"{path}: size mismatch. Expected {expected_bytes} bytes, got {actual_bytes}."
        )
    data = np.fromfile(path, dtype=dtype_obj)
    return data.reshape(shape)


def _uint(raw: bytes, idx: int) -> int:
    """Read uint32 at 4-byte word index *idx*."""
    return struct.unpack_from("<I", raw, idx * 4)[0]


def _double(raw: bytes, idx: int) -> float:
    """Read float64 spanning two 4-byte words starting at *idx*."""
    return struct.unpack_from("<d", raw, idx * 4)[0]


def _compute_data_offset(raw: bytes, width: int, height: int,
                         channel_count: int) -> int:
    """Compute byte offset where the raw data payload begins.

    Uses the region-count approach (matching IGOR / pyARPES) with a
    data-driven cross-check to guard against both overshoot (offset too
    large — data would extend past EOF) and undershoot (offset too small
    — header / region bytes misread as spectrum).
    """
    file_size = len(raw)
    expected_data_bytes = width * height * channel_count * 2

    n_regions = _uint(raw, 23)
    if n_regions > 500:   # sanity bound
        n_regions = 0
    region_offset = (200 + n_regions * 200) * 4

    # ---- overshoot guard ----
    if region_offset + expected_data_bytes > file_size:
        return max(file_size - expected_data_bytes, 200 * 4)

    # ---- undershoot guard ----
    if region_offset < 200 * 4:
        return max(file_size - expected_data_bytes, 200 * 4)

    return region_offset


OFFSET_CONFIGS = [
    # (width, height, e_step, a_step, e_off, a_off) 4-byte word indices
    (35, 36, 39, 41, 47, 49),   # standard SES layout
    (33, 34, 37, 39, 45, 47),   # older DA30 variant
    (37, 38, 41, 43, 49, 51),   # newer SES variant
]


def _try_read_header(raw: bytes, width_idx, height_idx,
                     e_step_idx, a_step_idx, e_off_idx, a_off_idx):
    """Try reading PXT header fields from given word offsets.
    Returns None if values appear invalid.
    """
    width = _uint(raw, width_idx)
    height = _uint(raw, height_idx)
    if width == 0 or height == 0 or width > 20000 or height > 20000:
        return None
    return {
        "width": width, "height": height,
        "energy_step": _double(raw, e_step_idx),
        "angle_step": _double(raw, a_step_idx),
        "energy_offset": _double(raw, e_off_idx),
        "angle_offset": _double(raw, a_off_idx),
    }


def read_pxt(
    path: Path,
    *,
    energy_offset_override: Optional[float] = None,
    energy_step_override: Optional[float] = None,
    angle_offset_override: Optional[float] = None,
    angle_step_override: Optional[float] = None,
    channel: int = 0,
    subtract_dark: bool = False,
) -> dict:
    """Read a Scienta DA30 PXT binary file.

    Data layout follows the IGOR / pyARPES convention:
    payload is reshaped as (channels, height, width) where
      - channels = detector slices (word 22)
      - height   = angle steps   (word 36 or 34 or 38)
      - width    = energy steps  (word 35 or 33 or 37)

    Returns dict with keys:
        spectrum     – 2D float32 [energy, angle]
        energy       – 1D float32 energy axis
        thetax       – 1D float32 angle axis
        ses_params   – dict of auto-extracted header fields
        raw_channels – 3D float32 [channels, height, width]
    """
    raw = path.read_bytes()
    file_size = len(raw)
    if file_size < 256:
        raise ValueError(f"{path}: file too small to be a valid PXT container.")

    channel_count = max(1, _uint(raw, 22))
    total_points = _uint(raw, 21)

    frame_type_bytes = raw[25 * 4: 27 * 4]
    frame_type = (frame_type_bytes.split(b"\x00", 1)[0]
                  .decode("ascii", errors="ignore")) or "unknown"

    # ---- locate dimensions via multiple offset configs ----
    header = None
    for cfg in OFFSET_CONFIGS:
        h = _try_read_header(raw, *cfg)
        if h is None:
            continue
        # sanity: total_points should be >= width * height (single-channel case)
        expected_min = h["width"] * h["height"]
        if total_points > 0 and expected_min > total_points * 5:
            continue
        header = h
        break

    if header is None:
        raise ValueError(
            f"{path}: could not find valid dimension fields in PXT header. "
            f"File size: {file_size} B, total_points={total_points}, "
            f"channels={channel_count}, frame_type={frame_type!r}."
        )

    width = header["width"]
    height = header["height"]
    energy_step_raw = header["energy_step"]
    angle_step_raw = header["angle_step"]
    energy_offset_raw = header["energy_offset"]
    angle_offset_raw = header["angle_offset"]

    energy_step = energy_step_override if energy_step_override is not None else energy_step_raw
    angle_step = angle_step_override if angle_step_override is not None else angle_step_raw
    energy_offset = energy_offset_override if energy_offset_override is not None else energy_offset_raw
    angle_offset = angle_offset_override if angle_offset_override is not None else angle_offset_raw

    # ---- validate calibration values ----
    if not (math.isfinite(energy_step) and abs(energy_step) > 1e-9):
        raise ValueError(
            f"{path}: energy_step={energy_step!r} is zero, NaN, or Inf."
        )
    if not (math.isfinite(angle_step) and abs(angle_step) > 1e-9):
        raise ValueError(
            f"{path}: angle_step={angle_step!r} is zero, NaN, or Inf."
        )
    if not math.isfinite(energy_offset):
        raise ValueError(
            f"{path}: energy_offset={energy_offset!r} is NaN or Inf."
        )
    if not math.isfinite(angle_offset):
        raise ValueError(
            f"{path}: angle_offset={angle_offset!r} is NaN or Inf."
        )

    # ---- data payload offset ----
    expected_data_bytes = width * height * channel_count * 2  # int16 = 2 bytes
    data_offset = _compute_data_offset(raw, width, height, channel_count)

    if data_offset < 0 or data_offset >= file_size:
        raise ValueError(
            f"{path}: data offset {data_offset} out of bounds "
            f"(file_size={file_size}, shape={width}x{height}x{channel_count})."
        )

    # ---- read & reshape (channels, height, width) ----
    payload = np.frombuffer(
        raw, dtype="<i2",
        count=width * height * channel_count,
        offset=data_offset,
    )
    # IGOR / pyARPES convention: data is (channels, height, width) in C-order
    payload = payload.reshape(channel_count, height, width)
    raw_channels = payload.astype(np.float32, copy=True)
    # Transpose to (channels, energy, angle) for consistent axis ordering
    # with spectrum: raw_channels[c, e, a] matches spectrum[e, a]
    raw_channels = raw_channels.transpose(0, 2, 1)  # (C, W, H)

    # ---- choose channel ----
    chosen_channel = channel
    if channel < 0:
        pos_means = [
            float(np.mean(np.clip(raw_channels[ch], a_min=0.0, a_max=None)))
            for ch in range(channel_count)
        ]
        chosen_channel = int(np.argmax(pos_means))

    if not 0 <= chosen_channel < channel_count:
        raise ValueError(
            f"{path}: channel {chosen_channel} out of range ({channel_count} channels)."
        )

    signal = raw_channels[chosen_channel].copy()  # [width, height] = [energy, angle]

    subtracted_from = None
    if subtract_dark and channel_count > 1:
        dark_idx = 1 if chosen_channel == 0 else (chosen_channel - 1)
        if 0 <= dark_idx < channel_count:
            signal = signal - raw_channels[dark_idx]
            subtracted_from = dark_idx

    signal = np.clip(signal, a_min=0.0, a_max=None)
    spectrum = signal.copy()  # already [width, height] = [energy, angle]

    energy_axis = (np.arange(width, dtype=np.float64) * energy_step + energy_offset).astype(np.float32)
    angle_axis = (np.arange(height, dtype=np.float64) * angle_step + angle_offset).astype(np.float32)

    ses_params = {
        "frame_type": frame_type,
        "channels_total": int(channel_count),
        "channel_used": int(chosen_channel),
        "energy_offset_eV": float(energy_offset_raw),
        "energy_step_eV": float(energy_step_raw),
        "angle_offset_deg": float(angle_offset_raw),
        "angle_step_deg": float(angle_step_raw),
        "total_points": int(total_points),
        "width": int(width),
        "height": int(height),
    }
    if subtracted_from is not None:
        ses_params["subtracted_channel"] = int(subtracted_from)

    return {
        "spectrum": spectrum.astype(np.float32, copy=False),
        "energy": energy_axis,
        "thetax": angle_axis,
        "ses_params": ses_params,
        "raw_channels": raw_channels,
    }
