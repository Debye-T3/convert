# README Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the repository README with an accurate Chinese laboratory manual, illustrated with four screenshots from the current application and followed by concise developer guidance.

**Architecture:** Treat the README as two connected layers: an experiment-user workflow first and a maintainer reference second. Capture the real PySide6 window in a deterministic empty state, then write documentation that only claims behavior verified in `gui/`, `converter/`, the batch scripts, and the existing tests.

**Tech Stack:** Markdown, PySide6, Python 3.11, Conda, PowerShell, unittest, Git

## Global Constraints

- The primary audience is laboratory users; maintainers are the secondary audience.
- Write prose in Chinese while preserving original English UI labels, parameter keys, commands, file extensions, and technical names.
- Use a laboratory operating-manual style centered on concrete steps, inputs, outputs, and cautions.
- Store PNG screenshots under `docs/images/readme/` with no personal paths, real sample names, or experimental data.
- Describe only behavior available in the current codebase.
- Do not modify converter logic, GUI behavior, batch scripts, dependency configuration, or generated data.
- Do not claim that the current GUI can generate preview PNG files.
- Do not add an installer, GitHub Release, sample experimental data, or build artifacts.

---

### Task 1: Capture the four current GUI tabs

**Files:**
- Create: `docs/images/readme/select-files.png`
- Create: `docs/images/readme/parameters.png`
- Create: `docs/images/readme/convert.png`
- Create: `docs/images/readme/h5-info.png`
- Inspect: `converter_app.py`
- Inspect: `gui/main_window.py`

**Interfaces:**
- Consumes: `gui.main_window.MainWindow`, whose `tabs` property contains the four current workflow tabs.
- Produces: Four 960×700 PNG images referenced by the rewritten README.

- [ ] **Step 1: Confirm a Python interpreter can import the GUI**

Run:

```powershell
conda run -n convert-da30 python -c "from PySide6.QtWidgets import QApplication; from gui.main_window import MainWindow; print(MainWindow.__name__)"
```

Expected: exit code 0 and output containing `MainWindow`.

- [ ] **Step 2: Create the screenshot directory**

Run:

```powershell
New-Item -ItemType Directory -Force docs\images\readme
```

Expected: `docs\images\readme` exists and contains no generated application data.

- [ ] **Step 3: Capture each tab from the actual PySide6 window**

