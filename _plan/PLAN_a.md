# PLAN.md — 光栅图转矢量图工具 (vecpic)

## 1. 项目概览

将 PNG、JPEG、BMP、GIF、TIFF、WebP 等光栅图片转换为 SVG 矢量图。核心矢量化由 **vtracer**（Rust 实现 + PyO3 Python 绑定）完成,提供 CLI 命令行工具及 Python API。

设计原则:
- **预处理与矢量化解耦**:由 Pillow 负责格式兼容与色彩规范化,vtracer 仅做矢量化,经像素接口直接对接,避免 vtracer 重复读盘且绕过其有限的格式支持。
- **配置集中化**:用 dataclass 统一参数,消除散落的 `**kwargs` 透传。
- **错误统一化**:自定义异常体系,CLI 层只做一次翻译。
- **可选依赖延迟导入**:cairosvg 等重型/平台敏感依赖按需加载。

## 2. 依赖

```
vtracer>=0.6.11    # 矢量化核心 (Rust + PyO3,pip 安装即用)
Pillow>=10.0       # 读取光栅图像格式 + 预处理
```

可选依赖(`pip install vecpic[export]`):

```
cairosvg>=2.7      # SVG → PDF/EPS 导出 (Linux 推荐,Windows/macOS 安装较麻烦)
```

无需安装 Rust 工具链:`vtracer` 的 PyPI 轮子已包含预编译的 Rust 二进制扩展。

> 注:cairosvg 依赖系统 cairo C 库,Windows/macOS 用户安装易失败。`writer.py` 采用延迟导入,缺失时给出明确指引,并支持通过 `inkscape` / `rsvg-convert` 子进程作为备选 backend。

## 3. 项目结构

```
vecpic/
├── vecpic/
│   ├── __init__.py          # 包入口,暴露 main() 和 convert()
│   ├── __main__.py          # python -m vecpic 入口
│   ├── cli.py               # argparse CLI 定义
│   ├── config.py            # VtracerConfig dataclass + 预设
│   ├── errors.py            # 自定义异常体系
│   ├── reader.py            # 图片格式检测与读取 (Pillow)
│   ├── converter.py         # 核心转换逻辑 (调用 vtracer API)
│   ├── writer.py            # SVG 后处理 & 多格式导出
│   └── pipeline.py          # 端到端流水线编排
├── tests/
│   ├── conftest.py          # pytest fixtures (临时目录、样本图片)
│   ├── fixtures/            # 测试图片资源
│   ├── test_reader.py       # 各格式读取测试
│   ├── test_converter.py    # vtracer 调用与参数测试 (桩化)
│   ├── test_writer.py       # 格式校验测试
│   ├── test_pipeline.py     # 端到端集成 + 视觉回归
│   └── test_cli.py          # CLI 集成测试
├── .github/workflows/ci.yml # 多平台/多 Python 版本 CI
├── pyproject.toml           # 项目元数据 + 构建配置
├── README.md
├── CHANGELOG.md
└── PLAN.md                  # 本规划文件
```

## 4. 模块设计

### 4.1 `errors.py` — 异常体系

```python
class VecpicError(Exception):
    """所有 vecpic 抛出的异常基类"""

class UnsupportedFormatError(VecpicError): ...
class EmptyFileError(VecpicError): ...
class VtracerNotInstalledError(VecpicError): ...
class ConversionFailedError(VecpicError): ...
class ExportBackendMissingError(VecpicError): ...
```

CLI 顶层只需 `try ... except VecpicError as e`,统一格式化输出与非零退出码。

### 4.2 `config.py` — 配置数据类与预设

