from __future__ import annotations

import os
import shutil
import subprocess
import sys
import json
import importlib
from pathlib import Path

import streamlit as st

from converter.analyzer import analyze_file, collect_supported_files
import converter.storage as storage_module
# Streamlit can hot-reload app.py while retaining an older imported Store class.
# Reload the tiny SQLite module so schema helpers added in later milestones are
# available without asking the teacher to stop every background worker.
storage_module = importlib.reload(storage_module)
ConverterStore = storage_module.ConverterStore
from converter.trinhmath_bridge import bank_status, sync_results_to_trinhmath
from converter.worker import process_one
from converter.post_ocr_service import parse_available_documents
from converter.matching_service import run_dry_match


APP_DIR = Path(__file__).parent
# Queue, staged images and OCR results can be several GB.  Prefer E: on this
# laptop; fall back to the project folder when the drive is unavailable.
PREFERRED_DATA_DIR = Path(r"E:\TrinhMath_Data\MathDocumentConverter")


def writable_data_directory(path: Path) -> bool:
    """Use the large E: workspace only when this process can really write it.

    An existing drive is not enough: Streamlit may be launched by a different
    Windows account/service which can see E: but cannot create its SQLite
    journal there.  In that case a local fallback keeps the app reachable
    instead of showing a blank connection error.
    """
    probe = path / ".trinhmath_write_probe"
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


DEFAULT_DATA_DIR = PREFERRED_DATA_DIR if writable_data_directory(PREFERRED_DATA_DIR) else APP_DIR / "data"
DATA_DIR = Path(os.environ.get("MATH_CONVERTER_DATA_DIR", DEFAULT_DATA_DIR))
INPUTS_DIR = DATA_DIR / "inputs"
STORE = ConverterStore(DATA_DIR / "converter.db")

