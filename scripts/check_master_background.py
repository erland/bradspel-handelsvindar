#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import sys, yaml, json
ROOT=Path(__file__).resolve().parents[1]
theme=yaml.safe_load((ROOT/"data/board-theme.yaml").read_text(encoding="utf-8"))["board_theme"]["themes"]
warnings=[]
for name,cfg in theme.items():
    bg=cfg.get("background") or {}
    if not bg.get("enabled"):
        continue
    rel=bg.get("image")
    if not rel:
        warnings.append(f"{name}: enabled background missing image")
        continue
    path=ROOT/rel
    if not path.exists():
        warnings.append(f"{name}: background file missing: {rel}")
        continue
    with Image.open(path) as im:
        w,h=im.size
        if w < 1600 or h < 1000:
            warnings.append(f"{name}: low background resolution {w}x{h}")
        ratio=w/h
        target=297/210
        if abs(ratio-target)>0.20:
            warnings.append(f"{name}: aspect ratio differs from A4 landscape")
print(json.dumps({"warnings":warnings,"count":len(warnings)},ensure_ascii=False,indent=2))
sys.exit(1 if warnings else 0)
