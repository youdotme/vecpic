# PLAN.md — 光栅图转矢量图工具 `vecpic`

## 1. 项目概览

`vecpic` 是一个将 PNG、JPEG、BMP、GIF、TIFF、WebP 等光栅图片转换为 SVG 矢量图的工具。

核心矢量化由 **vtracer** 完成。`vtracer` 是 Rust 实现的矢量化库，并提供 PyO3 Python 绑定。`vecpic` 在其基础上提供：

- 命令行工具 CLI；
- Python API；
- 图片读取与预处理；
- SVG 结构校验与安全输出；
- 可选 PDF/EPS 导出；
- 更统一的配置、异常和测试体系。

核心设计原则：

1. **预处理与矢量化解耦**

   由 Pillow 负责格式兼容、EXIF 方向修正、色彩空间转换、透明通道处理、尺寸限制等；由 vtracer 负责矢量化。

   `vecpic` 优先使用 vtracer 的像素接口，而不是文件接口，从而避免：

   - vtracer 重复读盘；
   - vtracer 格式支持有限；
   - Pillow 预处理结果无法传递给 vtracer；
   - 测试时难以桩化 vtracer 调用。

2. **配置集中化**

   使用 `dataclass` 统一管理 vtracer 参数，避免在代码中散落大量 `**kwargs` 透传。

3. **错误统一化**

   定义 `VecpicError` 异常体系，内部模块尽量抛出自定义异常。CLI 顶层只做一次异常翻译和退出码处理。

4. **可选依赖延迟导入**

   `cairosvg` 等重型或平台敏感依赖仅在 PDF/EPS 导出时按需导入，避免影响普通 SVG 转换。

5. **输出职责集中化**

   `converter.py` 只负责生成中间 SVG；`writer.py` 负责 SVG 校验、SVG 最终输出、原子替换、PDF/EPS 导出。`pipeline.py` 只负责流程编排，不直接操作最终输出文件。

6. **平台兼容优先**

   主功能应在 Linux、macOS、Windows 上均可运行。PDF/EPS 导出属于增强能力，应允许后端缺失时给出明确提示，而不是影响 SVG 主流程。

---

## 2. 功能范围

### 2.1 0.1.0 目标

首版重点保证核心转换能力稳定：

- 支持输入：
  - PNG
  - JPEG/JPG/JFIF/JPE
  - BMP
  - GIF，默认取首帧
  - TIFF/TIF，默认取首帧
  - WebP，默认取首帧
- 输出 SVG；
- CLI 命令：
  - `vecpic -i input.png`
  - `python -m vecpic -i input.png`
- Python API：
  - `vecpic.convert(...)`
- 支持 vtracer 常用参数；
- 支持预设：`bw`、`poster`、`photo`；
- 支持 EXIF 方向修正；
- 支持透明通道默认保留；
- 支持可选 flatten 背景色；
- 支持最大尺寸限制；
- 支持 SVG 结构校验；
- 支持 SVG 安全最终输出；
- 基础 CI 覆盖 Linux/macOS/Windows。

### 2.2 0.2.0 目标

在首版稳定后增强：

- PDF/EPS 导出能力完善；
- 多导出 backend：`cairosvg` / `inkscape` / `rsvg-convert`；
- 视觉回归测试；
- 批量处理；
- SVG 优化；
- 进度显示；
- 图片预处理滤镜。

---

## 3. 依赖

### 3.1 核心依赖

```text
vtracer>=0.6.11    # 矢量化核心，Rust + PyO3，PyPI 通常提供预编译 wheel
Pillow>=10.0       # 图片读取、格式兼容、预处理
```

用户无需安装 Rust 工具链。`vtracer` 的 PyPI 包通常包含预编译的 Rust 二进制扩展。

### 3.2 可选依赖

用户如需 SVG → PDF 等导出功能，可安装：

```bash
pip install vecpic[export]
```

可选依赖：

```text
cairosvg>=2.7
```

注意：

- CairoSVG 依赖系统 Cairo C 库；
- Linux 上通常较易安装；
- Windows/macOS 上可能因为系统库缺失导致安装或运行失败；
- 因此 `writer.py` 必须延迟导入 `cairosvg`；
- 缺失时应提示用户安装 `cairosvg`、`inkscape` 或 `rsvg-convert`。

### 3.3 开发依赖

```text
pytest
pytest-cov
ruff
mypy
pre-commit
scikit-image    # 仅用于视觉回归测试，可后置
```

---

## 4. 项目结构

```text
vecpic/
├── vecpic/
│   ├── __init__.py          # 包入口，暴露 convert() 和版本信息
│   ├── __main__.py          # python -m vecpic 入口
│   ├── cli.py               # argparse CLI 定义
│   ├── config.py            # VtracerConfig dataclass + 预设
│   ├── errors.py            # 自定义异常体系
│   ├── reader.py            # 图片格式检测与读取，基于 Pillow
│   ├── converter.py         # 核心转换逻辑，调用 vtracer API，生成中间 SVG
│   ├── writer.py            # SVG 校验、SVG 最终输出与 PDF/EPS 导出
│   └── pipeline.py          # 端到端流水线编排
├── tests/
│   ├── conftest.py          # pytest fixtures
│   ├── fixtures/            # 测试图片资源
│   ├── test_config.py
│   ├── test_errors.py
│   ├── test_reader.py
│   ├── test_converter.py    # vtracer 调用与参数测试，桩化
│   ├── test_writer.py       # SVG 校验、finalize_svg、导出测试
│   ├── test_pipeline.py
│   └── test_cli.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
└── PLAN.md
```

---

## 5. 模块设计

### 5.1 `errors.py` — 异常体系

所有由 `vecpic` 主动抛出的异常应继承自 `VecpicError`。

