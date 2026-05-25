"""Preview image generator for ARPES spectra."""

from pathlib import Path
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm


def compute_contrast(data: np.ndarray, pmin: float, pmax: float) -> Tuple[float, float]:
    """Percentile-based contrast limits."""
    if data.size == 0:
        return 1e-6, 1.0
    positive = data[data > 0]
    if positive.size == 0:
        positive = np.abs(data.ravel())
    vmin = float(np.percentile(positive, pmin)) if positive.size else 0.0
    vmax = float(np.percentile(positive, pmax)) if positive.size else 1.0
    if vmax <= vmin:
        vmax = float(positive.max()) if positive.size else 1.0
        vmin = max(vmax * 1e-3, 1e-6)
    return vmin, vmax


def generate_preview(
    spectrum: np.ndarray,
    energy_axis: np.ndarray,
    angle_axis: np.ndarray,
    destination: Path,
    *,
    cmap: str = "inferno",
    pmin: float = 1.0,
    pmax: float = 99.5,
    use_log: bool = True,
) -> None:
    """Generate a preview PNG of the ARPES spectrum."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = np.clip(spectrum, a_min=0.0, a_max=None)

    extent = [
        float(angle_axis[0]), float(angle_axis[-1]),
        float(energy_axis[0]), float(energy_axis[-1]),
    ]

    norm = None
    if use_log:
        vmin, vmax = compute_contrast(data, pmin, pmax)
        norm = LogNorm(vmin=vmin, vmax=vmax)

    fig, ax = plt.subplots(figsize=(7, 5))
    kwargs = {"origin": "lower", "aspect": "auto", "cmap": cmap, "extent": extent}
    if norm is not None:
        kwargs["norm"] = norm
    im = ax.imshow(data, **kwargs)
    fig.colorbar(im, ax=ax)
    title = "ARPES Spectrum"
    if use_log:
        title += " (log scale)"
    ax.set_title(title)
    ax.set_xlabel("Angle [deg]")
    ax.set_ylabel("Energy [eV]")
    fig.tight_layout()
    fig.savefig(destination, dpi=150)
    plt.close(fig)
