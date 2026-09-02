from __future__ import annotations

import tempfile
from pathlib import Path

from .ocr import Pix2TextProvider, cache_key


def render_pdf_page(source_path: Path, page_number: int, temporary_dir: Path) -> Path:
    try:
        import fitz
    except ImportError as error:
        raise RuntimeError("Thiếu PyMuPDF để render trang PDF scan.") from error
    document = fitz.open(source_path)
    page = document.load_page(page_number - 1)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    output = temporary_dir / f"page_{page_number}.png"
    pixmap.save(str(output))
    document.close()
    return output


def process_one(store, mode: str = "AUTO", provider: Pix2TextProvider | None = None) -> dict:
    job = store.next_waiting_job()
    if not job:
        return {"state": "idle", "message": "Không còn trang nào đang chờ OCR."}
    key = cache_key(job["input_hash"], mode)
    cached = store.cached_result(key)
    if cached:
        store.set_job(job["id"], "SUCCESS", "Dùng kết quả cache, không OCR lại")
        return {"state": "cached", "message": "Đã dùng cache.", "job_id": job["id"]}
    store.set_job(job["id"], "PROCESSING", "Đang OCR một trang", increment_attempt=True)
    source = Path(job["source_path"])
    owned_provider = provider is None
    active_provider = provider or Pix2TextProvider(mode)
    try:
        with tempfile.TemporaryDirectory(prefix="math_converter_") as temporary:
            image_path = source if job["kind"] == "IMAGE" else render_pdf_page(source, int(job["page_number"]), Path(temporary))
            try:
                result = active_provider.recognize_image(image_path)
            except RuntimeError as error:
                if "out of memory" not in str(error).lower() or mode.upper() == "CPU":
                    raise
                active_provider.release()
                active_provider = Pix2TextProvider("CPU")
                result = active_provider.recognize_image(image_path)
                result["fallback"] = "GPU thiếu bộ nhớ, đã chạy lại bằng CPU"
            finally:
                if owned_provider:
                    active_provider.release()
        store.save_result(int(job["page_id"]), key, result["markdown"], result["latex"], result)
        message = result.get("fallback") or f"OCR xong bằng {result['device']}"
        store.set_job(job["id"], "SUCCESS", message)
        store.log("INFO", f"{source.name} · trang {job['page_number']} · {message}")
        return {"state": "success", "message": message, "job_id": job["id"]}
    except Exception as error:
        store.set_job(job["id"], "FAILED", str(error)[:500])
        store.log("ERROR", f"{source.name} · trang {job['page_number']} · {error}")
        return {"state": "failed", "message": str(error), "job_id": job["id"]}
