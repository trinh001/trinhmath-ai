"""OCR cục bộ cho ảnh trong Word.

Chạy bởi TrinhMath AI sau khi Pix2Text đã được cài trên máy có năng lực phù hợp.
Không gọi Gemini hay bất kỳ API nào; mỗi kết quả bị giữ ở trạng thái cần duyệt.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from PIL import Image

from source_analyzer import build_candidates, map_docx_question_images


APP_DIR = Path(__file__).parent
SOURCES_DIR = APP_DIR / "sources"
SOURCES_FILE = APP_DIR / "source_catalog.json"
CANDIDATES_FILE = APP_DIR / "question_candidates.json"
ANALYSES_FILE = APP_DIR / "image_analysis.json"
STATUS_FILE = APP_DIR / "local_ocr_status.json"
STOP_FILE = APP_DIR / ".local_ocr_stop"
PDF_OCR_FILE = APP_DIR / "pdf_ocr_results.json"


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(path: Path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def write_status(state, processed=0, succeeded=0, failed=0, message=""):
    write_json(STATUS_FILE, {
        "state": state,
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "message": message,
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    })


def image_names_by_source():
    """Chỉ OCR ảnh nằm trong vùng câu hỏi; không lấy ảnh trang trí của Word."""
    names = {}
    for candidate in read_json(CANDIDATES_FILE, []):
        source_file = candidate.get("source_file", "")
        for image_name in candidate.get("source_image_names", []):
            names.setdefault(source_file, set()).add(image_name)
    if names:
        return names
    for source in read_json(SOURCES_FILE, []):
        source_file = source.get("file_name", "")
        path = SOURCES_DIR / source_file
        if path.suffix.lower() == ".docx" and path.exists():
            names[source_file] = {
                image_name
                for image_list in map_docx_question_images(path).values()
                for image_name in image_list
            }
    return names


def iter_unread_images(analyses):
    for source_file, image_names in image_names_by_source().items():
        path = SOURCES_DIR / source_file
        if not path.exists() or path.suffix.lower() != ".docx":
            continue
        try:
            with zipfile.ZipFile(path) as document:
                for image_name in sorted(image_names):
                    analysis_id = f"{source_file}::{image_name}"
                    if analysis_id in analyses:
                        continue
                    suffix = Path(image_name).suffix.lower()
                    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                        continue
                    try:
                        yield source_file, image_name, suffix, document.read(image_name)
                    except KeyError:
                        continue
        except zipfile.BadZipFile:
            continue


def as_text(result):
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, list):
        return "\n".join(str(item.get("text", "")) if isinstance(item, dict) else str(item) for item in result).strip()
    return str(result).strip()


def read_markdown_folder(folder: Path):
    """Pix2Text xuất Markdown theo trang/tài liệu; giữ lại đúng văn bản đã OCR."""
    parts = []
    for markdown_file in sorted(folder.rglob("*.md")):
        try:
            text = markdown_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def ocr_pending_pdfs(p2t, processed, succeeded, failed):
    """OCR từng PDF scan; lỗi một tệp không làm dừng kho còn lại."""
    pdf_results = read_json(PDF_OCR_FILE, {})
    sources = read_json(SOURCES_FILE, [])
    candidates = read_json(CANDIDATES_FILE, [])
    sources_changed = False
    for source in sources:
        source_file = source.get("file_name", "")
        source_path = SOURCES_DIR / source_file
        if source_path.suffix.lower() != ".pdf" or source_file in pdf_results:
            continue
        if STOP_FILE.exists():
            write_json(PDF_OCR_FILE, pdf_results)
            write_json(CANDIDATES_FILE, candidates)
            if sources_changed:
                write_json(SOURCES_FILE, sources)
            write_status("stopped", processed, succeeded, failed, "Đã dừng an toàn; PDF còn lại sẽ được tiếp tục sau.")
            return processed, succeeded, failed, True
        processed += 1
        write_status("running", processed, succeeded, failed, f"Đang OCR PDF: {source.get('original_name', source_file)}")
        try:
            with tempfile.TemporaryDirectory(prefix="trinhmath_pdf_ocr_") as output_dir:
                document = p2t.recognize_pdf(str(source_path), table_as_image=True)
                document.to_markdown(output_dir)
                text = read_markdown_folder(Path(output_dir))
            if not text:
                raise ValueError("Không lấy được Markdown từ PDF")
            pdf_results[source_file] = {
                "text": text,
                "status": "Đã OCR cục bộ — cần giáo viên/AI duyệt",
                "processed_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
            extracted = build_candidates(source, [line for line in text.splitlines() if line.strip()], requires_visual_review=True)
            for candidate in extracted:
                candidate.update({
                    "source_image_names": [],
                    "visual_flag_version": 2,
                    "ocr_origin": "PDF OCR cục bộ",
                    "visual_requirement": "PDF OCR cục bộ — cần duyệt",
                    "eligible_for_text_pipeline": False,
                })
            candidates = [item for item in candidates if item.get("source_file") != source_file] + extracted
            source["analysis_status"] = "done"
            source["status"] = f"Đã OCR cục bộ {len(extracted)} câu ứng viên — chờ duyệt"
            sources_changed = True
            succeeded += 1
        except Exception as error:
            pdf_results[source_file] = {
                "text": "",
                "status": "OCR cục bộ PDF lỗi — không tự dùng",
                "error": str(error)[:500],
                "processed_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            }
            failed += 1
        write_json(PDF_OCR_FILE, pdf_results)
        write_json(CANDIDATES_FILE, candidates)
        if sources_changed:
            write_json(SOURCES_FILE, sources)
    return processed, succeeded, failed, False


def main():
    try:
        from pix2text import Pix2Text
    except ImportError:
        write_status("failed", message="Thiếu Pix2Text. Hãy chạy CAI_DAT_OCR_CUC_BO.bat trên máy này.")
        return

    analyses = read_json(ANALYSES_FILE, {})
    processed = succeeded = failed = 0
    STOP_FILE.unlink(missing_ok=True)
    write_status("running", message="Đang khởi tạo mô hình OCR cục bộ…")
    try:
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"
        p2t = Pix2Text.from_config(device=device)
    except Exception as error:
        write_status("failed", message=f"Không tải được mô hình OCR cục bộ: {error}")
        return

    write_status("running", message=f"Đang OCR cục bộ bằng {'GPU NVIDIA' if device == 'cuda' else 'CPU'}…")

    for source_file, image_name, suffix, data in iter_unread_images(analyses):
        if STOP_FILE.exists():
            write_json(ANALYSES_FILE, analyses)
            write_status("stopped", processed, succeeded, failed, "Đã dừng an toàn; có thể tiếp tục sau.")
            return
        processed += 1
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
                temporary.write(data)
                image_path = temporary.name
            try:
                recognized = p2t.recognize(image_path, file_type="text_formula", return_text=True, mfr_batch_size=2)
            finally:
                Path(image_path).unlink(missing_ok=True)
            text = as_text(recognized)
            if not text:
                raise ValueError("OCR không đọc được nội dung ảnh")
            result = {
                "extracted_text": text,
                "latex": text if ("$" in text or "\\" in text) else "",
                "math_topic": "Chưa tự kết luận — cần duyệt",
                "question_type": "OCR cục bộ",
                "confidence": 0.65,
                "needs_teacher_review": True,
            }
            succeeded += 1
            read_status = "OCR cục bộ — cần giáo viên/AI duyệt"
        except Exception as error:
            result = {
                "extracted_text": "",
                "latex": "",
                "math_topic": None,
                "question_type": None,
                "confidence": 0.0,
                "needs_teacher_review": f"OCR cục bộ lỗi: {str(error)[:250]}",
            }
            failed += 1
            read_status = "OCR cục bộ lỗi — không tự quét lại"
        analyses[f"{source_file}::{image_name}"] = {
            "source_file": source_file,
            "image_name": image_name,
            "result": json.dumps(result, ensure_ascii=False),
            "analyzed_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "read_status": read_status,
            "safe_to_use": False,
            "usage_status": "Không dùng tự động — cần duyệt",
        }
        write_json(ANALYSES_FILE, analyses)
        write_status("running", processed, succeeded, failed, f"Đã lưu tiến độ sau ảnh {processed}.")

    write_json(ANALYSES_FILE, analyses)
    processed, succeeded, failed, stopped = ocr_pending_pdfs(p2t, processed, succeeded, failed)
    if stopped:
        return
    write_status("completed", processed, succeeded, failed, "Đã quét xong các ảnh và PDF chưa có kết quả OCR.")


if __name__ == "__main__":
    main()
