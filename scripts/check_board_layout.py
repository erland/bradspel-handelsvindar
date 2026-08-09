#!/usr/bin/env python3
from pathlib import Path
import yaml, math, json
ROOT=Path(__file__).resolve().parents[1]
board=yaml.safe_load((ROOT/"data/board.yaml").read_text(encoding="utf-8"))["board"]
layout=yaml.safe_load((ROOT/"data/board-layout.yaml").read_text(encoding="utf-8"))["board_layout"]
ports={p["name"]:p for p in layout["ports"]}
routes={r["id"]:r for r in layout["routes"]}

def box(p):
    x=p["x_mm"]+p.get("label_dx_mm",0); y=p["y_mm"]+p.get("label_dy_mm",-14)
    w=max(22,len(p["name"])*2.6+5)
    return (x-w/2,y-4.2,x+w/2,y+2.1)
def overlap(a,b,pad=0):
    return not (a[2]+pad<b[0] or b[2]+pad<a[0] or a[3]+pad<b[1] or b[3]+pad<a[1])
warnings=[]
names=list(ports)
for i,a in enumerate(names):
    for b in names[i+1:]:
        if overlap(box(ports[a]),box(ports[b]),1):
            warnings.append({"type":"label-label","a":a,"b":b})
for name,p in ports.items():
    bx=box(p)
    for other,q in ports.items():
        if name==other: continue
        x,y=q["x_mm"],q["y_mm"]
        if bx[0]-4 < x < bx[2]+4 and bx[1]-4 < y < bx[3]+4:
            warnings.append({"type":"label-port","label":name,"port":other})
report={"version":str(layout["version"]),"warnings":warnings,"count":len(warnings)}
out=ROOT/"output"/"layout-collision-report.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
