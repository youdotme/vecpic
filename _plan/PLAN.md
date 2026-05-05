# PLAN.md — 光栅图转矢量图工具 (vecpic)

## 1. 项目概览

将 PNG、JPEG、BMP、GIF、TIFF、WebP 等光栅图片转换为 SVG 矢量图。核心矢量化由 **vtracer**（Rust 实现 + PyO3 Python 绑定）完成，提供 CLI 命令行工具。

## 2. 依赖

```
vtracer>=0.6       # 矢量化核心 (Rust + PyO3，pip 安装即用)
Pillow>=10.0       # 读取光栅图像格式
cairosvg>=2.7      # SVG → PNG 预览 / SVG → PDF/EPS 导出 (可选)
```

无需安装 Rust 工具链：`vtracer` 的 PyPI 轮子已包含预编译的 Rust 二进制扩展。

## 3. 项目结构

```
vecpic/
├── vecpic/
│   ├── __init__.py          # 包入口，暴露 main() 和 convert()
│   ├── __main__.py          # python -m vecpic 入口
│   ├── cli.py               # argparse CLI 定义
│   ├── reader.py            # 图片格式检测与读取 (Pillow)
│   ├── converter.py         # 核心转换逻辑 (调用 vtracer API)
│   ├── writer.py            # SVG 后处理 & 多格式导出
│   └── pipeline.py          # 端到端流水线编排
├── tests/
│   ├── conftest.py          # pytest fixtures (临时目录、样本图片)
│   ├── test_reader.py       # 各格式读取测试
│   ├── test_converter.py    # vtracer 调用与参数测试
│   ├── test_writer.py       # 格式校验测试
│   └── test_cli.py          # CLI 集成测试
├── pyproject.toml           # 项目元数据 + 构建配置
└── PLAN.md                  # 本规划文件
```

## 4. 模块设计

### 4.1 `reader.py` — 图片读取

```python
SUPPORTED_INPUTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp'}

def read_image(path: str) -> PIL.Image.Image:
    """打开并校验图片，返回 Pillow Image 对象"""

def detect_format(path: str) -> str:
    """从文件头检测真实格式（即使后缀错误也能识别）"""
```

职责：
- 用 `PIL.Image.open()` 打开文件
- 校验文件可读、非空
- 对 GIF 取首帧，对透明 PNG 做白底合成
- 对 CMYK 自动转 RGB

### 4.2 `converter.py` — 矢量化核心

```python
def convert_to_svg(
    input_path: str,
    output_path: str,
    colormode: str = "color",      # 'color' | 'bw'
    hierarchical: str = "stacked", # 'stacked' | 'cutout'
    mode: str = "spline",          # 'spline' | 'polygon' | 'pixel'
    filter_speckle: int = 4,
    color_precision: int = 6,
    layer_difference: int = 16,
    corner_threshold: int = 60,
    length_threshold: float = 4.0,
    splice_threshold: int = 45,
    path_precision: int = 8,
) -> None:
    """直接调用 vtracer.convert_image_to_svg_py()"""
```

参数来源：vtracer 的 `Config` 结构体字段（见 `cmdapp/src/main.rs`）

三项预设快捷方式：
| preset | colormode | mode | filter_speckle | 场景 |
|--------|-----------|------|----------------|------|
| `bw` | `bw` | `spline` | 0 | 文字/签名/线条图 |
| `poster` | `color` | `polygon` | 4 | 插画/flat design |
| `photo` | `color` | `spline` | 10 | 照片/复杂图像 |

### 4.3 `writer.py` — SVG 后处理 & 导出

```python
def validate_svg(path: str) -> bool:
    """校验输出是否为合法 XML/SVG 文件"""

def svg_to_pdf(svg_path: str, pdf_path: str) -> None:
    """cairosvg 转 PDF"""

def svg_to_eps(svg_path: str, eps_path: str) -> None:
    """cairosvg 转 EPS"""
```

### 4.4 `cli.py` — 命令行界面

```
usage: vecpic [-h] -i INPUT [-o OUTPUT] [--preset {bw,poster,photo}]
              [--colormode {color,bw}] [--hierarchical {stacked,cutout}]
              [--mode {spline,polygon,pixel}] [--filter-speckle N]
              [--color-precision N] [--gradient-step N]
              [--corner-threshold N] [--segment-length F]
              [--splice-threshold N] [--path-precision N]
              [--format {svg,pdf,eps}]

options:
  -i, --input PATH          输入图片路径 (必需)
  -o, --output PATH         输出文件路径 (默认: input_name.svg)
  --preset {bw,poster,photo}  预设配置
  --colormode {color,bw}    色彩模式 (默认: color)
  --mode {spline,polygon,pixel} 路径平滑模式 (默认: spline)
  --filter-speckle N        过滤小于 N px 的碎片 (默认: 4)
  ...（其余 vtracer 参数原样透传）
```

