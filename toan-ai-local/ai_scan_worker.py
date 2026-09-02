"""Worker nền đọc ảnh công thức bằng Gemini theo từng nhóm nhỏ."""

import json
import os
import time
import traceback
from datetime import datetime

import app


STATUS_FILE = app.AI_SCAN_STATUS_FILE
STOP_FILE = app.AI_SCAN_STOP_FILE


def _now():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def write_status(state, **updates):
    """Ghi nguyên tử để giao diện có thể đọc tiến độ trong lúc worker chạy."""
    current = {}
    try:
        current = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    current.update(updates)
    current["state"] = state
    current["updated_at"] = _now()
    temporary = STATUS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATUS_FILE)


def is_quota_or_rate_limit(message):
    text = str(message).lower()
    return " 429" in text or "lỗi 429" in text or "quota" in text or "rate limit" in text


def wait_for_quota_retry(processed, successes, failures, source_name):
    """Chờ nền một phút rồi thử lại cùng ảnh; người dùng vẫn có thể bấm Dừng."""
    retry_seconds = 65
    for seconds_left in range(retry_seconds, 0, -1):
        if STOP_FILE.exists():
            return False
        if seconds_left in {retry_seconds, 30, 1}:
            write_status(
                "waiting_quota",
                processed=processed,
                successes=successes,
                failures=failures,
                last_source=source_name,
                message=f"Gemini đang tạm hết quota. App tự thử lại sau {seconds_left} giây; không cần bấm tiếp.",
            )
        time.sleep(1)
    return not STOP_FILE.exists()


def run_scan(api_key):
    """Chạy bằng khóa trong bộ nhớ phiên; không truyền khóa qua dòng lệnh/ghi ra đĩa."""
    if not api_key:
        write_status(
            "stopped",
            message="Không có khóa Gemini trong phiên đang mở. Hãy vào Kết nối AI để nhập khóa rồi chạy lại.",
            processed=0,
        )
        return

    model = app.get_gemini_image_model(api_key)
    if not model:
        write_status(
            "failed",
            message="Không tìm thấy model Gemini phù hợp hoặc không kết nối được Gemini. Hãy kiểm tra lại tại Kết nối AI.",
            processed=0,
        )
        return

    started_at = _now()
    processed = successes = failures = 0
    write_status(
        "running",
        pid=os.getpid(),
        started_at=started_at,
        processed=processed,
        successes=successes,
        failures=failures,
        last_source="",
        message=f"Đang quét tự động từng nhóm 3 ảnh bằng {model}.",
    )

    try:
        group_number = 0
        while not STOP_FILE.exists():
            pending_images = app.get_unread_question_images(limit=3)
            if not pending_images:
                attached, _ = app.attach_safe_visuals_to_candidates()
                write_status(
                    "completed",
                    processed=processed,
                    successes=successes,
                    failures=failures,
                    message=f"Đã quét hết ảnh còn lại. Đã ghép {attached} ảnh đủ tin cậy vào câu hỏi.",
                )
                return

            group_number += 1
            for source, image in pending_images:
                if STOP_FILE.exists():
                    break
                source_name = source["file_name"]
                write_status(
                    "running",
                    processed=processed,
                    successes=successes,
                    failures=failures,
                    last_source=f"{source_name} — {image['name'].split('/')[-1]}",
                    message=f"Đang quét nhóm {group_number}, ảnh {processed + 1}.",
                )
                while not STOP_FILE.exists():
                    ok, result = app.read_image_with_gemini(api_key, image, model=model)
                    if ok:
                        app.save_image_analysis(source_name, image, result)
                        successes += 1
                        break
                    if is_quota_or_rate_limit(result):
                        # Không ghi lỗi quota như ảnh đã xử lý: worker tự thử lại cùng ảnh.
                        if wait_for_quota_retry(processed, successes, failures, source_name):
                            continue
                        break
                    # Lỗi đọc riêng của ảnh được lưu để tránh gửi lặp vô hạn.
                    app.save_image_analysis(source_name, image, result, read_ok=False)
                    failures += 1
                    break
                processed += 1

            # Chỉ ghép theo từng 10 nhóm để không làm chậm việc đọc ảnh.
            if group_number % 10 == 0:
                app.attach_safe_visuals_to_candidates()

        attached, _ = app.attach_safe_visuals_to_candidates()
        write_status(
            "stopped",
            processed=processed,
            successes=successes,
            failures=failures,
            message=f"Đã dừng theo yêu cầu. Đã ghép {attached} ảnh đủ tin cậy; có thể tiếp tục sau.",
        )
    except Exception as error:
        write_status(
            "failed",
            processed=processed,
            successes=successes,
            failures=failures,
            message=f"Quét nền gặp lỗi: {error}",
            technical_error=traceback.format_exc(limit=3),
        )


def main():
    """Chế độ dự phòng nếu worker được chạy trực tiếp từ lệnh."""
    run_scan(app.load_saved_gemini_key())


if __name__ == "__main__":
    main()
