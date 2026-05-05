"""Graphical user interface for vecpic using tkinter.

Requires Python with Tcl/Tk support and Pillow with ImageTk.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
from pathlib import Path

from PIL import Image

from .config import PRESETS, QUALITY_LEVELS, VtracerConfig
from .pipeline import SUPPORTED_OUTPUT_FORMATS


class _LogHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[str]):
        super().__init__()
        self.log_queue = log_queue
        self.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        self.log_queue.put(self.format(record))


class VecpicGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("vecpic — Raster to Vector Converter")
        self.root.geometry("820x680")
        self.root.minsize(700, 550)

        self.input_path: str | None = None
        self.preview_image: Image.Image | None = None
        self.preview_tk = None
        self.thumbnail_size = (240, 240)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self._setup_logging()

        self.thread: threading.Thread | None = None
        self._converting = False

        self.icons: dict[str, object] = {}
        self._build_ui()
        self._poll_log_queue()

    def _setup_logging(self) -> None:
        handler = _LogHandler(self.log_queue)
        logging.getLogger("vecpic").addHandler(handler)
        logging.getLogger("vecpic").setLevel(logging.INFO)

    # ---- ui construction ----

    def _build_ui(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill=tk.BOTH, expand=True)

        paned = ttk.PanedWindow(outer, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned)
        paned.add(left, weight=1)
        self._build_left_panel(left, tk, ttk)

        right = ttk.Frame(paned)
        paned.add(right, weight=2)
        self._build_right_panel(right, tk, ttk)

        bottom = ttk.Frame(outer)
        bottom.pack(fill=tk.BOTH, expand=False, pady=(5, 0))
        self._build_bottom_bar(bottom, tk, ttk)

    def _build_left_panel(self, parent, tk, ttk) -> None:
        parent.columnconfigure(0, weight=1)

        in_frame = ttk.Labelframe(parent, text="Input", padding=5)
        in_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        in_frame.columnconfigure(0, weight=1)

        row = ttk.Frame(in_frame)
        row.grid(row=0, column=0, sticky="ew")
        self.input_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.input_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(row, text="Browse\u2026", command=self._browse_input).pack(
            side=tk.RIGHT, padx=(5, 0)
        )

        info_frame = ttk.Frame(in_frame)
        info_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        self.info_format_var = tk.StringVar()
        self.info_size_var = tk.StringVar()
        self.info_mode_var = tk.StringVar()
        ttk.Label(info_frame, textvariable=self.info_format_var, font=("", 9)).pack(anchor=tk.W)
        ttk.Label(info_frame, textvariable=self.info_size_var, font=("", 9)).pack(anchor=tk.W)
        ttk.Label(info_frame, textvariable=self.info_mode_var, font=("", 9)).pack(anchor=tk.W)

        preview_frame = ttk.Labelframe(parent, text="Preview", padding=5)
        preview_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 5))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        self.preview_label = ttk.Label(preview_frame, anchor=tk.CENTER)
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        out_frame = ttk.Labelframe(parent, text="Output Format", padding=5)
        out_frame.grid(row=2, column=0, sticky="ew")
        self.format_var = tk.StringVar(value="svg")
        self.format_var.trace_add("write", self._on_format_changed)
        for i, fmt in enumerate(sorted(SUPPORTED_OUTPUT_FORMATS)):
            ttk.Radiobutton(
                out_frame, text=fmt.upper(), variable=self.format_var, value=fmt
            ).grid(row=0, column=i, padx=(0, 10))

        out_path_frame = ttk.Frame(parent)
        out_path_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        out_path_frame.columnconfigure(0, weight=1)
        self.output_var = tk.StringVar()
        ttk.Entry(out_path_frame, textvariable=self.output_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(out_path_frame, text="Save As\u2026", command=self._browse_output).grid(
            row=0, column=1, padx=(5, 0)
        )

    def _build_right_panel(self, parent, tk, ttk) -> None:
        parent.columnconfigure(0, weight=1)

        preset_frame = ttk.Labelframe(parent, text="Presets", padding=5)
        preset_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        self.preset_var = tk.StringVar(value="")
        descriptions = {
            "bw": "B&W line art, icons, text, documents",
            "poster": "Illustrations, flat design, posters",
            "photo": "Photographs, complex colour images",
        }
        col = 0
        for key in ("photo", "poster", "bw"):
            ttk.Radiobutton(
                preset_frame,
                text=f"{key} \u2014 {descriptions[key]}",
                variable=self.preset_var,
                value=key,
                command=self._on_preset_changed,
            ).grid(row=0, column=col, sticky="w", padx=(0, 12), pady=2)
            col += 1

        ttk.Radiobutton(
            preset_frame,
            text="Custom",
            variable=self.preset_var,
            value="",
            command=self._on_preset_changed,
        ).grid(row=0, column=col, sticky="w", pady=2)

        quality_frame = ttk.Labelframe(parent, text="Quality", padding=5)
        quality_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        quality_descriptions = {
            "low": "Fast, compact, max 1024 px",
            "medium": "Balanced, max 2048 px, clear edges",
            "high": "Detailed, max 3072 px, sharp edges",
            "extreme": "Maximum detail, max 4096 px, edge priority",
        }
        self.quality_var = tk.StringVar(value="low")
        qcol = 0
        for key in ("low", "medium", "high", "extreme"):
            ttk.Radiobutton(
                quality_frame,
                text=f"{key} \u2014 {quality_descriptions[key]}",
                variable=self.quality_var,
                value=key,
                command=self._on_quality_changed,
            ).grid(row=0, column=qcol, sticky="w", padx=(0, 8), pady=2)
            qcol += 1

        self._build_param_frame(parent, tk, ttk)
        self._build_extra_frame(parent, tk, ttk)
        self._build_log_frame(parent, tk, ttk)

    def _build_param_frame(self, parent, tk, ttk) -> None:
        self.param_frame = ttk.Labelframe(parent, text="Vtracer Parameters", padding=5)
        self.param_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        self.param_frame.columnconfigure(1, weight=1)
        self.param_frame.columnconfigure(3, weight=1)

        self.param_widgets: dict[str, object] = {}

        specs: list[tuple[str, str, list[str]]] = [
            ("colormode", "Colormode", ["color", "bw"]),
            ("hierarchical", "Hierarchical", ["stacked", "cutout"]),
            ("mode", "Curve Mode", ["spline", "polygon", "pixel"]),
        ]
        for row_idx, (key, label, choices) in enumerate(specs):
            ttk.Label(self.param_frame, text=label + ":").grid(
                row=row_idx, column=0, sticky="w", padx=(0, 5), pady=1
            )
            default = VtracerConfig().__dataclass_fields__[key].default
            var = tk.StringVar(value=default)
            combo = ttk.Combobox(
                self.param_frame,
                textvariable=var,
                values=choices,
                state="readonly",
                width=14,
            )
            combo.grid(row=row_idx, column=1, sticky="w", pady=1)
            self.param_widgets[key] = combo

        int_fields: list[tuple[str, str]] = [
            ("filter_speckle", "Filter Speckle"),
            ("color_precision", "Color Precision"),
            ("layer_difference", "Layer Diff."),
            ("corner_threshold", "Corner Thresh. (°, edge sharpness)"),
            ("max_iterations", "Max Iterations"),
            ("splice_threshold", "Splice Thresh."),
            ("path_precision", "Path Precision"),
        ]
        for idx, (key, label) in enumerate(int_fields):
            col = (idx % 2) * 2
            row = 3 + idx // 2
            ttk.Label(self.param_frame, text=label + ":").grid(
                row=row, column=col, sticky="w", padx=(0, 5), pady=1
            )
            default = VtracerConfig().__dataclass_fields__[key].default
            var = tk.IntVar(value=default)
            spin = ttk.Spinbox(self.param_frame, from_=0, to=999, textvariable=var, width=6)
            spin.grid(row=row, column=col + 1, sticky="w", pady=1)
            self.param_widgets[key] = spin

        row = 3 + (len(int_fields) + 1) // 2
        ttk.Label(self.param_frame, text="Length Thresh.:").grid(
            row=row, column=0, sticky="w", padx=(0, 5), pady=1
        )
        self.len_thresh_var = tk.DoubleVar(value=4.0)
        ttk.Spinbox(
            self.param_frame,
            from_=0.0,
            to=100.0,
            increment=0.5,
            textvariable=self.len_thresh_var,
            width=6,
        ).grid(row=row, column=1, sticky="w", pady=1)

    def _build_extra_frame(self, parent, tk, ttk) -> None:
        extra = ttk.Labelframe(parent, text="Extra Options", padding=5)
        extra.grid(row=3, column=0, sticky="ew", pady=(0, 5))
        extra.columnconfigure(1, weight=1)

        ttk.Label(extra, text="Max Size (px):").grid(row=0, column=0, sticky="w")
        self.max_size_var = tk.StringVar(value="")
        ttk.Entry(extra, textvariable=self.max_size_var, width=10).grid(
            row=0, column=1, sticky="w", padx=(5, 20)
        )

        ttk.Label(extra, text="Flatten BG:").grid(row=0, column=2, sticky="w")
        self.flatten_var = tk.StringVar(value="")
        ttk.Entry(extra, textvariable=self.flatten_var, width=12).grid(
            row=0, column=3, sticky="w", padx=(5, 0)
        )
        ttk.Label(extra, text='e.g. "#ffffff" or "white"', font=("", 8)).grid(
            row=0, column=4, sticky="w", padx=(2, 0)
        )

        self.keep_svg_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            extra,
            text="Keep intermediate SVG on PDF/EPS export",
            variable=self.keep_svg_var,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))

    def _build_log_frame(self, parent, tk, ttk) -> None:
        log_frame = ttk.Labelframe(parent, text="Log", padding=5)
        log_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 5))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)

        self.log_text = tk.Text(
            log_frame,
            height=6,
            width=50,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Courier", 9),
            relief=tk.SUNKEN,
            borderwidth=1,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def _build_bottom_bar(self, parent, tk, ttk) -> None:
        parent.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(parent, mode="indeterminate")
        self.progress.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, sticky="e")

        self.convert_btn = ttk.Button(btn_frame, text="Convert", command=self._start_conversion)
        self.convert_btn.pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(btn_frame, text="Clear Log", command=self._clear_log).pack(
            side=tk.RIGHT, padx=(5, 0)
        )

    # ---- presets ----

    def _on_format_changed(self, *_args) -> None:
        current = self.output_var.get()
        if current and self.input_path:
            p = Path(self.input_path)
            self.output_var.set(str(p.with_suffix(f".{self.format_var.get()}")))

    def _on_preset_changed(self) -> None:
        key = self.preset_var.get()
        if key in PRESETS:
            self._apply_config(PRESETS[key])
            self._on_quality_changed()

    def _on_quality_changed(self) -> None:
        qkey = self.quality_var.get()
        if qkey in QUALITY_LEVELS:
            self._apply_quality(QUALITY_LEVELS[qkey])

    def _apply_quality(self, overrides: dict[str, object]) -> None:
        from tkinter import ttk as _ttk

        for name, value in overrides.items():
            if name == "max_size":
                self.max_size_var.set(str(value))
                continue
            if name not in self.param_widgets:
                continue
            widget = self.param_widgets[name]
            if isinstance(widget, _ttk.Combobox):
                widget.set(str(value))
            elif isinstance(widget, _ttk.Spinbox):
                widget.set(str(value))
        if "length_threshold" in overrides:
            self.len_thresh_var.set(overrides["length_threshold"])

    def _apply_config(self, config: VtracerConfig) -> None:
        from tkinter import ttk as _ttk

        d = config.to_dict()
        for name, widget in self.param_widgets.items():
            value = d.get(name)
            if value is None:
                continue
            if isinstance(widget, _ttk.Combobox):
                widget.set(str(value))
            elif isinstance(widget, _ttk.Spinbox):
                widget.set(str(value))
        self.len_thresh_var.set(d["length_threshold"])

    # ---- file dialogs ----

    def _browse_input(self) -> None:
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Select Input Image",
            filetypes=[
                (
                    "All supported",
                    "*.png *.jpg *.jpeg *.jpe *.jfif *.bmp *.gif *.tif *.tiff *.webp",
                ),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg *.jpe *.jfif"),
                ("BMP", "*.bmp"),
                ("GIF", "*.gif"),
                ("TIFF", "*.tif *.tiff"),
                ("WebP", "*.webp"),
                ("All files", "*"),
            ],
        )
        if path:
            self._set_input(Path(path))

    def _browse_output(self) -> None:
        from tkinter import filedialog

        fmt = self.format_var.get()
        path = filedialog.asksaveasfilename(
            title="Save Output",
            defaultextension=f".{fmt}",
            filetypes=[
                (f"{fmt.upper()} files", f"*.{fmt}"),
                ("All files", "*"),
            ],
        )
        if path:
            self.output_var.set(path)

    def _set_input(self, path: Path) -> None:
        self.input_path = str(path)
        self.input_var.set(str(path))
        try:
            img = Image.open(path)
            self.info_format_var.set(f"Format: {img.format}")
            self.info_size_var.set(f"Size: {img.width} x {img.height} px")
            self.info_mode_var.set(f"Mode: {img.mode}")
            self._show_preview(img)
            self.output_var.set(str(path.with_suffix(f".{self.format_var.get()}")))
        except Exception as exc:
            self.info_format_var.set(f"Error: {exc}")
            self.info_size_var.set("")
            self.info_mode_var.set("")

    def _show_preview(self, img: Image.Image) -> None:
        from PIL import Image as PILImage

        tw, th = self.thumbnail_size
        img_copy = img.copy()
        img_copy.thumbnail((tw, th), PILImage.LANCZOS)
        if img_copy.mode == "RGBA":
            bg = PILImage.new("RGBA", img_copy.size, (240, 240, 240, 255))
            img_copy = PILImage.alpha_composite(bg, img_copy)
        elif img_copy.mode not in ("RGB",):
            img_copy = img_copy.convert("RGB")

        from PIL import ImageTk

        self.preview_tk = ImageTk.PhotoImage(img_copy)
        self.preview_label.configure(image=self.preview_tk, text="")

    # ---- logging ----

    def _poll_log_queue(self) -> None:
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(msg)
        self.root.after(100, self._poll_log_queue)

    def _append_log(self, msg: str) -> None:
        self.log_text.configure(state=self.tk.NORMAL)
        self.log_text.insert(self.tk.END, msg + "\n")
        self.log_text.see(self.tk.END)
        self.log_text.configure(state=self.tk.DISABLED)

    def _clear_log(self) -> None:
        self.log_text.configure(state=self.tk.NORMAL)
        self.log_text.delete("1.0", self.tk.END)
        self.log_text.configure(state=self.tk.DISABLED)

    # ---- conversion ----

    def _gather_config(self) -> VtracerConfig:
        from tkinter import ttk as _ttk

        preset = self.preset_var.get()
        if preset in PRESETS:
            config = PRESETS[preset]
        else:
            config = VtracerConfig()

        overrides: dict[str, object] = {}
        for name, widget in self.param_widgets.items():
            if isinstance(widget, _ttk.Combobox):
                overrides[name] = widget.get()
            elif isinstance(widget, _ttk.Spinbox):
                try:
                    overrides[name] = int(widget.get())
                except ValueError:
                    pass
        overrides["length_threshold"] = self.len_thresh_var.get()
        return config.merged(**overrides)

    def _start_conversion(self) -> None:
        from tkinter import messagebox

        if not self.input_path:
            messagebox.showwarning("No Input", "Please select an input image first.")
            return

        output = self.output_var.get().strip()
        if not output:
            messagebox.showwarning("No Output", "Please specify an output path.")
            return

        if self._converting:
            return

        self._converting = True
        self.convert_btn.configure(state=self.tk.DISABLED, text="Converting\u2026")
        self.progress.start(10)
        self._clear_log()
        logging.getLogger("vecpic").info("Starting conversion\u2026")

        config = self._gather_config()
        output_format = self.format_var.get()
        max_size_str = self.max_size_var.get().strip()
        max_size = int(max_size_str) if max_size_str else None
        flatten_bg = self.flatten_var.get().strip() or None

        self.thread = threading.Thread(
            target=self._run_conversion,
            args=(config, output, output_format, max_size, flatten_bg),
            daemon=True,
        )
        self.thread.start()

    def _run_conversion(
        self,
        config: VtracerConfig,
        output: str,
        output_format: str,
        max_size: int | None,
        flatten_bg: str | None,
    ) -> None:
        from .pipeline import convert

        log = logging.getLogger("vecpic")
        d = config.to_dict()
        log.info(
            "Config: preset=%s, quality=%s, colormode=%s, mode=%s, filter_speckle=%s, path_precision=%s",
            self.preset_var.get() or "custom",
            self.quality_var.get(),
            d["colormode"],
            d["mode"],
            d["filter_speckle"],
            d["path_precision"],
        )
        try:
            result = convert(
                input_path=self.input_path,
                output_path=output,
                output_format=output_format,
                max_size=max_size,
                flatten_bg=flatten_bg,
                keep_svg=self.keep_svg_var.get(),
                colormode=config.colormode,
                hierarchical=config.hierarchical,
                mode=config.mode,
                filter_speckle=config.filter_speckle,
                color_precision=config.color_precision,
                layer_difference=config.layer_difference,
                corner_threshold=config.corner_threshold,
                length_threshold=config.length_threshold,
                max_iterations=config.max_iterations,
                splice_threshold=config.splice_threshold,
                path_precision=config.path_precision,
            )
            log.info("Conversion successful \u2192 %s", result)
        except Exception as exc:
            log.error("Conversion failed: %s", exc)
        finally:
            self.root.after(0, self._conversion_done)

    def _conversion_done(self) -> None:
        self._converting = False
        self.progress.stop()
        self.convert_btn.configure(state=self.tk.NORMAL, text="Convert")


def main() -> None:
    """Entry point for vecpic GUI.

    Raises SystemExit with a helpful message if tkinter is not available.
    """
    try:
        import tkinter as tk
    except ImportError:
        sys.exit(
            "tkinter is not available on this Python installation.\n\n"
            "Install Python with Tcl/Tk support:\n"
            "  brew install python-tk@3.14   (macOS)\n"
            "  apt install python3-tk         (Linux)\n"
            "  Reinstall Python from python.org (Windows)"
        )

    from tkinter import ttk

    root = tk.Tk()
    style = ttk.Style()
    available = style.theme_names()
    preferred = [t for t in ("aqua", "clam", "alt", "default") if t in available]
    if preferred:
        style.theme_use(preferred[0])
    VecpicGUI(root)
    root.mainloop()
