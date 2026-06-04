# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python 3.11 Windows desktop app for converting ARPES/DA30 data into HDF5 files readable by ERLab/xarray. The entry point is `converter_app.py`.

- `converter/` contains conversion logic, HDF5/xarray I/O, preview generation, and format readers.
- `converter/readers/` contains file-format loaders for `.txt`, `.pxt/.pxp`, IGOR, and DA30 `.zip` inputs.
- `gui/` contains the PySide6 interface, organized by workflow tab.
- `data/converted_h5/` contains sample or generated conversion output; avoid treating this as application source.
- `build/` and `dist/` are PyInstaller outputs and should not be edited manually.

## Build, Test, and Development Commands

Create or update the conda environment from the checked-in dependency file:

```bat
conda env create -f environment.yml
conda env update -n convert-da30 -f environment.yml
```

Run the GUI locally:

```bat
run.bat
```

Package the onedir Windows executable:

```bat
build_exe.bat
```

The packaged app is written to `dist\converter_app\converter_app.exe`. Distribute the full `dist\converter_app` folder, not only the executable.

## Coding Style & Naming Conventions

Use standard Python style with 4-space indentation. Keep core conversion code independent of Qt; GUI imports belong in `gui/`, while reusable conversion behavior belongs in `converter/`. Prefer `pathlib.Path` for filesystem paths, snake_case for functions and variables, and PascalCase for Qt widget classes. Reader modules should follow the existing `*_reader.py` naming pattern.

## Testing Guidelines

No automated test suite is currently present. When adding tests, place them under `tests/` and use `pytest` naming conventions such as `test_engine.py` and `test_convert_file_txt()`. Prioritize tests for pure functions in `converter/`, especially format detection, parameter merging, reader behavior, and HDF5 output paths. For GUI changes, run `run.bat` and manually verify the affected tab workflow.

## Commit & Pull Request Guidelines

Recent commit messages are short, imperative summaries, for example `Support DA30 H5 conversion workflow` and `Add README with HDF5 conversion instructions`. Keep commits focused on one logical change.

Pull requests should include a clear description, changed formats or workflows, manual verification steps, and screenshots for visible GUI changes. Note any generated files intentionally updated under `dist/` or `data/`; otherwise leave generated artifacts out of the change.

## Security & Configuration Tips

Do not commit local agent or machine-specific configuration such as `.claude/`. Avoid hard-coding new absolute paths; existing batch files already contain Windows-specific fallbacks for this workstation.