```python
class VecpicError(Exception):
    """所有 vecpic 抛出的异常基类"""


class ConfigError(VecpicError):
    """配置错误，例如未知参数、非法参数值、预设不存在"""


class FileAccessError(VecpicError):
    """文件访问错误基类"""


class InputFileNotFoundError(FileAccessError):
    """输入文件不存在"""


class OutputPermissionError(FileAccessError):
    """输出路径无写入权限"""


class UnsupportedFormatError(VecpicError):
    """不支持的输入格式"""


class EmptyFileError(VecpicError):
    """输入文件为空"""


class InvalidImageError(VecpicError):
    """图片损坏、无法解码或 Pillow 无法识别"""


class ImageTooLargeError(VecpicError):
    """图片尺寸过大，存在内存风险"""


class VtracerNotInstalledError(VecpicError):
    """vtracer 未安装或无法导入"""


class ConversionFailedError(VecpicError):
    """vtracer 转换失败"""


class SvgValidationError(VecpicError):
    """生成的 SVG 未通过结构校验"""


class ExportBackendMissingError(VecpicError):
    """缺少 PDF/EPS 导出 backend"""


class ExportFailedError(VecpicError):
    """PDF/EPS 导出失败"""
```

设计要求：

- 内部模块尽量将底层异常包装为 `VecpicError` 子类；
- CLI 顶层主要捕获 `VecpicError`；
- 对极少数未包装的意外异常，CLI 可在 `--debug` 或 `-vv` 时输出 traceback；
- 常规模式下输出简洁错误信息。

CLI 顶层示例：

```python
try:
    ...
except VecpicError as exc:
    logger.error("%s", exc)
    return 1
except KeyboardInterrupt:
    logger.error("用户中断")
    return 130
```

---

### 5.2 `config.py` — 配置数据类与预设

#### 5.2.1 `VtracerConfig`

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from .errors import ConfigError

_NON_NEGATIVE_INT_FIELDS = (
    "filter_speckle",
    "color_precision",
    "layer_difference",
    "corner_threshold",
    "max_iterations",
    "splice_threshold",
    "path_precision",
)


@dataclass(frozen=True)
class VtracerConfig:
    colormode: str = "color"          # "color" | "bw"
    hierarchical: str = "stacked"     # "stacked" | "cutout"
    mode: str = "spline"              # "spline" | "polygon" | "pixel"

    filter_speckle: int = 4
    color_precision: int = 6
    layer_difference: int = 16

    corner_threshold: int = 60
    length_threshold: float = 4.0
    max_iterations: int = 10
    splice_threshold: int = 45
    path_precision: int = 3

    def __post_init__(self) -> None:
        if self.colormode not in {"color", "bw"}:
            raise ConfigError(f"非法 colormode: {self.colormode!r}")

        if self.hierarchical not in {"stacked", "cutout"}:
            raise ConfigError(f"非法 hierarchical: {self.hierarchical!r}")

        if self.mode not in {"spline", "polygon", "pixel"}:
            raise ConfigError(f"非法 mode: {self.mode!r}")

        for name in _NON_NEGATIVE_INT_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, int):
                raise ConfigError(f"{name} 必须是整数")
            if value < 0:
                raise ConfigError(f"{name} 必须 >= 0")

        if self.length_threshold < 0:
            raise ConfigError("length_threshold 必须 >= 0")

    def merged(self, **overrides: object) -> "VtracerConfig":
        """
        显式参数覆盖当前配置，None 值忽略。

        未知字段直接抛 ConfigError，避免用户传错参数名后被静默忽略。
        """
        valid_keys = set(self.__dataclass_fields__)
        unknown = set(overrides) - valid_keys
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ConfigError(f"未知配置项: {names}")

        values = {k: v for k, v in overrides.items() if v is not None}
        return replace(self, **values)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
```

说明：

- `max_iterations` 纳入配置，保持与 vtracer 常用参数一致；
- `path_precision` 默认值采用更接近 vtracer 常见默认行为的 `3`；
- 参数校验放在 `VtracerConfig` 内部；
- 公共 API 中传入的未知参数不得静默忽略；
- `to_dict()` 直接复用 `dataclasses.asdict`，新增字段时无需同步维护。

#### 5.2.2 预设

```python
PRESETS: dict[str, VtracerConfig] = {
    "bw": VtracerConfig(
        colormode="bw",
        mode="spline",
        filter_speckle=0,
    ),
    "poster": VtracerConfig(
        colormode="color",
        mode="polygon",
        filter_speckle=4,
    ),
    "photo": VtracerConfig(
        colormode="color",
        mode="spline",
        filter_speckle=10,
    ),
}
```

预设合并语义：

```python
pipeline.convert(
    input_path="input.png",
    preset="bw",
    filter_speckle=2,
)
```

等价于：

1. 取 `PRESETS["bw"]`；
2. 用显式传入的 `filter_speckle=2` 覆盖预设；
3. 其他字段保留预设值。

| preset | colormode | mode | filter_speckle | 适用场景 |
|---|---|---|---:|---|
| `bw` | `bw` | `spline` | 0 | 文字、签名、线条图、黑白图标 |
| `poster` | `color` | `polygon` | 4 | 插画、flat design、海报风格图片 |
| `photo` | `color` | `spline` | 10 | 照片、复杂色彩图片 |

---

### 5.3 `reader.py` — 图片读取与预处理

#### 5.3.1 支持格式

`vecpic` 应以 Pillow 识别出的真实格式为准，文件扩展名只用于提示和默认输出路径推断。

```python
SUPPORTED_FORMATS = {"PNG", "JPEG", "BMP", "GIF", "TIFF", "WEBP"}

SUPPORTED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".jpe", ".jfif",
    ".bmp", ".gif", ".tif", ".tiff", ".webp",
}
```

行为约定：

- 如果扩展名不常见，但文件头可被 Pillow 正确识别为支持格式，则允许转换，并输出 warning；
- 如果扩展名支持，但真实格式不支持，则拒绝；
- 如果 Pillow 无法识别，抛 `InvalidImageError`；
- 空文件抛 `EmptyFileError`。

#### 5.3.2 接口设计

```python
from pathlib import Path
from PIL import Image


def detect_format(path: str | Path) -> str:
    """
    使用 Pillow 从文件头检测真实格式。
    返回值如 "PNG" / "JPEG" / "GIF" / "TIFF" / "WEBP"。
    检测失败时抛 InvalidImageError。
    """


