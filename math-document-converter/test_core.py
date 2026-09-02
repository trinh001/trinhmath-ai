from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from converter.analyzer import analyze_file
from converter.ocr import cache_key
from converter.storage import ConverterStore


with TemporaryDirectory() as temporary:
    root = Path(temporary)
    image = root / "cong_thuc.png"
    Image.new("RGB", (40, 30), "white").save(image)
    kind, pages = analyze_file(image)
    assert kind == "IMAGE" and pages[0]["classification"] == "SCAN_PAGE"
    store = ConverterStore(root / "converter.db")
    document_id = store.register_document(image, kind, pages)
    assert document_id and store.summary()["WAITING"] == 1
    job = store.next_waiting_job()
    key = cache_key(job["input_hash"], "AUTO")
    store.save_result(job["page_id"], key, "$x^2$", ["x^2"], {"device": "test"})
    store.set_job(job["id"], "SUCCESS", "Kiểm tra cache")
    assert store.cached_result(key)["markdown"] == "$x^2$"
    assert store.summary()["SUCCESS"] == 1

print("CONVERTER_CORE=OK")
