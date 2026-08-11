#!/usr/bin/env python3
"""Preflight professional board themes and layout sources."""
from pathlib import Path
import math, sys, yaml

ROOT=Path(__file__).resolve().parents[1]
layout=yaml.safe_load((ROOT/"data/board-layout.yaml").read_text(encoding="utf-8"))["board_layout"]
board=yaml.safe_load((ROOT/"data/board.yaml").read_text(encoding="utf-8"))["board"]
themes=yaml.safe_load((ROOT/"data/board-theme.yaml").read_text(encoding="utf-8"))["board_theme"]["themes"]
coast=yaml.safe_load((ROOT/"data/coastline.yaml").read_text(encoding="utf-8"))["coastline"]

warnings=[]
w=float(layout["page"]["width_mm"]); h=float(layout["page"]["height_mm"])
margin=float(layout["page"]["safe_margin_mm"])
ports={p["name"]:p for p in layout["ports"]}
routes={r["id"]:r for r in layout["routes"]}

for name,p in ports.items():
    x=float(p["x_mm"]); y=float(p["y_mm"])
    if not (margin <= x <= w-margin and margin <= y <= h-margin):
        warnings.append(f"port outside safe area: {name}")
    lx=x+float(p.get("label_dx_mm",0)); ly=y+float(p.get("label_dy_mm",-14))
    label_w=max(22,len(name)*2.6+5)
    if lx-label_w/2 < margin or lx+label_w/2 > w-margin or ly-5 < margin or ly+3 > h-margin:
        warnings.append(f"label outside safe area: {name}")

route_ids={r["id"] for r in board["connections"]}
if route_ids != set(routes):
    warnings.append("board-layout route IDs do not exactly match board route IDs")

for theme_name,theme in themes.items():
    for key in ("paper","sea","land","ink","label","frame"):
        if key not in theme["palette"]:
            warnings.append(f"{theme_name}: missing palette key {key}")
    for typ in ("röd","lila","blå","grön"):
        if typ not in theme["routes"]:
            warnings.append(f"{theme_name}: missing route style {typ}")
        elif float(theme["routes"][typ]["width_mm"]) < 1.5:
            warnings.append(f"{theme_name}: route {typ} thinner than 1.5 mm")
    if float(theme["typography"]["port_size"]) < 3.2:
        warnings.append(f"{theme_name}: port names may be too small")

for land in coast["landmasses"]:
    for x,y in land["points"]:
        if not (0 <= float(x) <= w and 0 <= float(y) <= h):
            warnings.append(f'coastline point outside page: {land["id"]}')

icons=["anchor.svg","compass.svg","sail.svg","road.svg","river.svg","archipelago.svg"]
for icon in icons:
    if not (ROOT/"assets"/"icons"/icon).exists():
        warnings.append(f"missing icon: {icon}")

print({"version":(ROOT/"VERSION").read_text(encoding="utf-8").strip(),"warnings":warnings,"count":len(warnings)})
sys.exit(1 if warnings else 0)