def read_image(
    path: str | Path,
    *,
    max_size: int | None = None,
    flatten_bg: str | None = None,
) -> Image.Image:
    """
    打开、校验并规范化图片。

    处理内容:
    1. 检查文件存在;
    2. 检查文件非空;
    3. 使用 Pillow 检测真实格式;
    4. 校验真实格式是否支持;
    5. 应用 EXIF Orientation 修正;
    6. GIF/WebP/TIFF 多帧默认取首帧;
    7. CMYK / P / L 等模式转换为 RGB 或 RGBA;
    8. 默认保留 alpha;
    9. flatten_bg 不为空时，将透明通道合成到指定背景色;
    10. max_size 不为空时，将最长边缩放到不超过 max_size;
    11. 返回 Pillow Image。
    """
```

#### 5.3.3 EXIF 方向修正

手机照片常带 EXIF Orientation，读取后必须调用：

```python
from PIL import ImageOps

image = ImageOps.exif_transpose(image)
```

#### 5.3.4 多帧图片策略

对 GIF / 动态 WebP / 多页 TIFF 默认只取首帧：

```python
try:
    image.seek(0)
except EOFError:
    ...
```

日志：

```text
INFO: 检测到多帧图片，已使用首帧
```

未来可扩展 `--frame-index N`，不纳入 0.1.0。

#### 5.3.5 色彩空间处理

| 输入模式 | 默认处理 |
|---|---|
| `RGB` | 保持 |
| `RGBA` | 保持 alpha |
| `LA` | 转为 `RGBA` |
| `L` | 转为 `RGB` |
| `P` | 若有透明信息转 `RGBA`，否则转 `RGB` |
| `CMYK` | 转为 `RGB` |
| 其他 | 尽量转 `RGBA` 或 `RGB`，失败抛 `InvalidImageError` |

不使用 `print()`，统一使用 `logging`。示例日志：

```text
INFO: 已转换 CMYK → RGB
INFO: 已转换 P → RGBA
DEBUG: 检测到透明通道，默认保留 alpha
```

#### 5.3.6 透明通道与背景合成

默认行为：

- 保留 alpha；
- 将 RGBA 像素传给 vtracer；
- 不自动合成白底。

仅当用户显式传入 `flatten_bg` 时合成背景色：

```bash
vecpic -i logo.png --flatten-bg "#ffffff"
vecpic -i logo.png --flatten-bg white
```

```python
convert("logo.png", flatten_bg="#ffffff")
```

`flatten_bg` 设计为字符串而不是布尔值，便于用户指定背景颜色。

#### 5.3.7 尺寸限制

`max_size` 表示最长边最大像素数。

行为：

- `max_size is None`：不主动缩放；若最长边超过 10000px 输出 warning；
- 指定 `max_size`：`Image.thumbnail()` 按比例缩放，保留长宽比，记录缩放前后尺寸。

示例日志：

```text
WARNING: 输入图片尺寸很大: 18000x12000，转换可能非常慢，可考虑使用 --max-size
INFO: 已缩放图片: 18000x12000 -> 2048x1365
```

#### 5.3.8 Pillow 解压炸弹风险

需要处理 Pillow 的 `DecompressionBombWarning` / `DecompressionBombError`。

```python
MAX_PIXELS_WARNING = 100_000_000
MAX_PIXELS_HARD_LIMIT = 300_000_000

# 模块加载时设置 Pillow 全局上限，避免 vecpic 之外的代码绕过检查
Image.MAX_IMAGE_PIXELS = MAX_PIXELS_HARD_LIMIT
```

行为：

- 超过 warning 阈值，输出 warning；
- 超过 hard limit，抛 `ImageTooLargeError`；
- 提示用户使用较小图片或 `--max-size`。

---

### 5.4 `converter.py` — 矢量化核心

#### 5.4.1 接口

```python
from pathlib import Path
from PIL import Image
from .config import VtracerConfig


def convert_image(
    image: Image.Image,
    output_path: str | Path,
    config: VtracerConfig,
) -> None:
    """
    将 Pillow Image 转换为中间 SVG 文件。

    使用 vtracer 的像素接口，而不是文件接口。

    步骤:
    1. 延迟 import vtracer;
    2. 将 Pillow Image 统一转为 RGBA;
    3. 获取 bytes 和尺寸;
    4. 通过适配层调用 vtracer;
    5. 将 SVG 写入 output_path;
    6. 捕获并包装 vtracer 异常。

    注意:
    - converter.py 只负责生成中间 SVG；
    - 不负责最终输出路径的原子替换；
    - 最终 SVG 输出由 writer.finalize_svg() 负责。
    """
```

#### 5.4.2 使用像素接口的原因

1. 让 `reader.py` 的预处理结果真正生效；
2. 绕过 vtracer 文件接口的格式限制；
3. 避免 vtracer 重复读盘；
4. 便于对 vtracer 调用做单元测试桩化；
5. 便于未来支持从内存图像直接转换。

#### 5.4.3 vtracer 导入

```python
try:
    import vtracer
except ImportError as exc:
    raise VtracerNotInstalledError(
        "未安装 vtracer，请执行: pip install vtracer"
    ) from exc
```

#### 5.4.4 vtracer API 适配层

不同 vtracer 小版本的 Python API 可能存在差异，因此需要封装适配层。

```python
def _call_vtracer_convert_pixels_to_svg(
    vtracer_module: object,
    pixels: bytes,
    size: tuple[int, int],
    config: VtracerConfig,
) -> str:
    """
    调用 vtracer 像素接口，统一返回 SVG 字符串。

    实现注意:
    - 确认当前 vtracer 版本的准确签名;
    - 尽量使用 keyword args;
    - 必要时通过 inspect.signature 做兼容;
    - 对已知参数别名做映射;
    - 不支持的参数应在 DEBUG 日志中说明。
    """
```

参数名映射示例：

```python
VTRACER_PARAM_ALIASES = {
    "layer_difference": ("layer_difference", "gradient_step"),
}
```

处理策略：

1. 以当前 vtracer 官方参数名为主；
2. 对少数历史别名做兼容；
3. 当前 vtracer 不支持某参数时：
   - DEBUG 日志记录；
   - 若该参数是用户显式设置的，考虑抛 `ConfigError`；
   - 若是默认参数，可跳过。

#### 5.4.5 输出写入

vtracer 不同版本中“像素接口”可能存在两种行为：

- 返回 SVG 字符串，由 `vecpic` 自行写文件；
- 直接写出到给定文件路径。

适配层 `_call_vtracer_convert_pixels_to_svg` 应屏蔽这一差异：**对外始终返回 SVG 字符串**；若底层只支持写文件，则在临时路径写出后读回字符串再返回。

上层逻辑保持简单：

```python
svg = _call_vtracer_convert_pixels_to_svg(...)
Path(output_path).write_text(svg, encoding="utf-8")
```

> 这是本规划中唯一与 vtracer 实际 API 强耦合、需要在实现阶段重点验证的假设。

#### 5.4.6 异常处理

- vtracer 未安装：`VtracerNotInstalledError`；
- vtracer 内部异常：包装为 `ConversionFailedError`；
- 保留原始异常 message，DEBUG 模式下可通过异常链看到原始 traceback。

```python
try:
    svg = _call_vtracer_convert_pixels_to_svg(...)
