"""Cầu nối một chiều, an toàn giữa Math Document Converter và TrinhMath AI.

Không sao chép cả kho đề vào Converter. Với Word, chỉ các ảnh đã được TrinhMath
đánh dấu là nằm trong một câu hỏi mới được giải nén cục bộ thành hàng OCR.
Kết quả luôn được đồng bộ về trạng thái *cần duyệt*; Converter không tự đưa câu
hình vào đề của học sinh.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path

from .analyzer import analyze_file


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def default_trinhmath_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "toan-ai-local"


def _read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def bank_status(trinhmath_dir: Path | None = None) -> dict:
    root = Path(trinhmath_dir or default_trinhmath_dir())
    catalog = _read_json(root / "source_catalog.json", [])
    candidates = _read_json(root / "question_candidates.json", [])
    indexed_images = sum(len(item.get("source_image_names", [])) for item in candidates)
    unique_images = sum(len(images) for images in _question_image_names(candidates).values())
    return {
        "root": root,
        "available": root.is_dir() and (root / "sources").is_dir(),
        "sources": len(catalog),
        "candidates": len(candidates),
        "indexed_images": indexed_images,
        "unique_images": unique_images,
    }


def _question_image_names(candidates: list[dict]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for candidate in candidates:
        source_file = candidate.get("source_file")
        if not source_file:
            continue
        for image_name in candidate.get("source_image_names", []):
            if Path(image_name).suffix.lower() in IMAGE_SUFFIXES:
                result.setdefault(source_file, set()).add(image_name)
    return result


def _manifest_path(data_dir: Path) -> Path:
    return Path(data_dir) / "trinhmath_bridge_manifest.json"


def stage_trinhmath_bank_batch(store, data_dir: Path, limit: int = 50, trinhmath_dir: Path | None = None) -> dict:
    """Stage a resumable, small batch of Word question images into the OCR queue.

    The manifest is the checkpoint.  This keeps a browser refresh or a stopped
    Streamlit request from making a large import start over at the beginning.
    """
    root = Path(trinhmath_dir or default_trinhmath_dir())
    sources_dir = root / "sources"
    catalog = _read_json(root / "source_catalog.json", [])
    candidates = _read_json(root / "question_candidates.json", [])
    if not sources_dir.is_dir():
        raise RuntimeError("Không tìm thấy thư mục sources của TrinhMath AI.")

    requested = _question_image_names(candidates)
    stage_dir = Path(data_dir) / "bridge-inputs"
    stage_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = _manifest_path(data_dir)
    manifest = _read_json(manifest_file, {})
    expected = sum(len(images) for images in requested.values())
    staged_now = skipped = 0

    for source in catalog:
        source_file = source.get("file_name", "")
        image_names = requested.get(source_file, set())
        original = sources_dir / source_file
        if not image_names or original.suffix.lower() != ".docx" or not original.is_file():
            continue
        source_key = hashlib.sha256(source_file.encode("utf-8")).hexdigest()[:16]
        try:
            with zipfile.ZipFile(original) as archive:
                available = set(archive.namelist())
                for image_name in sorted(image_names):
                    extension = Path(image_name).suffix.lower()
                    image_key = hashlib.sha256(image_name.encode("utf-8")).hexdigest()[:16]
                    staged = stage_dir / source_key / f"{image_key}{extension}"
                    manifest_key = str(staged.resolve())
                    if manifest_key in manifest and staged.exists():
                        continue
                    if image_name not in available:
                        skipped += 1
                        continue
                    staged.parent.mkdir(parents=True, exist_ok=True)
                    staged.write_bytes(archive.read(image_name))
                    store.register_document(staged, "IMAGE", [{"number": 1, "classification": "SCAN_PAGE", "text": ""}])
                    manifest[manifest_key] = {
                        "source_file": source_file,
                        "image_name": image_name,
                        "original_name": source.get("original_name", source_file),
                    }
                    staged_now += 1
                    if staged_now >= limit:
                        manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                        return {"staged_now": staged_now, "staged_total": len(manifest), "expected": expected, "remaining": max(expected - len(manifest), 0), "skipped": skipped}
        except (OSError, zipfile.BadZipFile, KeyError):
            skipped += len(image_names)

    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"staged_now": staged_now, "staged_total": len(manifest), "expected": expected, "remaining": max(expected - len(manifest), 0), "skipped": skipped}


def import_trinhmath_bank(store, data_dir: Path, trinhmath_dir: Path | None = None) -> dict:
    """Stage only question images (and scanned PDFs) from an existing TrinhMath bank."""
    root = Path(trinhmath_dir or default_trinhmath_dir())
    sources_dir = root / "sources"
    catalog = _read_json(root / "source_catalog.json", [])
    candidates = _read_json(root / "question_candidates.json", [])
    if not sources_dir.is_dir():
        raise RuntimeError("Không tìm thấy thư mục sources của TrinhMath AI.")

    requested = _question_image_names(candidates)
    stage_dir = Path(data_dir) / "bridge-inputs"
    stage_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = _manifest_path(data_dir)
    manifest = _read_json(manifest_file, {})
    staged_images = staged_pdfs = skipped = 0

    for source in catalog:
        source_file = source.get("file_name", "")
        original = sources_dir / source_file
        if not original.is_file():
            skipped += 1
            continue
        suffix = original.suffix.lower()
        if suffix == ".docx":
            image_names = requested.get(source_file, set())
            if not image_names:
                continue
            source_key = hashlib.sha256(source_file.encode("utf-8")).hexdigest()[:16]
            try:
                with zipfile.ZipFile(original) as archive:
                    available = set(archive.namelist())
                    for image_name in sorted(image_names):
                        if image_name not in available:
                            skipped += 1
                            continue
                        data = archive.read(image_name)
                        extension = Path(image_name).suffix.lower()
                        image_key = hashlib.sha256(image_name.encode("utf-8")).hexdigest()[:16]
                        staged = stage_dir / source_key / f"{image_key}{extension}"
                        staged.parent.mkdir(parents=True, exist_ok=True)
                        if not staged.exists() or staged.read_bytes() != data:
                            staged.write_bytes(data)
                        store.register_document(staged, "IMAGE", [{"number": 1, "classification": "SCAN_PAGE", "text": ""}])
                        manifest[str(staged.resolve())] = {
                            "source_file": source_file,
                            "image_name": image_name,
                            "original_name": source.get("original_name", source_file),
                        }
                        staged_images += 1
            except (OSError, zipfile.BadZipFile, KeyError):
                skipped += 1
        elif suffix == ".pdf":
            # The existing analyzer keeps pages with selectable text out of OCR.
            try:
                kind, pages = analyze_file(original)
                store.register_document(original, kind, pages)
                staged_pdfs += 1
            except Exception:
                skipped += 1

    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    store.log("INFO", f"Đã đọc Kho TrinhMath: {staged_images} ảnh câu hỏi, {staged_pdfs} PDF.")
    return {"images": staged_images, "pdfs": staged_pdfs, "skipped": skipped, "manifest": len(manifest)}


def sync_results_to_trinhmath(store, data_dir: Path, trinhmath_dir: Path | None = None) -> int:
    """Write local OCR results back as *needs review*, never automatically approved."""
    root = Path(trinhmath_dir or default_trinhmath_dir())
    manifest = _read_json(_manifest_path(data_dir), {})
    if not manifest:
        return 0
    analysis_path = root / "image_analysis.json"
    analyses = _read_json(analysis_path, {})
    changed = 0
    with store.session() as connection:
        rows = connection.execute(
            """SELECT documents.source_path, ocr_results.markdown, ocr_results.latex_json
               FROM ocr_results
               JOIN pages ON ocr_results.page_id = pages.id
               JOIN documents ON pages.document_id = documents.id
               JOIN jobs ON jobs.page_id = pages.id
               WHERE jobs.status='SUCCESS'"""
        ).fetchall()
    for row in rows:
        mapping = manifest.get(str(Path(row["source_path"]).resolve()))
        if not mapping:
            continue
        try:
            latex = json.loads(row["latex_json"])
        except json.JSONDecodeError:
            latex = []
        result = {
            "extracted_text": row["markdown"],
            "latex": "\n".join(latex),
            "math_topic": None,
            "question_type": "Ảnh/công thức đọc bằng OCR cục bộ",
            "confidence": 0.0,
            "needs_teacher_review": "OCR cục bộ đã đọc; cần AI hoặc giáo viên kiểm tra trước khi dùng tự động.",
        }
        analysis_id = f"{mapping['source_file']}::{mapping['image_name']}"
        analyses[analysis_id] = {
            "source_file": mapping["source_file"],
            "image_name": mapping["image_name"],
            "result": json.dumps(result, ensure_ascii=False),
            "analyzed_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "read_status": "Đã đọc cục bộ — cần duyệt",
            "safe_to_use": False,
            "usage_status": "Không dùng tự động — cần duyệt",
        }
        changed += 1
    if changed:
        analysis_path.write_text(json.dumps(analyses, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed
