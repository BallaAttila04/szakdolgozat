import sys, json
from pathlib import Path
import duckdb, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import abrak_v7 as a7
U = Path("/mnt/user-data/uploads/Szakdolgozat"); ki = Path(sys.argv[1]); ki.mkdir(exist_ok=True)
mit = sys.argv[2:]
land = json.loads(Path(__file__).resolve().parent.parent.joinpath("ne/land10.geojson").read_text(encoding="utf-8"))
kapuk = json.loads((U / "scripts/kapuk.json").read_text(encoding="utf-8"))["kapuk"]
con = duckdb.connect(); o = U / "outputs"
if "terkep" in mit: print(a7.terkep_attekinto(con, o / "tarolo/ev=2026/ho=07/aisdk-2026-07-15.parquet", kapuk, land, ki))
if "suruseg" in mit: print(a7.tanker_suruseg(con, o / "tarolo_hormuz", pd.read_csv(o / "hormuz/mintanap_mutatok.csv", dtype={"nap": str}), land, ki))
if "idosor" in mit: print(a7.h1_idosor(o / "hormuz/mintanap_mutatok.csv", o / "hormuz/kiterjesztett/mintanap_mutatok.csv", ki))
if "ket" in mit: print(a7.ket_szoros(U / "data/portwatch_chokepoints_2026-10-25.csv", [o / "hormuz/napi.csv", o / "hormuz/kiterjesztett/napi.csv", o / "hormuz/kitoltes/napi.csv"], o / "hormuz/kiterjesztett/mintanap_mutatok.csv", o / "monitor/kapuvonal_napi.csv", ki))