- `--output` 缺省时，输出与输入同目录、同名 `.svg`
- `--format` 缺省时，从输出文件后缀自动推断
- 输出格式：SVG（直接输出）、PDF/EPS（通过 cairosvg 转换）

### 4.5 `pipeline.py` — 流水线编排

```python
def convert(
    input_path: str,
    output_path: str | None = None,
    preset: str | None = None,
    **kwargs
) -> str:
    """
    端到端流程:
    1. 校验输入文件存在 + 格式支持
    2. 读取图片做预检查 (尺寸、色彩模式)
    3. 调用 vtracer 转换
    4. 校验输出 SVG
    5. (可选) 转为 PDF/EPS
    返回: 输出文件路径
    """
```

## 5. 错误处理矩阵

| 错误场景 | 处理方式 |
|----------|----------|
| 输入文件不存在 | `FileNotFoundError` + 可读提示 |
| 不支持的格式 | 列出支持格式并提示 |
| 文件是 0 字节 | 明确提示"文件为空" |
| CMYK 图像 | 自动转 RGB 并打印 warning |
| 透明通道 | 合成白底并打印 warning |
| vtracer 未安装 | `ImportError` → 提示 `pip install vtracer` |
| vtracer 返回错误 | 捕获异常，打印原始错误消息 |
| 超大图片 (>10000px) | 打印 warning 说明可能耗时 |
| 输出路径无写权限 | 捕获 PermissionError |

## 6. 数据流

```
用户输入 path.png
       │
       ▼
   reader.read_image()
       │  Pillow Image (RGBA→RGB, CMYK→RGB)
       ▼
   pipeline.convert()
       │  vtracer API (Rust 核心处理)
       ▼
   输出 path.svg
       │  ┌─ svg → 直接完成
       │  ├─ pdf → cairosvg.svg2pdf()
       └──┼─ eps → cairosvg.svg2eps()
```

## 7. 测试策略

| 层级 | 内容 | 框架 |
|------|------|------|
| 单元测试 | `reader.py` 格式检测、`writer.py` SVG 校验 | `pytest` |
| 集成测试 | 端到端转换 PNG→SVG，断言输出存在/非空/合法 | `pytest` + tempfile |
| CLI 测试 | `subprocess.run(["python", "-m", "vecpic", ...])` | `pytest` |
| 回归测试 | 固定测试图片 → 固定期望输出 → hash 比对 | `pytest` |

测试 fixtures 放在 `tests/fixtures/`，包含：纯色方块 PNG、透明背景 PNG、JPEG 照片、GIF 动画（首帧）、色彩渐变图。

## 8. `pyproject.toml` 概览

```toml
[project]
name = "vecpic"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["Pillow>=10.0", "vtracer>=0.6"]

[project.optional-dependencies]
export = ["cairosvg>=2.7"]
dev = ["pytest", "pytest-cov"]

[project.scripts]
vecpic = "vecpic.cli:main"

[tool.setuptools.packages.find]
where = ["."]
```

## 9. 实现顺序

| 阶段 | 文件 | 产出 |
|------|------|------|
| 1 | `pyproject.toml`, `vecpic/__init__.py` | 可安装的空包 |
| 2 | `vecpic/reader.py` + `tests/test_reader.py` | 图片读取模块 + 测试 |
| 3 | `vecpic/converter.py` + `tests/test_converter.py` | vtracer 调用封装 |
| 4 | `vecpic/writer.py` + `tests/test_writer.py` | SVG 校验与多格式导出 |
| 5 | `vecpic/cli.py` + `vecpic/__main__.py` | CLI 界面 |
| 6 | `vecpic/pipeline.py` + `tests/test_cli.py` | 端到端集成 |
| 7 | 全面测试 + `README.md` | 文档与发布 |

## 10. 后续增强方向

- **批量处理**：`vecpic input/ output/ --recursive`
- **图片预处理滤镜**：去噪 (JPEG artifacts)、锐化、对比度增强
- **SVG 大小优化**：scour/svgo 集成
- **进度条**：大图转换时 `tqdm` 显示进度
- **GUI**：基于此 CLI 的简单 `tkinter`/`PySimpleGUI` 窗口
