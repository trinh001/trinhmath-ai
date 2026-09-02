"""Resumable background feeder from TrinhMath's indexed images to OCR.

It never sends files to the Internet.  It stages a small checkpointed batch,
then lets the separate OCR worker consume it concurrently.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

from converter.storage import ConverterStore
from converter.trinhmath_bridge import stage_trinhmath_bank_batch


def write_status(path: Path, **values) -> None:
    values["updated_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    # Streamlit can start a replacement importer while the former process is
    # finishing.  A PID-specific temporary file avoids a Windows rename race.
    temporary = path.with_name(f"{path.stem}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    stop_path = data_dir / "bridge_import_stop.flag"
    status_path = data_dir / "bridge_import_status.json"
    stop_path.unlink(missing_ok=True)
    store = ConverterStore(data_dir / "converter.db")
    write_status(status_path, state="starting", pid=os.getpid(), staged_total=0, expected=0, remaining=0, message="Đang kiểm tra Kho đề…")
    try:
        while True:
            if stop_path.exists():
                write_status(status_path, state="stopped", pid=os.getpid(), message="Đã dừng theo yêu cầu.")
                return
            result = stage_trinhmath_bank_batch(store, data_dir, limit=max(1, args.batch_size))
            write_status(status_path, state="running", pid=os.getpid(), **result, message=f"Đã đưa thêm {result['staged_now']} ảnh vào hàng OCR.")
            if result["staged_now"] == 0:
                write_status(status_path, state="completed", pid=os.getpid(), **result, message="Đã đưa toàn bộ ảnh đã lập chỉ mục vào hàng OCR.")
                return
            time.sleep(0.2)
    except Exception as error:
        write_status(status_path, state="failed", pid=os.getpid(), message=str(error)[:500])
        raise


if __name__ == "__main__":
    main()
