"""Tiện ích cục bộ cho không gian giải bài của TrinhMath AI.

Mô-đun này không gọi mạng và không lưu đề vào kho câu hỏi. Nó chỉ chuẩn hóa,
đánh dấu chỗ dễ OCR sai và tạo hướng học ban đầu để giao diện luôn yêu cầu
người dùng xác nhận đề trước khi chuyển sang AI.
"""

from __future__ import annotations

import re
import unicodedata


OCR_SENSITIVE_SYMBOLS = {
    "-": "dấu âm / phép trừ",
    "+": "dấu cộng",
    "/": "phân số hoặc phép chia",
    "√": "dấu căn",
    "^": "số mũ",
    "∫": "tích phân",
    "lim": "giới hạn",
    "log": "lôgarit",
    "→": "vectơ hoặc giới hạn",
    "∈": "ký hiệu thuộc tập hợp",
}


def normalize_problem_text(value: str) -> str:
    """Giữ nguyên nội dung toán, chỉ sửa khoảng trắng gây nhiễu khi nhập/OCR."""
    text = unicodedata.normalize("NFC", str(value or "")).replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def find_ocr_review_points(text: str) -> list[str]:
    """Những ký hiệu cần người dùng nhìn lại trước khi dùng AI."""
    lowered = text.lower()
    points = [label for symbol, label in OCR_SENSITIVE_SYMBOLS.items() if symbol.lower() in lowered]
    if re.search(r"\b[0-9a-zA-Z]\s*[²³⁴⁵⁶⁷⁸⁹]", text):
        points.append("chỉ số mũ Unicode")
    if re.search(r"\b[Il1]\b", text):
        points.append("ký tự I / l / 1 dễ nhầm")
    return list(dict.fromkeys(points))


def infer_local_topic(text: str) -> str:
    """Nhận diện thô để gợi ý cách học, không dùng làm nhãn chính thức của kho đề."""
    normalized = "".join(
        char for char in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")
    rules = [
        (("log", "logarit", "mu"), "Hàm số mũ và lôgarit"),
        (("tich phan", "∫", "nguyen ham"), "Nguyên hàm và tích phân"),
        (("dao ham", "cuc tri", "don dieu"), "Ứng dụng đạo hàm"),
        (("luong giac", "sin", "cos", "tan", "cot"), "Lượng giác"),
        (("vector", "vectơ", "toạ do", "toa do"), "Vectơ và tọa độ"),
        (("xac suat", "bayes"), "Xác suất"),
        (("gioi han", "lim"), "Giới hạn"),
        (("phuong trinh", "bat phuong trinh"), "Phương trình và bất phương trình"),
    ]
    return next((topic for words, topic in rules if any(word in normalized for word in words)), "Chưa xác định — cần phân tích")


def local_study_hint(text: str, hint_number: int = 1) -> str:
    """Gợi ý an toàn khi chưa có AI; cố ý không trả lời thay học sinh."""
    topic = infer_local_topic(text)
    hints = {
        "Hàm số mũ và lôgarit": [
            "Em hãy ghi điều kiện xác định trước, đặc biệt với biểu thức có logarit.",
            "Sau đó thử đưa hai vế về cùng cơ số hoặc đặt ẩn phụ phù hợp.",
        ],
        "Nguyên hàm và tích phân": [
            "Em thử nhận diện dạng hàm dưới dấu tích phân và công thức nguyên hàm gần nhất.",
            "Nếu là tích phân xác định, chỉ thay cận sau khi đã tìm được nguyên hàm.",
        ],
        "Ứng dụng đạo hàm": [
            "Em hãy xác định tập xác định, rồi tính đạo hàm trước khi lập bảng xét dấu.",
            "Từ dấu của đạo hàm, em mới kết luận về đơn điệu hoặc cực trị.",
        ],
        "Lượng giác": [
            "Em thử đưa các biểu thức về sin, cos hoặc một công thức lượng giác quen thuộc.",
            "Sau khi biến đổi, nhớ đối chiếu nghiệm với điều kiện ban đầu.",
        ],
    }
    selected = hints.get(topic, [
        "Em hãy gạch chân dữ kiện, yêu cầu cần tìm và điều kiện xác định của bài.",
        "Thử gọi tên dạng toán, rồi chọn công thức hoặc định lý phù hợp trước khi biến đổi.",
    ])
    return selected[min(max(hint_number - 1, 0), len(selected) - 1)]


def build_problem_review(text: str) -> dict:
    clean = normalize_problem_text(text)
    points = find_ocr_review_points(clean)
    return {
        "text": clean,
        "topic_hint": infer_local_topic(clean),
        "review_points": points,
        "ready": len(clean) >= 8,
    }
