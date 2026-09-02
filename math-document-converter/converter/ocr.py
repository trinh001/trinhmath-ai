from __future__ import annotations

import gc
import hashlib
import os
import re
from pathlib import Path


def configure_local_runtime() -> None:
    """Keep model/config caches inside the converter folder, not the Windows profile."""
    app_dir = Path(__file__).resolve().parent.parent
    data_dir = Path(os.environ.get("MATH_CONVERTER_DATA_DIR", app_dir / "data"))
    runtime_dir = data_dir / "runtime"
    for name in ("appdata", "localappdata", "matplotlib", "torch", "huggingface"):
        (runtime_dir / name).mkdir(parents=True, exist_ok=True)
    # The desktop sandbox may not permit writes to AppData/Roaming.  These
    # libraries only need a small settings/cache directory, so make it local.
    os.environ["APPDATA"] = str(runtime_dir / "appdata")
    os.environ["LOCALAPPDATA"] = str(runtime_dir / "localappdata")
    os.environ["MPLCONFIGDIR"] = str(runtime_dir / "matplotlib")
    os.environ["TORCH_HOME"] = str(runtime_dir / "torch")
    os.environ["YOLO_CONFIG_DIR"] = str(runtime_dir / "appdata")
    os.environ["HF_HOME"] = str(runtime_dir / "huggingface")
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(runtime_dir / "huggingface" / "hub")


class Pix2TextProvider:
    """OCR provider cục bộ, thiết kế để thay thế được bằng provider khác sau này."""

    def __init__(self, mode: str = "AUTO"):
        self.mode = mode.upper()
        self._engine = None
        self.active_device = "cpu"

    def initialize(self):
        configure_local_runtime()
        try:
            import torch
            from pix2text import Pix2Text
        except ImportError as error:
            raise RuntimeError("Chưa cài Pix2Text/PyTorch. Hãy chạy CAI_DAT_CONVERTER.bat trước.") from error
        use_cuda = self.mode != "CPU" and torch.cuda.is_available()
        self.active_device = "cuda" if use_cuda else "cpu"
        # GTX 1650 4GB: không nhận bảng ở V1 và batch công thức mặc định là 1.
        self._engine = Pix2Text.from_config(enable_table=False, device=self.active_device)
        return self.active_device

    def recognize_image(self, image_path: Path) -> dict:
        if self._engine is None:
            self.initialize()
        page = self._engine.recognize_page(str(image_path), page_number=0, resized_shape=768, mfr_batch_size=1)
        data_dir = Path(os.environ.get("MATH_CONVERTER_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
        output_dir = data_dir / "ocr-output" / image_path.stem
        # Pix2Text 1.1 writes any detected figures/tables beside Markdown.
        # Passing markdown_fn=None keeps the database result authoritative.
        markdown = page.to_markdown(output_dir, markdown_fn=None) if hasattr(page, "to_markdown") else str(page)
        latex = re.findall(r"\${1,2}(.*?)\${1,2}", markdown, flags=re.DOTALL)
        return {"markdown": markdown, "latex": latex, "device": self.active_device}

    def release(self):
        self._engine = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass


def cache_key(input_hash: str, mode: str) -> str:
    return hashlib.sha256(f"pix2text-v1|{input_hash}|{mode}|batch=1|tables=off".encode()).hexdigest()