except Exception as exc:
    raise ConversionFailedError(f"vtracer 转换失败: {exc}") from exc
```

#### 5.4.7 日志

DEBUG 日志输出最终生效的配置：

```text
DEBUG: vtracer config: {'colormode': 'color', 'mode': 'spline', ...}
```

不得输出完整像素数据。

---

### 5.5 `writer.py` — SVG 校验、SVG 最终输出与导出

`writer.py` 统一负责所有“输出相关”能力：

1. 校验 SVG；
2. 将临时 SVG 安全发布为最终 SVG 文件；
3. 导出 PDF/EPS；
4. 包装输出权限错误；
5. 为未来 SVG 后处理、压缩、优化预留入口。

`pipeline.py` 不应直接调用 `os.replace()` 操作最终输出文件，而应调用 `writer.finalize_svg()`。

#### 5.5.1 SVG 校验

```python
from pathlib import Path


def validate_svg(path: str | Path) -> None:
    """校验 SVG 结构，失败抛 SvgValidationError。"""
```

校验规则：

1. XML 可解析；
2. 根元素 local name 必须是 `svg`；
3. 必须有 `viewBox` 或 `width` + `height`；
4. 至少包含一个图形元素；
5. 图形元素递归查找，不仅限根节点直接子元素。

```python
GRAPHIC_TAGS = {
    "path", "polygon", "polyline",
    "rect", "circle", "ellipse", "line",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
```

不应只接受 `{http://www.w3.org/2000/svg}svg`，也应兼容无命名空间但结构合理的 SVG。

#### 5.5.2 SVG 直接输出：`finalize_svg()`

虽然 SVG 是 vtracer 的原生输出格式，但最终 SVG 文件写入仍应由 `writer.py` 负责，而不是由 `pipeline.py` 直接 `os.replace()`。

接口：

```python
def finalize_svg(
    tmp_svg_path: str | Path,
    output_path: str | Path,
    *,
    validate: bool = True,
) -> None:
    """
    将临时 SVG 安全发布为最终 SVG 文件。

    步骤:
    1. 可选执行 validate_svg(tmp_svg_path);
    2. 确保输出目录存在;
    3. 使用 os.replace() 原子替换目标文件;
    4. 捕获 PermissionError/OSError 并包装为 OutputPermissionError。

    注意:
    - tmp_svg_path 通常由 converter.convert_image() 生成;
    - output_path 是用户最终期望的 .svg 输出路径;
    - 若 validate=True，校验失败时不得覆盖已有目标文件。
    """
```

设计原因：

- 避免转换失败时留下半截文件；
- 避免 SVG 校验失败时覆盖用户已有文件；
- 保持所有输出相关逻辑集中在 `writer.py`；
- 方便未来增加 SVG 后处理、压缩、优化、格式化；
- 让 `pipeline.py` 只负责编排，不处理底层文件替换细节。

推荐实现要点：

```python
import os
from pathlib import Path

from .errors import OutputPermissionError


def finalize_svg(
    tmp_svg_path: str | Path,
    output_path: str | Path,
    *,
    validate: bool = True,
) -> None:
    tmp_svg_path = Path(tmp_svg_path)
    output_path = Path(output_path)

    if validate:
        validate_svg(tmp_svg_path)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp_svg_path, output_path)
    except PermissionError as exc:
        raise OutputPermissionError(f"无写入权限: {output_path}") from exc
    except OSError as exc:
        raise OutputPermissionError(f"无法写入输出文件 {output_path}: {exc}") from exc
```

说明：

- `os.replace()` 在同一文件系统内可尽量保证原子替换；
- 因此 pipeline 中创建临时目录时应将临时文件放在目标目录下；
- 如果目标文件已存在，`os.replace()` 会覆盖；
- 若需要防止覆盖，未来可增加 `--no-overwrite` 参数。

#### 5.5.3 导出接口：`export_svg()`

```python
def export_svg(
    svg_path: str | Path,
    output_path: str | Path,
    output_format: str,        # "pdf" | "eps"
    *,
    backend: str = "auto",     # "auto" | "cairosvg" | "inkscape" | "rsvg"
) -> None:
    """
    将 SVG 导出为 PDF/EPS。

    注意:
    - 调用前应确保 svg_path 已通过 validate_svg();
    - export_svg() 内部也可以做轻量校验或信任上层;
    - 所有导出失败应包装为 ExportFailedError 或 ExportBackendMissingError。
    """
```

#### 5.5.4 PDF 导出策略

PDF backend 优先级：

1. `cairosvg`
2. `inkscape`
3. `rsvg-convert`

`cairosvg` 延迟导入：

```python
try:
    import cairosvg
except ImportError:
    ...
```

#### 5.5.5 EPS 导出策略

EPS 的支持情况更复杂，不应默认假设 CairoSVG 一定可靠支持 EPS。

EPS backend 优先级：

1. `inkscape`
2. `rsvg-convert`，若当前版本支持 EPS；
3. `cairosvg`，仅在确认可用时作为 fallback。

#### 5.5.6 外部命令检测

```python
import shutil

shutil.which("inkscape")
shutil.which("rsvg-convert")
```

外部命令失败时捕获 `subprocess.CalledProcessError`，包装为 `ExportFailedError`。

#### 5.5.7 缺少导出 backend

如果所有 backend 不可用，抛 `ExportBackendMissingError`，信息应给出明确方案：

```text
无法导出 PDF/EPS，未找到可用 backend。

可选方案:
1. pip install vecpic[export]
2. 安装 Inkscape 并确保 inkscape 在 PATH 中
3. 安装 librsvg 并确保 rsvg-convert 在 PATH 中
```

---

### 5.6 `cli.py` — 命令行界面

#### 5.6.1 基础用法

```text
usage: vecpic -i INPUT [-o OUTPUT]
              [--format {svg,pdf,eps}]
              [--export-backend {auto,cairosvg,inkscape,rsvg}]
              [--preset {bw,poster,photo}]
              [--colormode {color,bw}]
              [--hierarchical {stacked,cutout}]
              [--mode {spline,polygon,pixel}]
              [--filter-speckle N]
              [--color-precision N]
              [--layer-difference N]
              [--corner-threshold N]
              [--length-threshold F]
              [--max-iterations N]
              [--splice-threshold N]
              [--path-precision N]
              [--max-size N]
              [--flatten-bg COLOR]
              [--keep-svg]
              [-v | -vv | -q]
```

#### 5.6.2 参数说明

| 参数 | 说明 |
|---|---|
| `-i`, `--input` | 输入图片路径 |
| `-o`, `--output` | 输出文件路径 |
| `--format` | 输出格式，`svg`、`pdf`、`eps` |
| `--export-backend` | 导出 backend，默认 `auto` |
| `--preset` | 使用预设配置 |
| `--colormode` 等 vtracer 参数 | 见 5.2 / 5.6.5 |
| `--max-size` | 限制输入图最长边 |
| `--flatten-bg` | 将透明通道合成到指定背景色 |
| `--keep-svg` | 导出 PDF/EPS 时保留中间 SVG |
| `-v` | INFO 日志 |
| `-vv` | DEBUG 日志 |
| `-q` | 仅 ERROR 日志 |

#### 5.6.3 日志级别

| 参数 | logging level |
|---|---|
| 无 | `WARNING` |
| `-v` | `INFO` |
| `-vv` | `DEBUG` |
| `-q` | `ERROR` |

#### 5.6.4 输出格式推断规则

未知后缀视为错误，具体规则按以下优先级：

1. 显式指定 `--format`，以 `--format` 为准；
2. 同时指定 `--output` 且后缀与 `--format` 冲突，报 `ConfigError`；
3. 未指定 `--format`，但指定了 `--output`，从输出后缀推断；
4. `--format` 与 `--output` 都未指定，默认输出 SVG；
5. 未指定 `--output`，根据输入文件名生成默认输出路径。

| 命令 | 行为 |
|---|---|
| `vecpic -i a.png` | 输出 `a.svg` |
| `vecpic -i a.png -o out.svg` | 输出 SVG |
| `vecpic -i a.png -o out.pdf` | 输出 PDF |
| `vecpic -i a.png --format pdf` | 输出 `a.pdf` |
| `vecpic -i a.png -o out.pdf --format svg` | 报错，格式冲突 |
| `vecpic -i a.png -o out.xxx` | 报错，未知后缀 |

#### 5.6.5 参数命名

CLI 参数尽量与 vtracer 官方 CLI 保持一致；Python 内部统一使用下划线命名：

| CLI | Python |
|---|---|
| `--filter-speckle` | `filter_speckle` |
| `--color-precision` | `color_precision` |
| `--layer-difference` | `layer_difference` |
| `--corner-threshold` | `corner_threshold` |
| `--length-threshold` | `length_threshold` |
| `--max-iterations` | `max_iterations` |
| `--splice-threshold` | `splice_threshold` |
| `--path-precision` | `path_precision` |

---

### 5.7 `pipeline.py` — 流水线编排

#### 5.7.1 Python API

```python
from pathlib import Path


def convert(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    preset: str | None = None,
    output_format: str | None = None,
    export_backend: str = "auto",
    max_size: int | None = None,
    flatten_bg: str | None = None,
    keep_svg: bool = False,
    colormode: str | None = None,
    hierarchical: str | None = None,
    mode: str | None = None,
    filter_speckle: int | None = None,
    color_precision: int | None = None,
    layer_difference: int | None = None,
    corner_threshold: int | None = None,
    length_threshold: float | None = None,
    max_iterations: int | None = None,
    splice_threshold: int | None = None,
    path_precision: int | None = None,
) -> str:
    """端到端转换流程，返回最终输出文件路径字符串。"""
```

公共签名虽长，但对 IDE 自动补全和静态检查友好。

内部把 11 个 vtracer 参数收拢到 `overrides` dict 后传给 `VtracerConfig.merged()`，避免业务代码再处理无限制 `**kwargs`：

```python
overrides = {
    "colormode": colormode,
    "hierarchical": hierarchical,
    "mode": mode,
    "filter_speckle": filter_speckle,
    "color_precision": color_precision,
    "layer_difference": layer_difference,
    "corner_threshold": corner_threshold,
    "length_threshold": length_threshold,
    "max_iterations": max_iterations,
    "splice_threshold": splice_threshold,
    "path_precision": path_precision,
}
```

#### 5.7.2 流程

```text
1. 校验输入路径存在且是文件;
2. 根据 output_path / output_format 推断最终输出路径和格式;
3. reader.read_image() 读取并预处理图片;
4. 根据 preset 获取基础 VtracerConfig;
5. 用显式参数覆盖配置;
6. 在目标目录创建临时目录;
7. converter.convert_image() 生成临时 SVG;
8. writer.validate_svg() 校验临时 SVG;
9. format=svg:
     调用 writer.finalize_svg(tmp_svg, final_svg, validate=False);
10. format=pdf/eps:
     调用 writer.export_svg(tmp_svg, final_output, output_format, backend=export_backend);
     keep_svg 决定是否保留中间 SVG;
11. 返回最终输出路径。
```

说明：

- 第 8 步已经统一执行 `writer.validate_svg()`；
- 因此第 9 步调用 `finalize_svg(..., validate=False)`，避免重复校验；
- 如果希望 `finalize_svg()` 自身完全独立，也可以让第 9 步使用默认 `validate=True`，但会多解析一次 SVG；
- `pipeline.py` 不直接 `os.replace()`，所有最终输出写入由 `writer.py` 负责。

#### 5.7.3 临时文件与原子写入

临时文件应创建在目标输出目录中：

```python
with tempfile.TemporaryDirectory(dir=output_dir) as tmpdir:
    tmp_svg = Path(tmpdir) / "intermediate.svg"
```

原因：

- 避免跨文件系统移动导致非原子操作；
- 便于 `writer.finalize_svg()` 内部使用 `os.replace()`；
- 写到无权限目录时产生明确错误；
- 失败时不污染目标目录；
- SVG 校验失败时不会覆盖用户已有目标文件。

SVG 最终输出：

```python
writer.finalize_svg(tmp_svg, final_svg_path, validate=False)
```

PDF/EPS 导出时：

- 中间 SVG 默认清理；
- `--keep-svg` 时保留到同目录；
- 保留中间 SVG 时也应通过 `writer.finalize_svg()` 或安全复制逻辑写入，而不是裸 `shutil.copyfile()`。

#### 5.7.4 输出路径推断

```python
def resolve_output_path_and_format(
    input_path: Path,
    output_path: Path | None,
    output_format: str | None,
) -> tuple[Path, str]:
    ...

SUPPORTED_OUTPUT_FORMATS = {"svg", "pdf", "eps"}
```

---

## 6. 错误处理矩阵

| 错误场景 | 异常类 | CLI 输出 |
|---|---|---|
| 输入文件不存在 | `InputFileNotFoundError` | `找不到文件: ...` |
| 输入路径不是文件 | `FileAccessError` | `输入路径不是文件: ...` |
| 文件 0 字节 | `EmptyFileError` | `文件为空: ...` |
| Pillow 无法识别图片 | `InvalidImageError` | `无法读取图片，文件可能损坏或格式不受支持: ...` |
| 真实格式不支持 | `UnsupportedFormatError` | `不支持的图片格式: ...，支持: PNG/JPEG/BMP/GIF/TIFF/WEBP` |
| 扩展名异常但真实格式支持 | 不抛 | `WARNING: 文件扩展名异常，但真实格式为 PNG，继续处理` |
| EXIF 方向修正 | 不抛 | `DEBUG: 已应用 EXIF Orientation 修正` |
| GIF/WebP/TIFF 多帧 | 不抛 | `INFO: 检测到多帧图片，已使用首帧` |
| CMYK 图像 | 不抛 | `INFO: 已转换 CMYK → RGB` |
| P/L/LA 图像 | 不抛 | `INFO: 已转换色彩模式 ...` |
| 透明通道 | 不抛 | `DEBUG: 检测到透明通道，默认保留 alpha` |
| 指定 flatten 背景 | 不抛 | `INFO: 已将透明通道合成到背景色 ...` |
| 超大图，未指定 `--max-size` | 不抛 | `WARNING: 图片尺寸很大，转换可能较慢` |
| 图片超过硬限制 | `ImageTooLargeError` | `图片过大，请缩小输入图片或使用 --max-size` |
| 配置参数非法 | `ConfigError` | `配置错误: ...` |
| preset 不存在 | `ConfigError` | `未知 preset: ...` |
| `--format` 与 `--output` 后缀冲突 | `ConfigError` | `输出格式与文件后缀冲突: ...` |
| vtracer 未安装 | `VtracerNotInstalledError` | `未安装 vtracer，请执行: pip install vtracer` |
| vtracer 内部异常 | `ConversionFailedError` | `转换失败: ...` |
| 生成 SVG 无效 | `SvgValidationError` | `生成的 SVG 未通过校验: ...` |
| SVG 最终输出失败 | `OutputPermissionError` | `无法写入输出文件: ...` |
| 输出无写权限 | `OutputPermissionError` | `无写入权限: ...` |
| 缺失导出 backend | `ExportBackendMissingError` | 给出 CairoSVG / Inkscape / rsvg-convert 安装方案 |
| 导出命令失败 | `ExportFailedError` | `导出失败: ...` |
| 用户中断 | `KeyboardInterrupt` | `用户中断`，退出码 130 |

---

## 7. 数据流

```text
用户输入 path.png
      │
      ▼
pipeline.convert()
      │
      ├─ 校验输入路径
      ├─ 推断输出路径和格式
      │
      ▼
reader.read_image()
      │  Pillow Image
      │  - 文件存在/非空校验
      │  - 文件头真实格式检测
      │  - EXIF Orientation 修正
      │  - GIF/WebP/TIFF 首帧
      │  - CMYK/P/L/LA 等色彩规范化
      │  - 默认保留 alpha
      │  - 可选 flatten 背景
      │  - 可选 thumbnail() 缩放
      │
      ▼
config = PRESETS[preset].merged(...)
      │
      ▼
converter.convert_image()
      │  Image → RGBA bytes
      │  vtracer 适配层调用
      │  写入临时 SVG
      │
      ▼
writer.validate_svg()
      │
      ├─ format=svg
      │     └─ writer.finalize_svg(tmp_svg, final_svg)
      │
      ├─ format=pdf
      │     └─ writer.export_svg(tmp_svg, final_pdf, "pdf")
      │
      └─ format=eps
            └─ writer.export_svg(tmp_svg, final_eps, "eps")
```

职责边界：

```text
reader.py     负责读图和预处理
converter.py  负责生成中间 SVG
writer.py     负责校验、最终输出、格式导出
pipeline.py   负责编排，不直接写最终输出
```

---

## 8. 测试策略

### 8.1 测试层级

| 层级 | 内容 | 框架 |
|---|---|---|
| 单元测试 | `config`、`errors`、`reader`、`writer.validate_svg`、`writer.finalize_svg` | `pytest` |
| 桩化测试 | `converter` 中 vtracer 调用适配、参数映射、异常包装 | `pytest` + `monkeypatch` |
| pipeline & CLI | 端到端流程，可桩化 converter；`subprocess` 跑 CLI | `pytest` |
| vtracer 集成 | 真实调用 vtracer，PNG/JPEG → SVG | `pytest.mark.slow` |
| 导出测试 | SVG → PDF/EPS，根据环境 skip | `pytest` |
| 回归测试，视觉 + 结构 | SVG 渲染回 PNG 算 SSIM；path 数量、文件大小、viewBox 等结构指标 | `pytest` + `scikit-image` |

### 8.2 reader 测试

fixtures：

- 纯色方块 PNG；
- 透明背景 PNG；
- JPEG 照片；
- 带 EXIF Orientation 的 JPEG；
- CMYK JPEG；
- 多帧 GIF；
- 多页 TIFF；
- 动态 WebP，生成困难可后置；
- 色彩渐变图；
- 扩展名错误但文件头正确的图片；
- 空文件、损坏图片；
- 超大图，代码生成，不入库。

测试点：

- 真实格式检测；
- 扩展名不匹配 warning；
- CMYK → RGB；
- P/L/LA 转换；
- 透明 alpha 保留；
- flatten 背景；
- max_size 缩放；
- EXIF 修正；
- 多帧首帧；
- 空文件；
- 损坏文件；
- 不支持格式。

### 8.3 converter 测试

使用 `monkeypatch` 注入假的 `vtracer` 模块。

测试点：

- vtracer 未安装抛 `VtracerNotInstalledError`；
- Pillow Image 转 RGBA；
- pixels 为 `bytes`；
- size 正确；
- 配置参数正确传入；
- 参数别名映射正确；
- vtracer 抛异常时包装为 `ConversionFailedError`；
- SVG 字符串正确写入中间文件；
- DEBUG 日志不包含像素数据；
- converter 不负责最终输出原子替换。

### 8.4 writer 测试

测试点：

#### `validate_svg()`

- 有效 SVG 通过；
- 非 XML 抛 `SvgValidationError`；
- 根节点不是 SVG 抛错；
- 缺尺寸信息抛错；
- 缺图形元素抛错；
- 嵌套 `<g><path /></g>` 通过；
- namespace 与无 namespace 均处理。

#### `finalize_svg()`

- 有效临时 SVG 能原子移动到最终路径；
- `validate=True` 时会先校验 SVG；
- 无效 SVG 不覆盖已有目标文件；
- 目标目录不存在时自动创建；
- 目标文件已存在时可被 `os.replace()` 替换；
- `PermissionError` 包装为 `OutputPermissionError`；
- `OSError` 包装为 `OutputPermissionError`；
- 移动后临时文件不存在；
- Windows/macOS/Linux 行为均需覆盖基础场景。

#### `export_svg()`

- PDF/EPS backend 缺失抛 `ExportBackendMissingError`；
- 外部命令失败抛 `ExportFailedError`；
- `backend=auto` 按优先级选择；
- `backend=cairosvg/inkscape/rsvg` 指定不可用时给出明确错误。

### 8.5 pipeline & CLI 测试

pipeline 关注：

- 默认输出路径；
- 显式输出路径；
- `--format` 推断；
- `--format` 与后缀冲突；
- preset 合并；
- 显式参数覆盖 preset；
- 临时文件清理；
- SVG 输出调用 `writer.finalize_svg()`；
- pipeline 不直接调用 `os.replace()`；
- PDF/EPS 中间 SVG 清理；
- `keep_svg=True` 保留中间 SVG；
- SVG 校验失败时不覆盖已有目标文件。

CLI 测试：

```python
subprocess.run(
    [sys.executable, "-m", "vecpic", "-i", "input.png"],
    capture_output=True,
    text=True,
)
```

测试点：

- `vecpic -h`；
- `python -m vecpic -h`；
- PNG → SVG；
- 缺失输入文件；
- 不支持格式；
- 参数非法；
- verbosity；
- `--format` 冲突；
- `--preset`；
- `--flatten-bg`；
- `--max-size`。

### 8.6 回归测试，视觉 + 结构

不作为 0.1.0 发布硬门槛，可后置。

视觉：

1. SVG → CairoSVG/Inkscape 渲染回 PNG；
2. 与原图对齐尺寸；
3. 计算 SSIM；
4. 阈值暂定 `>= 0.85`；
5. 照片更宽松；
6. flat design 更严格。

结构：

- path 数量在合理区间；
- SVG 文件大小在合理范围；
- viewBox 比例匹配原图；
- SVG 解析正常；
- 不出现空 SVG。

不使用 hash 比对 SVG：

- vtracer 不同版本输出 path 顺序、浮点精度、格式化均可能变化；
- hash 断言极脆弱。

---

## 9. CI 策略

### 9.1 快速单测

平台：

- Linux
- macOS
- Windows

Python：

- 3.10
- 3.11
- 3.12

内容：

- config；
- reader；
- writer validate；
- writer finalize；
- converter 桩化；
- pipeline 桩化；
- CLI 基础测试；
- ruff；
- mypy。

### 9.2 vtracer 集成测试

优先 Linux，Python 3.10/3.11/3.12。

测试：

- PNG → SVG；
- JPEG → SVG；
- 透明 PNG → SVG。

```python
@pytest.mark.slow
```

本地：

```bash
pytest -m slow
```

默认 CI 可跳过 slow，或仅在 Linux 跑 slow。

### 9.3 export 测试

仅 Linux，允许跳过：

```python
pytest.importorskip("cairosvg")

if shutil.which("inkscape") is None:
    pytest.skip("inkscape not installed")

if shutil.which("rsvg-convert") is None:
    pytest.skip("rsvg-convert not installed")
```

---

## 10. `pyproject.toml` 概览

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "vecpic"
version = "0.1.0"
description = "Convert raster images to SVG vector graphics using vtracer."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "vecpic maintainers" }]
keywords = ["svg", "vector", "raster", "image", "vtracer", "pillow"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: End Users/Desktop",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Multimedia :: Graphics :: Graphics Conversion",
]
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
    "pre-commit",
    "scikit-image",
]