```python
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class VtracerConfig:
    colormode: str = "color"          # 'color' | 'bw'
    hierarchical: str = "stacked"     # 'stacked' | 'cutout'
    mode: str = "spline"              # 'spline' | 'polygon' | 'pixel'
    filter_speckle: int = 4
    color_precision: int = 6
    layer_difference: int = 16
    corner_threshold: int = 60
    length_threshold: float = 4.0
    splice_threshold: int = 45
    path_precision: int = 8

    def merged(self, **overrides) -> "VtracerConfig":
        """显式参数覆盖预设,None 值忽略"""
        return replace(self, **{k: v for k, v in overrides.items() if v is not None})

PRESETS: dict[str, VtracerConfig] = {
    "bw":     VtracerConfig(colormode="bw", filter_speckle=0),
    "poster": VtracerConfig(mode="polygon", filter_speckle=4),
    "photo":  VtracerConfig(mode="spline",  filter_speckle=10),
}
```

预设语义:`pipeline.convert(preset="bw", filter_speckle=2)` = 取 `bw` 预设后,显式参数覆盖。

| preset | colormode | mode | filter_speckle | 场景 |
|--------|-----------|------|----------------|------|
| `bw` | `bw` | `spline` | 0 | 文字/签名/线条图 |
| `poster` | `color` | `polygon` | 4 | 插画/flat design |
| `photo` | `color` | `spline` | 10 | 照片/复杂图像 |

### 4.3 `reader.py` — 图片读取

```python
SUPPORTED_INPUTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp'}

def read_image(path: str) -> PIL.Image.Image:
    """打开并校验图片,返回规范化后的 RGBA Pillow Image"""

def detect_format(path: str) -> str:
    """从文件头检测真实格式(即使后缀错误也能识别)"""
```

职责:
- `PIL.Image.open()` 打开文件,校验可读、非空(否则抛 `EmptyFileError`)。
- 后缀不在 `SUPPORTED_INPUTS` → `UnsupportedFormatError`。
- GIF 取首帧。
- CMYK / P / L → 转 RGB,并用 `logging.info()` 记录(不再使用 `print`)。
- 透明 PNG/WebP:**保留 alpha 传给 vtracer**(vtracer 像素接口接收 RGBA);仅当用户传 `--flatten-bg` 时合成白底。
- 超过 `--max-size` 的图按比例 `Image.thumbnail()` 缩放,记录 INFO 日志。

### 4.4 `converter.py` — 矢量化核心

```python
def convert_image(
    image: PIL.Image.Image,
    output_path: str,
    config: VtracerConfig,
) -> None:
    """
    通过 vtracer.convert_pixels_to_svg() 进行矢量化。

    使用 pixels 接口而非 file 接口的原因:
      1. 让 reader.py 的色彩规范化/缩放真正生效;
      2. 绕过 vtracer 自身有限的格式支持(无需 vtracer 直接读 GIF/CMYK 等);
      3. 便于做尺寸限制与单测桩化。
    """
```

实现要点:
- 延迟 `import vtracer`,失败抛 `VtracerNotInstalledError("pip install vtracer")`。
- 输入 Pillow Image → 转 RGBA → `tobytes()` 喂给 `vtracer.convert_pixels_to_svg(pixels, size, **cfg_dict)`。
- 维护**参数名映射表**(CLI 友好名 → vtracer 实参名),对不同 vtracer 小版本做兼容(如 `layer_difference` vs `gradient_step`)。
- 捕获 vtracer 抛出的任何异常,包装为 `ConversionFailedError`,保留原始 message。
- DEBUG 日志输出最终生效的 config 全字段。

### 4.5 `writer.py` — SVG 校验与导出

```python
def validate_svg(path: str) -> bool:
    """
    结构性校验,而非仅 XML well-formed:
      1. 根元素必须是 {http://www.w3.org/2000/svg}svg
      2. 必须有 viewBox 或 width+height
      3. 至少包含一个 path / polygon / rect / circle 子元素
    使用标准库 xml.etree.ElementTree,不引入新依赖。
    """

def svg_to_pdf(svg_path: str, pdf_path: str) -> None:
    """优先 cairosvg;缺失则尝试 inkscape/rsvg-convert;均无则 ExportBackendMissingError"""

def svg_to_eps(svg_path: str, eps_path: str) -> None:
    """同上"""
```

