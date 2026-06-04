实现将 DA30 的原始 `.txt/.pxt/.zip` 数据转换为 ERLab/xarray 可读取的 HDF5 文件。

## 开发运行

在已安装 Anaconda 且存在 `convert-da30` 环境的开发电脑上运行：

```bat
run.bat
```

`run.bat` 会在 `D:\Projects\convert` 中启动 GUI：

```bat
run.bat
```

脚本会优先使用 `%USERPROFILE%\anaconda3\Scripts\conda.exe run -n convert-da30`，找不到 conda 时回退到 `D:\Anaconda\envs\convert-da30\python.exe`。

## 构建文件夹版 EXE

第一版封装采用 PyInstaller onedir 文件夹版，不制作安装器，也不制作单文件 EXE。

```bat
build_exe.bat
```

脚本会优先使用 conda 环境运行 PyInstaller，找不到 conda 时回退到 `D:\Anaconda\envs\convert-da30\Scripts\pyinstaller.exe`。

构建输出：

```text
dist\converter_app\converter_app.exe
```

## 分发方式

将整个文件夹复制到目标 Windows 电脑：

```text
dist\converter_app
```

目标电脑运行：

```text
converter_app.exe
```

不要只复制 `converter_app.exe`，它依赖同目录下的库文件和资源文件。目标电脑不需要安装 Python 或 Conda。

## 注意

- `data/converted_h5` 中的实验输出不属于软件封装内容。
- `.claude` 等本地配置不属于软件封装内容。
- 如果目标电脑缺少 Microsoft Visual C++ Runtime，需先安装对应运行库。
