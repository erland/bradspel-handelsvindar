#!/usr/bin/env python3
"""Create transparent individual trade-seal PNGs from the approved 2x2 source sheet."""
from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"assets/icons/source/trade-seals-generated-sheet-v1.1.png"
OUT=ROOT/"assets/icons/trade-seals"
OUT.mkdir(parents=True,exist_ok=True)

items=[
    ("blue-trade-seal.png",(0,0,512,512)),
    ("red-trade-seal.png",(512,0,1024,512)),
    ("green-trade-seal.png",(0,512,512,1024)),
    ("purple-trade-seal.png",(512,512,1024,1024)),
]

img=Image.open(SOURCE).convert("RGB")
if img.size != (1024,1024):
    raise SystemExit(f"Expected 1024x1024 source sheet, got {img.size}")

for filename,box in items:
    q=img.crop(box).convert("RGBA")
    h,w=q.height,q.width
    yy,xx=np.ogrid[:h,:w]
    cx,cy=w/2,h/2
    dist=np.sqrt(((xx-cx)/(w/2))**2+((yy-cy)/(h/2))**2)
    alpha=np.clip((0.96-dist)/0.20,0,1)
    alpha=Image.fromarray((alpha*255).astype(np.uint8),"L").filter(ImageFilter.GaussianBlur(2.0))
    q.putalpha(alpha)
    q=q.crop(q.getbbox())
    canvas=Image.new("RGBA",(512,512),(0,0,0,0))
    q.thumbnail((480,480),Image.Resampling.LANCZOS)
    canvas.alpha_composite(q,((512-q.width)//2,(512-q.height)//2))
    canvas.save(OUT/filename,optimize=True)

print(f"Built {len(items)} trade-seal icons in {OUT}")