cairosvg 仅在被调用时才 import,缺失时给出可执行的安装/替代指引。

### 4.6 `cli.py` — 命令行界面

```
usage: vecpic [-h] -i INPUT [-o OUTPUT] [--preset {bw,poster,photo}]
              [--colormode {color,bw}] [--hierarchical {stacked,cutout}]
              [--mode {spline,polygon,pixel}]
              [--filter-speckle N] [--color-precision N]
              [--layer-difference N] [--corner-threshold N]
              [--length-threshold F] [--splice-threshold N]
              [--path-precision N]
              [--max-size N] [--flatten-bg]
              [--format {svg,pdf,eps}]
              [-v | -vv | -q]
```

- 参数命名**与 vtracer 官方 CLI 完全一致**,便于用户迁移。
- `-v/-vv/-q` 控制 `logging` 级别(WARNING / INFO / DEBUG / ERROR)。
- `--output` 缺省 → 输入同目录、同名 `.svg`。
- `--format` 缺省 → 由输出后缀推断。
- `--max-size` 缺省 → 仅在 > 10000px 时打 warning,不缩放。
- 顶层捕获 `VecpicError`,格式化输出后 `sys.exit(1)`。

### 4.7 `pipeline.py` — 流水线编排

```python
def convert(
    input_path: str,
    output_path: str | None = None,
    preset: str | None = None,
    output_format: str | None = None,
    max_size: int | None = None,
    flatten_bg: bool = False,
    **overrides,                      # 覆盖预设的 vtracer 参数
) -> str:
    """
    端到端流程:
      1. 校验输入存在 + 格式支持 (errors)
      2. reader.read_image() 做色彩规范化/可选缩放
      3. config = PRESETS[preset].merged(**overrides) (或默认)
      4. converter.convert_image(image, tmp_svg, config)
      5. writer.validate_svg()
      6. 按 output_format 转 PDF/EPS (可选)
    返回最终输出路径。
    """
```

## 5. 错误处理矩阵

| 错误场景 | 异常类 | CLI 输出 |
|---|---|---|
| 输入文件不存在 | `FileNotFoundError` | "找不到文件: ..." |
| 不支持的格式 | `UnsupportedFormatError` | 列出支持格式 |
| 文件 0 字节 | `EmptyFileError` | "文件为空: ..." |
| CMYK 图像 | (不抛) | INFO 日志 "已转换 CMYK→RGB" |
| 透明通道 | (不抛) | DEBUG 日志,默认保留 alpha |
| 超大图(>10000px) | (不抛) | WARNING 日志;`--max-size` 时自动缩放 |
| vtracer 未安装 | `VtracerNotInstalledError` | 提示 `pip install vtracer` |
| vtracer 内部异常 | `ConversionFailedError` | 包装并保留原 message |
| 输出无写权限 | `PermissionError` | "无写入权限: ..." |
| 缺失 cairosvg/inkscape | `ExportBackendMissingError` | 给出 3 种可选方案 |

## 6. 数据流

```
  用户输入 path.png
        │
        ▼
  reader.read_image()
        │  Pillow Image
        │  - 0 字节/格式校验
        │  - GIF 首帧
        │  - CMYK/P/L → RGB
        │  - 可选 thumbnail() 缩放
        │  - 默认保留 alpha
        ▼
  config = PRESETS[preset].merged(**cli_args)
        │
        ▼
  converter.convert_image()
        │  Image → RGBA bytes
        │  vtracer.convert_pixels_to_svg(pixels, size, **cfg)
        ▼
  tmp .svg
        │
        ▼
  writer.validate_svg()  (结构性断言)
        │
        ├─ format=svg → 移动到目标路径
        ├─ format=pdf → cairosvg / inkscape / rsvg-convert
        └─ format=eps → 同上
```

