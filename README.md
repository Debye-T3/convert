# DA30 HDF5 Converter

这是一个面向 Windows 桌面的 Python 3.11 应用，用于把 ARPES / Scienta DA30 数据转换为 ERLab 和 xarray 可读取的 HDF5 文件。应用入口是 `converter_app.py`，界面使用 PySide6。

## 支持的输入

- DA30 `.txt` 导出文件
- DA30 `.pxt` 二进制文件
- IGOR `.pxp` 实验文件
- DA30 `.zip` 导出包，包含 `Spectrum_*.ini` 和 `Spectrum_*.bin`

转换结果会写出为 `.h5`，可选生成 `.png` 预览图。`.pxt` 读取支持选择通道、自动选择通道、暗通道扣除，以及能量轴和角度轴校准覆盖。

## 项目结构

```text
converter_app.py        GUI 入口
converter/              转换、读取、HDF5/xarray 写出和预览逻辑
converter/readers/      txt、pxt/pxp、IGOR、DA30 zip 读取器
gui/                    PySide6 界面和各工作流标签页
tests/                  纯 Python 行为测试
data/converted_h5/      本地转换输出，不作为源码维护
data/previews/          本地预览图输出，不作为源码维护
build/                  PyInstaller 构建中间产物
dist/                   PyInstaller 打包输出
```

`converter/` 不依赖 Qt；GUI 相关代码应放在 `gui/`。

## 环境准备

使用仓库中的 conda 环境文件创建或更新环境：

```bat
conda env create -f environment.yml
conda env update -n convert-da30 -f environment.yml
```

## 本地运行

```bat
run.bat
```

`run.bat` 会优先使用 `%USERPROFILE%\anaconda3\Scripts\conda.exe run -n convert-da30`，找不到时回退到 `D:\Anaconda\envs\convert-da30\python.exe`。

## 打包 Windows 可执行程序

```bat
build_exe.bat
```

打包输出位于：

```text
dist\converter_app\converter_app.exe
```

分发时请复制整个文件夹：

```text
dist\converter_app
```

不要只复制 `converter_app.exe`，它依赖同目录下的库文件和资源文件。目标电脑不需要安装 Python 或 Conda；如果缺少 Microsoft Visual C++ Runtime，需要先安装对应运行库。

## 测试

当前 `main` 分支还没有完整的自动化测试套件。新增测试时请放在 `tests/`，优先覆盖 `converter/` 中的纯 Python 逻辑，例如格式识别、参数合并、读取器行为和 HDF5 输出路径。

如果测试使用标准库 `unittest`：

```bat
conda run -n convert-da30 python -m unittest discover -s tests
```

如果测试使用 `pytest`，请先确认环境中已安装 `pytest`：

```bat
python -m pytest tests
```

## 不应提交的内容

以下内容是本地配置、缓存、生成数据或构建产物，不应作为源码上传：

- `.claude/`
- `.pytest_cache/`
- `__pycache__/`
- `*.pyc`
- `build/`
- `dist/`
- `data/converted_h5/`
- `data/previews/`

如果这些文件已经被 Git 跟踪，需要先从索引中移除；仅写入 `.gitignore` 不会自动取消跟踪。
