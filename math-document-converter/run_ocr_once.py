"""Run one local OCR job from the durable Converter queue.

Useful both for a smoke test and later background-worker integration.
"""

from pathlib import Path

from converter.storage import ConverterStore
from converter.worker import process_one


if __name__ == "__main__":
    store = ConverterStore(Path(__file__).parent / "data" / "converter.db")
    print(process_one(store, "CPU"))