## 7. 测试策略

| 层级 | 内容 | 框架 |
|------|------|------|
| 单元测试 | `reader` 格式检测/色彩规范化、`config` 预设合并、`writer` 结构校验、`errors` 翻译 | `pytest` |
| 桩化单测 | `converter` 用 `monkeypatch` 替换 `vtracer.convert_pixels_to_svg`,验证参数映射与异常包装 | `pytest` + `monkeypatch` |
| 集成测试 | 真实调用 vtracer,端到端 PNG→SVG;打 `@pytest.mark.slow` 标记 | `pytest` + `tmp_path` |
| 视觉回归 | SVG → cairosvg 渲染回 PNG → 与原图算 SSIM,阈值 ≥ 0.85 | `pytest` + `scikit-image` (dev) |
| 结构回归 | path 数量在 [N-tol, N+tol] 区间;文件大小在合理范围;viewBox 比例匹配原图 | `pytest` |
| CLI 测试 | `subprocess.run([sys.executable, "-m", "vecpic", ...])` | `pytest` |

> **不使用 hash 比对回归**:vtracer 不同版本输出会有微小差异,hash 断言极脆弱。

测试 fixtures 放 `tests/fixtures/`,包含:纯色方块 PNG、透明背景 PNG、JPEG 照片、CMYK JPEG、多帧 GIF、色彩渐变图、超大图(用代码生成,不入库)。

## 8. `pyproject.toml` 概览

```toml
[project]
name = "vecpic"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "Pillow>=10.0",
    "vtracer>=0.6.11",
]

[project.optional-dependencies]
export = ["cairosvg>=2.7"]
dev = [
    "pytest",
    "pytest-cov",
    "ruff",
    "mypy",
    "scikit-image",   # 视觉回归 SSIM
    "pre-commit",
]

[project.scripts]
vecpic = "vecpic.cli:main"

[tool.setuptools.packages.find]
where = ["."]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
strict = true

[tool.pytest.ini_options]
markers = ["slow: 调用真实 vtracer 的集成测试"]
addopts = "-ra --strict-markers"
```

> cairosvg 不在主 `dependencies` 中,仅作可选导出依赖。

## 9. 实现顺序

| 阶段 | 文件 | 产出 |
|------|------|------|
| 1 | `pyproject.toml`、`vecpic/__init__.py`、`errors.py`、`config.py` | `pip install -e .` 通过,异常与配置就绪 |
| 2 | `reader.py` + 单测(CMYK/透明/GIF 多帧/超大图 fixtures) | reader 覆盖率 100% |
| 3 | `converter.py` + 桩化单测 | 与 vtracer 解耦,参数映射稳定 |
| 4 | `writer.py`(结构校验 + 延迟导入 cairosvg + 备选 backend) | export 可选生效 |
| 5 | `pipeline.py`、`cli.py`、`__main__.py` + 集成测试 | `vecpic -i x.png` 跑通 |
| 6 | `logging` 接入、`.github/workflows/ci.yml`(3.10/3.11/3.12 × Linux/macOS/Windows)、ruff/mypy/pre-commit | 绿色 CI |
| 7 | 视觉回归测试、`README.md`、`CHANGELOG.md`、PyPI 发布 | 0.1.0 上线 |

## 10. 后续增强方向

- **批量处理**:`vecpic input/ output/ --recursive`,可结合 `ProcessPoolExecutor` 并行。
- **图片预处理滤镜**:去噪 (JPEG artifacts)、锐化、对比度增强。
- **SVG 大小优化**:scour/svgo 集成。
- **进度条**:大图或批量转换时 `tqdm` 显示进度。
- **GUI**:基于此 CLI 的简单 `tkinter`/`PySimpleGUI` 窗口。
- **更多导出格式**:PDF 矢量保真之外,可探索 EMF、AI(通过 inkscape)。