st.set_page_config(page_title="Math Document Converter", page_icon="📄", layout="wide")
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg,#f7f9ff,#f2fbfa); color:#17223b; }
.block-container { max-width:1280px; padding-top:2rem; }
.converter-header { padding:20px 22px; border-radius:18px; color:white; background:linear-gradient(110deg,#3048ad,#0b9b93); margin-bottom:18px; }
.converter-header h1 { color:white; margin:0; font-size:2rem; }
.converter-header p { margin:8px 0 0; opacity:.9; }
div[data-testid="stMetric"] { background:rgba(255,255,255,.85); border:1px solid #dfe7f5; border-radius:14px; padding:12px; }
div[data-testid="stDataFrame"] { background:white; border:1px solid #dfe7f5; border-radius:12px; }
</style>
""", unsafe_allow_html=True)


def save_uploads(uploaded_files) -> list[Path]:
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for uploaded in uploaded_files or []:
        target = INPUTS_DIR / uploaded.name
        target.write_bytes(uploaded.getvalue())
        paths.append(target)
    return paths


def register_paths(paths: list[Path]):
    added, errors = 0, []
    for path in paths:
        try:
            kind, pages = analyze_file(path)
            STORE.register_document(path, kind, pages)
            STORE.log("INFO", f"Đã phân tích {path.name}: {len(pages)} trang")
            added += 1
        except Exception as error:
            errors.append(f"{path.name}: {error}")
            STORE.log("ERROR", f"Không phân tích được {path.name}: {error}")
    return added, errors


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "Sẽ xuất hiện sau vài ảnh quét xong"
    if seconds < 60:
        return f"khoảng {seconds} giây"
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours:
        return f"khoảng {hours} giờ {minutes} phút"
    return f"khoảng {minutes} phút"


def get_progress_stats(store, summary: dict) -> dict:
    """Support a hot-reloaded Streamlit session that still holds an older Store class."""
    method = getattr(store, "progress_stats", None)
    if callable(method):
        return method()
    # Safe fallback: status counts are still available in every database version.
    total = sum(summary.values())
    success = summary.get("SUCCESS", 0)
    failed = summary.get("FAILED", 0) + summary.get("WARNING", 0)
    skipped = summary.get("SKIPPED", 0)
    completed = success + failed + skipped
    waiting = summary.get("WAITING", 0) + summary.get("RETRY", 0) + summary.get("PROCESSING", 0)
    return {"total": total, "completed": completed, "success": success, "failed": failed, "skipped": skipped, "waiting": waiting, "ratio": completed / total if total else 0.0, "eta_seconds": None}


def get_parser_summary(store) -> dict:
    method = getattr(store, "parsed_summary", None)
    if callable(method):
        return method()
    # Compatibility fallback for a live Streamlit session that still owns an
    # older ConverterStore instance.
    with store.session() as connection:
        questions = connection.execute("SELECT COUNT(*) AS amount FROM parsed_questions").fetchone()["amount"]
        confident = connection.execute("SELECT COUNT(*) AS amount FROM parsed_questions WHERE confidence >= .7").fetchone()["amount"]
        unassigned = connection.execute("SELECT COUNT(*) AS amount FROM parser_unassigned_blocks").fetchone()["amount"]
    return {"questions": int(questions or 0), "confident": int(confident or 0), "unassigned": int(unassigned or 0)}


def get_parsed_rows(store, limit: int = 100):
    method = getattr(store, "parsed_questions", None)
    if callable(method):
        return method(limit)
    with store.session() as connection:
        return connection.execute(
            """SELECT parsed_questions.*, documents.source_path
               FROM parsed_questions JOIN documents ON documents.id=parsed_questions.document_id
               ORDER BY parsed_questions.updated_at DESC, parsed_questions.id DESC LIMIT ?""", (limit,)
        ).fetchall()


def get_match_rows(store, limit: int = 100, status: str | None = None):
    method = getattr(store, "match_reviews", None)
    if callable(method):
        return method(limit, status)
    with store.session() as connection:
        values = []
        where = ""
        if status and status != "Tất cả":
            where = "WHERE match_reviews.status=?"
            values.append(status)
        values.append(limit)
        return connection.execute(
            f"""SELECT match_reviews.*, parsed_questions.question_number, parsed_questions.question_type,
                       parsed_questions.question_text, parsed_questions.raw_ocr_text,
                       documents.source_path, parsed_questions.first_page_number
                FROM match_reviews JOIN parsed_questions ON parsed_questions.id=match_reviews.parser_draft_id
                JOIN documents ON documents.id=parsed_questions.document_id
                {where} ORDER BY match_reviews.updated_at DESC LIMIT ?""",
            values,
        ).fetchall()


def load_trinhmath_candidates() -> dict[str, dict]:
    path = APP_DIR.parent / "toan-ai-local" / "question_candidates.json"
    try:
        return {item.get("candidate_id"): item for item in json.loads(path.read_text(encoding="utf-8")) if item.get("candidate_id")}
    except (OSError, json.JSONDecodeError):
        return {}


def auto_ocr_status() -> dict:
    path = DATA_DIR / "auto_ocr_status.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"state": "idle"}


def bridge_import_status() -> dict:
    path = DATA_DIR / "bridge_import_status.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"state": "idle"}


def start_auto_ocr(mode: str) -> None:
    status_path = DATA_DIR / "auto_ocr_status.json"
    stop_path = DATA_DIR / "auto_ocr_stop.flag"
    stop_path.unlink(missing_ok=True)
    status_path.write_text(json.dumps({"state": "starting", "message": "Đang khởi động quét tự động…"}, ensure_ascii=False), encoding="utf-8")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [sys.executable, str(APP_DIR / "ocr_background_worker.py"), "--data-dir", str(DATA_DIR), "--mode", mode],
        cwd=APP_DIR,
        creationflags=flags,
    )


def start_bridge_import() -> None:
    status_path = DATA_DIR / "bridge_import_status.json"
    (DATA_DIR / "bridge_import_stop.flag").unlink(missing_ok=True)
    status_path.write_text(json.dumps({"state": "starting", "message": "Đang khởi động nhập Kho đề…"}, ensure_ascii=False), encoding="utf-8")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [sys.executable, str(APP_DIR / "bridge_background_importer.py"), "--data-dir", str(DATA_DIR)],
        cwd=APP_DIR,
        creationflags=flags,
    )


@st.fragment(run_every="10s")
def render_live_progress() -> None:
    """Refresh only the lightweight status area while OCR runs in the background."""
    summary = STORE.summary()
    progress_stats = get_progress_stats(STORE, summary)
    auto_status = auto_ocr_status()
    bridge_status = bridge_import_status()
    metrics = st.columns(5)
    for column, label, key in zip(metrics, ["Tổng trang", "Chờ OCR", "Đang chạy", "Thành công", "Lỗi"], ["TOTAL", "WAITING", "PROCESSING", "SUCCESS", "FAILED"]):
        column.metric(label, summary.get(key, 0))
    if not progress_stats["total"]:
        st.info("Chưa có dữ liệu trong hàng OCR. Khi bạn đọc Kho đề hoặc thêm tài liệu, tiến độ sẽ hiện tại đây.")
        return
    if bridge_status.get("state") in {"starting", "running"}:
        expected = int(bridge_status.get("expected", 0) or 0)
        staged = int(bridge_status.get("staged_total", 0) or 0)
        bridge_ratio = staged / expected if expected else 0.0
        st.progress(bridge_ratio, text=f"Đưa ảnh từ Kho đề vào hàng OCR: {staged:,}/{expected:,}".replace(",", "."))
        st.caption(f"Kho đề đang được nhập nền · {bridge_status.get('message', '')}")
    if auto_status.get("state") in {"starting", "running"}:
        ocr_total = progress_stats["success"] + progress_stats["waiting"] + progress_stats["failed"]
        ocr_ratio = progress_stats["success"] / ocr_total if ocr_total else 0.0
        st.progress(ocr_ratio, text=f"OCR tự động: đã đọc {progress_stats['success']}/{ocr_total} ảnh hiện có")
        st.caption(f"Tự cập nhật mỗi 10 giây · worker đang chạy · cập nhật gần nhất: {auto_status.get('updated_at', 'đang khởi động')}")
    else:
        st.info(f"Đang chuẩn bị hàng đợi: đã đưa {progress_stats['total']} mục vào Converter. Con số này còn tăng khi Kho đề vẫn đang được lấy; đây chưa phải phần trăm OCR.")
    status_line = f"Đọc được {progress_stats['success']} · Lỗi/cần thử lại {progress_stats['failed']} · Trích trực tiếp {progress_stats['skipped']} · Còn chờ {progress_stats['waiting']}"
    if progress_stats["waiting"]:
        status_line += f" · Ước tính còn {format_duration(progress_stats['eta_seconds'])}"
    st.caption(status_line)


def main():
    st.markdown("""<div class='converter-header'><h1>Math Document Converter</h1><p>Chuyển tài liệu Toán thành Markdown, LaTeX và JSON cục bộ. Direct extraction trước, OCR sau.</p></div>""", unsafe_allow_html=True)
    st.caption("Milestone 1 · Không gửi tài liệu ra Internet · GPU 4GB mặc định chỉ xử lý một trang mỗi lượt.")

    summary = STORE.summary()
    render_live_progress()

    input_tab, queue_tab, review_tab, parser_tab, matching_tab, log_tab = st.tabs(["Thêm tài liệu", "Hàng đợi OCR", "Kiểm tra kết quả", "Parser câu hỏi", "Ghép & duyệt", "Nhật ký"])
    with input_tab:
        st.subheader("Đưa tài liệu vào Converter")
        bank = bank_status()
        st.markdown("#### Kho đề TrinhMath AI")
        if bank["available"]:
            st.success(f"Đã thấy {bank['sources']} tài liệu, {bank['candidates']} câu đã tách và {bank['unique_images']} ảnh riêng biệt cần OCR.")
            st.caption(f"{bank['indexed_images']:,} lượt ảnh được tham chiếu trong câu hỏi đã được gộp ảnh trùng, nên không quét lặp lại.".replace(",", "."))
            st.caption("Nút này không tải lại file. Converter chỉ giải nén cục bộ các ảnh nằm trong câu hỏi và đưa chúng vào hàng OCR, theo tiến trình nền có thể tiếp tục sau khi đóng tab.")
            bridge = bridge_import_status()
            if bridge.get("state") in {"starting", "running"}:
                st.info(f"Đang nhập Kho đề nền: {bridge.get('staged_total', 0):,}/{bridge.get('expected', 0):,} ảnh · {bridge.get('message', '')}".replace(",", "."))
            elif bridge.get("state") == "completed":
                st.success(f"Đã nhập xong {bridge.get('staged_total', 0):,}/{bridge.get('expected', 0):,} ảnh riêng biệt vào hàng OCR.".replace(",", "."))
            else:
                if st.button("Bắt đầu / tiếp tục đọc Kho đề", type="primary"):
                    start_bridge_import()
                    st.rerun()
        else:
            st.info("Chưa tìm thấy Kho đề TrinhMath AI cạnh Converter; bạn vẫn có thể chọn file/thư mục bên dưới.")
        st.divider()
        st.caption("Chỉ dùng phần dưới đây cho tài liệu chưa từng nhập vào TrinhMath AI.")
        st.info("PDF có chữ được trích trực tiếp và đánh dấu SKIPPED; ảnh/PDF scan mới vào hàng OCR. Tệp đã có cùng nội dung sẽ không bị OCR lại.")
        uploads = st.file_uploader("Chọn một hoặc nhiều PDF/ảnh/Word", type=["pdf", "docx", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
        folder = st.text_input("Hoặc nhập đường dẫn thư mục trên máy", placeholder=r"Ví dụ: D:\TaiLieuToan\PDF")
        if st.button("Phân tích và đưa vào hàng đợi", type="primary"):
            paths = save_uploads(uploads)
            if folder.strip():
                folder_path = Path(folder.strip())
                if folder_path.is_dir():
                    paths.extend(collect_supported_files(folder_path))
                else:
                    st.error("Không tìm thấy thư mục này trên máy.")
            if not paths:
                st.warning("Hãy chọn tệp hoặc nhập thư mục hợp lệ.")
            else:
                with st.spinner("Đang kiểm tra từng tệp và chỉ đưa trang scan vào OCR..."):
                    added, errors = register_paths(paths)
                st.success(f"Đã phân tích {added} tệp.")
                if errors:
                    st.warning("\n".join(errors[:10]))

    with queue_tab:
        st.subheader("Hàng đợi an toàn cho GTX 1650 4GB")
        mode = st.radio("Chế độ xử lý", ["AUTO", "GPU", "CPU"], horizontal=True, help="AUTO ưu tiên CUDA nếu có; khi Pix2Text báo thiếu bộ nhớ, một trang sẽ được thử lại bằng CPU.")
        jobs_to_run = st.slider("Số trang xử lý trong lượt này", 1, 10, 1, help="GPU 4GB nên để 1 khi thử lần đầu.")
        left, right = st.columns(2)
        with left:
            run = st.button("Chạy lượt OCR", type="primary", disabled=summary.get("WAITING", 0) + summary.get("RETRY", 0) == 0)
        with right:
            retry = st.button("Đưa trang lỗi về hàng chờ")
        if retry:
            amount = STORE.retry_failed()
            st.success(f"Đã đưa {amount} trang lỗi/cảnh báo về hàng chờ.")
        st.divider()
        auto = auto_ocr_status()
        st.subheader("Quét tự động liên tục")
        st.caption("Nạp mô hình một lần, rồi tự quét từng ảnh trong hàng chờ. Có thể đóng tab trình duyệt; tiến độ vẫn được lưu trên máy.")
        if auto.get("state") in {"starting", "running"}:
            st.info(f"Đang quét tự động · đã xử lý {auto.get('processed', 0)} ảnh trong lượt này · {auto.get('message', 'Đang chạy…')}")
            if st.button("Dừng quét tự động an toàn"):
                (DATA_DIR / "auto_ocr_stop.flag").write_text("stop", encoding="utf-8")
                st.warning("Đã gửi yêu cầu dừng; ảnh đang xử lý sẽ hoàn tất rồi worker dừng.")
        else:
            if auto.get("state") == "completed":
                st.success(f"Lượt trước đã hoàn tất: {auto.get('succeeded', 0)} ảnh thành công, {auto.get('failed', 0)} ảnh lỗi.")
            elif auto.get("state") == "failed":
                st.error(f"Worker dừng vì lỗi: {auto.get('message', '')}")
            if st.button("Bắt đầu quét tự động", type="primary", disabled=summary.get("WAITING", 0) + summary.get("RETRY", 0) == 0):
                start_auto_ocr(mode)
                st.rerun()
        st.caption("Tiến độ ở đầu trang tự cập nhật mỗi 10 giây khi worker đang chạy.")
        if run:
            progress = st.progress(0, text="Đang chuẩn bị…")
            outcomes = []
            for index in range(int(jobs_to_run)):
                result = process_one(STORE, mode)
                outcomes.append(result["message"])
                progress.progress((index + 1) / int(jobs_to_run), text=result["message"])
                if result["state"] == "idle":
                    break
            progress.empty()
            st.success("Lượt OCR đã kết thúc. Tiến độ đã ghi vào SQLite; có thể đóng app và tiếp tục sau.")
            st.code("\n".join(outcomes), language="text")
        rows = [dict(row) for row in STORE.jobs(100)]
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có trang nào trong hàng đợi.")

    with review_tab:
        st.subheader("Kết quả và những trang cần xem lại")
        rows = [dict(row) for row in STORE.jobs(100)]
        if not rows:
            st.info("Kết quả OCR sẽ xuất hiện tại đây.")
        else:
            labels = {f"#{row['id']} · {Path(row['source_path']).name} · trang {row['page_number']} · {row['status']}": row for row in rows}
            selected = st.selectbox("Chọn một trang", list(labels))
            row = labels[selected]
            with STORE.session() as connection:
                result = connection.execute("SELECT * FROM ocr_results WHERE page_id = (SELECT page_id FROM jobs WHERE id=?)", (row["id"],)).fetchone()
            if result:
                markdown_tab, latex_tab, json_tab = st.tabs(["Rendered", "LaTeX", "JSON"])
                with markdown_tab:
                    st.markdown(result["markdown"])
                with latex_tab:
                    st.code(result["latex_json"], language="json")
                with json_tab:
                    st.code(result["result_json"], language="json")
            else:
                st.info("Trang này chưa có kết quả OCR. Nếu là TEXT_PAGE, nội dung được trích trực tiếp và không OCR lại ở Milestone 1.")
        st.divider()
        st.caption("Kết quả OCR cục bộ luôn được trả về TrinhMath với trạng thái cần duyệt; không tự đưa vào đề học sinh.")
        if st.button("Đồng bộ kết quả về Kho đề TrinhMath"):
            amount = sync_results_to_trinhmath(STORE, DATA_DIR)
            st.success(f"Đã đồng bộ {amount} ảnh OCR về Kho đề ở trạng thái cần duyệt.")

    with parser_tab:
        st.subheader("Post-OCR Question Parser")
        st.caption("Parser chỉ đọc OCR/direct text đã có và lưu bản nháp cấu trúc riêng; không thay đổi OCR gốc hay tự phát hành câu cho học sinh.")
        parser_summary = get_parser_summary(STORE)
        parse_metrics = st.columns(3)
        parse_metrics[0].metric("Câu đã parse", parser_summary["questions"])
        parse_metrics[1].metric("Độ tin cậy ≥ 0,7", parser_summary["confident"])
        parse_metrics[2].metric("Đoạn chưa gắn", parser_summary["unassigned"])
        if st.button("Chạy / chạy lại Parser cho OCR hiện có", type="primary"):
            with st.spinner("Đang tách câu và kiểm tra dữ liệu. OCR gốc không bị thay đổi…"):
                outcome = parse_available_documents(STORE)
            st.success(f"Đã phân tích {outcome['documents']} tài liệu: {outcome['questions']} câu, {outcome['unassigned']} đoạn cần xem lại.")
            st.rerun()
        parsed_rows = [dict(row) for row in get_parsed_rows(STORE, 100)]
        if parsed_rows:
            labels = {
                f"#{row['id']} · Câu {row['question_number'] or '?'} · {Path(row['source_path']).name} · tin cậy {row['confidence']:.0%}": row
                for row in parsed_rows
            }
            selected_label = st.selectbox("Xem bản nháp câu hỏi", list(labels), key="parsed_question_select")
            selected = labels[selected_label]
            left, right = st.columns(2)
            with left:
                st.markdown("**OCR gốc (giữ để đối chiếu)**")
                st.code(selected["raw_ocr_text"], language="markdown")
            with right:
                st.markdown("**Parser hiểu**")
                structured = dict(selected)
                for key in ("question_math_json", "options_json", "images_json", "flags_json", "validation_json"):
                    structured[key] = json.loads(structured[key] or ("{}" if key == "validation_json" else "[]"))
                st.json(structured)
        else:
            st.info("Chưa có bản nháp parser. Khi OCR đã có kết quả, bấm nút chạy Parser ở trên.")

    with matching_tab:
        st.subheader("Ghép Parser với câu gốc và duyệt an toàn")
        st.caption("Bước này chỉ tạo quyết định có thể truy vết trong Converter. Không câu nào được tự phát hành sang phần làm bài của học sinh.")
        match_summary = STORE.match_summary() if callable(getattr(STORE, "match_summary", None)) else {}
        metric_columns = st.columns(5)
        metric_columns[0].metric("Chờ duyệt", match_summary.get("REVIEW_REQUIRED", 0))
        metric_columns[1].metric("Đã nối hình/công thức", match_summary.get("LINKED_SUPPLEMENT", 0))
        metric_columns[2].metric("Đã xác nhận ghép", match_summary.get("APPROVED_MANUAL", 0))
        metric_columns[3].metric("Không dùng", match_summary.get("REJECTED", 0))
        metric_columns[4].metric("Tự động đủ điều kiện", match_summary.get("APPROVED", 0))

        if st.button("Chạy đối chiếu an toàn (dry run)", type="primary"):
            with st.spinner("Đang đối chiếu Parser với câu gốc; không thay đổi kho câu hỏi…"):
                _, report = run_dry_match(STORE, DATA_DIR)
            st.success("Đã cập nhật hàng duyệt. Kho câu hỏi chính chưa bị sửa.")
            st.json(report)
            st.rerun()

        status_labels = {
            "Tất cả": "Tất cả",
            "REVIEW_REQUIRED": "Cần giáo viên duyệt",
            "LINKED_SUPPLEMENT": "Đã nối hình/công thức — chưa phát hành",
            "APPROVED_MANUAL": "Đã xác nhận ghép",
            "REJECTED": "Không dùng",
            "APPROVED": "Đủ điều kiện tự động",
        }
        selected_status = st.selectbox("Lọc hàng duyệt", list(status_labels), format_func=lambda key: status_labels[key])
        match_rows = [dict(row) for row in get_match_rows(STORE, 200, selected_status)]
        if not match_rows:
            st.info("Chưa có kết quả đối chiếu. Hãy chạy dry run sau khi Parser đã tạo bản nháp.")
        else:
            labels = {
                f"#{row['parser_draft_id']} · Câu {row.get('question_number') or '?'} · {Path(row['source_path']).name} · điểm ghép {row['match_score']:.0%}": row
                for row in match_rows
            }
            selected_label = st.selectbox("Chọn một mục để đối chiếu", list(labels), key="match_review_select")
            selected = labels[selected_label]
            candidates = load_trinhmath_candidates()
            source_candidate = candidates.get(selected.get("matched_candidate_id"))
            left, center, right = st.columns(3)
            with left:
                st.markdown("**OCR gốc**")
                st.caption(f"Nguồn: {Path(selected['source_path']).name} · trang {selected.get('first_page_number') or '?'}")
                st.code(selected.get("raw_ocr_text", ""), language="markdown")
            with center:
                st.markdown("**Parser hiểu**")
                st.markdown(selected.get("question_text", "_Không có nội dung_"))
                st.caption(f"Dạng: {selected.get('question_type', 'unknown')} · Tin cậy parser: {float(selected.get('parser_confidence', 0) or 0):.0%}")
                try:
                    parser_flags = json.loads(selected.get("flags_json") or "[]")
                except json.JSONDecodeError:
                    parser_flags = ["Không đọc được cờ parser"]
                if parser_flags:
                    st.warning("Cờ parser: " + ", ".join(parser_flags))
            with right:
                st.markdown("**Câu gốc được đề xuất**")
                if source_candidate:
                    st.markdown(source_candidate.get("question_text") or "_Câu gốc chưa có phần chữ_")
                    st.caption(f"Mã: {source_candidate.get('candidate_id')} · Câu {source_candidate.get('question_number', '?')} · {source_candidate.get('source_name', '')}")
                else:
                    st.warning("Chưa có ứng viên ghép rõ ràng; app không tự tạo câu mới.")
                st.caption(f"Điểm ghép: {selected['match_score']:.1%} · Mơ hồ: {'Có' if selected.get('ambiguity') else 'Không'}")
            detail_left, detail_right = st.columns(2)
            with detail_left:
                st.markdown("**Lý do và điểm thành phần**")
                st.write(selected.get("decision_reason", ""))
                try:
                    st.json(json.loads(selected.get("score_breakdown_json") or "{}"))
                except json.JSONDecodeError:
                    st.code(selected.get("score_breakdown_json", ""))
            with detail_right:
                st.markdown("**Kiểm tra dữ liệu**")
                try:
                    st.json(json.loads(selected.get("validation_json") or "{}"))
                except json.JSONDecodeError:
                    st.code(selected.get("validation_json", ""))

            st.divider()
            st.caption("Xác nhận ở đây chỉ ghi vào nhật ký duyệt Converter. Việc đưa vào đề cho học sinh vẫn cần bước phát hành riêng ở TrinhMath AI.")
            review_reason = st.text_input("Ghi chú duyệt (không bắt buộc)", key=f"match_reason_{selected['parser_draft_id']}")
            action_left, action_mid, action_right = st.columns(3)
            if action_left.button("Giữ ở hàng cần duyệt", key=f"hold_{selected['parser_draft_id']}"):
                STORE.record_manual_match_decision(selected["parser_draft_id"], "REVIEW_REQUIRED", review_reason or "teacher_kept_for_review")
                st.rerun()
            if action_mid.button("Xác nhận bản ghép", type="primary", key=f"approve_match_{selected['parser_draft_id']}"):
                if not source_candidate:
                    st.warning("Không thể xác nhận vì chưa có câu gốc được ghép.")
                else:
                    STORE.record_manual_match_decision(selected["parser_draft_id"], "APPROVED_MANUAL", review_reason or "teacher_confirmed_match")
                    st.success("Đã ghi nhận xác nhận và nhật ký. Chưa phát hành cho học sinh.")
                    st.rerun()
            if action_right.button("Không dùng bản nháp này", key=f"reject_match_{selected['parser_draft_id']}"):
                STORE.record_manual_match_decision(selected["parser_draft_id"], "REJECTED", review_reason or "teacher_rejected_parser_draft")
                st.rerun()

    with log_tab:
        events = [dict(row) for row in STORE.recent_events()]
        st.dataframe(events, use_container_width=True, hide_index=True) if events else st.info("Chưa có nhật ký.")


if __name__ == "__main__":
    main()