[project.scripts]
vecpic = "vecpic.cli:main"

[tool.setuptools.packages.find]
where = ["."]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = []

[tool.mypy]
python_version = "3.10"
warn_unused_configs = true
disallow_untyped_defs = true
no_implicit_optional = true
check_untyped_defs = true

[[tool.mypy.overrides]]
module = ["vtracer.*", "cairosvg.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
markers = [
    "slow: tests that call real vtracer or external rendering backends",
]
addopts = "-ra --strict-markers"
```

说明：

- `cairosvg` 不放入主依赖；
- `mypy strict = true` 暂不启用，避免 Pillow/vtracer 类型缺失导致早期开发阻力过高；
- 后续类型标注稳定后，可逐步收紧 mypy。

---

## 11. 实现顺序

| 阶段 | 文件/内容 | 产出 |
|---|---|---|
| 1 | `pyproject.toml`、`vecpic/__init__.py`、`errors.py`、`config.py` | `pip install -e .` 通过；异常与配置体系就绪 |
| 2 | `reader.py` + 单测 | 格式检测、EXIF、透明、CMYK、GIF/TIFF 首帧、超大图处理 |
| 3 | `converter.py` + vtracer 适配层 + 桩化单测 | 与 vtracer 解耦；参数映射稳定；能生成中间 SVG |
| 4 | `writer.py` | SVG 校验；`finalize_svg()` 安全输出；PDF/EPS 导出接口；backend 缺失提示 |
| 5 | `pipeline.py` | 端到端编排；临时文件；调用 `writer.finalize_svg()`；路径推断 |
| 6 | `cli.py`、`__main__.py`、CLI 测试 | `vecpic -i x.png` 与 `python -m vecpic` 跑通 |
| 7 | CI、ruff、mypy、pre-commit | 基础质量门禁 |
| 8 | README、CHANGELOG、示例图片 | 发布前文档 |
| 9 | vtracer slow 集成测试 | 真实转换验证 |
| 10 | 视觉/结构回归 | 可后置，不阻塞 0.1.0 |
| 11 | PyPI 发布 | 0.1.0 上线 |

---

## 12. 文档交付物

PLAN 不展开 README/CONTRIBUTING 的具体内容，仅明确交付清单：

- `README.md`：覆盖安装、CLI 示例、Python API 示例、支持格式、参数说明、PDF/EPS backend 说明、常见问题；
- `CONTRIBUTING.md`：覆盖本地安装、运行测试，含 slow、ruff/mypy、CLI 调试等开发命令；
- `CHANGELOG.md`：Keep a Changelog 格式，跟踪版本变更。

---

## 13. 后续增强方向

| 方向 | 概要 | 备选实现 |
|---|---|---|
| 批量处理 | 递归目录、保留结构、跳过已存在、并行 | `concurrent.futures.ProcessPoolExecutor` |
| 预处理滤镜 | 去噪 / 锐化 / 对比度 / 灰度 / 阈值化 | `Pillow ImageFilter` / `ImageOps` |
| SVG 优化 | 减小 SVG 体积、清理冗余属性 | `scour` / `svgo`，Node |
| 进度显示 | 批量转换进度反馈 | `tqdm`，可选依赖 |
| GUI | 简单图形界面包装 CLI/API | `tkinter` / `PySide` / `PySimpleGUI` |
| 更多导出格式 | EMF / AI / PS / 多页 PDF / PNG 预览 | Inkscape backend |

原则：

- 这些能力均不应进入 0.1.0 核心依赖；
- 新功能优先以可选依赖或可选 backend 形式接入；
- SVG 优化应优先接入 `writer.py`，因为它已经集中负责 SVG 最终输出。

---

## 14. 关键风险与应对

| 风险 | 表现 | 应对 |
|---|---|---|
| vtracer Python API 变化 | 参数名 / 函数签名 / 返回值 / wheel 平台支持变化 | 适配层 + 参数映射单测；pin 最低版本；README 说明支持范围；可加版本检测 |
| CairoSVG 平台问题 | Windows/macOS 缺系统 Cairo；EPS 支持不稳；安装失败 | 仅 optional 依赖；延迟导入；Inkscape / rsvg-convert fallback；PDF/EPS 不作为核心能力 |
| 大图性能与内存 | 内存占用高、转换时间长、CI 慢 | `--max-size`；超大图 warning；hard limit；slow 测试分离；批量限制并发 |
| SVG 输出不稳定 | vtracer 不同版本 path 顺序、浮点数差异 | 不用 hash 回归；改用结构性校验 + SSIM 视觉回归，允许误差 |
| 最终文件被破坏 | 转换失败或 SVG 无效时覆盖已有输出 | 使用临时 SVG + `writer.validate_svg()` + `writer.finalize_svg()` 原子替换 |
| pipeline 职责膨胀 | pipeline 直接处理输出文件细节 | 输出相关逻辑全部集中到 `writer.py` |

---

## 15. 0.1.0 验收标准

0.1.0 发布前至少满足：

1. `pip install -e .` 成功；
2. `vecpic -h` 正常；
3. `python -m vecpic -h` 正常；
4. PNG → SVG 成功；
5. JPEG → SVG 成功；
6. 透明 PNG 默认保留 alpha；
7. `--flatten-bg "#ffffff"` 生效；
8. `--max-size` 生效；
9. `--preset bw/poster/photo` 生效；
10. vtracer 参数可通过 CLI 覆盖；
11. 错误输入有清晰错误信息；
12. SVG 结构校验生效；
13. SVG 最终输出通过 `writer.finalize_svg()` 完成；
14. SVG 校验失败时不会覆盖已有目标文件；
15. 单元测试通过；
16. converter 桩化测试通过；
17. writer finalize 测试通过；
18. Linux/macOS/Windows 基础 CI 通过；
19. README 包含安装、CLI、Python API 示例。

---

## 16. 总结

`vecpic` 的核心路线是：

```text
Pillow 读取与预处理
        ↓
vtracer 像素接口矢量化
        ↓
生成中间 SVG
        ↓
writer.py 校验并安全发布 SVG
        ↓
可选 PDF/EPS 导出
```

首版聚焦：

- 稳定转换 SVG；
- 清晰 CLI；
- 可用 Python API；
- 健壮错误处理；
- 安全输出文件；
- 良好测试覆盖；
- 平台兼容。

PDF/EPS、视觉回归、批量转换、SVG 优化等能力可逐步加入，避免 0.1.0 范围过大导致发布风险过高。

---

**本规划中唯一需要在实现阶段提前验证的强假设**：`vtracer` 像素接口的实际签名与返回值形式，详见 §5.4.5。所有对其的调用都应封装在 `_call_vtracer_convert_pixels_to_svg` 适配层中，使上层代码与 vtracer 版本差异完全解耦。

**输出职责最终约定**：

```text
converter.py:
    生成临时 SVG。

writer.py:
    validate_svg() 校验 SVG。
    finalize_svg() 将临时 SVG 安全发布为最终 SVG。
    export_svg() 将 SVG 导出为 PDF/EPS。

pipeline.py:
    只负责编排流程，不直接 os.replace() 最终输出文件。
```