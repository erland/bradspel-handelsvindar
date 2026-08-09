#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]
with tempfile.NamedTemporaryFile(suffix=".json",delete=False) as f:
    out=f.name
cmd=[sys.executable,str(ROOT/"scripts/simulate_strategic.py"),"--games-per-lineup","2","--seed","12345","--output",out]
subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
data=json.loads(Path(out).read_text(encoding="utf-8"))
assert data["engine_constraints"]["uses_actual_hands"]
for pc,summary in data["by_player_count"].items():
    assert summary["games"]>0
    assert summary["illegal_action_count"]==0
    assert summary["stalemate_rate"]<1
print("STRATEGIC SIMULATOR SMOKE TEST OK")
