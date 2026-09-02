import json
import sqlite3
import hashlib
import secrets
import unicodedata
import os
import socket
import base64
import zipfile
import ctypes
import io
import random
import shutil
import html
import re
import threading
import subprocess
import sys
import importlib.util

os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.dirname(__file__), "tmp", "matplotlib"))
from ctypes import wintypes
from PIL import Image
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from source_analyzer import analyze_sources, has_ooxml_math, map_docx_question_images
from health_checks import audit_data_links, has_data_link_errors, validate_curricula
from problem_workspace import build_problem_review, local_study_hint
from datetime import datetime, timedelta
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.platypus import Image as PdfImage
from matplotlib.mathtext import math_to_image

import streamlit as st


APP_DIR = Path(__file__).parent
BANK_FILE = APP_DIR / "question_bank.json"
DB_FILE = APP_DIR / "results.db"
SOURCES_DIR = APP_DIR / "sources"
SOURCES_FILE = APP_DIR / "source_catalog.json"
CURRICULUM_FILE = APP_DIR / "curriculum_grade12.json"
CURRICULUM_GRADE10_FILE = APP_DIR / "curriculum_grade10.json"
CURRICULUM_GRADE11_FILE = APP_DIR / "curriculum_grade11.json"
CANDIDATES_FILE = APP_DIR / "question_candidates.json"
IMAGE_ANALYSIS_FILE = APP_DIR / "image_analysis.json"
QUESTION_DRAFTS_FILE = APP_DIR / "question_drafts.json"
APPROVED_QUESTIONS_FILE = APP_DIR / "approved_questions.json"
QUIZ_VARIANTS_FILE = APP_DIR / "quiz_variants.json"
BACKUPS_DIR = APP_DIR / "backups"
PDF_FONT = Path("C:/Windows/Fonts/times.ttf")
PDF_FONT_BOLD = Path("C:/Windows/Fonts/timesbd.ttf")
GEMINI_KEY_FILE = APP_DIR / ".gemini_key.bin"
REMEMBERED_USER_FILE = APP_DIR / ".remembered_user.json"
AI_SCAN_STATUS_FILE = APP_DIR / "ai_scan_status.json"
AI_SCAN_STOP_FILE = APP_DIR / ".ai_scan_stop"
LOCAL_OCR_STATUS_FILE = APP_DIR / "local_ocr_status.json"
LOCAL_OCR_STOP_FILE = APP_DIR / ".local_ocr_stop"

LEARNING_SCOPES = [
    "Ôn theo bài học",
    "Ôn theo chuyên đề",
    "Kiểm tra giữa kỳ I",
    "Kiểm tra cuối kỳ I",
    "Kiểm tra giữa kỳ II",
    "Kiểm tra cuối kỳ II",
    "Thi thử & đề THPT Quốc gia",
]

UPLOAD_TEMPLATE_TEXT = """MẪU GẮN NHÃN TÀI LIỆU TRINHMATH AI

Tên tệp: ................................................
Khối lớp: Lớp 10 / Lớp 11 / Lớp 12
Mục đích: Ôn theo bài học / Ôn theo chuyên đề / Kiểm tra giữa kỳ I / Kiểm tra cuối kỳ I / Kiểm tra giữa kỳ II / Kiểm tra cuối kỳ II / Thi thử & đề THPT Quốc gia
Chương: ..................................................
Bài học: .................................................
Loại câu: Trắc nghiệm 4 lựa chọn / Đúng-Sai / Trả lời ngắn / Tự luận / Bộ hỗn hợp

Gợi ý: Tên tệp nên có lớp, chương hoặc dạng bài. Ví dụ:
Lop12_TichPhan_OnChuyenDe.docx
Lop11_GiuaKy1_DeMau.pdf
Lop12_ThiThuTNTHPT_2025.docx
"""

