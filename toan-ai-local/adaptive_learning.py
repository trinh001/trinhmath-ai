"""Các quy tắc thuần dữ liệu cho lộ trình luyện tập thích ứng."""

from __future__ import annotations

import random
import unicodedata


def _normalize_text(value: object) -> str:
    text = str(value or "")
    return "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")


def build_next_practice_recommendation(topic_results: object) -> dict[str, object]:
    """Tạo gợi ý dựa theo từng chủ đề, không suy diễn vượt dữ liệu lượt làm."""
    topic_rows = []
    for topic, result in (topic_results or {}).items():
        try:
            correct, total = int(result[0]), int(result[1])
        except (IndexError, TypeError, ValueError):
            continue
        if total <= 0:
            continue
        topic_rows.append({
            "topic": str(topic or "Dạng câu vừa làm"),
            "correct": correct,
            "total": total,
            "accuracy": correct / total,
        })

    if not topic_rows:
        return {
            "stage": "Chưa đủ dữ liệu",
            "focus_topics": [],
            "message": "Làm thêm một lượt có câu được phân theo chủ đề để app tạo lộ trình chính xác hơn.",
            "next_step": "Bắt đầu bằng một lượt luyện ngắn 3 câu.",
            "difficulty": "Nhận biết",
        }

    topic_rows.sort(key=lambda item: (item["accuracy"], -item["total"], item["topic"]))
    weakest = topic_rows[0]
    weak_topics = [item for item in topic_rows if item["accuracy"] < 0.6]
    consolidation_topics = [item for item in topic_rows if item["accuracy"] < 0.8]
    if weak_topics:
        focus_topics = [item["topic"] for item in weak_topics[:2]]
        return {
            "stage": "Củng cố nền tảng",
            "focus_topics": focus_topics,
            "message": (
                f"Ưu tiên **{', '.join(focus_topics)}**. Em đang đúng "
                f"{weakest['correct']}/{weakest['total']} ý ở phần này; hãy làm 3 câu cùng dạng từ cơ bản đến thông hiểu."
            ),
            "next_step": "Nếu làm đúng ít nhất 2/3 câu, chuyển sang 1 câu cùng chủ đề có mức cao hơn.",
            "difficulty": "Nhận biết → Thông hiểu",
        }
    if consolidation_topics:
        focus_topics = [item["topic"] for item in consolidation_topics[:2]]
        return {
            "stage": "Luyện chắc",
            "focus_topics": focus_topics,
            "message": (
                f"Em đã có nền ở **{', '.join(focus_topics)}**, nhưng cần thêm một lượt ngắn để chắc kiến thức "
                f"({weakest['correct']}/{weakest['total']} ý đúng ở phần thấp nhất)."
            ),
            "next_step": "Làm 2–3 câu có thay đổi dữ kiện; sau khi đúng ổn định, thử một câu vận dụng.",
            "difficulty": "Thông hiểu",
        }
    return {
        "stage": "Mở rộng",
        "focus_topics": [weakest["topic"]],
        "message": (
            f"Em đã làm tốt các chủ đề trong lượt này. Để tiến bộ tiếp, hãy giữ **{weakest['topic']}** "
            "làm mốc và thử một dạng khác hoặc một câu khó hơn."
        ),
        "next_step": "Làm 1–2 câu vận dụng; nếu sai, quay lại một câu thông hiểu để xác định đúng điểm hổng.",
        "difficulty": "Thông hiểu → Vận dụng",
    }


def cognitive_level_band(level: object) -> str:
    """Nhóm mức độ nhận thức để chọn câu, nhưng không thay đổi nhãn hiển thị."""
    text = _normalize_text(level)
    if "van dung cao" in text:
        return "stretch"
    if "van dung" in text:
        return "advanced"
    if "thong hieu" in text:
        return "standard"
    if "nhan biet" in text:
        return "foundation"
    return "unknown"


def practice_difficulty_plan(accuracy: float | None = None) -> dict[str, object]:
    """Quy tắc tăng/giảm độ khó rõ ràng, có fallback cho kho nhỏ."""
    if accuracy is None:
        return {
            "code": "balanced",
            "preferred_bands": ["foundation", "standard", "advanced", "stretch"],
            "label": "Lượt khởi động cân bằng",
            "message": "Chưa có đủ lịch sử ở chủ đề này, nên app chọn câu theo mức cân bằng để xác định điểm bắt đầu.",
        }
    if accuracy < 0.6:
        return {
            "code": "foundation",
            "preferred_bands": ["foundation", "standard"],
            "label": "Củng cố nền tảng",
            "message": "App ưu tiên câu nhận biết và thông hiểu trước; làm chắc rồi mới tăng độ khó.",
        }
    if accuracy < 0.8:
        return {
            "code": "standard",
            "preferred_bands": ["standard", "foundation", "advanced"],
            "label": "Luyện chắc",
            "message": "App ưu tiên câu thông hiểu, có thể xen một câu nền tảng hoặc vận dụng nhẹ.",
        }
    return {
        "code": "advanced",
        "preferred_bands": ["advanced", "stretch", "standard"],
        "label": "Mở rộng độ khó",
        "message": "App ưu tiên câu vận dụng hoặc vận dụng cao; nếu kho chưa có, sẽ dùng câu thông hiểu đã duyệt thay thế.",
    }


def select_adaptive_question_ids(questions: list[tuple[str, dict]], count: int, plan: dict) -> list[str]:
    """Chọn theo độ ưu tiên; chỉ fallback khi kho chưa đủ câu đúng mức."""
    preferred_bands = list(plan.get("preferred_bands") or [])
    rank = {band: index for index, band in enumerate(preferred_bands)}
    groups: dict[int, list[str]] = {}
    for candidate_id, question in questions:
        band = cognitive_level_band(question.get("cognitive_level"))
        groups.setdefault(rank.get(band, len(rank)), []).append(candidate_id)
    selected: list[str] = []
    for group_rank in sorted(groups):
        group = groups[group_rank]
        take = min(int(count) - len(selected), len(group))
        if take > 0:
            selected.extend(random.sample(group, take))
        if len(selected) >= int(count):
            break
    return selected