Run this PowerShell command from the repository root:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
conda run -n convert-da30 python -c "from pathlib import Path; from PySide6.QtWidgets import QApplication; from gui.main_window import MainWindow; app=QApplication([]); w=MainWindow(); w.resize(960,700); w.show(); app.processEvents(); out=Path('docs/images/readme'); names=['select-files','parameters','convert','h5-info']; [(w.tabs.setCurrentIndex(i), app.processEvents(), w.grab().save(str(out/f'{name}.png'), 'PNG')) for i,name in enumerate(names)]; w.close()"
```

Expected: the four files listed above are created as valid PNG images.

- [ ] **Step 4: Verify screenshot dimensions and file signatures**

Run:

```powershell
conda run -n convert-da30 python -c "from pathlib import Path; from PySide6.QtGui import QImage; p=Path('docs/images/readme'); [(lambda img,n: print(n, img.width(), img.height(), img.format().name))(QImage(str(p/n)), n) for n in ['select-files.png','parameters.png','convert.png','h5-info.png']]"
```

Expected: four output lines, each reporting `960 700` and a non-invalid image format.

- [ ] **Step 5: Visually inspect all four images**

Open each image and confirm:

- The correct tab is selected.
- Text and controls are legible and not clipped.
- No user-specific absolute path, real sample name, or experiment data appears.
- The images show the current four-tab GUI, not the unused `PreviewTab`.

If an image fails any condition, repeat Step 3 after correcting only the capture state or window sizing; do not alter application code to improve the screenshot.

---

### Task 2: Rewrite README as the laboratory workflow manual

**Files:**
- Modify: `README.md`
- Reference: `docs/images/readme/select-files.png`
- Reference: `docs/images/readme/parameters.png`
- Reference: `docs/images/readme/convert.png`
- Reference: `docs/images/readme/h5-info.png`
- Reference: `environment.yml`
- Reference: `run.bat`
- Reference: `build_exe.bat`
- Reference: `gui/file_tab.py`
- Reference: `gui/params_tab.py`
- Reference: `gui/convert_tab.py`
- Reference: `gui/h5_info_tab.py`
- Reference: `converter/engine.py`
- Reference: `converter/xarray_io.py`

**Interfaces:**
- Consumes: The four screenshots from Task 1 and verified behavior from the listed source files.
- Produces: A standalone `README.md` that lets a new laboratory user run a conversion and lets a maintainer locate development commands.

- [ ] **Step 1: Replace the introduction and feature overview**

Write a Chinese title and a concise description that identifies the application as a Windows/Python 3.11 PySide6 tool for converting ARPES/Scienta DA30 data to ERLab/xarray-readable HDF5.

Immediately follow with a feature list covering exactly these available capabilities:

- Batch selection of `.txt`, `.pxt`, `.pxp`, and DA30 `.zip` inputs.
- Batch defaults, per-file overrides, custom metadata fields, and Excel import/export.
- HDF5 output compatible with xarray/ERLab conventions.
- Collision-safe output names.
- Inspection of converted H5 structure inside the GUI.

Do not list GUI preview generation as a feature.

- [ ] **Step 2: Add environment requirements and portable startup commands**

Document Windows, Conda, and the checked-in Python 3.11 environment. Include these commands verbatim:

```bat
conda env create -f environment.yml
conda env update -n convert-da30 -f environment.yml
conda run -n convert-da30 python converter_app.py
```

Explain that `run.bat` is convenient on the original workstation but contains `D:\Projects\convert` and a fallback under `D:\Anaconda`; users on another machine must either use the portable Conda command or edit the script paths.

- [ ] **Step 3: Write the four-step GUI workflow with screenshots**

Create one subsection for each actual tab and place the matching image directly below the short step introduction:

```markdown
![选择输入文件界面](docs/images/readme/select-files.png)
![实验参数设置界面](docs/images/readme/parameters.png)
![批量转换界面](docs/images/readme/convert.png)
![H5 文件信息界面](docs/images/readme/h5-info.png)
```

The step text must state:

1. `Select Files`: drag and drop or browse for supported files, remove unwanted entries, and continue.
2. `Parameters`: enter batch defaults, override values per file, add custom fields, and optionally use Excel.
3. `Convert`: choose an output folder, start conversion, watch progress/logs, and open the result folder.
4. `H5 Info`: browse the output directory or open one `.h5` file and inspect its xarray-relevant structure.

- [ ] **Step 4: Document Excel parameter exchange**

Explain the exact workflow:

1. Select the source files so the parameter table has file rows.
2. Export `parameters_template.xlsx` from the Parameters tab.
3. Keep a `file` or `path` column in the workbook.
4. Fill standard or custom parameter columns.
5. Import the completed `.xlsx`; matching rows populate per-file overrides.

List representative standard fields: `sample_name`, `sample_id`, positions, sample angles, `temperature_K`, `photon_energy_eV`, `polarization`, `slit`, and `work_function_eV`.

- [ ] **Step 5: Add the input-format reference table**

Create a Markdown table with one row per extension and these verified rules:

| 格式 | 当前读取行为 |
| --- | --- |
| `.txt` | 读取 DA30 文本导出并标准化能量/角度维度。 |
| `.pxt` | 若旁边存在同名 `.txt`，优先读取该文本文件；否则使用 DA30 PXT 读取器。 |
| `.pxp` | 递归读取 IGOR experiment；多 wave 内容可能形成 `xarray.DataTree`。 |
| `.zip` | 读取含 `Spectrum_*.ini` 与 `Spectrum_*.bin` 的 DA30 导出包；多区域内容可能形成 `xarray.DataTree`。 |

Below the table, document the available PXT parameters: `pxt_channel` (`-1` for auto), `pxt_subtract_dark`, `pxt_energy_offset`, `pxt_energy_step`, `pxt_angle_offset`, and `pxt_angle_step`.

- [ ] **Step 6: Explain output behavior and current limitations**

State all of the following:

- Default GUI output folder is `data/converted_h5/`.
- Output uses `.h5` and xarray-compatible `h5netcdf`/NetCDF4-style storage.
- Existing files are not overwritten; `name.h5` becomes `name_1.h5`, then `name_2.h5`.
- Single-region sources normally load as `xarray.DataArray` or `xarray.Dataset`; multi-region sources may load as `xarray.DataTree`.
- The backend contains preview-generation code, but the current main window does not include `PreviewTab` and the GUI conversion worker disables previews.
- The application does not modify the source data files.

- [ ] **Step 7: Add troubleshooting guidance**

Cover these concrete cases and resolutions:

- `run.bat` cannot find Conda/Python: use the portable Conda command or update the paths in the batch file.
- `.pxt` appears to use unexpected data: check whether a same-stem `.txt` exists beside it.
- Output name has `_1` or `_2`: an earlier H5 with the base name already exists.
- `.zip` fails to load: verify the archive is a DA30 export containing the required spectrum `.ini` and `.bin` members.
- Packaged executable fails when copied alone: distribute the full onedir folder.

- [ ] **Step 8: Add maintainer documentation**

Include:

- A concise project tree for `converter_app.py`, `converter/`, `converter/readers/`, `gui/`, `tests/`, `data/converted_h5/`, `build/`, and `dist/`.
- The statement that `converter/` remains independent of Qt and GUI code belongs in `gui/`.
- The current test command:

```bat
conda run -n convert-da30 python -m unittest discover -s tests
```

- The build command and output:

```bat
build_exe.bat
```

```text
dist\converter_app\converter_app.exe
```

- A warning to distribute the complete `dist\converter_app` directory and to account for the absolute paths inside `build_exe.bat` on other workstations.

---

### Task 3: Verify the finished documentation

**Files:**
- Verify: `README.md`
- Verify: `docs/images/readme/select-files.png`
- Verify: `docs/images/readme/parameters.png`
- Verify: `docs/images/readme/convert.png`
- Verify: `docs/images/readme/h5-info.png`

**Interfaces:**
- Consumes: The finished Markdown and screenshots from Tasks 1–2.
- Produces: Evidence that the README is internally consistent, its assets resolve, and existing converter tests still pass.

- [ ] **Step 1: Check required local links and images**

Run:

```powershell
@(
  'environment.yml',
  'run.bat',
  'build_exe.bat',
  'converter_app.py',
  'docs/images/readme/select-files.png',
  'docs/images/readme/parameters.png',
  'docs/images/readme/convert.png',
  'docs/images/readme/h5-info.png'
) | ForEach-Object { if (-not (Test-Path $_)) { throw "Missing README target: $_" } }
```

Expected: exit code 0 with no missing-target exception.

- [ ] **Step 2: Scan for placeholders and inaccurate preview claims**

Run:

```powershell
rg -n "TBD|TODO|待补充|稍后添加|GUI.*生成.*预览|预览标签页" README.md
```

Expected: no matches.

- [ ] **Step 3: Run the existing unit tests**

Run:

```powershell
conda run -n convert-da30 python -m unittest discover -s tests
```

Expected: all discovered tests pass with exit code 0.

- [ ] **Step 4: Check Markdown-sensitive whitespace and repository changes**

Run:

```powershell
git diff --check
git status --short
```

Expected: `git diff --check` produces no output; status lists only the approved README, screenshot assets, and implementation-plan changes.

- [ ] **Step 5: Review the rendered reading order**

Inspect `README.md` from top to bottom and confirm:

- A new laboratory user reaches runnable commands before developer internals.
- Each screenshot is adjacent to its workflow step.
- Technical tables remain readable without horizontal scrolling at ordinary GitHub width.
- No section contradicts the current GUI or conversion engine.
- No machine-private path is shown except the documented hard-coded paths already present in the repository scripts.

- [ ] **Step 6: Commit the completed documentation after user authorization**

Run only after confirming the Git author identity with the user:

```powershell
git add README.md docs/images/readme docs/superpowers/plans/2026-07-22-readme-rewrite.md
git commit -m "Rewrite README as laboratory guide"
```

Expected: one focused commit containing the README, its four screenshots, and this implementation plan.
