"""Dữ liệu đối chiếu nguồn cho màn giáo viên duyệt bản nháp.

Module này chỉ tổng hợp dữ liệu đã có trong kho: không đọc tệp, không gọi AI và
không thay đổi candidate hay kết quả OCR.  Nhờ vậy giao diện có thể cho giáo
viên xem đúng câu nguồn, tình trạng từng mảnh ảnh và các cờ chất lượng trước
khi mở khóa một bản nháp cục bộ.
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping

from source_quality import source_content_quality_issues
from local_review_workflow import LOCAL_DRAFT_PROVENANCE, review_decision_text


def _unique_strings(values: object) -> list[str]:
    """Giữ thứ tự ảnh gốc, bỏ phần tử rỗng hoặc bị lặp."""
    result: list[str] = []
    for value in values if isinstance(values, list) else []:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _normalized_text(value: object) -> str:
    """Chuẩn hóa ghi chú OCR để nhận diện lỗi nguồn, không suy diễn nội dung."""
    text = str(value or "")
    return "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")


def _parsed_image_result(record: object) -> Mapping:
    if not isinstance(record, Mapping):
        return {}
    result = record.get("result")
    try:
        parsed = json.loads(result) if isinstance(result, str) else result
    except (TypeError, json.JSONDecodeError):
        parsed = None
    if isinstance(parsed, list):
        parsed = next((item for item in parsed if isinstance(item, Mapping)), None)
    return parsed if isinstance(parsed, Mapping) else {}


def _legacy_formula_damage_issue(record: object, image_name: str) -> str | None:
    """Chỉ nhận diện lỗi ảnh MathType đã được OCR xác nhận là không thể đọc.

    Không coi mọi ảnh chưa đủ tin cậy là lỗi vĩnh viễn: ảnh đó vẫn có thể cần
    đọc lại hoặc giáo viên kiểm tra. Cờ này chỉ áp dụng khi lượt đọc hoàn tất,
    confidence bằng 0 và ghi chú mô tả ảnh chồng nét/méo/lỗi/không thể đọc.
    """
    if not isinstance(record, Mapping) or record.get("read_status") != "Đã đọc":
        return None
    parsed = _parsed_image_result(record)
    try:
        confidence = float(parsed.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0
    note = _normalized_text(parsed.get("needs_teacher_review"))
    fatal_markers = ("khong the doc", "bi loi", "chong cheo", "bop meo", "overlapping")
    if confidence <= 0 and any(marker in note for marker in fatal_markers):
        return (
            f"Mảnh MathType `{str(image_name).split('/')[-1]}` bị lỗi/chồng nét trong nguồn; "
            "không thể đọc chắc chắn công thức."
        )
    return None


def _image_read_summary(record: object) -> dict[str, object]:
    if not isinstance(record, Mapping):
        return {
            "read_status": "Chưa đọc",
            "usage_status": "Chưa có kết quả đọc ảnh",
            "safe_to_use": False,
            "confidence": None,
            "needs_teacher_review": True,
        }

    parsed = _parsed_image_result(record)

    confidence = parsed.get("confidence")
    try:
        confidence = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence = None
    return {
        "read_status": str(record.get("read_status") or "Chưa đọc"),
        "usage_status": str(record.get("usage_status") or "Không dùng tự động — cần duyệt"),
        "safe_to_use": bool(record.get("safe_to_use")),
        "confidence": confidence,
        "needs_teacher_review": parsed.get("needs_teacher_review", True),
    }


def build_source_review_snapshot(
    candidate: object,
    image_analyses: object,
    manual_formula_overrides: object = None,
) -> dict[str, object]:
    """Tạo snapshot bất biến cho một lần giáo viên đối chiếu nguồn.

    ``visuals`` luôn đủ mọi mảnh ảnh mà candidate tham chiếu, kể cả khi OCR
    chưa đọc chúng. Điều đó giúp giao diện không tạo cảm giác sai rằng câu chỉ
    dùng chữ khi thực tế vẫn có ảnh/công thức cần xem.
    """
    if not isinstance(candidate, Mapping):
        return {
            "valid": False,
            "source_issues": ["Candidate không đúng định dạng."],
            "visuals": [],
            "requires_visual_review": True,
        }

    analyses = image_analyses if isinstance(image_analyses, Mapping) else {}
    overrides = manual_formula_overrides if isinstance(manual_formula_overrides, Mapping) else {}
    source_file = str(candidate.get("source_file") or "")
    ordinary = _unique_strings(candidate.get("source_image_names"))
    legacy = _unique_strings(candidate.get("legacy_math_image_names"))
    names = _unique_strings([*ordinary, *legacy])
    visuals = []
    fatal_formula_issues = []
    for image_name in names:
        analysis_id = f"{source_file}::{image_name}"
        analysis = analyses.get(analysis_id)
        summary = _image_read_summary(analysis)
        fatal_issue = None
        if image_name in legacy and not str(overrides.get(image_name) or "").strip():
            fatal_issue = _legacy_formula_damage_issue(analysis, image_name)
            if fatal_issue:
                fatal_formula_issues.append(fatal_issue)
        visuals.append({
            "image_name": image_name,
            "kind": "MathType/công thức cũ" if image_name in legacy else "Ảnh nhúng",
            "fatal_source_issue": fatal_issue,
            **summary,
        })

    return {
        "valid": True,
        "source_file": source_file,
        "source_name": str(candidate.get("source_name") or source_file or "Không rõ nguồn"),
        "question_number": str(candidate.get("question_number") or "?"),
        "question_text": str(candidate.get("question_text") or "").strip(),
        "solution_text": str(candidate.get("solution_text") or "").strip(),
        "source_issues": [*source_content_quality_issues(dict(candidate)), *fatal_formula_issues],
        "fatal_formula_issues": fatal_formula_issues,
        "visuals": visuals,
        "requires_visual_review": bool(candidate.get("requires_visual_review") or candidate.get("has_legacy_mathtype") or names),
    }


def build_local_review_queue(
    drafts: object,
    candidates: object,
    image_analyses: object,
    manual_formula_overrides: object = None,
) -> dict[str, object]:
    """Phân luồng nháp cục bộ để giáo viên biết câu nào cần làm trước.

    Đây là bảng điều phối thuần dữ liệu.  Nó không thay `requires_teacher_review`,
    không suy ra đúng/sai Toán và không tự chuyển bất kỳ câu nào sang ngân hàng.
    """
    draft_records = drafts if isinstance(drafts, Mapping) else {}
    candidate_map = {
        str(item.get("candidate_id") or ""): item
        for item in candidates if isinstance(item, Mapping) and item.get("candidate_id")
    } if isinstance(candidates, list) else {}
    counts = {
        "ready_for_comparison": 0,
        "blocked_by_source": 0,
        "needs_visual_review": 0,
        "teacher_flagged": 0,
        "approved": 0,
    }
    override_map = manual_formula_overrides if isinstance(manual_formula_overrides, Mapping) else {}
    local_entries = []
    for candidate_id, record in draft_records.items():
        if not isinstance(record, Mapping) or record.get("provenance") not in LOCAL_DRAFT_PROVENANCE:
            continue
        candidate = candidate_map.get(str(candidate_id), {})
        snapshot = build_source_review_snapshot(
            candidate,
            image_analyses,
            override_map.get(str(candidate_id)),
        )
        local_entries.append((str(candidate_id), record, candidate, snapshot))

    # Một mảnh MathType đã xác nhận hỏng nghĩa là cả lô nháp cục bộ của cùng
    # tệp không có nguồn đủ để đối chiếu. Chặn theo lô chỉ là một phân loại
    # dẫn xuất; không sửa nháp, nguồn, OCR hoặc quyết định giáo viên.
    blocked_batches_by_source = {}
    for candidate_id, _record, candidate, snapshot in local_entries:
        source_file = str(snapshot.get("source_file") or candidate.get("source_file") or "").strip()
        fatal_issues = list(snapshot.get("fatal_formula_issues") or [])
        if not source_file or not fatal_issues:
            continue
        batch = blocked_batches_by_source.setdefault(source_file, {
            "source_file": source_file,
            "source_name": str(snapshot.get("source_name") or source_file),
            "affected_candidate_ids": [],
            "fatal_formula_issues": [],
        })
        batch["affected_candidate_ids"].append(candidate_id)
        for issue in fatal_issues:
            if issue not in batch["fatal_formula_issues"]:
                batch["fatal_formula_issues"].append(issue)

    rows = []
    for candidate_id, record, candidate, snapshot in local_entries:
        source_file = str(snapshot.get("source_file") or candidate.get("source_file") or "").strip()
        blocked_batch = blocked_batches_by_source.get(source_file)
        if record.get("status") == "Đã duyệt và đưa vào ngân hàng":
            bucket = "approved"
        elif record.get("review_decision"):
            bucket = "teacher_flagged"
        elif blocked_batch:
            bucket = "blocked_by_source"
        elif snapshot.get("source_issues") or not snapshot.get("valid"):
            bucket = "blocked_by_source"
        elif snapshot.get("requires_visual_review"):
            bucket = "needs_visual_review"
        else:
            bucket = "ready_for_comparison"
        counts[bucket] += 1
        source_issues = snapshot.get("source_issues") or []
        decision = review_decision_text(record.get("review_decision"))
        batch_reason = (
            f"Chặn cả lô từ tệp nguồn vì {len(blocked_batch['fatal_formula_issues'])} mảnh MathType "
            "bị lỗi/chồng nét; cần chép lại công thức hoặc thay nguồn rõ hơn."
            if blocked_batch else ""
        )
        rows.append({
            "candidate_id": str(candidate_id),
            "bucket": bucket,
            "source_file": source_file,
            "source_name": snapshot.get("source_name", "Không rõ nguồn"),
            "question_number": snapshot.get("question_number", "?"),
            "lesson": str(candidate.get("lesson") or "Chưa phân loại"),
            "reason": decision or batch_reason or (str(source_issues[0]) if source_issues else "Sẵn sàng để giáo viên đối chiếu."),
        })
    rank = {
        "ready_for_comparison": 0,
        "needs_visual_review": 1,
        "blocked_by_source": 2,
        "teacher_flagged": 3,
        "approved": 4,
    }
    rows.sort(key=lambda item: (rank[item["bucket"]], item["lesson"], item["source_name"], item["question_number"]))
    blocked_batches = []
    for batch in blocked_batches_by_source.values():
        batch["affected_candidate_ids"].sort()
        batch["local_draft_count"] = sum(
            1 for _candidate_id, _record, candidate, snapshot in local_entries
            if str(snapshot.get("source_file") or candidate.get("source_file") or "").strip() == batch["source_file"]
        )
        blocked_batches.append(batch)
    blocked_batches.sort(key=lambda item: (item["source_name"], item["source_file"]))
    return {"counts": counts, "rows": rows, "blocked_batches": blocked_batches}


def build_local_source_batches(local_review_queue: object) -> list[dict[str, object]]:
    """Gom nháp cục bộ theo tệp nguồn để giáo viên không phải dò từng câu.

    Đây chỉ là bảng điều phối dẫn xuất. Việc gắn cờ cả lô vẫn đòi hỏi giáo viên
    xác nhận trong UI và không bao giờ chuyển câu sang trạng thái đã duyệt.
    """
    queue = local_review_queue if isinstance(local_review_queue, Mapping) else {}
    rows = queue.get("rows") if isinstance(queue.get("rows"), list) else []
    batches: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        source_file = str(row.get("source_file") or "").strip()
        if not source_file:
            continue
        source_name = str(row.get("source_name") or source_file)
        bucket = str(row.get("bucket") or "blocked_by_source")
        batch = batches.setdefault(source_file, {
            "source_file": source_file,
            "source_name": source_name,
            "candidate_ids": [],
            "counts": {
                "ready_for_comparison": 0,
                "needs_visual_review": 0,
                "blocked_by_source": 0,
                "teacher_flagged": 0,
                "approved": 0,
            },
            "reasons": [],
        })
        candidate_id = str(row.get("candidate_id") or "").strip()
        if candidate_id and candidate_id not in batch["candidate_ids"]:
            batch["candidate_ids"].append(candidate_id)
        if bucket in batch["counts"]:
            batch["counts"][bucket] += 1
        reason = str(row.get("reason") or "").strip()
        if reason and reason not in batch["reasons"]:
            batch["reasons"].append(reason)

    result = []
    for batch in batches.values():
        batch["candidate_ids"].sort()
        result.append(batch)
    result.sort(
        key=lambda item: (
            -int(item["counts"]["blocked_by_source"]),
            -int(item["counts"]["needs_visual_review"]),
            str(item["source_name"]),
        )
    )
    return result


def prioritize_draft_ids_for_review(
    draft_ids: object,
    reviewable_ids: object,
    local_review_queue: object,
) -> list[str]:
    """Đặt nháp có thể đối chiếu an toàn lên đầu danh sách chọn của giáo viên.

    Thứ tự này chỉ ảnh hưởng giao diện. Nó không thay trạng thái nháp hoặc tự
    mở khóa/duyệt bất kỳ câu nào.
    """
    all_ids = [str(candidate_id) for candidate_id in draft_ids if str(candidate_id)] if isinstance(draft_ids, list) else []
    reviewable = [str(candidate_id) for candidate_id in reviewable_ids if str(candidate_id)] if isinstance(reviewable_ids, list) else []
    queue = local_review_queue if isinstance(local_review_queue, Mapping) else {}
    queue_rows = queue.get("rows") if isinstance(queue.get("rows"), list) else []
    local_ready = [
        str(row.get("candidate_id"))
        for row in queue_rows
        if isinstance(row, Mapping) and row.get("bucket") == "ready_for_comparison" and row.get("candidate_id")
    ]
    local_visual = [
        str(row.get("candidate_id"))
        for row in queue_rows
        if isinstance(row, Mapping) and row.get("bucket") == "needs_visual_review" and row.get("candidate_id")
    ]
    ordered = []
    for candidate_id in [*local_ready, *reviewable, *local_visual, *all_ids]:
        if candidate_id in all_ids and candidate_id not in ordered:
            ordered.append(candidate_id)
    return ordered
