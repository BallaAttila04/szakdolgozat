import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import duckdb, uj_abrak_v9 as u
ki=Path(sys.argv[1]); ki.mkdir(exist_ok=True)
land=json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
kapuk=json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))["kapuk"]
print(u.h3_racs_nagyobb(duckdb.connect(), Path(sys.argv[4]), kapuk, land, ki))
