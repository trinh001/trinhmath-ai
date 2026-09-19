"""Dịch vụ thuần lưu kết quả Math Verifier vào biến thể nháp có audit trail."""

from __future__ import annotations

import copy
import json
from datetime import datetime
from typing import Any

from math_verifier import verify_math_claim


RELEASED_STATUS = "Đã duyệt — sẵn sàng cho học sinh"


def attach_math_verification(
    record: object,
    claim: object,
    checked_at: str | None = None,
) -> tuple[bool, dict[str, Any] | None, dict[str, Any]]:
    """Tạo phiên bản record mới có audit trail, không thay đổi đầu vào.

    Chỉ variant nháp mới nhận kết quả. Variant đã phát hành không được âm thầm
    sửa, kể cả chỉ là thêm metadata, để giáo viên có lịch sử phát hành ổn định.
    """
    if not isinstance(record, dict):
        return False, None, {"status": "INCONCLUSIVE", "message": "Không tìm thấy bản nháp biến thể hợp lệ."}
    if record.get("status") == RELEASED_STATUS:
        return False, None, {
            "status": "UNSUPPORTED",
            "message": "Biến thể đã phát hành không được sửa âm thầm. Hãy tạo bản nháp dẫn xuất mới để kiểm tra lại.",
        }
    try:
        variant = json.loads(record.get("variant", ""))
    except (TypeError, json.JSONDecodeError):
        return False, None, {"status": "INCONCLUSIVE", "message": "Bản nháp biến thể không đúng định dạng JSON."}
    if not isinstance(variant, dict):
        return False, None, {"status": "INCONCLUSIVE", "message": "Bản nháp biến thể không có dữ liệu câu hỏi hợp lệ."}
    if not isinstance(claim, dict):
        return False, None, {"status": "INCONCLUSIVE", "message": "Dữ liệu xác minh phải có cấu trúc rõ ràng."}

    result = verify_math_claim(claim)
    timestamp = checked_at or datetime.now().strftime("%d/%m/%Y %H:%M")
    audit_entry = {
        "checked_at": timestamp,
        "claim": copy.deepcopy(claim),
        "result": copy.deepcopy(result),
        "provenance": "teacher_structured_math_verification",
    }
    updated_variant = dict(variant)
    updated_variant["math_verification"] = {
        **copy.deepcopy(result),
        "checked_at": timestamp,
        "claim": copy.deepcopy(claim),
        "provenance": "teacher_structured_math_verification",
    }
    updated_record = dict(record)
    history = list(record.get("math_verification_history") or [])
    history.append(audit_entry)
    updated_record["math_verification_history"] = history
    updated_record["math_verification_updated_at"] = timestamp
    updated_record["variant"] = json.dumps(updated_variant, ensure_ascii=False)
    return True, updated_record, result
