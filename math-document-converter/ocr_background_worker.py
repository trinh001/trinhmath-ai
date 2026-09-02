"""Durable sequential OCR worker for Math Document Converter.

It uses one Pix2Text instance for the whole run, writes visible status after
every page, and can be stopped by creating `auto_ocr_stop.flag` in data_dir.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from converter.ocr import Pix2TextProvider
from converter.storage import ConverterStore
from converter.worker import process_one


def write_status(path: Path, **values) -> None:
    values["updated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--mode", choices=["AUTO", "GPU", "CPU"], default="AUTO")
    parser.add_argument("--watch-seconds", type=int, default=1800, help="Keep watching for newly staged pages after the queue becomes temporarily empty.")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    status_path = data_dir / "auto_ocr_status.json"
    stop_path = data_dir / "auto_ocr_stop.flag"
    stop_path.unlink(missing_ok=True)
    store = ConverterStore(data_dir / "converter.db")
    provider = Pix2TextProvider(args.mode)
    processed = succeeded = failed = 0
    idle_started_at: float | None = None
    write_status(status_path, state="starting", pid=os.getpid(), mode=args.mode, processed=0, succeeded=0, failed=0, message="Đang nạp mô hình OCR…")
    try:
        provider.initialize()
        while True:
            if stop_path.exists():
                write_status(status_path, state="stopped", pid=os.getpid(), mode=args.mode, processed=processed, succeeded=succeeded, failed=failed, message="Đã dừng theo yêu cầu.")
                return
            result = process_one(store, args.mode, provider=provider)
            if result["state"] == "idle":
                if idle_started_at is None:
                    idle_started_at = time.monotonic()
                waited = int(time.monotonic() - idle_started_at)
                if waited >= args.watch_seconds:
                    write_status(status_path, state="completed", pid=os.getpid(), mode=args.mode, processed=processed, succeeded=succeeded, failed=failed, message="Đã quét hết hàng đợi; không có ảnh mới trong 30 phút.")
                    return
                write_status(status_path, state="running", pid=os.getpid(), mode=args.mode, processed=processed, succeeded=succeeded, failed=failed, message=f"Đang chờ ảnh mới từ Kho đề ({waited // 60}/{args.watch_seconds // 60} phút)…")
                time.sleep(5)
                continue
            idle_started_at = None
            processed += 1
            succeeded += int(result["state"] in {"success", "cached"})
            failed += int(result["state"] == "failed")
            write_status(status_path, state="running", pid=os.getpid(), mode=args.mode, processed=processed, succeeded=succeeded, failed=failed, message=result["message"])
            time.sleep(0.15)
    except Exception as error:
        write_status(status_path, state="failed", pid=os.getpid(), mode=args.mode, processed=processed, succeeded=succeeded, failed=failed, message=str(error)[:500])
        raise
    finally:
        provider.release()


if __name__ == "__main__":
    main()
