from pathlib import Path
import json
from converter.storage import ConverterStore
from converter.matching_service import run_dry_match

root = Path(__file__).parent
store = ConverterStore(root / "data" / "converter.db")
_, report = run_dry_match(store, root / "data")
(root / "data" / "matching_dry_run_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