st.set_page_config(page_title="TrinhMath AI — Học Toán có lộ trình", page_icon="📐", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Be Vietnam Pro', sans-serif; }
.stApp { background: linear-gradient(135deg, #f7f9ff 0%, #f3fbfb 100%); color: #17223b; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #eef2ff 0%, #f6fffe 100%); border-right: 1px solid #dce5f5; }
[data-testid="stSidebar"] h1 { color: #263d9c; font-size: 1.35rem; }
h1, h2, h3 { color: #1f2d5f; letter-spacing: -0.02em; }
.block-container { max-width: 1450px; padding-top: 2.2rem; padding-bottom: 3rem; }
.tm-page-header { padding: 4px 0 18px; margin-bottom: 14px; border-bottom: 1px solid #dfe7f5; }
.tm-page-kicker { color: #0b8e88; font-weight: 700; font-size: .75rem; letter-spacing: .12em; }
.tm-page-title { color: #1f2d5f; font-size: 2rem; font-weight: 750; line-height: 1.18; margin: 6px 0 7px; }
.tm-page-copy { color: #5d6a85; font-size: .98rem; max-width: 760px; line-height: 1.6; }
.tm-flow-card { min-height: 92px; padding: 14px 15px; border: 1px solid #dfe7f5; border-radius: 14px; background: rgba(255,255,255,.76); }
.tm-flow-card-active { border-color: #75c8c2; background: linear-gradient(135deg,#f1fbfa,#f4f7ff); box-shadow: 0 8px 22px rgba(11,142,136,.08); }
.tm-flow-number { color: #0b8e88; font-size: .76rem; font-weight: 750; letter-spacing: .08em; }
.tm-flow-title { color: #273762; font-weight: 700; margin-top: 4px; }
.tm-flow-copy { color: #61708b; font-size: .84rem; line-height: 1.45; margin-top: 4px; }
.tm-section-label { color: #3048ad; font-size: .77rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; margin: 22px 0 7px; }
.tm-question-number { display: inline-flex; align-items: center; justify-content: center; min-width: 32px; height: 32px; padding: 0 8px; border-radius: 10px; color: white; background: linear-gradient(135deg,#3048ad,#0b9b93); font-weight: 700; margin-right: 8px; }
.tm-question-title { color: #28365f; font-weight: 700; font-size: 1rem; }
div[data-testid="stVerticalBlockBorderWrapper"] { border: 1px solid #dfe7f5; border-radius: 16px; background: rgba(255,255,255,.82); box-shadow: 0 7px 20px rgba(33,61,135,.045); }
div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 5px 7px 8px; }
div[data-testid="stMetric"] { background: rgba(255,255,255,.86); border: 1px solid #e1e8f5; border-radius: 16px; padding: 16px; box-shadow: 0 8px 24px rgba(43,68,135,.06); }
.stButton > button { border-radius: 10px; font-weight: 600; border: 1px solid #cbd7f0; }
.stButton > button[kind="primary"] { background: linear-gradient(100deg,#3048ad,#0b9b93); color: white; border: none; }
div[data-baseweb="tab-list"] { gap: 8px; }
button[data-baseweb="tab"] { border-radius: 9px 9px 0 0; font-weight: 600; }
div[data-testid="stAlert"] { border-radius: 12px; }
div[data-testid="stDataFrame"] { background: rgba(255,255,255,.82); border: 1px solid #e1e8f5; border-radius: 14px; overflow: hidden; }
div[data-testid="stExpander"] { background: rgba(255,255,255,.78); border: 1px solid #e1e8f5; border-radius: 12px; }
div[data-testid="stForm"] { background: rgba(255,255,255,.76); border: 1px solid #e1e8f5; border-radius: 16px; padding: 18px; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div { border-radius: 10px; border-color: #d5dff1; background: rgba(255,255,255,.92); }
[data-testid="stSidebar"] .stRadio label { padding: 7px 8px; border-radius: 8px; font-size: .92rem; }
[data-testid="stSidebar"] .stRadio label:hover { background: #e0e9ff; }
hr { border-color: #e1e8f5 !important; }
</style>
""", unsafe_allow_html=True)


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _make_blob(data):
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def protect_for_windows_user(value):
    """Mã hóa bằng Windows DPAPI; chỉ cùng tài khoản Windows này giải mã được."""
    if os.name != "nt":
        return None
    source, source_buffer = _make_blob(value.encode("utf-8"))
    encrypted = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptProtectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(encrypted))
    if not ok:
        return None
    try:
        return ctypes.string_at(encrypted.pbData, encrypted.cbData)
    finally:
        kernel32.LocalFree(encrypted.pbData)


def unprotect_for_windows_user(value):
    if os.name != "nt":
        return ""
    source, source_buffer = _make_blob(value)
    decrypted = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    ok = crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(decrypted))
    if not ok:
        return ""
    try:
        return ctypes.string_at(decrypted.pbData, decrypted.cbData).decode("utf-8")
    finally:
        kernel32.LocalFree(decrypted.pbData)


def load_saved_gemini_key():
    try:
        return unprotect_for_windows_user(GEMINI_KEY_FILE.read_bytes()) if GEMINI_KEY_FILE.exists() else ""
    except OSError:
        return ""


def save_gemini_key_for_this_laptop(key):
    protected = protect_for_windows_user(key)
    if not protected:
        return False
    GEMINI_KEY_FILE.write_bytes(protected)
    return True


def get_ai_scan_status():
    """Đọc trạng thái worker nền; file hỏng/tạm thời đang ghi được xem là chưa có."""
    try:
        return json.loads(AI_SCAN_STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_local_ocr_status():
    try:
        return json.loads(LOCAL_OCR_STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def local_ocr_is_installed():
    return importlib.util.find_spec("pix2text") is not None


def start_local_ocr():
    """Khởi chạy OCR ở tiến trình riêng để trang web không bị treo."""
    status = get_local_ocr_status()
    if status.get("state") == "running":
        return False, "OCR cục bộ đang chạy trên máy này."
    if not local_ocr_is_installed():
        return False, "Máy này chưa cài bộ OCR cục bộ. Hãy bấm CAI_DAT_OCR_CUC_BO.bat một lần rồi mở lại app."
    LOCAL_OCR_STOP_FILE.unlink(missing_ok=True)
    try:
        subprocess.Popen(
            [sys.executable, str(APP_DIR / "local_ocr.py")],
            cwd=str(APP_DIR),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True, "Đã bắt đầu OCR cục bộ. App lưu tiến độ sau mỗi ảnh; bạn có thể quay lại xem trạng thái."
    except OSError as error:
        return False, f"Không khởi động được OCR cục bộ: {error}"


def write_ai_scan_status(state, **updates):
    status = get_ai_scan_status()
    status.update(updates)
    status["state"] = state
    status["updated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    temporary = AI_SCAN_STATUS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(AI_SCAN_STATUS_FILE)


def start_background_ai_scan(api_key):
    """Khởi động worker trong app để khóa chỉ ở bộ nhớ của phiên hiện tại."""
    current = get_ai_scan_status()
    if current.get("state") in {"starting", "running", "waiting_quota"}:
        return False, "Quét nền đang chạy. Hãy bấm Cập nhật tiến độ thay vì mở thêm một lượt quét."
    if not api_key or len(api_key.strip()) < 20:
        return False, "Chưa có khóa Gemini hợp lệ trong phiên này. Hãy vào Góc cùng suy nghĩ AI để lưu khóa trước."
    try:
        AI_SCAN_STOP_FILE.unlink(missing_ok=True)
        write_ai_scan_status(
            "starting",
            processed=0,
            successes=0,
            failures=0,
            message="Đang khởi động quét nền…",
        )
        # Import muộn để tránh vòng lặp app <-> worker khi Streamlit nạp app.py.
        from ai_scan_worker import run_scan
        thread = threading.Thread(target=run_scan, args=(api_key.strip(),), daemon=True, name="gemini-image-scan")
        thread.start()
        return True, "Đã bắt đầu quét nền. App sẽ tự đi tiếp từng nhóm 3 ảnh."
    except (OSError, RuntimeError) as error:
        write_ai_scan_status("failed", message=f"Không khởi động được quét nền: {error}")
        return False, f"Không khởi động được quét nền: {error}"


def stop_background_ai_scan():
    AI_SCAN_STOP_FILE.write_text("stop", encoding="utf-8")


def render_live_ai_scan_status():
    """Bảng tiến độ ổn định trong Góc cùng suy nghĩ AI."""
    scan_status = get_ai_scan_status()
    scan_state = scan_status.get("state", "")
    processed = int(scan_status.get("processed", 0) or 0)
    successes = int(scan_status.get("successes", 0) or 0)
    failures = int(scan_status.get("failures", 0) or 0)
    if scan_state in {"starting", "running", "waiting_quota"}:
        st.info(
            f"Quét nền đang chạy: đã xử lý {processed} ảnh "
            f"({successes} đọc được, {failures} ảnh lỗi). {scan_status.get('message', '')}"
        )
        if scan_status.get("last_source"):
            st.caption(f"Đang xử lý: {scan_status['last_source']}")
        st.caption(f"Cập nhật lần cuối: {scan_status.get('updated_at', 'đang khởi tạo')}. Một ảnh phức tạp có thể mất đến 2 phút.")
        if st.button("Cập nhật tiến độ", key="refresh_background_scan"):
            st.rerun()
        if st.button("Dừng quét nền sau ảnh hiện tại", type="secondary", key="stop_background_scan"):
            stop_background_ai_scan()
            st.warning("Đã gửi yêu cầu dừng. Worker sẽ lưu ảnh hiện tại rồi dừng an toàn.")
    elif scan_state:
        st.info(scan_status.get("message", "Lượt quét nền trước đã kết thúc."))


def get_remembered_user():
    if not REMEMBERED_USER_FILE.exists():
        return None
    try:
        saved = json.loads(REMEMBERED_USER_FILE.read_text(encoding="utf-8"))
        with sqlite3.connect(DB_FILE) as connection:
            row = connection.execute("SELECT username, display_name, role FROM users WHERE username = ?", (saved.get("username"),)).fetchone()
        return {"username": row[0], "display_name": row[1], "role": row[2]} if row else None
    except (OSError, json.JSONDecodeError):
        return None


def remember_user_on_this_laptop(user):
    REMEMBERED_USER_FILE.write_text(json.dumps({"username": user["username"]}, ensure_ascii=False), encoding="utf-8")


def load_bank():
    with BANK_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def latex_to_pdf_image(latex):
    """Vẽ LaTeX cục bộ bằng MathText, không cần cài LaTeX hay gửi dữ liệu ra ngoài."""
    image_buffer = io.BytesIO()
    math_to_image(f"${latex}$", image_buffer, dpi=180, format="png", color="#111111")
    image_buffer.seek(0)
    with Image.open(image_buffer) as image:
        width, height = image.size
    image_buffer.seek(0)
    scale = min(1, (14 * cm) / (width * 72 / 180))
    return PdfImage(image_buffer, width=width * 72 / 180 * scale, height=height * 72 / 180 * scale)


def normalize_pdf_math(text):
    """Chuẩn hóa vài ký hiệu Toán phổ biến của ngân hàng mẫu trước khi xuất PDF."""
    text = str(text)

    def integral_to_latex(match):
        lower = match.group(1).translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789"))
        upper = match.group(2).translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-"))
        integrand = match.group(3).translate(str.maketrans({"²": "^2", "³": "^3", "⁴": "^4", "⁵": "^5", "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9"}))
        return rf"$\int_{{{lower}}}^{{{upper}}} {integrand}\,d{match.group(4)}$"

    text = re.sub(r"∫([₀₁₂₃₄₅₆₇₈₉]+)([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)\s*(.*?)\s*d([a-zA-Z])", integral_to_latex, text)
    text = text.replace("∫x dx", r"$\int x\,dx$")
    text = re.sub(r"\b([A-Z]{2})\s*=\s*\((?=[-\d])", lambda match: rf"$\overrightarrow{{{match.group(1)}}}$ = (", text)
    if "vectơ" in text.lower():
        text = re.sub(r"\b([A-Z]{2})\b", lambda match: rf"$\overrightarrow{{{match.group(1)}}}$", text)
    return text


def math_display_text(text):
    """Chuẩn hóa ký hiệu phổ biến trước khi Streamlit/KaTeX hiển thị."""
    return normalize_pdf_math(str(text))


def render_page_header(kicker, title, copy):
    """Tiêu đề đồng nhất cho các không gian học và biên soạn."""
    st.markdown(
        f"<div class='tm-page-header'><div class='tm-page-kicker'>{html.escape(kicker)}</div>"
        f"<div class='tm-page-title'>{html.escape(title)}</div>"
        f"<div class='tm-page-copy'>{html.escape(copy)}</div></div>",
        unsafe_allow_html=True,
    )


def render_workflow_steps(steps, active_index):
    """Hiển thị cùng một lộ trình ngắn trên các màn hình giáo viên."""
    columns = st.columns(len(steps))
    for index, (title, copy) in enumerate(steps):
        active_class = " tm-flow-card-active" if index == active_index else ""
        with columns[index]:
            st.markdown(
                f"<div class='tm-flow-card{active_class}'><div class='tm-flow-number'>{index + 1:02d}</div>"
                f"<div class='tm-flow-title'>{html.escape(title)}</div>"
                f"<div class='tm-flow-copy'>{html.escape(copy)}</div></div>",
                unsafe_allow_html=True,
            )


def build_exam_pdf(bank, include_answers=False):
    """Xuất đề mẫu và tùy chọn đáp án; không ghi tên trường hoặc nguồn tài liệu."""
    if PDF_FONT.exists() and PDF_FONT_BOLD.exists():
        pdfmetrics.registerFont(TTFont("ToanTimes", str(PDF_FONT)))
        pdfmetrics.registerFont(TTFont("ToanTimesBold", str(PDF_FONT_BOLD)))
        regular, bold = "ToanTimes", "ToanTimesBold"
    else:
        regular, bold = "Helvetica", "Helvetica-Bold"
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.7 * cm, leftMargin=1.7 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ToanTitle", parent=styles["Title"], fontName=bold, fontSize=16, leading=20, alignment=TA_CENTER, textColor=colors.HexColor("#243B6B"))
    heading = ParagraphStyle("ToanHeading", parent=styles["Heading2"], fontName=bold, fontSize=12, leading=16, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("ToanBody", parent=styles["BodyText"], fontName=regular, fontSize=10.5, leading=15, spaceAfter=5)
    story = [Paragraph("ĐỀ LUYỆN TOÁN THPT", title), Spacer(1, 0.25 * cm), Paragraph("Họ và tên: ....................................................    Lớp: ............", body), Spacer(1, 0.2 * cm)]

    def add(text):
        parts = re.split(r"(\$[^$]+\$)", normalize_pdf_math(text))
        if len(parts) == 3 and parts[1].startswith("$") and parts[1].endswith("$") and len(parts[0]) <= 40 and len(parts[2]) <= 30:
            try:
                formula_image = latex_to_pdf_image(parts[1][1:-1])
                inline = Table([[
                    Paragraph(html.escape(parts[0]), body),
                    formula_image,
                    Paragraph(html.escape(parts[2]), body),
                ]], colWidths=[pdfmetrics.stringWidth(parts[0], regular, 10.5) + 4, formula_image.drawWidth + 8, pdfmetrics.stringWidth(parts[2], regular, 10.5) + 4], hAlign="LEFT")
                inline.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
                story.append(inline)
                return
            except Exception:
                pass
        for part in parts:
            if not part:
                continue
            if part.startswith("$") and part.endswith("$"):
                try:
                    story.append(latex_to_pdf_image(part[1:-1]))
                except Exception:
                    story.append(Paragraph(html.escape(part), body))
            else:
                story.append(Paragraph(html.escape(part).replace("\n", "<br/>"), body))

    story.append(Paragraph("Phần I. Trắc nghiệm nhiều lựa chọn", heading))
    for index, question in enumerate(bank.get("multiple_choice", []), start=1):
        add(f"Câu {index}. {question.get('question', '')}")
        for option_index, option in enumerate(question.get("options", [])):
            add(f"{chr(65 + option_index)}. {option}")
    story.append(Paragraph("Phần II. Trắc nghiệm đúng/sai", heading))
    for index, question in enumerate(bank.get("true_false", []), start=1):
        add(f"Câu {index}. {question.get('context', question.get('question', ''))}")
        for item in question.get("items", []):
            add(f"{item.get('id', '')}. {item.get('text', '')}")
    story.append(Paragraph("Phần III. Trả lời ngắn", heading))
    for index, question in enumerate(bank.get("short_answer", []), start=1):
        add(f"Câu {index}. {question.get('question', '')}")
        story.append(Spacer(1, 0.5 * cm))

    if include_answers:
        story.append(PageBreak())
        story.append(Paragraph("ĐÁP ÁN VÀ HƯỚNG DẪN", title))
        story.append(Paragraph("Phần I", heading))
        for index, question in enumerate(bank.get("multiple_choice", []), start=1):
            add(f"Câu {index}: {question.get('answer', '')}. {question.get('solution', '')}")
        story.append(Paragraph("Phần II", heading))
        for index, question in enumerate(bank.get("true_false", []), start=1):
            answers = ", ".join(f"{item.get('id', '')}: {item.get('answer', '')}" for item in question.get("items", []))
            add(f"Câu {index}: {answers}")
        story.append(Paragraph("Phần III", heading))
        for index, question in enumerate(bank.get("short_answer", []), start=1):
            add(f"Câu {index}: {question.get('answer', '')}. {question.get('solution', '')}")

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.line(document.leftMargin, 1.25 * cm, A4[0] - document.rightMargin, 1.25 * cm)
        canvas.setFont(regular, 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(document.leftMargin, 0.85 * cm, "TrinhMath AI")
        canvas.drawRightString(A4[0] - document.rightMargin, 0.85 * cm, f"Trang {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return buffer.getvalue()


def init_database():
    SOURCES_DIR.mkdir(exist_ok=True)
    if not SOURCES_FILE.exists():
        SOURCES_FILE.write_text("[]", encoding="utf-8")
    with sqlite3.connect(DB_FILE) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                score REAL NOT NULL,
                correct_count INTEGER NOT NULL,
                total_items INTEGER NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        try:
            connection.execute("ALTER TABLE attempts ADD COLUMN grade TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            connection.execute("ALTER TABLE attempts ADD COLUMN study_goal TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            connection.execute("ALTER TABLE attempts ADD COLUMN username TEXT")
        except sqlite3.OperationalError:
            pass


def backup_data_once_per_day():
    """Sao lưu dữ liệu do giáo viên tạo trước khi app tiếp tục làm việc."""
    backup_dir = BACKUPS_DIR / datetime.now().strftime("%Y-%m-%d")
    if backup_dir.exists():
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    for path in [DB_FILE, SOURCES_FILE, CANDIDATES_FILE, IMAGE_ANALYSIS_FILE, QUESTION_DRAFTS_FILE, APPROVED_QUESTIONS_FILE, QUIZ_VARIANTS_FILE]:
        if path.exists():
            shutil.copy2(path, backup_dir / path.name)


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 310000).hex()
    return f"{salt}${digest}"


def verify_password(password, stored_hash):
    salt, expected = stored_hash.split("$", 1)
    return secrets.compare_digest(hash_password(password, salt), stored_hash)


def create_user(username, display_name, password, role):
    try:
        with sqlite3.connect(DB_FILE) as connection:
            connection.execute(
                "INSERT INTO users (username, display_name, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (username.lower().strip(), display_name.strip(), hash_password(password), role, datetime.now().strftime("%d/%m/%Y %H:%M")),
            )
        return True, "Đăng ký thành công. Bạn có thể đăng nhập ngay."
    except sqlite3.IntegrityError:
        return False, "Tên đăng nhập này đã tồn tại."


def authenticate(username, password):
    with sqlite3.connect(DB_FILE) as connection:
        row = connection.execute(
            "SELECT username, display_name, password_hash, role FROM users WHERE username = ?",
            (username.lower().strip(),),
        ).fetchone()
    if row and verify_password(password, row[2]):
        return {"username": row[0], "display_name": row[1], "role": row[3]}
    return None


def save_attempt(student_name, username, grade, study_goal, score, correct_count, total_items):
    with sqlite3.connect(DB_FILE) as connection:
        connection.execute(
            "INSERT INTO attempts (student_name, submitted_at, score, correct_count, total_items, grade, study_goal, username) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (student_name, datetime.now().strftime("%d/%m/%Y %H:%M"), score, correct_count, total_items, grade, study_goal, username),
        )


def get_attempts(username=None):
    with sqlite3.connect(DB_FILE) as connection:
        if username:
            return connection.execute(
                "SELECT student_name, grade, study_goal, submitted_at, score, correct_count, total_items FROM attempts WHERE username = ? ORDER BY id DESC",
                (username,),
            ).fetchall()
        return connection.execute("SELECT student_name, grade, study_goal, submitted_at, score, correct_count, total_items FROM attempts ORDER BY id DESC").fetchall()


def get_learning_recommendations(rows):
    """Tóm tắt phần cần ôn từ các lượt làm đã được lưu."""
    by_goal = {}
    for row in rows:
        goal, score = str(row[2] or "Toán THPT"), float(row[4] or 0)
        scores = by_goal.setdefault(goal, [])
        scores.append(score)
    return sorted(
        ((goal, round(sum(scores) / len(scores), 1), len(scores)) for goal, scores in by_goal.items()),
        key=lambda item: item[1],
    )


def get_weak_topic_for_user(username, available_topics):
    """Trả về một chủ đề yếu đã có trong kho câu đã duyệt, nếu có lịch sử làm bài."""
    topic_scores = {}
    for row in get_attempts(username):
        goal = str(row[2] or "")
        # Lượt luyện mới lưu theo dạng "Ôn theo ...: Chủ đề"; vẫn đọc được
        # cả dữ liệu cũ có nhãn "Luyện: Chủ đề".
        topic = goal.split(":", 1)[1].strip() if ":" in goal else goal.removeprefix("Luyện: ").strip()
        if topic not in available_topics:
            continue
        topic_scores.setdefault(topic, []).append(float(row[4] or 0))
    if not topic_scores:
        return None
    return min(topic_scores, key=lambda topic: sum(topic_scores[topic]) / len(topic_scores[topic]))


def get_sources():
    return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))


def get_candidates():
    if not CANDIDATES_FILE.exists():
        return []
    return json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))


def refresh_candidate_visual_flags(max_sources=4, max_bytes=12 * 1024 * 1024):
    """Nâng cấp nhãn hình của dữ liệu cũ theo đúng từng câu, không theo cả tệp.

    Đây là thao tác cục bộ và chỉ sửa nhãn an toàn; không xóa tệp gốc, câu hỏi,
    bản nháp AI hay kết quả học sinh.
    """
    candidates = get_candidates()
    pending = [item for item in candidates if item.get("visual_flag_version") != 2]
    if not pending:
        return 0, 0
    pending_sources = []
    for item in pending:
        source_file = item.get("source_file", "")
        if source_file not in pending_sources:
            pending_sources.append(source_file)
    selected_names, selected_bytes = [], 0
    for source_file in pending_sources:
        source_size = (SOURCES_DIR / source_file).stat().st_size if (SOURCES_DIR / source_file).exists() else 0
        # Luôn nhận ít nhất một tệp; tệp lớn sẽ tự thành một nhóm riêng.
        if selected_names and (len(selected_names) >= max_sources or selected_bytes + source_size > max_bytes):
            break
        selected_names.append(source_file)
        selected_bytes += source_size
    selected_sources = set(selected_names)
    selected_items = [item for item in pending if item.get("source_file", "") in selected_sources]
    per_file = {}
    for item in selected_items:
        source_file = item.get("source_file", "")
        if source_file in per_file:
            continue
        path = SOURCES_DIR / source_file
        if path.suffix.lower() == ".docx" and path.exists():
            per_file[source_file] = (map_docx_question_images(path), has_ooxml_math(path))
        else:
            per_file[source_file] = ({}, False)
    changed = 0
    for item in selected_items:
        image_map, contains_ooxml_math = per_file[item.get("source_file", "")]
        image_names = image_map.get(str(item.get("question_number", "")), [])
        item["source_image_names"] = image_names
        # Công thức OOXML đã được source_analyzer chuyển trực tiếp sang LaTex.
        # Chỉ hình nhúng thật mới cần quét/duyệt bằng AI.
        item["contains_ooxml_math"] = contains_ooxml_math
        item["math_extraction_status"] = "Đã trích OOXML sang LaTex" if contains_ooxml_math else "Không có công thức OOXML"
        item["requires_visual_review"] = bool(image_names)
        item["visual_flag_version"] = 2
        changed += 1
    CANDIDATES_FILE.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    remaining = len(pending) - changed
    return changed, remaining


def get_image_analyses():
    if not IMAGE_ANALYSIS_FILE.exists():
        return {}
    return json.loads(IMAGE_ANALYSIS_FILE.read_text(encoding="utf-8"))


def get_question_drafts():
    if not QUESTION_DRAFTS_FILE.exists():
        return {}
    return json.loads(QUESTION_DRAFTS_FILE.read_text(encoding="utf-8"))


def save_question_draft(candidate_id, draft):
    drafts = get_question_drafts()
    try:
        parsed = json.loads(draft) if isinstance(draft, str) else draft
        status = "Bản nháp AI — chưa dùng cho học sinh" if parsed.get("usable") else "Thiếu dữ kiện — không dùng tự động"
    except (TypeError, json.JSONDecodeError):
        status = "AI trả lời chưa hoàn chỉnh — cần tạo lại"
    drafts[candidate_id] = {"draft": draft, "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"), "status": status}
    QUESTION_DRAFTS_FILE.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")


def refresh_question_draft_statuses():
    """Không để bản nháp JSON lỗi hoặc thiếu dữ kiện bị hiểu nhầm là dùng được."""
    drafts = get_question_drafts()
    changed = False
    for record in drafts.values():
        try:
            parsed = json.loads(record.get("draft", ""))
            status = "Bản nháp AI — chưa dùng cho học sinh" if parsed.get("usable") else "Thiếu dữ kiện — không dùng tự động"
        except (TypeError, json.JSONDecodeError):
            status = "AI trả lời chưa hoàn chỉnh — cần tạo lại"
        if record.get("status") not in {"Đã duyệt và đưa vào ngân hàng", status}:
            record["status"] = status
            changed = True
    if changed:
        QUESTION_DRAFTS_FILE.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")


def get_approved_questions():
    if not APPROVED_QUESTIONS_FILE.exists():
        return []
    return json.loads(APPROVED_QUESTIONS_FILE.read_text(encoding="utf-8"))


def get_quiz_variants():
    if not QUIZ_VARIANTS_FILE.exists():
        return {}
    return json.loads(QUIZ_VARIANTS_FILE.read_text(encoding="utf-8"))


def get_ready_export_bank():
    """Chỉ dùng câu đã duyệt cho học sinh, không xuất các câu Word thô hoặc AI chưa chắc."""
    bank = {"multiple_choice": [], "true_false": [], "short_answer": []}
    for record in get_quiz_variants().values():
        if record.get("status") != "Đã duyệt — sẵn sàng cho học sinh":
            continue
        try:
            question = json.loads(record["variant"])
        except (TypeError, KeyError, json.JSONDecodeError):
            continue
        if question.get("type") == "multiple_choice" and len(question.get("options") or []) == 4:
            bank["multiple_choice"].append({"question": question.get("question", ""), "options": question["options"], "answer": question.get("correct_answer", ""), "solution": question.get("solution", "")})
        elif question.get("type") == "short_answer":
            bank["short_answer"].append({"question": question.get("question", ""), "answer": question.get("correct_answer", ""), "solution": question.get("solution", "")})
    return bank


def get_ready_export_bank_for_grade(grade=None):
    """Lấy câu đã duyệt từ toàn kho theo khối, không phụ thuộc file gốc là đề gì.

    Đề giữa/cuối kỳ và đề THPT có thể phối hợp câu từ mọi bài/chuyên đề liên quan
    trong kho. Câu Word thô, ảnh chưa chắc và bản nháp AI vẫn luôn bị loại.
    """
    bank = {"multiple_choice": [], "true_false": [], "short_answer": []}
    for candidate_id, record in get_quiz_variants().items():
        if record.get("status") != "Đã duyệt — sẵn sàng cho học sinh":
            continue
        metadata = record.get("metadata") or get_candidate_metadata(candidate_id)
        if grade and metadata.get("grade") != grade:
            continue
        try:
            question = json.loads(record["variant"])
        except (TypeError, KeyError, json.JSONDecodeError):
            continue
        if question.get("type") == "multiple_choice" and len(question.get("options") or []) == 4:
            bank["multiple_choice"].append({"question": question.get("question", ""), "options": question["options"], "answer": question.get("correct_answer", ""), "solution": question.get("solution", "")})
        elif question.get("type") == "short_answer":
            bank["short_answer"].append({"question": question.get("question", ""), "answer": question.get("correct_answer", ""), "solution": question.get("solution", "")})
    return bank


def get_bank_quality_report():
    """Tổng hợp trạng thái dữ liệu để giáo viên không cần rà thủ công toàn kho.

    Báo cáo này chỉ đếm và kiểm tra định dạng cục bộ. Một câu chỉ được tính là
    sẵn sàng nếu đã được giáo viên duyệt và có cấu trúc chấm tự động hợp lệ.
    """
    sources = get_sources()
    candidates = get_candidates()
    drafts = get_question_drafts()
    variants = get_quiz_variants()
    image_analyses = get_image_analyses()
    data_audit = audit_data_links(sources, candidates, variants, SOURCES_DIR)
    source_status = {"pending": 0, "ocr": 0, "done": 0}
    for source in sources:
        status = source.get("analysis_status")
        if status == "done":
            source_status["done"] += 1
        elif status == "needs_ocr":
            source_status["ocr"] += 1
        else:
            source_status["pending"] += 1

    draft_status = {"usable": 0, "blocked": 0, "invalid": 0, "approved": 0}
    for record in drafts.values():
        if record.get("status") == "Đã duyệt và đưa vào ngân hàng":
            draft_status["approved"] += 1
            continue
        try:
            parsed = json.loads(record.get("draft", ""))
            if parsed.get("usable") and not parsed.get("requires_teacher_review"):
                draft_status["usable"] += 1
            else:
                draft_status["blocked"] += 1
        except (TypeError, json.JSONDecodeError):
            draft_status["invalid"] += 1

    variant_status = {"ready": 0, "draft": 0, "invalid": 0}
    for record in variants.values():
        try:
            question = json.loads(record.get("variant", ""))
            valid_mc = question.get("type") != "multiple_choice" or len(question.get("options") or []) == 4
            valid_short = question.get("type") != "short_answer" or bool(str(question.get("correct_answer", "")).strip())
            is_valid = bool(question.get("usable")) and not question.get("requires_teacher_review") and valid_mc and valid_short
        except (TypeError, json.JSONDecodeError):
            is_valid = False
        if record.get("status") == "Đã duyệt — sẵn sàng cho học sinh" and is_valid:
            variant_status["ready"] += 1
        elif is_valid:
            variant_status["draft"] += 1
        else:
            variant_status["invalid"] += 1

    visual_waiting = sum(1 for item in candidates if item.get("requires_visual_review") and not item.get("visual_paths"))
    visual_labels_to_upgrade = sum(1 for item in candidates if item.get("visual_flag_version") != 2)
    image_status = {
        "read": sum(1 for item in image_analyses.values() if item.get("read_status", "Đã đọc") == "Đã đọc"),
        "failed": sum(1 for item in image_analyses.values() if item.get("read_status") == "Đọc lỗi — không tự quét lại"),
        "safe": sum(1 for item in image_analyses.values() if item.get("safe_to_use")),
    }
    return {
        "sources": source_status,
        "candidates_total": len(candidates),
        "candidates_visual_waiting": visual_waiting,
        "visual_labels_to_upgrade": visual_labels_to_upgrade,
        "images": image_status,
        "data_audit": data_audit,
        "curriculum_errors": validate_curricula(load_curriculum),
        "drafts": draft_status,
        "variants": variant_status,
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


def save_quiz_variant(candidate_id, variant):
    variants = get_quiz_variants()
    variants[candidate_id] = {
        "variant": variant,
        "metadata": get_candidate_metadata(candidate_id),
        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status": "Bản nháp trắc nghiệm — chưa dùng cho học sinh",
    }
    QUIZ_VARIANTS_FILE.write_text(json.dumps(variants, ensure_ascii=False, indent=2), encoding="utf-8")


def approve_quiz_variant(candidate_id):
    variants = get_quiz_variants()
    record = variants.get(candidate_id)
    try:
        variant = json.loads(record["variant"])
    except (TypeError, KeyError, json.JSONDecodeError):
        return False, "Bản nháp trắc nghiệm không đúng định dạng."
    if not variant.get("usable") or variant.get("requires_teacher_review"):
        return False, "AI gắn cờ cần xem lại nên chưa thể đưa cho học sinh."
    if variant.get("type") == "multiple_choice" and len(variant.get("options") or []) != 4:
        return False, "Câu trắc nghiệm phải có đúng 4 lựa chọn."
    record["status"] = "Đã duyệt — sẵn sàng cho học sinh"
    QUIZ_VARIANTS_FILE.write_text(json.dumps(variants, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, "Đã duyệt biến thể trắc nghiệm."


def approve_question_draft(candidate_id):
    drafts = get_question_drafts()
    record = drafts.get(candidate_id)
    if not record:
        return False, "Không tìm thấy bản nháp này."
    try:
        draft = json.loads(record["draft"])
    except (TypeError, json.JSONDecodeError):
        return False, "Bản nháp không đúng định dạng JSON."
    if not draft.get("usable") or draft.get("requires_teacher_review"):
        return False, "Bản nháp đang được gắn cờ cần duyệt thêm nên chưa thể đưa vào ngân hàng tự động."
    approved = get_approved_questions()
    approved = [item for item in approved if item.get("candidate_id") != candidate_id]
    approved.append({
        "candidate_id": candidate_id,
        "question": draft,
        "approved_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status": "Đã duyệt — sẵn sàng dùng khi tạo đề",
    })
    APPROVED_QUESTIONS_FILE.write_text(json.dumps(approved, ensure_ascii=False, indent=2), encoding="utf-8")
    record["status"] = "Đã duyệt và đưa vào ngân hàng"
    QUESTION_DRAFTS_FILE.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, "Đã đưa câu vào ngân hàng đã duyệt."


def show_question_draft_preview(draft_text):
    """Hiển thị bản nháp bằng ngôn ngữ giáo viên thay vì JSON kỹ thuật."""
    try:
        draft = json.loads(draft_text) if isinstance(draft_text, str) else draft_text
    except (TypeError, json.JSONDecodeError):
        st.error("Không đọc được bản nháp này. Giữ nguyên ở trạng thái chưa duyệt.")
        return None
    st.markdown("#### Xem trước câu hỏi")
    st.markdown(math_display_text(draft.get("question_latex_or_text", "AI chưa tạo được nội dung đề.")))
    options = draft.get("options") or []
    if options:
        for index, option in enumerate(options):
            st.markdown(f"{chr(65 + index)}. {math_display_text(option)}")
    st.caption(f"Dạng: {draft.get('question_type', 'Chưa xác định')} · Chủ đề: {draft.get('topic', 'Chưa xác định')} · Mức độ: {draft.get('cognitive_level', 'Chưa xác định')}")
    with st.expander("Xem đáp án và lời giải trước khi duyệt"):
        st.markdown(f"**Đáp án:** {math_display_text(draft.get('correct_answer', 'Chưa có'))}")
        st.markdown("**Lời giải:**")
        st.markdown(math_display_text(draft.get("solution_latex_or_text", "Chưa có lời giải.")))
    if draft.get("requires_teacher_review"):
        st.warning("AI gắn cờ cần xem lại; app sẽ không cho duyệt tự động.")
    return draft


def normalize_ai_image_result(result):
    """Chuẩn hóa phản hồi Gemini: chấp nhận JSON object hoặc mảng JSON.

    Một số model đôi khi bọc kết quả một ảnh trong mảng một phần tử. App chỉ
    nhận đối tượng đầu tiên có cấu trúc đọc ảnh, tuyệt đối không coi mảng lạ là
    đủ tin cậy.
    """
    try:
        parsed = json.loads(result) if isinstance(result, str) else result
    except (TypeError, json.JSONDecodeError):
        return None
    if isinstance(parsed, list):
        parsed = next((item for item in parsed if isinstance(item, dict)), None)
    return parsed if isinstance(parsed, dict) else None


def is_ai_image_safe_to_use(result):
    parsed = normalize_ai_image_result(result)
    try:
        confidence = float((parsed or {}).get("confidence", 0))
        return bool(parsed) and not bool(parsed.get("needs_teacher_review", True)) and confidence >= 0.8
    except (TypeError, ValueError):
        return False


def apply_image_safety_policy():
    """Ảnh không chắc chắn chỉ được giữ làm tham khảo, không đưa vào đề tự động."""
    analyses = get_image_analyses()
    changed = False
    for item in analyses.values():
        safe = is_ai_image_safe_to_use(item.get("result", ""))
        status = "Đủ tin cậy để dùng tự động" if safe else "Không dùng tự động — cần duyệt"
        if item.get("usage_status") != status:
            item["usage_status"] = status
            item["safe_to_use"] = safe
            changed = True
    if changed:
        IMAGE_ANALYSIS_FILE.write_text(json.dumps(analyses, ensure_ascii=False, indent=2), encoding="utf-8")
    return analyses


def attach_safe_visuals_to_candidates():
    """Nối kết quả ảnh đủ tin cậy vào câu cùng vị trí trong tài liệu Word."""
    candidates = get_candidates()
    analyses = apply_image_safety_policy()
    safe_results = {
        analysis_id: item for analysis_id, item in analyses.items() if item.get("safe_to_use")
    }
    maps = {}
    attached = 0
    for item in candidates:
        source_file = item.get("source_file", "")
        if source_file not in maps:
            path = SOURCES_DIR / source_file
            maps[source_file] = map_docx_question_images(path) if path.suffix.lower() == ".docx" else {}
        image_names = maps[source_file].get(str(item.get("question_number", "")), [])
        visual_results = []
        for image_name in image_names:
            analysis = safe_results.get(f"{source_file}::{image_name}")
            if analysis:
                visual_results.append({"image_name": image_name, "ai_result": analysis["result"]})
        item["visual_status"] = "Có hình chưa được duyệt — không dùng tự động" if image_names and not visual_results else ("Đã ghép hình AI đủ tin cậy" if visual_results else "Không có hình AI đã duyệt")
        item["visual_ai_results"] = visual_results
        attached += len(visual_results)
    CANDIDATES_FILE.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    return attached, len(candidates)


def save_image_analysis(source_file, image, result, read_ok=True):
    analyses = get_image_analyses()
    analysis_id = f"{source_file}::{image['name']}"
    normalized_result = normalize_ai_image_result(result)
    stored_result = json.dumps(normalized_result, ensure_ascii=False) if normalized_result is not None else (result if isinstance(result, str) else json.dumps(result, ensure_ascii=False))
    safe = is_ai_image_safe_to_use(normalized_result)
    analyses[analysis_id] = {
        "source_file": source_file,
        "image_name": image["name"],
        "result": stored_result,
        "analyzed_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "read_status": "Đã đọc" if read_ok else "Đọc lỗi — không tự quét lại",
        "safe_to_use": safe,
        "usage_status": "Đủ tin cậy để dùng tự động" if safe else ("Không dùng tự động — cần duyệt" if read_ok else "Không dùng — có lỗi khi AI đọc"),
    }
    IMAGE_ANALYSIS_FILE.write_text(json.dumps(analyses, ensure_ascii=False, indent=2), encoding="utf-8")


def analyze_question_sources():
    sources = get_sources()
    pending = [source for source in sources if source.get("analysis_status") not in {"done", "needs_ocr"}]
    existing = {item["candidate_id"]: item for item in get_candidates()}
    candidates, results = analyze_sources(pending, SOURCES_DIR)
    existing.update({item["candidate_id"]: item for item in candidates})
    CANDIDATES_FILE.write_text(json.dumps(list(existing.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    result_status = {file_name: status for file_name, _, status in results}
    for source in sources:
        status = result_status.get(source["file_name"])
        if status in {"Đã tách câu ứng viên", "Đã tách câu PDF có chữ"}:
            source["analysis_status"] = "done"
            source["status"] = "Đã tách câu — chờ AI phân loại và giáo viên duyệt"
        elif status == "PDF cần OCR/AI ở bước tiếp theo":
            source["analysis_status"] = "needs_ocr"
            source["status"] = "Chờ OCR/AI đọc PDF"
    SOURCES_FILE.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    return results, len(existing), len(pending)


def refresh_ooxml_math_candidates():
    """Nâng cấp an toàn các câu Word có công thức sang LaTex cục bộ.

    Chỉ thay văn bản/cờ hình được trích lại; giữ nguyên nhãn, bản nháp, câu đã
    duyệt và lịch sử học sinh đã có.
    """
    sources = [source for source in get_sources() if source["file_name"].lower().endswith(".docx") and has_ooxml_math(SOURCES_DIR / source["file_name"])]
    if not sources:
        return 0, 0
    refreshed, _ = analyze_sources(sources, SOURCES_DIR)
    existing = {item["candidate_id"]: item for item in get_candidates()}
    changed = 0
    copied_fields = {
        "question_text", "solution_text", "source_image_names", "requires_visual_review",
        "contains_ooxml_math", "math_extraction_status", "visual_flag_version",
    }
    for fresh in refreshed:
        current = existing.get(fresh["candidate_id"])
        if not current:
            continue
        for field in copied_fields:
            current[field] = fresh.get(field)
        current.pop("visual_ai_results", None)
        current["visual_status"] = "Chờ ghép ảnh thật (nếu có)" if current.get("source_image_names") else "Không cần quét ảnh — đã đọc công thức Word trực tiếp"
        changed += 1
    CANDIDATES_FILE.write_text(json.dumps(list(existing.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    return changed, len(sources)


def infer_question_kind(text, source_kind):
    """Nhận diện sơ bộ tại máy; giáo viên vẫn duyệt câu có cấu trúc đặc biệt."""
    normalized = normalize_text(text)
    if "dung/sai" in normalized or "dung sai" in normalized:
        return "Đúng / Sai"
    if all(marker in normalized for marker in ("a)", "b)", "c)", "d)")) and source_kind != "Ngân hàng trắc nghiệm nhiều lựa chọn":
        return "Đúng / Sai (cần duyệt)"
    if source_kind == "Ngân hàng câu trả lời ngắn":
        return "Trả lời ngắn"
    if source_kind == "Ngân hàng câu tự luận":
        return "Tự luận"
    if source_kind == "Ngân hàng câu đúng/sai":
        return "Đúng / Sai"
    if source_kind == "Ngân hàng trắc nghiệm nhiều lựa chọn" or all(marker in normalized for marker in ("a.", "b.", "c.", "d.")):
        return "Trắc nghiệm 4 lựa chọn"
    return "Chưa nhận diện (cần duyệt)"


def infer_topic(text, lesson):
    normalized = normalize_text(f"{lesson} {text}")
    topic_rules = [
        (("don dieu", "cuc tri"), "Tính đơn điệu và cực trị"),
        (("max", "min", "gia tri lon nhat", "gia tri nho nhat", "toi uu"), "Giá trị lớn nhất, nhỏ nhất và tối ưu"),
        (("tiem can",), "Đường tiệm cận"),
        (("khao sat", "do thi"), "Khảo sát và vẽ đồ thị hàm số"),
        (("nguyen ham",), "Nguyên hàm"),
        (("tich phan",), "Tích phân"),
        (("mat phang",), "Phương trình mặt phẳng"),
        (("duong thang",), "Phương trình đường thẳng trong không gian"),
        (("mat cau",), "Phương trình mặt cầu"),
        (("bayes", "xac suat toan phan"), "Xác suất toàn phần và Bayes"),
        (("xac suat co dieu kien",), "Xác suất có điều kiện"),
        (("phuong sai", "do lech chuan"), "Phương sai và độ lệch chuẩn"),
        (("khoang tu phan vi", "khoang bien thien"), "Khoảng biến thiên và khoảng tứ phân vị"),
        (("vector",), "Vectơ trong không gian"),
    ]
    for keywords, topic in topic_rules:
        if any(keyword in normalized for keyword in keywords):
            return topic
    return lesson if lesson != "Chưa phân loại" else "Chưa phân loại (cần AI/giáo viên duyệt)"


def infer_level(text):
    normalized = normalize_text(text)
    if any(word in normalized for word in ("tham so", "thuc te", "toi uu", "chung minh", "tim tat ca")):
        return "Vận dụng"
    if any(word in normalized for word in ("tinh", "giai", "xac dinh")):
        return "Thông hiểu"
    return "Nhận biết"


def classify_candidates_locally(only_text=False):
    """Gắn nhãn nền tảng từ văn bản và nhãn nguồn, không thay thế AI ngữ nghĩa."""
    candidates = get_candidates()
    for item in candidates:
        if only_text and not item.get("eligible_for_text_pipeline", False):
            continue
        text = item.get("question_text", "")
        item["question_type"] = infer_question_kind(text, item.get("document_kind", ""))
        item["topic"] = infer_topic(text, item.get("lesson", "Chưa phân loại"))
        item["cognitive_level"] = infer_level(text)
        needs_review = item.get("requires_visual_review", False) or "cần duyệt" in item["question_type"].lower()
        item["status"] = "Cần giáo viên/AI duyệt" if needs_review else "Đã gắn nhãn sơ bộ"
    CANDIDATES_FILE.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    return candidates


def apply_visual_quality_gate():
    """Chỉ mở câu cho luồng văn bản khi dữ kiện hình không thể làm đổi đáp án.

    Không có nhãn 'an toàn' thì ưu tiên chặn, tuyệt đối không suy đoán từ tên tệp.
    """
    candidates, analyses = get_candidates(), apply_image_safety_policy()
    visual_cues = ("hình", "đồ thị", "biểu đồ", "bảng", "quan sát", "minh họa", "dựa vào", "hình bên")
    changed = 0
    for item in candidates:
        text = normalize_text(item.get("question_text", ""))
        image_names = item.get("source_image_names") or []
        if item.get("ocr_origin") == "PDF OCR cục bộ":
            requirement, eligible = "PDF OCR cục bộ — cần duyệt", False
        elif not image_names:
            requirement, eligible = "Đủ văn bản — không cần ảnh", True
        elif any(cue in text for cue in visual_cues):
            requirement, eligible = "Ảnh là dữ kiện bắt buộc — chờ duyệt", False
        else:
            image_ids = [f"{item.get('source_file', '')}::{name}" for name in image_names]
            all_safe = bool(image_ids) and all(analyses.get(image_id, {}).get("safe_to_use") for image_id in image_ids)
            requirement = "Ảnh đã xác nhận an toàn" if all_safe else "Cần xác minh ảnh trước"
            eligible = all_safe
        if item.get("visual_requirement") != requirement or item.get("eligible_for_text_pipeline") != eligible:
            item["visual_requirement"] = requirement
            item["eligible_for_text_pipeline"] = eligible
            changed += 1
    if changed:
        CANDIDATES_FILE.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed, sum(1 for item in candidates if item.get("eligible_for_text_pipeline"))


def test_gemini_connection(api_key):
    """Kiểm tra key, tự chọn một model đang có, rồi gửi yêu cầu ngắn."""
    try:
        list_request = Request(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": api_key},
            method="GET",
        )
        with urlopen(list_request, timeout=20) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
        available = {item.get("name", "").removeprefix("models/") for item in models}
        # Ưu tiên Flash Lite/Flash cho lượt kiểm tra và phân loại hàng loạt,
        # tránh model suy luận nặng làm người dùng phải chờ lâu.
        preferred = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash", "gemini-2.5-flash"]
        model = next((name for name in preferred if name in available), None)
        if not model:
            return False, "Key hợp lệ nhưng project này chưa có model Gemini phù hợp để tạo nội dung. Hãy kiểm tra quota trong Google AI Studio."
    except HTTPError as error:
        if error.code in {401, 403}:
            return False, "Gemini từ chối khóa này. Hãy tạo key mới trong Google AI Studio và thử lại."
        return False, f"Không kiểm tra được key Gemini (lỗi {error.code})."
    except (URLError, TimeoutError, socket.timeout):
        return False, "Máy chưa kết nối được tới Gemini. Đây thường là lỗi mạng/tường lửa hoặc Gemini đang chậm; key chưa bị kết luận là sai."
    except Exception as error:
        return False, f"Không thể kiểm tra Gemini: {error}"


def ask_gemini_as_tutor(api_key, problem_text, mode, student_step="", hint_number=1):
    """Một cửa gọi AI cho Góc giải bài, luôn dựa trên đề người dùng đã xác nhận.

    Không dùng hàm này để nhập kho hoặc phát hành câu hỏi. Lời giải đầy đủ chỉ
    được yêu cầu khi người học chủ động chọn nút tương ứng.
    """
    if not api_key or len(api_key.strip()) < 20:
        return False, "Chưa có khóa Gemini trong phiên này. Giáo viên hãy kết nối ở Góc cùng suy nghĩ AI trước."
    mode_instructions = {
        "hint": "Chỉ cho MỘT gợi ý ngắn cho bước tiếp theo, không tiết lộ đáp số hay lời giải hoàn chỉnh.",
        "step": "Đánh giá bước làm của học sinh là đúng, sai, hay chưa đủ. Nêu chính xác lý do thật ngắn và đưa một gợi ý nhỏ tiếp theo. Không giải hết bài.",
        "solution": "Trình bày lời giải từng bước, chia rõ Phân tích, Giải, Kết luận. Nêu điều kiện cần thiết và không bịa dữ kiện.",
    }
    instruction = mode_instructions.get(mode, mode_instructions["hint"])
    prompt = f"""Bạn là Thầy AI của TrinhMath AI, hướng dẫn Toán THPT Việt Nam.
Đề dưới đây đã được học sinh/giáo viên XÁC NHẬN lại sau OCR. {instruction}
Ưu tiên cách giải phổ thông dễ hiểu. Mọi công thức dùng LaTeX đặt trong $...$ hoặc $$...$$.
Không tự khẳng định kết quả chắc chắn nếu đề thiếu dữ kiện; khi đó nói rõ cần kiểm tra lại.
Trả về JSON thuần với các trường: response, detected_topic, confidence, needs_review.
Lượt gợi ý hiện tại: {hint_number}.
Đề đã xác nhận:\n{problem_text[:7000]}
{f"Bước học sinh đã làm: {student_step[:2000]}" if student_step else ""}"""
    try:
        model = get_gemini_image_model(api_key)
        if not model:
            return False, "Không tìm thấy model Gemini phù hợp trong project này. Hãy kiểm tra lại kết nối hoặc quota."
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.15, "maxOutputTokens": 3000, "responseMimeType": "application/json"},
        }
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(payload).encode("utf-8"),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = "\n".join(part.get("text", "") for part in body.get("candidates", [{}])[0].get("content", {}).get("parts", [])).strip()
        parsed = normalize_ai_image_result(content)
        if not parsed or not str(parsed.get("response", "")).strip():
            return False, "AI trả về nội dung chưa đúng định dạng; đề chưa được xem là đã giải. Hãy thử lại sau."
        return True, parsed
    except HTTPError as error:
        return False, f"Gemini trả về lỗi {error.code}: {error.read().decode('utf-8', errors='replace')[:300]}"
    except (URLError, TimeoutError, socket.timeout):
        return False, "Gemini chưa phản hồi kịp. Đề và phần học sinh đã nhập vẫn được giữ trên màn hình; bạn có thể thử lại."
    except Exception as error:
        return False, f"Không thể nhận hỗ trợ từ AI: {error}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": "Reply with exactly: KET_NOI_THANH_CONG"}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 16},
    }).encode("utf-8")
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=payload,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=75) as response:
            body = json.loads(response.read().decode("utf-8"))
        parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        reply = " ".join(part.get("text", "") for part in parts).strip()
        return True, f"Kết nối thành công bằng {model}: {reply or 'OK'}"
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")[:500]
        if error.code in {401, 403}:
            return False, "Gemini từ chối khóa này. Hãy kiểm tra key hoặc quyền của project."
        if error.code == 429:
            return False, "Bạn đã chạm giới hạn Gemini tạm thời. Hãy chờ quota rồi thử lại."
        return False, f"Gemini trả về lỗi {error.code}: {details}"
    except URLError:
        return False, "Không kết nối được Internet hoặc máy chủ Gemini. Hãy kiểm tra mạng rồi thử lại."
    except (TimeoutError, socket.timeout):
        return False, "Gemini chưa phản hồi kịp. Hãy thử lại sau khoảng một phút; app không gửi kho đề trong lần kiểm tra này."
    except Exception as error:
        return False, f"Không thể kiểm tra Gemini: {error}"


def get_docx_images(path, allowed_names=None):
    """Lấy ảnh nhúng trong Word; WMF được chuyển cục bộ sang PNG để AI đọc."""
    mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    try:
        with zipfile.ZipFile(path) as archive:
            images = []
            for name in archive.namelist():
                suffix = Path(name).suffix.lower()
                if not name.startswith("word/media/") or (allowed_names and name not in allowed_names):
                    continue
                data = archive.read(name)
                if suffix in mime_types:
                    images.append({"name": name, "mime_type": mime_types[suffix], "data": data})
                elif suffix == ".wmf":
                    with Image.open(io.BytesIO(data)) as image:
                        image.load()
                        converted = io.BytesIO()
                        image.convert("RGB").save(converted, format="PNG")
                    images.append({"name": name, "mime_type": "image/png", "data": converted.getvalue()})
        return images, None
    except (zipfile.BadZipFile, KeyError, OSError) as error:
        return [], f"Không đọc được ảnh trong Word: {error}"


def get_unread_question_images(limit=3):
    """Lấy vài ảnh công thức chưa quét, chỉ từ vị trí câu hỏi trong Word."""
    analyses = get_image_analyses()
    pending = []
    for source in get_sources():
        if not source["file_name"].lower().endswith(".docx"):
            continue
        source_path = SOURCES_DIR / source["file_name"]
        image_names = {name for names in map_docx_question_images(source_path).values() for name in names}
        images, error = get_docx_images(source_path, image_names)
        if error:
            continue
        for image in images:
            if f"{source['file_name']}::{image['name']}" not in analyses:
                pending.append((source, image))
                if len(pending) >= limit:
                    return pending
    return pending


def count_unread_question_images():
    """Đếm tiến độ từ chỉ mục đã lập, không giải nén lại toàn bộ Word mỗi lần."""
    analyses = get_image_analyses()
    indexed_ids = {
        f"{item.get('source_file')}::{image_name}"
        for item in get_candidates()
        for image_name in item.get("source_image_names", [])
    }
    # Kho cũ chưa nâng cấp chỉ mục: không đoán số lượng bằng cách quét lại 100+ MB Word.
    return len(indexed_ids - set(analyses)) if indexed_ids else None


def get_gemini_image_model(api_key):
    """Chọn model một lần; worker nền dùng lại để không gọi danh sách model cho từng ảnh."""
    try:
        list_request = Request("https://generativelanguage.googleapis.com/v1beta/models", headers={"x-goog-api-key": api_key}, method="GET")
        with urlopen(list_request, timeout=20) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
        available = {item.get("name", "").removeprefix("models/") for item in models}
        preferred = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.7-flash", "gemini-2.5-flash"]
        return next((name for name in preferred if name in available), "")
    except (HTTPError, URLError, TimeoutError, socket.timeout, OSError, json.JSONDecodeError):
        return ""


def read_image_with_gemini(api_key, image, model=None):
    """Gửi đúng một ảnh để kiểm thử nhận diện công thức; không gửi cả kho đề."""
    prompt = """Đây là một ảnh trích từ tài liệu Toán THPT Việt Nam. Hãy đọc chính xác nội dung nhìn thấy.
Nếu có công thức, chép lại bằng LaTeX. Sau đó trả về JSON thuần, gồm các trường:
    extracted_text, latex, math_topic, question_type, confidence, needs_teacher_review.
Không tự bịa phần không nhìn rõ; khi không chắc hãy ghi rõ trong needs_teacher_review."""
    try:
        model = model or get_gemini_image_model(api_key)
        if not model:
            return False, "Không tìm thấy model Gemini phù hợp trong project này."
        payload = {
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": image["mime_type"], "data": base64.b64encode(image["data"]).decode("ascii")}},
            ]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1600, "responseMimeType": "application/json"},
        }
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(payload).encode("utf-8"),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
        parts = body.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        output = "\n".join(part.get("text", "") for part in parts).strip()
        return True, output or "Gemini không trả về nội dung đọc được."
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")[:500]
        return False, f"Gemini trả về lỗi {error.code}: {details}"
    except (URLError, TimeoutError, socket.timeout):
        return False, "Gemini chưa trả lời kịp ảnh này. Hãy thử ảnh khác hoặc thử lại sau."
    except Exception as error:
        return False, f"Không thể đọc ảnh bằng Gemini: {error}"


def create_question_draft_with_gemini(api_key, candidate):
    """Tạo bản nháp từ câu chữ, kèm ảnh khi ảnh đã được AI xác nhận an toàn."""
    image_names = {item["image_name"] for item in candidate.get("visual_ai_results", [])}
    images = []
    if image_names:
        images, error = get_docx_images(SOURCES_DIR / candidate["source_file"], image_names)
        if error:
            return False, error
    visual_warning = "Có hình chưa được duyệt nên hình đó KHÔNG được gửi. Không suy đoán nội dung hình; nếu câu cần hình, đặt usable=false." if candidate.get("requires_visual_review") and not images else ""
    prompt = f"""Bạn là trợ lý biên soạn ngân hàng câu hỏi Toán THPT. Hãy lập một bản nháp cho ĐÚNG MỘT bài dưới đây, dùng văn bản và các ảnh đi kèm.
{visual_warning}
Không đoán hoặc tự tạo dữ kiện bị thiếu. Nếu không đủ thông tin, đặt usable=false và giải thích ngắn.
Nếu đủ, trả về JSON thuần gồm: usable, question_type, question_latex_or_text, options (mảng, nếu có), correct_answer, solution_latex_or_text, topic, cognitive_level, requires_teacher_review, reason.
Lời giải phải ngắn gọn, tối đa 12 dòng. Luôn đóng đủ JSON; không dùng ký tự xuống dòng thô bên trong chuỗi JSON.
Mọi công thức phải ở LaTeX. Đây là nhãn nguồn, không hiển thị nguồn/trường: khối {candidate.get('grade')}, chương {candidate.get('chapter')}, bài {candidate.get('lesson')}.
Văn bản đã tách từ Word: {candidate.get('question_text', '')[:5000]}"""
    try:
        list_request = Request("https://generativelanguage.googleapis.com/v1beta/models", headers={"x-goog-api-key": api_key}, method="GET")
        with urlopen(list_request, timeout=20) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
        available = {item.get("name", "").removeprefix("models/") for item in models}
        model = next((name for name in ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"] if name in available), None)
        if not model:
            return False, "Không tìm thấy model Gemini phù hợp để lập bản nháp."
        parts = [{"text": prompt}]
        parts.extend({"inline_data": {"mime_type": image["mime_type"], "data": base64.b64encode(image["data"]).decode("ascii")}} for image in images)
        payload = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.05, "maxOutputTokens": 5000, "responseMimeType": "application/json"}}
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps(payload).encode("utf-8"),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=150) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = "\n".join(part.get("text", "") for part in body.get("candidates", [{}])[0].get("content", {}).get("parts", [])).strip()
        if not text:
            return False, "Gemini không trả về bản nháp."
        return True, text
    except HTTPError as error:
        return False, f"Gemini trả về lỗi {error.code}: {error.read().decode('utf-8', errors='replace')[:500]}"
    except (URLError, TimeoutError, socket.timeout):
        return False, "Gemini chưa trả lời kịp khi lập bản nháp. Hãy thử lại sau; app chưa lưu câu nào từ lượt này."
    except Exception as error:
        return False, f"Không tạo được bản nháp: {error}"


def create_quiz_variant_with_gemini(api_key, approved_question, desired_type):
    """Chuyển một câu đã duyệt sang định dạng học sinh có thể chấm tự động."""
    question = approved_question["question"]
    format_instruction = (
        "Tạo đúng 4 lựa chọn A, B, C, D; chỉ một lựa chọn đúng; tạo phương án nhiễu hợp lý."
        if desired_type == "multiple_choice"
        else "Tạo câu trả lời ngắn có một đáp án ngắn, rõ ràng, có thể so khớp tự động."
    )
    prompt = f"""Chuyển câu Toán THPT đã được giáo viên duyệt dưới đây thành một câu {"trắc nghiệm 4 lựa chọn" if desired_type == "multiple_choice" else "trả lời ngắn"} độc lập.
{format_instruction}
Không thay đổi kiến thức cốt lõi, không tự bịa dữ kiện. Nếu không thể chuyển an toàn, usable=false.
Trả về JSON thuần gồm usable, type, question, options (mảng 4 chuỗi nếu trắc nghiệm, nếu không thì []), correct_answer (A/B/C/D nếu trắc nghiệm), solution, topic, cognitive_level, requires_teacher_review, reason.
Câu nguồn: {question.get('question_latex_or_text', '')}
Đáp án nguồn: {question.get('correct_answer', '')}
Lời giải nguồn: {question.get('solution_latex_or_text', '')}"""
    try:
        list_request = Request("https://generativelanguage.googleapis.com/v1beta/models", headers={"x-goog-api-key": api_key}, method="GET")
        with urlopen(list_request, timeout=20) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
        available = {item.get("name", "").removeprefix("models/") for item in models}
        model = next((name for name in ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"] if name in available), None)
        if not model:
            return False, "Không tìm thấy model Gemini phù hợp."
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2200, "responseMimeType": "application/json"}}
        request = Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", data=json.dumps(payload).encode("utf-8"), headers={"x-goog-api-key": api_key, "Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
        result = "\n".join(part.get("text", "") for part in body.get("candidates", [{}])[0].get("content", {}).get("parts", [])).strip()
        return (True, result) if result else (False, "Gemini không trả về câu trắc nghiệm.")
    except HTTPError as error:
        return False, f"Gemini trả về lỗi {error.code}: {error.read().decode('utf-8', errors='replace')[:500]}"
    except (URLError, TimeoutError, socket.timeout):
        return False, "Gemini chưa trả lời kịp. Hãy thử lại sau."
    except Exception as error:
        return False, f"Không tạo được biến thể trắc nghiệm: {error}"


def load_grade12_curriculum():
    return json.loads(CURRICULUM_FILE.read_text(encoding="utf-8"))


def load_curriculum(grade):
    files = {
        "Lớp 10": CURRICULUM_GRADE10_FILE,
        "Lớp 11": CURRICULUM_GRADE11_FILE,
        "Lớp 12": CURRICULUM_FILE,
    }
    path = files.get(grade)
    return json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else []


def get_candidate_metadata(candidate_id):
    candidate = next((item for item in get_candidates() if item.get("candidate_id") == candidate_id), {})
    source = next((item for item in get_sources() if item.get("file_name") == candidate.get("source_file")), {})
    return {
        "grade": candidate.get("grade") or source.get("grade", "Lớp 12"),
        "chapter": candidate.get("chapter") or source.get("chapter", "Chưa phân loại"),
        "lesson": candidate.get("lesson") or source.get("lesson", "Chưa phân loại"),
        "exam_type": candidate.get("exam_type") or source.get("exam_type", "Khác"),
        "subtopic": candidate.get("subtopic") or source.get("subtopic", ""),
    }


def normalize_text(value):
    return "".join(char for char in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(char) != "Mn").replace("đ", "d")


def search_candidates_across_bank(query, limit=30):
    """Tìm trên toàn bộ kho đã nhập, không phụ thuộc thư mục/chương ban đầu."""
    terms = [term for term in normalize_text(query).split() if len(term) > 1]
    if not terms:
        return []
    ranked = []
    for item in get_candidates():
        content = " ".join(str(item.get(key, "")) for key in ["question_text", "topic", "lesson", "chapter", "source_name", "source_file"])
        normalized = normalize_text(content)
        score = sum(normalized.count(term) for term in terms)
        if score:
            ranked.append((score, item))
    return [item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:limit]]


def detect_source_classification(file_name):
    text = normalize_text(file_name)
    curriculum = load_grade12_curriculum()
    rules = [
        (("don dieu", "cuc tri"), 0, 0), (("gia tri lon nhat", "gia tri nho nhat"), 0, 1),
        (("tiem can",), 0, 2), (("khao sat", "do thi"), 0, 3), (("thuc tien",), 0, 4),
        (("vector",), 1, 0), (("he truc", "toa do trong khong gian"), 1, 1),
        (("phep toan vector",), 1, 2), (("khoang tu phan vi", "khoang bien thien"), 2, 0),
        (("phuong sai", "do lech chuan"), 2, 1), (("nguyen ham",), 3, 0),
        (("tich phan",), 3, 1), (("ung dung hinh hoc",), 3, 2),
        (("mat phang",), 4, 0), (("duong thang",), 4, 1), (("goc trong khong gian",), 4, 2),
        (("mat cau",), 4, 3), (("xac suat co dieu kien",), 5, 0), (("bayes", "xac suat toan phan"), 5, 1),
    ]
    for keywords, chapter_index, lesson_index in rules:
        if any(keyword in text for keyword in keywords):
            return curriculum[chapter_index]["chapter"], curriculum[chapter_index]["lessons"][lesson_index]
    return "Chưa phân loại", "Chưa phân loại"


def detect_source_grade(file_name):
    text = normalize_text(file_name)
    for grade, markers in {
        "Lớp 10": ("lop 10", "l10", "khoi 10"),
        "Lớp 11": ("lop 11", "l11", "khoi 11"),
        "Lớp 12": ("lop 12", "l12", "khoi 12", "thpt", "tn thpt"),
    }.items():
        if any(marker in text for marker in markers):
            return grade
    return "Chưa phân loại"


def detect_curriculum_classification(file_name, grade):
    """Tự xếp theo số Bài hoặc cụm từ tên bài khi tên tệp có đủ dữ kiện."""
    curriculum = load_curriculum(grade)
    text = normalize_text(file_name)
    number_match = re.search(r"bai\s*0*(\d{1,2})", text)
    if number_match:
        wanted = int(number_match.group(1))
        for chapter in curriculum:
            for lesson in chapter["lessons"]:
                if re.search(rf"bai\s+0*{wanted}(?:\D|$)", normalize_text(lesson)):
                    return chapter["chapter"], lesson
    for chapter in curriculum:
        for lesson in chapter["lessons"]:
            title = re.sub(r"^bai\s+\d+\.\s*", "", normalize_text(lesson))
            terms = [term for term in re.findall(r"[a-z]+", title) if len(term) >= 3 and term not in {"tap", "cuoi", "trong", "cua", "mot", "cac", "hai"}]
            if len(terms) >= 2 and all(term in text for term in terms[:2]):
                return chapter["chapter"], lesson
    return "Chưa phân loại", "Chưa phân loại"


def detect_exam_type(file_name):
    text = normalize_text(file_name)
    rules = [
        (("giua ky i", "giuaky i", "giua ky 1", "giuaky 1"), "Kiểm tra giữa kỳ I"),
        (("cuoi ky i", "cuoiky i", "cuoi ky 1", "cuoiky 1"), "Kiểm tra cuối kỳ I"),
        (("giua ky ii", "giuaky ii", "giua ky 2", "giuaky 2"), "Kiểm tra giữa kỳ II"),
        (("cuoi ky ii", "cuoiky ii", "cuoi ky 2", "cuoiky 2"), "Kiểm tra cuối kỳ II"),
        (("thi thu", "de thi thu", "thpt quoc gia", "tot nghiep thpt"), "Thi thử & đề THPT Quốc gia"),
        (("chuyen de",), "Ôn theo chuyên đề"),
    ]
    for markers, result in rules:
        if any(marker in text for marker in markers):
            return result
    return "Khác"


def detect_source_metadata(file_name):
    grade = detect_source_grade(file_name)
    exam_type = detect_exam_type(file_name)
    chapter, lesson = detect_curriculum_classification(file_name, grade) if grade != "Chưa phân loại" else ("Chưa phân loại", "Chưa phân loại")
    subtopic = Path(file_name).stem if exam_type == "Ôn theo chuyên đề" else ""
    return grade, chapter, lesson, exam_type, subtopic


def detect_document_kind(file_name):
    text = normalize_text(file_name)
    if "dung sai" in text:
        return "Ngân hàng câu đúng/sai"
    if "tra loi ngan" in text or "cau ngan" in text:
        return "Ngân hàng câu trả lời ngắn"
    if "tu luan" in text:
        return "Ngân hàng câu tự luận"
    if "trac nghiem" in text or "tnkq" in text:
        return "Ngân hàng trắc nghiệm nhiều lựa chọn"
    return "Bộ hỗn hợp / đề hoàn chỉnh"


def save_source(uploaded_file, school, exam_type, grade, chapter, lesson, document_kind, subtopic=""):
    safe_name = Path(uploaded_file.name).name.replace(" ", "_")
    stored_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_name}"
    (SOURCES_DIR / stored_name).write_bytes(uploaded_file.getvalue())
    auto_metadata = grade == "Tự nhận biết"
    detected = auto_metadata or chapter == "Tự nhận biết từ tên tệp"
    if auto_metadata:
        grade, chapter, lesson, exam_type, detected_subtopic = detect_source_metadata(uploaded_file.name)
        subtopic = subtopic.strip() or detected_subtopic
    elif detected and grade == "Lớp 12":
        chapter, lesson = detect_source_classification(uploaded_file.name)
    elif detected:
        chapter, lesson = "Chưa phân loại", "Chưa phân loại"
    if document_kind == "Tự nhận biết từ tên tệp":
        document_kind = detect_document_kind(uploaded_file.name)
    sources = get_sources()
    sources.append({
        "file_name": stored_name,
        "original_name": uploaded_file.name,
        "school": school.strip() or "Chưa ghi trường",
        "exam_type": exam_type,
        "grade": grade,
        "chapter": chapter,
        "lesson": lesson,
        "subtopic": subtopic.strip(),
        "document_kind": document_kind,
        "uploaded_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status": "Tự nhận biết từ tên tệp — chờ giáo viên xác nhận" if detected else "Chờ AI phân tích và giáo viên duyệt"
    })
    SOURCES_FILE.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")


def update_source_classification(file_name, chapter, lesson):
    sources = get_sources()
    changed = False
    for source in sources:
        if source["file_name"] == file_name:
            source["chapter"] = chapter
            source["lesson"] = lesson
            source["status"] = "Đã cập nhật phân loại — đã đồng bộ câu đã tách"
            changed = True
            break
    SOURCES_FILE.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    if not changed:
        return False

    # Không để danh sách nguồn và 350 câu đã tách mang hai nhãn khác nhau.
    candidates = get_candidates()
    for candidate in candidates:
        if candidate.get("source_file") == file_name:
            candidate["chapter"] = chapter
            candidate["lesson"] = lesson
            candidate["topic"] = infer_topic(candidate.get("question_text", ""), lesson)
            candidate["status"] = "Cần AI/giáo viên duyệt" if candidate.get("requires_visual_review") else "Đã gắn nhãn sơ bộ"
    CANDIDATES_FILE.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    # Biến thể đã duyệt dùng metadata riêng; đồng bộ để bộ lọc học sinh đổi ngay.
    variants = get_quiz_variants()
    for candidate_id, record in variants.items():
        candidate = next((item for item in candidates if item.get("candidate_id") == candidate_id), None)
        if candidate and candidate.get("source_file") == file_name:
            metadata = record.get("metadata") or {}
            metadata.update({"chapter": chapter, "lesson": lesson})
            record["metadata"] = metadata
    QUIZ_VARIANTS_FILE.write_text(json.dumps(variants, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def get_topics(bank):
    topics = set()
    for question in bank["multiple_choice"] + bank["short_answer"]:
        topics.add(question["topic"])
    for question in bank["true_false"]:
        topics.add(question["topic"])
    return sorted(topics)


def filter_bank_by_topic(bank, topic):
    if topic == "Tất cả chuyên đề":
        return bank
    return {
        "multiple_choice": [q for q in bank["multiple_choice"] if q["topic"] == topic],
        "true_false": [q for q in bank["true_false"] if q["topic"] == topic],
        "short_answer": [q for q in bank["short_answer"] if q["topic"] == topic],
    }


def exam_duration_minutes(study_goal):
    """Ôn từng chương/bài ngắn hơn, các đề kiểm tra giữ thời lượng chuẩn."""
    return 45 if study_goal in {"Ôn theo bài học", "Ôn theo chương"} else 90


def start_exam_timer(timer_key, minutes):
    timers = dict(st.session_state.get("exam_timers", {}))
    timer = timers.get(timer_key)
    if not timer:
        timer = {
            "deadline": datetime.now().timestamp() + minutes * 60,
            "minutes": minutes,
            "finished": False,
        }
        timers[timer_key] = timer
        st.session_state.exam_timers = timers
    return timer


def begin_exam_session(timer_key, minutes):
    """Chỉ bắt đầu tính giờ sau khi học sinh chủ động mở đề."""
    active_sessions = set(st.session_state.get("active_exam_sessions", []))
    if timer_key in active_sessions:
        start_exam_timer(timer_key, minutes)
        return True
    st.markdown(
        f"<div style='padding:16px 18px;border:1px solid #dfe7f5;border-radius:14px;background:rgba(255,255,255,.78);margin:8px 0 14px'>"
        f"<div style='font-weight:700;color:#243a88'>Sẵn sàng bắt đầu?</div>"
        f"<div style='color:#5d6a85;margin-top:4px'>Thời gian làm bài là <b>{minutes} phút</b> và chỉ bắt đầu đếm khi em bấm nút bên dưới.</div></div>",
        unsafe_allow_html=True,
    )
    safe_key = hashlib.sha1(timer_key.encode("utf-8")).hexdigest()[:12]
    if st.button("Bắt đầu làm đề", type="primary", key=f"start_exam_{safe_key}"):
        start_exam_timer(timer_key, minutes)
        active_sessions.add(timer_key)
        st.session_state.active_exam_sessions = list(active_sessions)
        st.rerun()
    return False


def clear_exam_timer(timer_key):
    timers = dict(st.session_state.get("exam_timers", {}))
    timers.pop(timer_key, None)
    st.session_state.exam_timers = timers
    active_sessions = set(st.session_state.get("active_exam_sessions", []))
    active_sessions.discard(timer_key)
    st.session_state.active_exam_sessions = list(active_sessions)
    if st.session_state.get("auto_submit_timer") == timer_key:
        st.session_state.pop("auto_submit_timer", None)


def consume_auto_submit(timer_key):
    if st.session_state.get("auto_submit_timer") != timer_key:
        return False
    st.session_state.pop("auto_submit_timer", None)
    return True


@st.fragment(run_every=1)
def render_exam_timer(timer_key):
    """Đồng hồ chạy độc lập để bài tự nộp ngay cả khi học sinh không bấm gì."""
    timer = (st.session_state.get("exam_timers") or {}).get(timer_key)
    if not timer:
        return
    remaining = max(0, int(timer.get("deadline", 0) - datetime.now().timestamp()))
    minutes, seconds = divmod(remaining, 60)
    urgent = remaining <= 300
    color = "#c13f57" if urgent else "#0b8e88"
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center;padding:11px 14px;"
        f"border:1px solid #dfe7f5;border-radius:12px;background:rgba(255,255,255,.78);margin:0 0 12px'>"
        f"<span style='color:#5d6a85;font-weight:600'>Thời gian còn lại</span>"
        f"<span style='font-size:1.25rem;font-weight:750;color:{color};font-variant-numeric:tabular-nums'>{minutes:02d}:{seconds:02d}</span></div>",
        unsafe_allow_html=True,
    )
    if remaining == 0 and not timer.get("finished"):
        timers = dict(st.session_state.get("exam_timers", {}))
        timers[timer_key] = {**timer, "finished": True}
        st.session_state.exam_timers = timers
        st.session_state.auto_submit_timer = timer_key
        st.rerun()


def render_local_ocr_panel():
    """Màn hình vận hành OCR cục bộ, độc lập hoàn toàn với Gemini."""
    st.divider()
    st.subheader("Quét dữ liệu bằng OCR cục bộ")
    st.caption("Dành cho máy có GPU mạnh. Quét ảnh câu hỏi trong Word và PDF scan; tài liệu luôn nằm trên máy, không gửi Gemini, Google hay dịch vụ khác.")
    status = get_local_ocr_status()
    state = status.get("state", "")
    if not local_ocr_is_installed():
        st.warning("Bộ OCR Pix2Text chưa được cài trên máy này. Không cần cài trên laptop hiện tại nếu chỉ dùng Gemini.")
        st.markdown("Khi ở máy mạnh, bấm đúp file `CAI_DAT_OCR_CUC_BO.bat` trong thư mục app một lần, chờ cài xong rồi mở lại app.")
        return
    st.success("Bộ OCR cục bộ đã sẵn sàng trên máy này.")
    if state == "running":
        st.info(
            f"OCR cục bộ đang chạy: đã xử lý {status.get('processed', 0)} mục (ảnh/PDF) "
            f"({status.get('succeeded', 0)} có kết quả, {status.get('failed', 0)} lỗi)."
        )
        st.caption(status.get("message", "Đang đọc ảnh và công thức…"))
        if st.button("Dừng OCR cục bộ sau ảnh đang xử lý"):
            LOCAL_OCR_STOP_FILE.write_text("stop", encoding="utf-8")
            st.info("Đã yêu cầu dừng an toàn. Tiến độ đã lưu sẽ được giữ nguyên.")
    else:
        if state in {"completed", "stopped", "failed"}:
            st.info(status.get("message", "Lượt OCR trước đã kết thúc."))
        st.warning("Kết quả OCR cục bộ luôn được gắn cờ cần giáo viên/AI kiểm tra trước khi dùng cho học sinh.")
        if st.button("Bắt đầu OCR cục bộ toàn kho (Word + PDF)", type="primary"):
            started, message = start_local_ocr()
            (st.success if started else st.error)(message)
            if started:
                st.rerun()


def render_exam(bank, title, caption):
    answers = {}
    total_items = len(bank.get("multiple_choice", [])) + sum(len(item.get("items", [])) for item in bank.get("true_false", [])) + len(bank.get("short_answer", []))
    st.markdown(f"<div style='padding:18px 20px;border-radius:15px;background:linear-gradient(110deg,#eef2ff,#e7fbf8);margin-bottom:14px'><div style='font-size:22px;font-weight:700;color:#243a88'>{html.escape(title)}</div><div style='margin-top:5px;color:#52627f'>{html.escape(caption)} · {total_items} ý cần hoàn thành</div></div>", unsafe_allow_html=True)

    if bank["multiple_choice"]:
        st.markdown("<div class='tm-section-label'>Phần I · Chọn một đáp án đúng</div>", unsafe_allow_html=True)
    for index, question in enumerate(bank["multiple_choice"], start=1):
        with st.container(border=True):
            st.markdown(f"<span class='tm-question-number'>{index}</span><span class='tm-question-title'>Chọn đáp án phù hợp nhất</span>", unsafe_allow_html=True)
            answers[question["id"]] = st.radio(
                math_display_text(question["question"]),
                options=[math_display_text(option) for option in question["options"]],
                index=None,
                key=question["id"],
            )

    if bank["true_false"]:
        st.markdown("<div class='tm-section-label'>Phần II · Đúng / Sai</div>", unsafe_allow_html=True)
        st.caption("Chọn Đúng hoặc Sai cho từng ý.")
    for index, question in enumerate(bank["true_false"], start=1):
        with st.container(border=True):
            st.markdown(f"<span class='tm-question-number'>{question.get('number', index)}</span><span class='tm-question-title'>Xét từng khẳng định</span>", unsafe_allow_html=True)
            st.markdown(math_display_text(question["context"]))
            for item in question["items"]:
                key = item["id"]
                answers[key] = st.radio(math_display_text(item["text"]), ["Đúng", "Sai"], index=None, horizontal=True, key=key)

    if bank["short_answer"]:
        st.markdown("<div class='tm-section-label'>Phần III · Trả lời ngắn</div>", unsafe_allow_html=True)
        st.caption("Nhập đáp số. Có thể dùng dấu phẩy hoặc dấu chấm cho số thập phân.")
    for index, question in enumerate(bank["short_answer"], start=1):
        with st.container(border=True):
            st.markdown(f"<span class='tm-question-number'>{index}</span><span class='tm-question-title'>Ghi đáp số</span>", unsafe_allow_html=True)
            answers[question["id"]] = st.text_input(math_display_text(question["question"]), key=question["id"])
    return answers


def normalized_number(value):
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def grade(bank, answers):
    details = []
    correct_count = 0
    total_items = 0
    topic_results = {}

    def add_result(label, topic, user_answer, correct_answer, solution, is_correct):
        nonlocal correct_count, total_items
        total_items += 1
        correct_count += int(is_correct)
        topic_results.setdefault(topic, [0, 0])
        topic_results[topic][0] += int(is_correct)
        topic_results[topic][1] += 1
        details.append({"label": label, "topic": topic, "user": user_answer or "Chưa trả lời", "answer": correct_answer, "solution": solution, "correct": is_correct})

    for question in bank["multiple_choice"]:
        add_result(question["id"], question["topic"], answers.get(question["id"]), question["answer"], question["solution"], answers.get(question["id"]) == math_display_text(question["answer"]))
    for question in bank["true_false"]:
        for item in question["items"]:
            add_result(item["id"], question["topic"], answers.get(item["id"]), item["answer"], item["solution"], answers.get(item["id"]) == item["answer"])
    for question in bank["short_answer"]:
        submitted = normalized_number(answers.get(question["id"]))
        expected = normalized_number(question["answer"])
        is_correct = submitted is not None and abs(submitted - expected) < 1e-8
        add_result(question["id"], question["topic"], answers.get(question["id"]), question["answer"], question["solution"], is_correct)
    return details, correct_count, total_items, topic_results


def show_results(bank, answers, student_name, username, student_grade, study_goal):
    details, correct_count, total_items, topic_results = grade(bank, answers)
    score = round(10 * correct_count / total_items, 2)
    save_attempt(student_name, username, student_grade, study_goal, score, correct_count, total_items)
    st.success(f"{student_name} ({student_grade}), bạn đạt {score}/10 — đúng {correct_count}/{total_items} ý được chấm.")
    st.subheader("Năng lực theo chuyên đề")
    columns = st.columns(len(topic_results))
    for column, (topic, result) in zip(columns, topic_results.items()):
        with column:
            rate = result[0] / result[1]
            st.metric(topic, f"{result[0]}/{result[1]}", f"{rate:.0%} chính xác")
    weak_topics = [topic for topic, result in topic_results.items() if result[0] / result[1] < 0.6]
    if weak_topics:
        st.info("Bài tiếp theo nên ưu tiên: " + ", ".join(weak_topics) + ".")
    else:
        st.info("Bạn đã nắm khá tốt đề mẫu. Hãy thử bài có mức vận dụng cao hơn.")
    st.subheader("Đáp án và cách giải")
    for detail in details:
        icon = "✅" if detail["correct"] else "❌"
        with st.expander(f"{icon} {detail['label']} — {detail['topic']}"):
            st.markdown(f"**Bạn chọn/nhập:** {math_display_text(detail['user'])}")
            st.markdown(f"**Đáp án:** {math_display_text(detail['answer'])}")
            st.markdown(f"**Cách giải:** {math_display_text(detail['solution'])}")


def render_approved_practice(grade=None, learning_scope="Luyện câu AI đã duyệt", chapter=None, lesson=None, subtopic=None):
    variants = get_quiz_variants()
    questions = []
    for candidate_id, item in variants.items():
        if item.get("status") != "Đã duyệt — sẵn sàng cho học sinh":
            continue
        try:
            metadata = item.get("metadata") or get_candidate_metadata(candidate_id)
            if grade and metadata.get("grade") != grade:
                continue
            if chapter and metadata.get("chapter") != chapter:
                continue
            if lesson and metadata.get("lesson") != lesson:
                continue
            if subtopic and metadata.get("subtopic") != subtopic:
                continue
            # Đề giữa/cuối kỳ và THPT được phép dùng mọi câu đã duyệt đúng khối
            # từ toàn kho, không giới hạn ở những file vốn mang nhãn "đề kiểm tra".
            questions.append((candidate_id, json.loads(item["variant"])))
        except (TypeError, json.JSONDecodeError):
            continue
    if not questions:
        st.info(f"Chưa có câu đã duyệt phù hợp với mục **{learning_scope}** của {grade or 'khối đang chọn'}. Khi bạn tải bộ đề mẫu đúng mục này và duyệt câu, app sẽ tự dùng chúng.")
        return
    by_id = dict(questions)
    topics = sorted({item.get("topic", "Toán THPT") for _, item in questions})
    recommended_topic = get_weak_topic_for_user(st.session_state.user["username"], topics)
    topic_options = ["Tự động chọn từ tất cả chủ đề"] + topics
    selected_topic = st.selectbox("Chủ đề cần luyện", topic_options, index=topic_options.index(recommended_topic) if recommended_topic else 0)
    if recommended_topic:
        st.info(f"App đang ưu tiên phần cần củng cố: {recommended_topic}.")
    available_ids = [candidate_id for candidate_id, item in questions if selected_topic == "Tự động chọn từ tất cả chủ đề" or item.get("topic", "Toán THPT") == selected_topic]
    count = st.number_input("Số câu trong lượt luyện", min_value=1, max_value=len(available_ids), value=min(5, len(available_ids)), step=1)
    set_key = f"practice_set::{grade}::{learning_scope}::{chapter}::{lesson}::{selected_topic}::{count}"
    if set_key not in st.session_state:
        st.session_state[set_key] = random.sample(available_ids, int(count))
    if st.button("Đổi sang lượt câu khác"):
        st.session_state[set_key] = random.sample(available_ids, int(count))
        st.rerun()
    active_questions = [(candidate_id, by_id[candidate_id]) for candidate_id in st.session_state[set_key] if candidate_id in by_id]
    timer_key = f"practice_timer::{st.session_state.user['username']}::{set_key}"
    duration_minutes = exam_duration_minutes(learning_scope)
    if not begin_exam_session(timer_key, duration_minutes):
        return
    render_exam_timer(timer_key)
    st.markdown(f"<div class='tm-section-label'>LƯỢT LUYỆN · {len(active_questions)} CÂU</div>", unsafe_allow_html=True)
    responses = {}
    for index, (candidate_id, question) in enumerate(active_questions, start=1):
        with st.container(border=True):
            st.markdown(f"<span class='tm-question-number'>{index}</span><span class='tm-question-title'>Câu luyện tập</span>", unsafe_allow_html=True)
            st.markdown(math_display_text(question.get("question", "")))
            st.caption(f"Chủ đề: {question.get('topic', 'Chưa xác định')} · Mức độ: {question.get('cognitive_level', 'Chưa xác định')}")
            if question.get("type") == "multiple_choice":
                responses[candidate_id] = st.radio("Chọn đáp án", question.get("options") or [], index=None, key=f"approved_answer_{candidate_id}")
            else:
                responses[candidate_id] = st.text_input("Nhập đáp án ngắn", key=f"approved_answer_{candidate_id}")
    timed_out = consume_auto_submit(timer_key)
    if timed_out or st.button("Nộp bài và xem lời giải", type="primary", key="submit_approved_practice"):
        if not timed_out and any(not response or not str(response).strip() for response in responses.values()):
            st.warning("Hãy trả lời đủ các câu trước khi nộp.")
        else:
            details, correct_count = [], 0
            for candidate_id, question in active_questions:
                response = responses[candidate_id]
                if question.get("type") == "multiple_choice":
                    correct_index = ord(str(question.get("correct_answer", ""))[:1].upper()) - ord("A")
                    correct_option = (question.get("options") or [])[correct_index] if 0 <= correct_index < len(question.get("options") or []) else ""
                    is_correct = response == correct_option
                else:
                    is_correct = normalize_text(response).strip() == normalize_text(str(question.get("correct_answer", ""))).strip()
                correct_count += int(is_correct)
                details.append((question, is_correct))
            user = st.session_state.user
            base_goal = learning_scope if learning_scope != "Luyện câu AI đã duyệt" else "Luyện câu AI đã duyệt"
            study_goal = f"{base_goal}: {selected_topic}" if selected_topic != "Tự động chọn từ tất cả chủ đề" else base_goal
            save_attempt(
                user["display_name"],
                user["username"],
                grade or "Chưa xác định",
                study_goal,
                round(10 * correct_count / len(active_questions), 2),
                correct_count,
                len(active_questions),
            )
            clear_exam_timer(timer_key)
            if timed_out:
                st.warning("Đã hết thời gian; app đã tự nộp các đáp án bạn đã làm.")
            st.success(f"Bạn đúng {correct_count}/{len(active_questions)} câu — {round(10 * correct_count / len(active_questions), 2)}/10.")
            for index, (question, is_correct) in enumerate(details, start=1):
                with st.expander(f"{'✅' if is_correct else '❌'} Câu {index}: đáp án và lời giải"):
                    st.markdown(f"**Đáp án tham khảo:** {math_display_text(question.get('correct_answer', 'Chưa có'))}")
                    st.markdown(math_display_text(question.get("solution", "Chưa có lời giải.")))


def calculate_learning_streak(rows):
    days = set()
    for row in rows:
        try:
            days.add(datetime.strptime(row[3], "%d/%m/%Y %H:%M").date())
        except (TypeError, ValueError):
            continue
    if not days:
        return 0
    day, streak = max(days), 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def render_dashboard(user):
    st.markdown(f"""<div style='padding:22px 24px;border-radius:18px;background:linear-gradient(105deg,#2e46a9,#109c95);color:white;margin-bottom:18px'>
    <div style='font-size:13px;opacity:.86'>TRINHMATH AI · HỌC TOÁN CÓ LỘ TRÌNH</div>
    <div style='font-size:28px;font-weight:700;margin-top:7px'>Chào {html.escape(user['display_name'])} 👋</div>
    <div style='margin-top:6px;opacity:.92'>Mỗi lượt học nhỏ đều giúp em đi xa hơn.</div></div>""", unsafe_allow_html=True)
    if user["role"] == "Giáo viên":
        sources, candidates, drafts = get_sources(), get_candidates(), get_question_drafts()
        variants = get_quiz_variants()
        ready = sum(1 for item in variants.values() if item.get("status") == "Đã duyệt — sẵn sàng cho học sinh")
        left, middle, right, last = st.columns(4)
        left.metric("Tài liệu nguồn", len(sources))
        middle.metric("Câu đã tách", len(candidates))
        right.metric("Bản nháp AI", len(drafts))
        last.metric("Câu sẵn sàng", ready)
        st.subheader("Việc cần làm tiếp theo")
        if not sources:
            st.info("Chưa có tài liệu. Vào Nhập kho đề để thêm Word/PDF.")
        else:
            pending = sum(1 for source in sources if source.get("analysis_status") not in {"done", "needs_ocr"})
            st.info(f"Kho hiện có {len(candidates)} câu đã tách. Có {pending} tệp mới chưa xử lý; các tệp đã xử lý sẽ không bị quét lại.")
            if ready < 5:
                st.warning("Kho câu cho học sinh còn ít. App vẫn chặn các câu chưa đủ dữ kiện để tránh đưa câu sai.")
            else:
                st.success("Đã có đủ câu để bắt đầu tạo các lượt luyện nhiều câu.")
        render_workflow_steps(
            [
                ("Nhập kho", "Lưu Word/PDF gốc, chọn cả thư mục nếu cần."),
                ("Kiểm duyệt", "Tách câu, kiểm tra công thức/hình và duyệt bản nháp."),
                ("Phát hành", "Chỉ câu đã duyệt mới đến được với học sinh."),
            ],
            0 if not sources else (2 if ready >= 5 else 1),
        )
    else:
        rows = get_attempts(user["username"])
        average = round(sum(float(row[4]) for row in rows) / len(rows), 1) if rows else 0
        left, middle, right = st.columns(3)
        left.metric("Lượt đã làm", len(rows))
        middle.metric("Điểm trung bình", f"{average}/10" if rows else "Chưa có")
        right.metric("Chuỗi học", f"{calculate_learning_streak(rows)} ngày")
        st.subheader("Hành trình học của em")
        if rows:
            recommendations = get_learning_recommendations(rows)
            weak_goal, weak_score, _ = recommendations[0]
            st.info(f"Gợi ý hôm nay: cùng bồi dưỡng **{weak_goal}** (điểm trung bình {weak_score}/10).")
        else:
            st.info("Bạn chưa có lượt làm nào. Hãy vào Làm bài để bắt đầu lưu tiến trình.")


def render_learning_journey(user):
    render_page_header("BẢN ĐỒ TIẾN BỘ", "Hành trình học của em", "Không phải bảng xếp hạng — đây là nơi để thấy em đã đi được bao xa và cần học gì tiếp.")
    rows = list(reversed(get_attempts(user["username"])))
    if not rows:
        st.info("Khi em hoàn thành lượt luyện đầu tiên, TrinhMath AI sẽ tạo bản đồ cần bồi dưỡng tại đây.")
        return
    scores = [float(row[4]) for row in rows]
    left, middle, right = st.columns(3)
    left.metric("Lượt đã hoàn thành", len(rows))
    middle.metric("Điểm gần nhất", f"{scores[-1]:.1f}/10")
    right.metric("Tiến bộ", f"{scores[-1] - scores[0]:+.1f}" if len(scores) > 1 else "Bắt đầu")
    st.subheader("Tiến trình của em")
    st.line_chart({"Điểm": scores}, height=220)
    recommendations = get_learning_recommendations(list(reversed(rows)))
    if recommendations:
        goal, score, _ = recommendations[0]
        st.info(f"Bước tiếp theo: ôn thêm **{goal}**. Đây là phần em đang cần thêm thời gian, không phải một nhãn cố định.")
    st.subheader("Những lượt học gần đây")
    st.dataframe([{"Ngày": row[3], "Nội dung": row[2] or "Luyện tập", "Điểm": f"{float(row[4]):.1f}/10", "Kết quả": f"{row[5]}/{row[6]}"} for row in rows[-10:]], use_container_width=True, hide_index=True)


def render_problem_solver():
    """Không gian giải một bài: bắt buộc xác nhận đề trước khi xin hỗ trợ AI."""
    render_page_header("GIẢI BÀI CÓ HƯỚNG DẪN", "Góc giải bài", "Đọc kỹ đề trước, rồi học từng bước. AI không nhận đề để giải cho đến khi em xác nhận lại nội dung.")
    input_mode = st.radio("Cách đưa đề vào", ["⌨ Nhập đề", "🖼️ Đọc từ ảnh"], horizontal=True, key="problem_input_mode")
    if input_mode == "🖼️ Đọc từ ảnh":
        uploaded_image = st.file_uploader("Chọn ảnh đề Toán", type=["png", "jpg", "jpeg", "webp"], key="problem_image_upload")
        st.caption("Ảnh chỉ được gửi đến Gemini khi em bấm “Đọc ảnh”. Sau đó em phải tự kiểm tra và xác nhận lại phần chữ/công thức trước khi xin lời giải.")
        if uploaded_image:
            image_data = uploaded_image.getvalue()
            st.image(image_data, caption="Xem lại ảnh trước khi nhận dạng", use_container_width=True)
            if st.button("Đọc ảnh để tạo bản nháp", type="secondary", key="read_problem_image"):
                api_key = st.session_state.get("gemini_api_key", "")
                if not api_key:
                    st.warning("Chưa có Gemini trong phiên này. Có thể chép đề bằng tay, hoặc giáo viên kết nối AI trước.")
                else:
                    image = {"name": uploaded_image.name, "mime_type": uploaded_image.type or "image/png", "data": image_data}
                    with st.spinner("Đang đọc ảnh thành văn bản và LaTeX; chưa yêu cầu AI giải bài..."):
                        ok, result = read_image_with_gemini(api_key, image)
                    parsed = normalize_ai_image_result(result) if ok else None
                    if not parsed:
                        st.error(result if not ok else "Không đọc được bản nháp từ ảnh. Hãy chép lại đề bằng tay hoặc thử ảnh rõ hơn.")
                    else:
                        extracted = str(parsed.get("extracted_text", "")).strip()
                        latex = str(parsed.get("latex", "")).strip()
                        st.session_state.problem_text_input = "\n".join(part for part in [extracted, f"${latex}$" if latex else ""] if part)
                        st.session_state.problem_ocr_notice = "Đây là bản nháp OCR. Hãy kiểm tra từng dấu, số mũ, phân số và công thức trước khi xác nhận."
                        st.rerun()
    if st.session_state.get("problem_ocr_notice"):
        st.warning(st.session_state.pop("problem_ocr_notice"))
    problem_text = st.text_area(
        "Đề bài cần kiểm tra",
        placeholder="Ví dụ: Giải phương trình $\\log_2(x-1)=3$.",
        height=180,
        key="problem_text_input",
    )
    review = build_problem_review(problem_text)
    if problem_text.strip():
        st.markdown("#### Bản xem trước")
        st.markdown(math_display_text(review["text"]))
        if review["review_points"]:
            st.warning("Hãy nhìn lại: " + ", ".join(review["review_points"]) + ".")
        else:
            st.caption("Không thấy ký hiệu OCR nhạy cảm phổ biến. Em vẫn nên kiểm tra dữ kiện, điều kiện và hình vẽ nếu có.")
        st.caption(f"Nhận diện sơ bộ: {review['topic_hint']}. Đây chỉ là gợi ý, chưa phải kết luận của AI.")
    if st.button("Xác nhận đề này để bắt đầu học", type="primary", disabled=not review["ready"], key="confirm_problem"):
        st.session_state.problem_session = {"text": review["text"], "topic_hint": review["topic_hint"], "confirmed_at": datetime.now().strftime("%d/%m/%Y %H:%M")}
        st.session_state.problem_tutor_messages = []
        st.success("Đề đã được xác nhận. Bây giờ em có thể chọn gợi ý hoặc nhờ Thầy AI kiểm tra từng bước.")

    session = st.session_state.get("problem_session")
    if not session:
        return
    st.divider()
    st.markdown("<div class='tm-section-label'>ĐỀ ĐÃ XÁC NHẬN</div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(math_display_text(session["text"]))
        st.caption(f"{session['topic_hint']} · Xác nhận lúc {session['confirmed_at']}")
    hint_col, step_col, solution_col = st.columns(3)
    messages = st.session_state.setdefault("problem_tutor_messages", [])
    with hint_col:
        if st.button("💡 Gợi ý", use_container_width=True, key="problem_hint"):
            hint_number = sum(1 for item in messages if item.get("kind") == "hint") + 1
            api_key = st.session_state.get("gemini_api_key", "")
            if api_key:
                with st.spinner("Thầy AI đang chuẩn bị đúng một gợi ý..."):
                    ok, response = ask_gemini_as_tutor(api_key, session["text"], "hint", hint_number=hint_number)
                content = response.get("response", "") if ok else response
                messages.append({"kind": "hint", "title": f"Gợi ý {hint_number}", "content": content, "ai": ok})
            else:
                messages.append({"kind": "hint", "title": f"Gợi ý {hint_number}", "content": local_study_hint(session["text"], hint_number), "ai": False})
    with step_col:
        st.caption("Nhập một bước em làm ở bên dưới rồi bấm kiểm tra.")
    with solution_col:
        if st.button("📖 Xem lời giải đầy đủ", use_container_width=True, key="problem_solution"):
            api_key = st.session_state.get("gemini_api_key", "")
            if not api_key:
                messages.append({"kind": "notice", "title": "Chưa thể tạo lời giải", "content": "Cần Gemini được kết nối trong phiên này. App không tự bịa lời giải khi chưa có AI hoặc bộ kiểm chứng.", "ai": False})
            else:
                with st.spinner("AI đang trình bày lời giải; kết quả cần được đọc và kiểm tra lại..."):
                    ok, response = ask_gemini_as_tutor(api_key, session["text"], "solution")
                content = response.get("response", "") if ok else response
                messages.append({"kind": "solution", "title": "Lời giải tham khảo" if ok else "Chưa tạo được lời giải", "content": content, "ai": ok})
    student_step = st.text_input("Bước em đang làm", placeholder="Ví dụ: Điều kiện là x > 1", key="problem_student_step")
    if st.button("👨‍🏫 Thầy AI kiểm tra bước này", type="secondary", disabled=not student_step.strip(), key="check_problem_step"):
        api_key = st.session_state.get("gemini_api_key", "")
        if not api_key:
            messages.append({"kind": "notice", "title": "Chưa đánh giá bước", "content": "Cần kết nối Gemini để nhận xét đúng/sai từng bước. Gợi ý cục bộ vẫn có thể dùng mà không gửi dữ liệu ra ngoài.", "ai": False})
        else:
            with st.spinner("Thầy AI đang đối chiếu bước em làm với đề đã xác nhận..."):
                ok, response = ask_gemini_as_tutor(api_key, session["text"], "step", student_step=student_step)
            content = response.get("response", "") if ok else response
            messages.append({"kind": "step", "title": "Nhận xét cho bước em làm" if ok else "Chưa đánh giá được bước", "content": content, "ai": ok})
    for message in messages:
        with st.expander(message["title"], expanded=message["kind"] != "solution"):
            st.markdown(math_display_text(message["content"]))
            if message.get("ai"):
                st.caption("Nội dung do AI hỗ trợ; với bài phức tạp hoặc hình học, hãy đối chiếu thêm với lời giải/giáo viên.")


def render_teacher_progress():
    """Tổng hợp ngắn gọn để giáo viên không rơi vào màn hình hành trình của học sinh."""
    render_page_header("THEO DÕI LỚP HỌC", "Tiến độ học sinh", "Xem lượt nộp, phần các em đang cần bồi dưỡng và những tín hiệu cần hỗ trợ thêm.")
    rows = get_attempts()
    if not rows:
        st.info("Chưa có lượt nộp bài nào. Khi học sinh làm đề, kết quả và gợi ý bồi dưỡng sẽ xuất hiện tại đây.")
        return
    students = sorted({str(row[0]) for row in rows if row[0]})
    average = round(sum(float(row[4] or 0) for row in rows) / len(rows), 1)
    left, middle, right = st.columns(3)
    left.metric("Học sinh có hoạt động", len(students))
    middle.metric("Lượt nộp đã lưu", len(rows))
    right.metric("Điểm trung bình", f"{average}/10")
    selected_student = st.selectbox("Xem chi tiết học sinh", ["Tất cả học sinh", *students])
    visible_rows = rows if selected_student == "Tất cả học sinh" else [row for row in rows if row[0] == selected_student]
    recommendations = get_learning_recommendations(visible_rows)
    if recommendations:
        goal, score, count = recommendations[0]
        st.info(f"Nội dung nên ưu tiên bồi dưỡng: **{goal}** — điểm trung bình {score}/10 qua {count} lượt.")
    st.subheader("Các lượt nộp gần đây")
    st.dataframe(
        [{"Học sinh": row[0], "Khối": row[1], "Nội dung": row[2] or "Luyện tập", "Nộp lúc": row[3], "Điểm": f"{float(row[4]):.1f}/10", "Kết quả": f"{row[5]}/{row[6]}"} for row in visible_rows[:50]],
        use_container_width=True,
        hide_index=True,
    )


def render_quality_control():
    """Màn hình kiểm định dành cho giáo viên, không làm thay đổi dữ liệu."""
    report = get_bank_quality_report()
    render_page_header("KIỂM ĐỊNH KHO ĐỀ", "An toàn & chất lượng", "Dữ liệu nào có thể dùng ngay và dữ liệu nào đang bị chặn an toàn để tránh xuất hiện trong bài làm của học sinh.")

    source_data = report["sources"]
    left, middle, right, last = st.columns(4)
    left.metric("Tệp đã tách", source_data["done"])
    middle.metric("PDF chờ OCR/AI", source_data["ocr"])
    right.metric("Tệp chưa xử lý", source_data["pending"])
    last.metric("Câu có thể dùng", report["variants"]["ready"])

    st.subheader("Hàng rào an toàn")
    safety_rows = [
        {"Hạng mục": "Câu ứng viên đã tách", "Số lượng": report["candidates_total"], "Ý nghĩa": "Dữ liệu thô, chưa đưa cho học sinh"},
        {"Hạng mục": "Câu cần kiểm tra hình/công thức", "Số lượng": report["candidates_visual_waiting"], "Ý nghĩa": "Đang bị chặn cho đến khi ảnh được AI/giáo viên xác nhận"},
        {"Hạng mục": "Ảnh AI đã đọc", "Số lượng": report["images"]["read"], "Ý nghĩa": "Đã lưu kết quả, không gửi lại ở lần quét sau"},
        {"Hạng mục": "Ảnh AI đọc lỗi", "Số lượng": report["images"]["failed"], "Ý nghĩa": "Được giữ lại và không tự quét lại"},
        {"Hạng mục": "Ảnh đủ tin cậy để ghép", "Số lượng": report["images"]["safe"], "Ý nghĩa": "Có thể dùng trong luồng tạo bản nháp AI"},
        {"Hạng mục": "Bản nháp AI hợp lệ", "Số lượng": report["drafts"]["usable"], "Ý nghĩa": "Có thể mở xem và duyệt"},
        {"Hạng mục": "Bản nháp thiếu dữ kiện", "Số lượng": report["drafts"]["blocked"], "Ý nghĩa": "Không dùng tự động"},
        {"Hạng mục": "Bản nháp AI không hoàn chỉnh", "Số lượng": report["drafts"]["invalid"], "Ý nghĩa": "Không dùng; có thể tạo lại"},
        {"Hạng mục": "Biến thể chờ duyệt", "Số lượng": report["variants"]["draft"], "Ý nghĩa": "Đã có cấu trúc chấm nhưng chưa phát hành"},
        {"Hạng mục": "Biến thể lỗi/thiếu dữ kiện", "Số lượng": report["variants"]["invalid"], "Ý nghĩa": "Không dùng tự động"},
        {"Hạng mục": "Biến thể đã sẵn sàng", "Số lượng": report["variants"]["ready"], "Ý nghĩa": "Được phép cho học sinh luyện và xuất đề"},
    ]
    st.dataframe(safety_rows, use_container_width=True, hide_index=True)

    st.subheader("Kiểm định liên kết hệ thống")
    audit = report["data_audit"]
    audit_rows = [
        {"Kiểm tra": "Tệp nguồn còn trên máy", "Lỗi": len(audit["missing_source_files"])},
        {"Kiểm tra": "Câu đã tách có tệp nguồn", "Lỗi": len(audit["orphan_candidates"])},
        {"Kiểm tra": "Biến thể có câu nguồn", "Lỗi": len(audit["orphan_variants"])},
        {"Kiểm tra": "Câu phát hành đủ cấu trúc chấm", "Lỗi": len(audit["invalid_ready"])},
        {"Kiểm tra": "Chương trình lớp 10–12", "Lỗi": len(report["curriculum_errors"])},
    ]
    st.dataframe(audit_rows, use_container_width=True, hide_index=True)
    if has_data_link_errors(audit) or report["curriculum_errors"]:
        st.warning("Phát hiện liên kết cần kiểm tra. App tiếp tục chặn dữ liệu không an toàn khỏi học sinh.")
    else:
        st.success("Kiểm định liên kết đạt: kho nguồn, câu hỏi, biến thể và chương trình học đang đồng bộ.")

    if report["visual_labels_to_upgrade"]:
        st.info(f"Có {report['visual_labels_to_upgrade']} nhãn hình theo phiên bản cũ. Có thể nâng cấp một lần để gắn hình theo đúng từng câu thay vì theo cả tệp.")
        if st.button("Nâng cấp nhãn hình theo từng câu"):
            with st.spinner("Đang đối chiếu vị trí hình với từng câu trong các tệp Word; dữ liệu gốc không bị thay đổi..."):
                updated, remaining = refresh_candidate_visual_flags()
            st.success(f"Đã cập nhật nhãn cho {updated} câu. Còn {remaining} câu sẽ được xử lý ở lần bấm tiếp theo để app luôn phản hồi nhanh.")
            st.rerun()

    if report["variants"]["ready"] < 5:
        st.warning("Kho phát hành cho học sinh còn ít. Đây là trạng thái an toàn: app không lấy câu Word/PDF thô hoặc câu AI chưa duyệt để lấp đầy đề.")
    else:
        st.success("Kho đã có đủ câu đã duyệt để tạo các lượt luyện nhiều câu mà không dùng dữ liệu chưa kiểm định.")

    st.download_button(
        "Tải báo cáo kiểm tra kho đề (JSON)",
        data=json.dumps(report, ensure_ascii=False, indent=2),
        file_name="bao_cao_kiem_tra_kho_de.json",
        mime="application/json",
    )
    st.caption(f"Báo cáo được tạo lúc {report['generated_at']}; không chứa khóa AI hoặc mật khẩu.")


def main():
    init_database()
    backup_data_once_per_day()
    refresh_question_draft_statuses()
    bank = load_bank()
    if "user" not in st.session_state:
        st.session_state.user = get_remembered_user()
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = load_saved_gemini_key() or os.getenv("GEMINI_API_KEY", "")
    if st.session_state.user is None:
        render_page_header("TRINHMATH AI", "Học Toán có lộ trình", "Một không gian học tập giúp mỗi em nhận ra mình cần bồi dưỡng điều gì tiếp theo.")
        login_tab, register_tab = st.tabs(["Đăng nhập", "Đăng ký"])
        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Tên đăng nhập")
                password = st.text_input("Mật khẩu", type="password")
                remember_login = st.checkbox("Ghi nhớ đăng nhập trên laptop này")
                login = st.form_submit_button("Đăng nhập", type="primary")
            if login:
                user = authenticate(username, password)
                if user:
                    st.session_state.user = user
                    if remember_login:
                        remember_user_on_this_laptop(user)
                    st.rerun()
                else:
                    st.error("Tên đăng nhập hoặc mật khẩu chưa đúng.")
        with register_tab:
            with st.form("register_form"):
                display_name = st.text_input("Họ và tên")
                new_username = st.text_input("Tên đăng nhập (không dấu, không khoảng trắng)")
                new_password = st.text_input("Mật khẩu", type="password")
                confirm_password = st.text_input("Nhập lại mật khẩu", type="password")
                role = st.selectbox("Bạn là", ["Học sinh", "Giáo viên"])
                register = st.form_submit_button("Tạo tài khoản")
            if register:
                if not display_name.strip() or len(new_username.strip()) < 3 or len(new_password) < 6:
                    st.warning("Hãy điền họ tên, tên đăng nhập ít nhất 3 ký tự và mật khẩu ít nhất 6 ký tự.")
                elif " " in new_username.strip() or new_password != confirm_password:
                    st.warning("Tên đăng nhập không có khoảng trắng và hai mật khẩu phải giống nhau.")
                else:
                    ok, message = create_user(new_username, display_name, new_password, role)
                    (st.success if ok else st.error)(message)
        return

    user = st.session_state.user
    st.sidebar.title("📐 TrinhMath AI")
    st.sidebar.caption("Học Toán có lộ trình")
    st.sidebar.caption(f"{user['display_name']} · {user['role']}")
    if st.sidebar.button("Đăng xuất"):
        st.session_state.user = None
        REMEMBERED_USER_FILE.unlink(missing_ok=True)
        st.rerun()
    if user["role"] == "Giáo viên":
        st.sidebar.divider()
        st.sidebar.caption("Công thức/hình trong Kho đề")
        st.sidebar.link_button("Mở Converter OCR cục bộ", "http://localhost:8503", use_container_width=True, help="Công cụ chỉ đọc các ảnh/công thức khó trong Kho đề; không cần tải lại Word/PDF.")
    page_labels = {"Trang chủ": "Tổng quan", "Góc giải bài": "Góc giải bài"}
    if user["role"] == "Giáo viên":
        page_labels.update({
            "Làm bài thử": "Làm bài",
            "Tiến độ học sinh": "Tiến độ học sinh",
            "Phòng biên soạn": "Ngân hàng đề",
            "Thêm tài liệu": "Nhập kho đề",
            "Hàng duyệt câu hỏi": "Phân tích kho đề",
            "An toàn & chất lượng": "Kiểm tra chất lượng",
            "Góc cùng suy nghĩ AI": "Góc cùng suy nghĩ AI",
        })
    else:
        page_labels.update({
            "Lượt học tiếp theo": "Làm bài",
            "Hành trình học": "Hành trình học",
            "Kết quả học tập": "Kết quả đã lưu",
        })
    page_label = st.sidebar.radio("Không gian của bạn", list(page_labels))
    page = page_labels[page_label]

    if page == "Tổng quan":
        render_dashboard(user)
    elif page == "Góc giải bài":
        render_problem_solver()
    elif page == "Tiến độ học sinh":
        render_teacher_progress()
    elif page == "Hành trình học":
        render_learning_journey(user)
    elif page == "Kiểm tra chất lượng":
        render_quality_control()
    elif page == "Làm bài":
        render_page_header("LƯỢT HỌC CÁ NHÂN", "Lượt học tiếp theo", "Học vừa sức hôm nay, tiến thêm một bước vào ngày mai.")
        profile_left, profile_right = st.columns(2)
        with profile_left:
            st.text_input("Học sinh", value=user["display_name"], disabled=True)
            student_name = user["display_name"]
        with profile_right:
            grade = st.selectbox("Khối lớp", ["Lớp 10", "Lớp 11", "Lớp 12"], index=2)
        if grade != "Lớp 12":
            st.info("Bạn có thể bắt đầu tải kho đề lớp này ngay. App sẽ chỉ lấy câu đúng khối lớp sau khi chúng được duyệt.")
        study_goal = st.selectbox("Hình thức học", ["Làm đề đầy đủ", *LEARNING_SCOPES, "Luyện câu AI đã duyệt"])
        if study_goal in LEARNING_SCOPES or study_goal == "Luyện câu AI đã duyệt":
            selected_chapter, selected_lesson, selected_subtopic = None, None, None
            if study_goal == "Ôn theo bài học":
                curriculum = load_curriculum(grade)
                source_chapters = sorted({item.get("chapter", "") for item in get_sources() if item.get("grade") == grade and item.get("chapter") not in {"", "Chưa phân loại"}})
                chapters = [item["chapter"] for item in curriculum] or source_chapters
                if not chapters:
                    st.info("Chưa có chương/bài của khối này trong kho. Bạn cứ tải các file đề mẫu lên, app sẽ tạo lựa chọn theo dữ liệu đã nhập.")
                else:
                    selected_chapter = st.selectbox("Chương cần ôn", chapters)
                    lessons = next((item["lessons"] for item in curriculum if item["chapter"] == selected_chapter), [])
                    if not lessons:
                        lessons = sorted({item.get("lesson", "") for item in get_sources() if item.get("grade") == grade and item.get("chapter") == selected_chapter and item.get("lesson") not in {"", "Chưa phân loại"}})
                    if lessons:
                        selected_lesson = st.selectbox("Bài học cần ôn", lessons)
            elif study_goal == "Ôn theo chuyên đề":
                specializations = sorted({item.get("subtopic", "").strip() for item in get_sources() if item.get("grade") == grade and item.get("subtopic", "").strip()})
                if specializations:
                    selected_subtopic = st.selectbox("Chuyên đề cần ôn", specializations)
                else:
                    st.info("Chưa có chuyên đề nào của khối này. Khi tải tài liệu, hãy điền ô “Tên chuyên đề” để app tự tạo lựa chọn tại đây.")
            elif study_goal in {"Kiểm tra giữa kỳ I", "Kiểm tra cuối kỳ I", "Kiểm tra giữa kỳ II", "Kiểm tra cuối kỳ II", "Thi thử & đề THPT Quốc gia"}:
                st.info("Đề này lấy các câu đã duyệt phù hợp với khối lớp từ toàn bộ kho, gồm cả câu thuộc bài học và chuyên đề. App không dùng câu thô/chưa duyệt.")
            render_approved_practice(grade, study_goal, selected_chapter, selected_lesson, selected_subtopic)
        else:
            active_bank = bank
            if study_goal == "Làm đề đầy đủ":
                exam_title = "Đề luyện TrinhMath AI"
                exam_caption = "Cấu trúc: 12 câu chọn đáp án · 4 câu đúng/sai (4 ý mỗi câu) · 6 câu trả lời ngắn"
            else:
                topic = st.selectbox("Chọn chuyên đề cần ôn", get_topics(bank))
                active_bank = filter_bank_by_topic(bank, topic)
                study_goal = f"Ôn chuyên đề: {topic}"
                exam_title = study_goal
                exam_caption = "Hệ thống chỉ hiển thị các câu hiện có thuộc chuyên đề này. Khi kho đề lớn hơn, app sẽ tự tạo một bài ôn đủ độ khó."
            timer_key = f"exam_timer::{user['username']}::{grade}::{study_goal}"
            duration_minutes = exam_duration_minutes(study_goal)
            if not begin_exam_session(timer_key, duration_minutes):
                return
            render_exam_timer(timer_key)
            answers = render_exam(active_bank, exam_title, exam_caption)
            timed_out = consume_auto_submit(timer_key)
            if timed_out or st.button("Nộp bài và chấm điểm", type="primary"):
                if timed_out:
                    st.warning("Đã hết thời gian; app đã tự nộp các đáp án bạn đã làm.")
                show_results(active_bank, answers, student_name, user["username"], grade, study_goal)
                clear_exam_timer(timer_key)
    elif page == "Kết quả đã lưu":
        render_page_header("NHÌN LẠI ĐỂ TIẾN BỘ", "Kết quả học tập", "Xem lại những lượt đã làm và các phần kiến thức cần được bồi dưỡng thêm.")
        rows = get_attempts() if user["role"] == "Giáo viên" else get_attempts(user["username"])
        if not rows:
            st.info("Chưa có lượt nộp bài nào.")
        else:
            st.dataframe(rows, column_config={0: "Học sinh", 1: "Khối lớp", 2: "Mục tiêu", 3: "Thời gian nộp", 4: "Điểm", 5: "Số ý đúng", 6: "Tổng số ý"}, use_container_width=True)
            recommendations = get_learning_recommendations(rows)
            st.subheader("Gợi ý ôn tập tự động")
            for goal, average_score, attempt_count in recommendations[:3]:
                if average_score < 6:
                    st.warning(f"Cần ưu tiên: **{goal}** — trung bình {average_score}/10 qua {attempt_count} lượt.")
                else:
                    st.success(f"Đang ổn: **{goal}** — trung bình {average_score}/10 qua {attempt_count} lượt.")
    elif page == "Ngân hàng đề":
        render_page_header("KHÔNG GIAN GIÁO VIÊN", "Phòng biên soạn", "Tìm, kiểm tra và xuất câu từ kho đã được duyệt. Tài liệu nguồn và tên trường luôn được giữ riêng khỏi đề học sinh.")
        render_workflow_steps(
            [
                ("Chọn dữ liệu", "Chỉ dùng câu đã duyệt trong kho."),
                ("Kiểm tra đề", "Rà cấu trúc, khối lớp và phạm vi ôn tập."),
                ("Xuất bản", "Tải đề hoặc đề kèm đáp án PDF."),
            ],
            1,
        )
        st.metric("Câu chọn đáp án", len(bank["multiple_choice"]))
        st.metric("Ý đúng/sai", sum(len(question["items"]) for question in bank["true_false"]))
        st.metric("Câu trả lời ngắn", len(bank["short_answer"]))
        st.divider()
        st.subheader("Tìm trong toàn bộ kho đề")
        st.caption("Tìm theo dạng/chủ đề, ví dụ: logarit, tích phân, vectơ, cực trị. Kết quả được rà trên tất cả tài liệu đã nhập.")
        bank_query = st.text_input("Nội dung cần tìm", placeholder="Ví dụ: logarit")
        if bank_query.strip():
            found = search_candidates_across_bank(bank_query)
            st.caption(f"Tìm thấy {len(found)} câu phù hợp nhất.")
            if found:
                st.dataframe([{
                    "Câu": item.get("question_number"),
                    "Bài học": item.get("lesson", "Chưa phân loại"),
                    "Chủ đề": item.get("topic", "Chưa phân loại"),
                    "Trích đề": item.get("question_text", "")[:180],
                    "Trạng thái": item.get("status", ""),
                } for item in found], use_container_width=True, hide_index=True)
            else:
                st.info("Chưa thấy từ khóa trong phần văn bản đã tách. Nếu đề nằm trong ảnh/công thức, hãy quét ảnh bằng Gemini trước.")
        st.divider()
        st.subheader("Xuất đề PDF")
        st.caption("Bản xuất không ghi trường hoặc nguồn tài liệu. Với đề giữa/cuối kỳ và THPT, app lấy mọi câu đã duyệt đúng khối từ toàn bộ kho.")
        export_grade, export_scope = st.columns(2)
        with export_grade:
            selected_export_grade = st.selectbox("Khối lớp của đề xuất", ["Lớp 10", "Lớp 11", "Lớp 12"], index=2)
        with export_scope:
            selected_export_scope = st.selectbox("Nhóm đề", ["Đề tổng hợp từ toàn kho", "Kiểm tra giữa kỳ I", "Kiểm tra cuối kỳ I", "Kiểm tra giữa kỳ II", "Kiểm tra cuối kỳ II", "Thi thử & đề THPT Quốc gia"])
        ready_export_bank = get_ready_export_bank_for_grade(selected_export_grade)
        ready_count = len(ready_export_bank["multiple_choice"]) + len(ready_export_bank["short_answer"])
        export_source = st.radio("Nguồn câu để xuất", ["Kho câu đã duyệt", "Đề mẫu kiểm tra giao diện"], horizontal=True)
        if export_source == "Kho câu đã duyệt":
            if not ready_count:
                st.warning(f"Kho {selected_export_grade} chưa có câu nào đã duyệt cho học sinh nên chưa thể xuất đề {selected_export_scope.lower()} thật.")
                active_export_bank = bank
            else:
                st.success(f"Đang dùng {ready_count} câu đã duyệt lớp {selected_export_grade} từ toàn kho cho {selected_export_scope.lower()}. Câu Word thô và câu AI chưa chắc chắn bị loại.")
                active_export_bank = ready_export_bank
        else:
            st.info("Đây chỉ là đề mẫu để kiểm tra bố cục PDF, không phải đề lấy từ kho của bạn.")
            active_export_bank = bank
        export_left, export_right = st.columns(2)
        with export_left:
            st.download_button("Tải đề PDF", data=build_exam_pdf(active_export_bank), file_name="de_luyen_toan_thpt.pdf", mime="application/pdf", type="primary")
        with export_right:
            st.download_button("Tải đề kèm đáp án PDF", data=build_exam_pdf(active_export_bank, include_answers=True), file_name="de_luyen_toan_thpt_kem_dap_an.pdf", mime="application/pdf")
    elif page == "Nhập kho đề":
        render_page_header("KHO DỮ LIỆU GỐC", "Thêm tài liệu", "Tải Word hoặc PDF gốc lên. App lưu nguyên bản để giữ công thức, hình vẽ và cách giải trước khi phân tích.")
        render_workflow_steps(
            [
                ("Tải tài liệu", "Chọn nhiều tệp hoặc toàn bộ thư mục."),
                ("Gắn bối cảnh", "Có thể để app tự nhận biết, hoặc chọn bài/chuyên đề."),
                ("Đưa vào hàng duyệt", "Tệp gốc được giữ nguyên trước khi AI xử lý."),
            ],
            0,
        )
        st.download_button("Tải mẫu gắn nhãn tài liệu", data=UPLOAD_TEMPLATE_TEXT, file_name="mau_gan_nhan_tai_lieu_toan.txt", mime="text/plain")
        if "upload_version" not in st.session_state:
            st.session_state.upload_version = 0
        if "upload_notice" in st.session_state:
            st.success(st.session_state.pop("upload_notice"))
        # Hai lựa chọn này nằm ngoài form để đổi khối là danh sách chương/bài đổi ngay.
        source_grade = st.selectbox("Khối lớp của đề", ["Tự nhận biết", "Lớp 10", "Lớp 11", "Lớp 12"], index=0, key="source_grade_selector")
        catalog_mode = st.radio(
            "Tài liệu này dùng để làm gì?",
            ["Tự động nhận biết cho cả lô", "Ôn theo chương / bài học", "Ôn theo chuyên đề", "Đề kiểm tra / thi thử", "Bộ hỗn hợp"],
            horizontal=True,
            key="catalog_mode_selector",
        )
        # Các trường phụ thuộc cũng ở ngoài form: đổi Chương là Bài học đổi ngay.
        curriculum = load_curriculum(source_grade)
        chapter_names = [item["chapter"] for item in curriculum]
        chapter, lesson, subtopic, exam_type = "Chưa phân loại", "Chưa phân loại", "", "Khác"
        if catalog_mode == "Ôn theo chương / bài học":
            chapter = st.selectbox("Chương", chapter_names, key=f"chapter_selector_{source_grade}")
            selected_lessons = next(item["lessons"] for item in curriculum if item["chapter"] == chapter)
            lesson = st.selectbox("Bài học", selected_lessons, key=f"lesson_selector_{source_grade}_{chapter}")
            exam_type = "Ôn theo bài học"
        elif catalog_mode == "Ôn theo chuyên đề":
            subtopic = st.text_input("Tên chuyên đề", placeholder="Ví dụ: Tích phân vận dụng; Oxyz; Lôgarit", key=f"subtopic_selector_{source_grade}")
            chapter = "Khác"
            exam_type = "Ôn theo chuyên đề"
        elif catalog_mode == "Đề kiểm tra / thi thử":
            exam_type = st.selectbox(
                "Loại đề",
                ["Kiểm tra giữa kỳ I", "Kiểm tra cuối kỳ I", "Kiểm tra giữa kỳ II", "Kiểm tra cuối kỳ II", "Thi thử & đề THPT Quốc gia"],
                key=f"exam_type_selector_{source_grade}",
            )
        elif catalog_mode == "Bộ hỗn hợp":
            st.caption("Bộ hỗn hợp: app sẽ phân loại sâu sau khi phân tích.")
        else:
            chapter, lesson, exam_type = "Tự nhận biết từ tên tệp", "Chưa phân loại", "Tự nhận biết"
            st.info("Bạn chỉ cần chọn nhiều file hoặc cả thư mục. App sẽ tự đọc tên tệp để xếp khối, bài/chương và loại đề; phần không chắc sẽ để AI kiểm tra sau.")
        with st.form("source_upload"):
            upload_mode = st.radio("Cách chọn tài liệu", ["Chọn nhiều file", "Chọn cả thư mục"], horizontal=True)
            if upload_mode == "Chọn cả thư mục":
                uploaded_files = st.file_uploader("Chọn thư mục chứa các tệp Word/PDF", type=["docx", "pdf"], accept_multiple_files="directory", key=f"folder_upload_{st.session_state.upload_version}")
            else:
                uploaded_files = st.file_uploader("Chọn một hoặc nhiều tệp Word/PDF", type=["docx", "pdf"], accept_multiple_files=True, key=f"files_upload_{st.session_state.upload_version}")
            school = st.text_input("Trường / nguồn đề", placeholder="Có thể để trống")
            document_kind = st.selectbox(
                "Loại tài liệu",
                ["Tự nhận biết từ tên tệp", "Ngân hàng trắc nghiệm nhiều lựa chọn", "Ngân hàng câu đúng/sai", "Ngân hàng câu trả lời ngắn", "Ngân hàng câu tự luận", "Bộ hỗn hợp / đề hoàn chỉnh"]
            )
            submitted = st.form_submit_button("Lưu vào kho đề", type="primary")
        if submitted:
            if not uploaded_files:
                st.warning("Hãy chọn ít nhất một tệp Word hoặc PDF.")
            elif catalog_mode == "Ôn theo chuyên đề" and not subtopic.strip():
                st.warning("Hãy nhập tên chuyên đề để sau này học sinh có thể chọn đúng chuyên đề này.")
            else:
                for uploaded_file in uploaded_files:
                    save_source(uploaded_file, school, exam_type, source_grade, chapter, lesson, document_kind, subtopic)
                st.session_state.upload_notice = f"Đã lưu {len(uploaded_files)} tài liệu gốc vào kho đề. Chúng đang chờ AI phân tích và giáo viên duyệt."
                st.session_state.upload_version += 1
                st.rerun()

        sources = get_sources()
        st.subheader("Tài liệu đã lưu")
        if not sources:
            st.info("Chưa có tài liệu nào. Hãy bắt đầu bằng một hoặc nhiều tệp Word/PDF; app sẽ giữ nguyên tệp gốc để bạn kiểm tra lại bất cứ lúc nào.")
        else:
            st.dataframe(sources, column_config={"original_name": "Tên tệp", "document_kind": "Loại tài liệu", "chapter": "Chương", "lesson": "Bài học", "subtopic": "Chuyên đề", "school": "Trường / nguồn", "exam_type": "Loại đề", "grade": "Khối lớp", "uploaded_at": "Đã lưu lúc", "status": "Trạng thái", "file_name": None}, use_container_width=True)
            with st.expander("Sửa chương / bài của tệp đã lưu"):
                source_map = {f"{item['original_name']} · {item['uploaded_at']}": item for item in sources}
                selected_label = st.selectbox("Chọn tệp cần sửa", list(source_map))
                selected_source = source_map[selected_label]
                curriculum = load_curriculum(selected_source.get("grade", "Lớp 12"))
                chapter_names = [item["chapter"] for item in curriculum]
                current_chapter_index = (["Chưa phân loại"] + chapter_names + ["Khác"]).index(selected_source.get("chapter", "Chưa phân loại")) if selected_source.get("chapter", "Chưa phân loại") in ["Chưa phân loại"] + chapter_names + ["Khác"] else 0
                corrected_chapter = st.selectbox("Chương đúng", ["Chưa phân loại"] + chapter_names + ["Khác"], index=current_chapter_index, key="corrected_chapter")
                corrected_lessons = next((item["lessons"] for item in curriculum if item["chapter"] == corrected_chapter), [])
                lesson_options = ["Chưa phân loại"] + corrected_lessons + ["Khác"]
                current_lesson_index = lesson_options.index(selected_source.get("lesson", "Chưa phân loại")) if selected_source.get("lesson", "Chưa phân loại") in lesson_options else 0
                corrected_lesson = st.selectbox("Bài học đúng", lesson_options, index=current_lesson_index, key="corrected_lesson")
                if st.button("Lưu phân loại mới"):
                    if update_source_classification(selected_source["file_name"], corrected_chapter, corrected_lesson):
                        st.success("Đã cập nhật và đồng bộ ngay vào các câu đã tách cùng biến thể liên quan.")
                    else:
                        st.error("Không tìm thấy tệp cần cập nhật.")
    elif page == "Phân tích kho đề":
        render_page_header("QUY TRÌNH KIỂM DUYỆT", "Hàng duyệt câu hỏi", "Tách câu ứng viên từ Word/PDF, giữ nguyên tệp gốc và chặn những nội dung có hình hoặc công thức cần kiểm tra kỹ.")
        render_workflow_steps(
            [
                ("Đọc tệp", "Tách văn bản trực tiếp từ Word/PDF có chữ."),
                ("Đối chiếu", "Chặn hình và công thức chưa đủ chắc chắn."),
                ("Duyệt phát hành", "Chỉ bản nháp hợp lệ mới được đưa vào ngân hàng."),
            ],
            1,
        )
        pending_count = sum(1 for source in get_sources() if source.get("analysis_status") not in {"done", "needs_ocr"})
        st.caption(f"Có {pending_count} tệp mới/chưa xử lý. Các tệp đã tách sẽ không bị quét lại.")
        if st.button("Phân tích tài liệu mới", type="primary"):
            with st.spinner("Đang đọc Word và PDF có chữ trong kho đề..."):
                results, total, processed = analyze_question_sources()
            st.success(f"Đã xử lý {processed} tệp mới, hiện có {total} câu ứng viên. PDF dạng ảnh/quét được đưa vào hàng chờ OCR/AI, không bị đọc đoán.")
            st.dataframe(results, column_config={0: "Tệp", 1: "Câu ứng viên", 2: "Trạng thái"}, use_container_width=True)
        apply_visual_quality_gate()
        candidates = get_candidates()
        st.metric("Câu ứng viên đã tách", len(candidates))
        if candidates:
            if "visual_attach_notice" in st.session_state:
                st.success(st.session_state.pop("visual_attach_notice"))
            if st.button("Ghép các hình AI đủ tin cậy vào câu hỏi"):
                with st.spinner("Đang đối chiếu vị trí ảnh và câu hỏi trong Word..."):
                    attached, total_candidates = attach_safe_visuals_to_candidates()
                st.session_state.visual_attach_notice = f"Đã ghép {attached} kết quả hình đủ tin cậy vào {total_candidates} câu. Ảnh cần duyệt bị loại khỏi luồng tự động."
                st.rerun()
            classified_count = sum(1 for item in candidates if item.get("status") == "Đã gắn nhãn sơ bộ")
            st.caption(f"Đã gắn nhãn sơ bộ: {classified_count}/{len(candidates)} câu. Công thức/hình vẫn được giữ trong tệp gốc để kiểm tra kỹ.")
            if st.button("Tự phân loại sơ bộ các câu Word", type="primary"):
                with st.spinner("Đang gắn nhãn chương, chủ đề, loại câu và mức độ..."):
                    candidates = classify_candidates_locally()
                approved = sum(1 for item in candidates if item.get("status") == "Đã gắn nhãn sơ bộ")
                review = len(candidates) - approved
                st.success(f"Đã gắn nhãn sơ bộ {approved} câu; {review} câu có hình/cấu trúc đặc biệt cần AI hoặc giáo viên duyệt.")
                st.rerun()
            st.caption("Đây là phân loại sơ bộ tại máy theo nội dung và tên tệp. Những câu chưa rõ sẽ được chuyển sang Góc cùng suy nghĩ AI hoặc hàng giáo viên duyệt, không bị app đoán bừa.")
            preview = [{
                "Câu": item.get("question_number"),
                "Chương": item.get("chapter"),
                "Bài học": item.get("lesson"),
                "Chủ đề": item.get("topic", "Chưa phân loại"),
                "Loại câu": item.get("question_type", "Chưa phân loại"),
                "Mức độ": item.get("cognitive_level", "Chưa phân loại"),
                "Trạng thái hình": item.get("visual_status", "Chưa ghép"),
                "Trạng thái": item.get("status"),
                "Cần xem hình": "Có" if item.get("requires_visual_review") else "Không",
            } for item in candidates[:50]]
            st.dataframe(preview, use_container_width=True, hide_index=True)
            text_only_candidates = [item for item in candidates if item.get("eligible_for_text_pipeline")]
            blocked_visual = len(candidates) - len(text_only_candidates)
            st.info(f"Có {len(text_only_candidates)} câu đủ điều kiện xử lý an toàn trước; {blocked_visual} câu còn lại bị chặn vì ảnh chưa được xác minh hoặc là dữ kiện bắt buộc.")
            if st.button("Phân loại trước các câu không dùng ảnh", type="primary"):
                with st.spinner("Đang gắn nhãn cho các câu văn bản thuần..."):
                    candidates = classify_candidates_locally(only_text=True)
                ready_text = sum(1 for item in candidates if item.get("eligible_for_text_pipeline") and item.get("status") == "Đã gắn nhãn sơ bộ")
                st.success(f"Đã xử lý nhóm câu không dùng ảnh. Có {ready_text}/{len(text_only_candidates)} câu đã được nhận diện sơ bộ.")
                st.rerun()
            draftable = text_only_candidates
            if draftable:
                st.divider()
                st.subheader("Tạo bản nháp từ nhóm không dùng ảnh")
                st.caption("AI chỉ đọc câu chữ và công thức đã trích trực tiếp từ Word. Không gửi ảnh và không chờ luồng OCR. Bản nháp luôn cần duyệt trước khi dùng.")
                existing_drafts = get_question_drafts()
                pending_drafts = [item for item in draftable if item["candidate_id"] not in existing_drafts]
                if pending_drafts and st.session_state.gemini_api_key:
                    batch_size = st.number_input("Số câu AI xử lý trong một lượt", min_value=1, max_value=min(5, len(pending_drafts)), value=min(3, len(pending_drafts)), step=1)
                    if st.button("Tạo bản nháp tự động theo lô", type="primary"):
                        created, skipped = 0, 0
                        progress = st.progress(0, text="Gemini đang đọc từng câu; câu thiếu dữ kiện sẽ được gắn cờ, không tự dùng.")
                        for index, item in enumerate(pending_drafts[:int(batch_size)], start=1):
                            ok, draft = create_question_draft_with_gemini(st.session_state.gemini_api_key, item)
                            if ok:
                                save_question_draft(item["candidate_id"], draft)
                                created += 1
                            else:
                                skipped += 1
                            progress.progress(index / int(batch_size), text=f"Đã xử lý {index}/{int(batch_size)} câu.")
                        progress.empty()
                        st.success(f"Đã lưu {created} bản nháp; {skipped} câu chưa đọc được hoặc cần thử lại. Chưa câu nào được đưa cho học sinh.")
                        st.rerun()
                candidate_map = {f"Câu {item.get('question_number')} · {item.get('lesson', 'Chưa phân loại')} · {item.get('source_name', '')}": item for item in draftable}
                draft_label = st.selectbox("Chọn khung câu để tạo thử", list(candidate_map), key="draft_candidate")
                chosen_candidate = candidate_map[draft_label]
                if not st.session_state.gemini_api_key:
                    st.info("Hãy vào Góc cùng suy nghĩ AI để lưu khóa Gemini trước khi tạo bản nháp.")
                elif st.button("Tạo bản nháp câu hỏi bằng Gemini", type="primary"):
                    with st.spinner("Gemini đang ghép văn bản, công thức và hình của một câu..."):
                        ok, draft = create_question_draft_with_gemini(st.session_state.gemini_api_key, chosen_candidate)
                    if ok:
                        save_question_draft(chosen_candidate["candidate_id"], draft)
                        st.success("Đã lưu bản nháp cục bộ. Câu này chưa được dùng cho học sinh.")
                        show_question_draft_preview(draft)
                    else:
                        st.error(draft)
            drafts = get_question_drafts()
            if drafts:
                st.divider()
                st.subheader("Duyệt bản nháp AI")
                draft_candidates = {candidate_id: record for candidate_id, record in drafts.items()}
                selected_draft_id = st.selectbox("Chọn bản nháp", list(draft_candidates), key="review_draft")
                selected_draft = draft_candidates[selected_draft_id]
                st.caption(f"Trạng thái: {selected_draft.get('status')} · Tạo lúc: {selected_draft.get('created_at')}")
                parsed_draft = show_question_draft_preview(selected_draft.get("draft", ""))
                if selected_draft.get("status") != "Đã duyệt và đưa vào ngân hàng":
                    if parsed_draft and parsed_draft.get("usable") and not parsed_draft.get("requires_teacher_review"):
                        if st.button("Duyệt và đưa câu này vào ngân hàng"):
                            ok, message = approve_question_draft(selected_draft_id)
                            (st.success if ok else st.warning)(message)
                    else:
                        st.info("Câu này thiếu dữ kiện hoặc cần xem lại, nên app không hiện nút duyệt.")
                else:
                    st.success("Câu này đã ở trong ngân hàng đã duyệt.")
            approved_questions = get_approved_questions()
            if approved_questions:
                st.divider()
                st.subheader("Chuyển câu đã duyệt sang trắc nghiệm")
                st.caption("Học sinh chỉ nhận biến thể trắc nghiệm/trả lời ngắn sau khi bạn duyệt bản xem trước.")
                approved_map = {f"Câu đã duyệt {index + 1} · {item['question'].get('topic', 'Toán THPT')}": item for index, item in enumerate(approved_questions)}
                approved_label = st.selectbox("Chọn câu nguồn", list(approved_map), key="approved_to_quiz")
                approved_question = approved_map[approved_label]
                quiz_type = st.radio("Dạng đưa cho học sinh", ["Trắc nghiệm 4 lựa chọn", "Trả lời ngắn"], horizontal=True, key="quiz_type")
                if not st.session_state.gemini_api_key:
                    st.info("Hãy lưu khóa Gemini trong Góc cùng suy nghĩ AI trước.")
                elif st.button("Tạo bản nháp trắc nghiệm", type="primary"):
                    desired_type = "multiple_choice" if quiz_type == "Trắc nghiệm 4 lựa chọn" else "short_answer"
                    with st.spinner("Gemini đang chuyển câu đã duyệt sang dạng có thể chấm tự động..."):
                        ok, variant = create_quiz_variant_with_gemini(st.session_state.gemini_api_key, approved_question, desired_type)
                    if ok:
                        save_quiz_variant(approved_question["candidate_id"], variant)
                        st.success("Đã tạo bản nháp trắc nghiệm. Bản nháp chưa xuất hiện cho học sinh.")
                        try:
                            preview = json.loads(variant)
                            st.markdown(preview.get("question", ""))
                            for index, option in enumerate(preview.get("options") or []):
                                st.markdown(f"{chr(65 + index)}. {option}")
                            with st.expander("Xem đáp án và lời giải"):
                                st.markdown(f"**Đáp án:** {preview.get('correct_answer', '')}")
                                st.markdown(preview.get("solution", ""))
                        except json.JSONDecodeError:
                            st.warning("AI trả về bản nháp cần kiểm tra lại.")
                    else:
                        st.error(variant)
                variants = get_quiz_variants()
                if variants:
                    st.markdown("#### Duyệt biến thể trước khi cho học sinh làm")
                    variant_id = st.selectbox("Chọn biến thể", list(variants), key="review_quiz_variant")
                    variant_record = variants[variant_id]
                    try:
                        variant_preview = json.loads(variant_record["variant"])
                        st.markdown(variant_preview.get("question", ""))
                        for index, option in enumerate(variant_preview.get("options") or []):
                            st.markdown(f"{chr(65 + index)}. {option}")
                        with st.expander("Đáp án và lời giải của biến thể"):
                            st.markdown(f"**Đáp án:** {variant_preview.get('correct_answer', '')}")
                            st.markdown(variant_preview.get("solution", ""))
                        if variant_record.get("status") != "Đã duyệt — sẵn sàng cho học sinh":
                            if st.button("Duyệt biến thể này cho học sinh"):
                                ok, message = approve_quiz_variant(variant_id)
                                (st.success if ok else st.warning)(message)
                        else:
                            st.success("Biến thể này đã sẵn sàng cho học sinh.")
                    except (TypeError, json.JSONDecodeError):
                        st.warning("Không đọc được bản nháp biến thể này.")
        analyses = apply_image_safety_policy()
        if analyses:
            st.divider()
            st.subheader("Kết quả AI đã đọc từ ảnh")
            st.caption(f"Đã lưu {len(analyses)} ảnh. Các ảnh này sẽ không bị gửi lại Gemini khi bạn quét tiếp.")
            analysis_rows = []
            for item in analyses.values():
                result = normalize_ai_image_result(item.get("result", "")) or {}
                analysis_rows.append({
                    "Tệp nguồn": item["source_file"],
                    "Ảnh": item["image_name"].split("/")[-1],
                    "Chủ đề AI": result.get("math_topic", "Chưa đọc được"),
                    "Loại nội dung": result.get("question_type", "Chưa đọc được"),
                    # Keep a single Arrow-compatible column type even when an
                    # unread image uses the "—" placeholder.
                    "Độ tin cậy": str(result.get("confidence", "—")),
                    "Cần duyệt": "Có" if result.get("needs_teacher_review") else "Không",
                    "Quy tắc dùng": item.get("usage_status", "Không dùng tự động — cần duyệt"),
                    "Đã đọc lúc": item["analyzed_at"],
                })
            st.dataframe(analysis_rows, use_container_width=True, hide_index=True)
    else:
        render_page_header("TRỢ LÝ RIÊNG CỦA KHO ĐỀ", "Góc cùng suy nghĩ AI", "Dùng AI để đọc công thức/hình, phân loại sâu và trích đáp án từ tài liệu của bạn.")
        render_workflow_steps(
            [
                ("Kết nối", "Lưu khóa Gemini cho phiên làm việc trên máy này."),
                ("Đọc dữ liệu", "Ưu tiên Word/PDF có chữ; chỉ dùng ảnh khi cần."),
                ("Giáo viên quyết định", "Kết quả AI phải qua hàng duyệt trước khi phát hành."),
            ],
            1,
        )
        st.warning("Không dán khóa API vào chat. Khóa chỉ được giữ trong phiên app đang mở trên laptop này và không được ghi vào kho đề.")
        with st.form("gemini_connection"):
            key = st.text_input("Gemini API key", value=st.session_state.gemini_api_key, type="password", help="Khóa thường bắt đầu bằng AIza hoặc AQ.")
            save_on_laptop = st.checkbox("Lưu khóa đã mã hóa trên laptop này", value=True)
            saved = st.form_submit_button("Lưu khóa cho phiên làm việc này", type="primary")
        if saved:
            if len(key.strip()) < 20:
                st.error("Khóa có vẻ chưa đúng. Hãy kiểm tra lại trong Google AI Studio.")
            else:
                st.session_state.gemini_api_key = key.strip()
                if save_on_laptop:
                    if save_gemini_key_for_this_laptop(key.strip()):
                        st.success("Đã lưu khóa đã mã hóa trên laptop này. Bạn không cần dán lại sau khi tải trang.")
                    else:
                        st.warning("Đã dùng khóa trong phiên này nhưng Windows chưa lưu mã hóa được. Bạn vẫn có thể dùng app ngay.")
                else:
                    GEMINI_KEY_FILE.unlink(missing_ok=True)
                    st.success("Đã dùng khóa cho phiên hiện tại, nhưng không lưu lại sau khi tắt/tải lại app.")
        if st.session_state.gemini_api_key:
            st.success("Gemini đã sẵn sàng để thử nghiệm trong phiên hiện tại.")
            if GEMINI_KEY_FILE.exists() and st.button("Xóa khóa đã lưu khỏi laptop này"):
                GEMINI_KEY_FILE.unlink(missing_ok=True)
                st.session_state.gemini_api_key = ""
                st.success("Đã xóa khóa đã lưu. Tải lại trang để kết thúc phiên đang dùng khóa.")
            if st.button("Kiểm tra kết nối Gemini"):
                with st.spinner("Đang gửi một câu kiểm tra ngắn đến Gemini..."):
                    ok, message = test_gemini_connection(st.session_state.gemini_api_key)
                if ok:
                    st.success(f"Kết nối thành công: {message}")
                    st.info("Kết nối đã ổn. Bước sau sẽ là cho AI đọc thử một tệp Word có công thức, rồi hiển thị kết quả để bạn duyệt trước khi chạy cả kho.")
                else:
                    st.error(message)
            st.divider()
            st.subheader("Thử đọc một ảnh công thức từ Word")
            st.caption("Chỉ ảnh bạn chọn được gửi tới Gemini. Kết quả thử chưa được lưu vào ngân hàng câu hỏi.")
            word_sources = [source for source in get_sources() if source["file_name"].lower().endswith(".docx")]
            if not word_sources:
                st.info("Chưa có tệp Word nào trong kho đề để thử đọc.")
            else:
                source_map = {f"{source['original_name']} · {source['uploaded_at']}": source for source in word_sources}
                source_label = st.selectbox("Chọn tệp Word để thử", list(source_map), key="gemini_source_trial")
                selected_source = source_map[source_label]
                source_path = SOURCES_DIR / selected_source["file_name"]
                question_image_map = map_docx_question_images(source_path)
                question_image_names = {name for values in question_image_map.values() for name in values}
                images, image_error = get_docx_images(source_path, question_image_names or None)
                if image_error:
                    st.error(image_error)
                elif not images:
                    st.warning("Tệp này chưa có ảnh gắn được vào khung câu để thử.")
                else:
                    if question_image_names:
                        st.caption(f"Đang chỉ hiển thị {len(images)} ảnh thuộc khung câu hỏi; ảnh WMF đã được chuyển cục bộ sang PNG.")
                    image_map = {f"Ảnh {index + 1}: {item['name'].split('/')[-1]} ({len(item['data']) // 1024} KB)": item for index, item in enumerate(images)}
                    image_label = st.selectbox("Chọn một ảnh", list(image_map), key="gemini_image_trial")
                    selected_image = image_map[image_label]
                    st.image(selected_image["data"], caption="Ảnh sẽ gửi cho Gemini khi bạn bấm nút bên dưới.", use_container_width=True)
                    if st.button("Cho Gemini đọc ảnh này", type="primary"):
                        with st.spinner("Gemini đang đọc ảnh và chuyển công thức sang LaTeX..."):
                            ok, result = read_image_with_gemini(st.session_state.gemini_api_key, selected_image)
                        if ok:
                            save_image_analysis(selected_source["file_name"], selected_image, result)
                            st.success("Đã nhận kết quả thử. Hãy so sánh với ảnh gốc trước khi duyệt.")
                            st.code(result, language="json")
                        else:
                            st.error(result)
                    st.divider()
                    analyses = get_image_analyses()
                    remaining = [image for image in images if f"{selected_source['file_name']}::{image['name']}" not in analyses]
                    st.subheader("Quét thử theo nhóm nhỏ")
                    st.caption(f"Tệp này có {len(images)} ảnh PNG/JPEG/WebP; đã lưu kết quả {len(images) - len(remaining)} ảnh. App chỉ gửi các ảnh chưa đọc.")
                    if not remaining:
                        st.success("Các ảnh hỗ trợ trong tệp này đã có kết quả. Bạn có thể chọn tệp khác hoặc chuyển sang bước ghép ảnh vào câu hỏi.")
                        batch_size = 0
                    elif len(remaining) == 1:
                        batch_size = 1
                        st.caption("Còn 1 ảnh chưa đọc, app sẽ quét đúng ảnh này khi bạn bấm nút.")
                    else:
                        max_batch = min(5, len(remaining))
                        batch_size = st.slider("Số ảnh muốn thử lần này", 1, max_batch, min(3, max_batch), key="gemini_batch_size")
                    if remaining and st.button("Quét nhóm ảnh thử", type="secondary"):
                        progress = st.progress(0, text="Đang chuẩn bị...")
                        successes, failures = 0, []
                        for index, image in enumerate(remaining[:batch_size], start=1):
                            progress.progress((index - 1) / batch_size, text=f"Đang đọc ảnh {index}/{batch_size}: {image['name'].split('/')[-1]}")
                            ok, result = read_image_with_gemini(st.session_state.gemini_api_key, image)
                            if ok:
                                save_image_analysis(selected_source["file_name"], image, result)
                                successes += 1
                            else:
                                save_image_analysis(selected_source["file_name"], image, result, read_ok=False)
                                failures.append(f"{image['name'].split('/')[-1]}: {result}")
                        progress.progress(1.0, text="Đã xong nhóm thử.")
                        if successes:
                            st.success(f"Đã đọc và lưu {successes} ảnh. Các lần sau ảnh này sẽ không bị gửi lại Gemini.")
                        if failures:
                            st.warning("Một số ảnh chưa đọc được:\n\n" + "\n\n".join(failures))
            st.divider()
            st.subheader("Tự quét công thức còn thiếu trong toàn kho")
            unread_total = count_unread_question_images()
            first_batch = get_unread_question_images(limit=3)
            scan_status = get_ai_scan_status()
            scan_state = scan_status.get("state", "")
            if scan_state in {"starting", "running", "waiting_quota"}:
                render_live_ai_scan_status()
            elif not first_batch:
                st.success("Không còn ảnh câu hỏi nào chưa quét trong các tệp Word hiện có.")
            else:
                progress_text = f"Còn {unread_total} ảnh câu hỏi chưa quét." if unread_total is not None else "Kho cũ chưa có chỉ mục ảnh theo từng câu; app đang quét theo từng nhóm nhỏ an toàn."
                st.caption(
                    f"{progress_text} Bấm một lần để app tự quét liên tục từng nhóm 3 ảnh. "
                    "Tiến độ được lưu sau từng ảnh; có thể đóng trang web nhưng laptop phải còn bật."
                )
                if scan_state == "paused_quota":
                    st.warning(scan_status.get("message", "Gemini đang tạm hết quota."))
                elif scan_state in {"stopped", "failed", "completed"}:
                    st.info(scan_status.get("message", "Lượt quét trước đã kết thúc."))
                button_label = "Tiếp tục quét nền tự động" if scan_state == "paused_quota" else "Bắt đầu quét nền tự động toàn kho"
                if st.button(button_label, type="primary"):
                    started, message = start_background_ai_scan(st.session_state.gemini_api_key)
                    if started:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("Sau khi tạo khóa mới trong Google AI Studio, dán khóa vào ô trên rồi bấm Lưu.")
        render_local_ocr_panel()


if __name__ == "__main__":
    main()
