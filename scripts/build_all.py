import base64
#!/usr/bin/env python3
"""Build all Handelsvindar printable artifacts.

Sources -> SVG/HTML -> PDF.
Older generated PDFs and generated SVG pages are removed before each build.
"""
from pathlib import Path
import yaml, html, math, textwrap, shutil, re, json
import cairosvg
from pypdf import PdfReader, PdfWriter
HTML = None
CSS = None  # Optional for board-only build

ROOT = Path(__file__).resolve().parents[1]
VERSION = "v2.3"
OUT_SVG = ROOT / "output" / "svg"
OUT_PDF = ROOT / "output" / "pdf"
OUT_PREVIEW = ROOT / "output" / "preview"
PDF_BOARD = OUT_PDF / "board"
PDF_DOCS = OUT_PDF / "docs"
PDF_CARDS = OUT_PDF / "cards"
PDF_AIDS = OUT_PDF / "player-aids"
PDF_COMPONENTS = OUT_PDF / "components"
SVG_BOARD = OUT_SVG / "board"
SVG_CARDS = OUT_SVG / "cards"
SVG_AIDS = OUT_SVG / "player-aids"
SVG_COMPONENTS = OUT_SVG / "components"
for d in (
    OUT_SVG, OUT_PDF, OUT_PREVIEW, PDF_BOARD, PDF_DOCS, PDF_CARDS,
    PDF_AIDS, PDF_COMPONENTS, SVG_BOARD, SVG_CARDS, SVG_AIDS, SVG_COMPONENTS
):
    d.mkdir(parents=True, exist_ok=True)

BOARD = yaml.safe_load((ROOT/"data"/"board.yaml").read_text(encoding="utf-8"))["board"]
BOARD_LAYOUT = yaml.safe_load((ROOT/"data"/"board-layout.yaml").read_text(encoding="utf-8"))["board_layout"]
CARDS = yaml.safe_load((ROOT/"data"/"cards.yaml").read_text(encoding="utf-8"))["route_cards"]
TRADE_SEAL_ICONS = yaml.safe_load((ROOT/"data"/"trade-seal-icons.yaml").read_text(encoding="utf-8"))
DELIVERIES = yaml.safe_load((ROOT/"data"/"deliveries.yaml").read_text(encoding="utf-8"))["deliveries"]
BOARD_THEMES = yaml.safe_load((ROOT/"data"/"board-theme.yaml").read_text(encoding="utf-8"))["board_theme"]["themes"]
COASTLINE = yaml.safe_load((ROOT/"data"/"coastline.yaml").read_text(encoding="utf-8"))["coastline"]

def _theme_background_image(theme):
    cfg = theme.get("background") or {}
    if not cfg.get("enabled"):
        return None, cfg
    rel = cfg.get("image")
    if not rel:
        return None, cfg
    path = ROOT / rel
    return (path if path.exists() else None), cfg

TERRAIN = yaml.safe_load((ROOT/"data"/"terrain.yaml").read_text(encoding="utf-8"))["terrain"]
ISLANDS = yaml.safe_load((ROOT/"data"/"islands.yaml").read_text(encoding="utf-8"))["islands"]

COLORS = {
    "blå": ("#2A718D", "#DCEFF8"),
    "röd": ("#B45445", "#F5DDD8"),
    "grön": ("#4F8461", "#E1EFE4"),
    "lila": ("#715298", "#ECE4F7"),
    "handelsvind": ("#C18A19", "#FFF2C9"),
}

def clean_generated_outputs():
    """Remove old generated PDF/SVG/preview files before rebuilding."""
    for folder, patterns in (
        (OUT_PDF, ("*.pdf",)),
        (OUT_SVG, ("*.svg",)),
        (OUT_PREVIEW, ("*.png", "*.svg")),
    ):
        for pattern in patterns:
            for path in folder.rglob(pattern):
                path.unlink()
    manifest = ROOT/"output"/"PRINT_MANIFEST.json"
    if manifest.exists():
        manifest.unlink()

def svg_to_pdf(svg_path, pdf_path):
    cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))

def merge_pdfs(paths, out):
    writer = PdfWriter()
    for p in paths:
        for page in PdfReader(str(p)).pages:
            writer.add_page(page)
    with open(out, "wb") as f:
        writer.write(f)

def render_template(path, values):
    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{"+key+"}}", str(value))
    return text

def _quad_point(p0, p1, p2, t):
    u = 1-t
    return (u*u*p0[0] + 2*u*t*p1[0] + t*t*p2[0],
            u*u*p0[1] + 2*u*t*p1[1] + t*t*p2[1])

def _smooth_closed_path(points):
    """Create a soft closed SVG path through structured coastline points."""
    if len(points) < 3:
        return ""
    pts=[(float(x),float(y)) for x,y in points]
    first_mid=((pts[-1][0]+pts[0][0])/2,(pts[-1][1]+pts[0][1])/2)
    parts=[f"M {first_mid[0]:.2f} {first_mid[1]:.2f}"]
    for i,p in enumerate(pts):
        nxt=pts[(i+1)%len(pts)]
        mid=((p[0]+nxt[0])/2,(p[1]+nxt[1])/2)
        parts.append(f"Q {p[0]:.2f} {p[1]:.2f} {mid[0]:.2f} {mid[1]:.2f}")
    parts.append("Z")
    return " ".join(parts)

def _anchor_symbol(x, y, size, color):
    """Compact native SVG anchor symbol; avoids external file dependency in PDFs."""
    s=size
    return (
        f'<g transform="translate({x-s/2:.2f},{y-s/2:.2f}) scale({s/24:.4f})" fill="{color}">'
        '<path d="M11 3h2v5h3v2h-3v7.1c2.5-.4 4.3-1.7 5.4-4.1l1.8.8C18.7 17.3 15.9 19 12 19s-6.7-1.7-8.2-5.2l1.8-.8c1.1 2.4 2.9 3.7 5.4 4.1V10H8V8h3V3zm1-2a2 2 0 110 4 2 2 0 010-4z"/>'
        '</g>'
    )


def _route_path_and_control(c, rl, positions):
    """Return SVG path and representative control point for route geometry."""
    x1,y1=positions[c["from"]]; x2,y2=positions[c["to"]]
    waypoints=rl.get("waypoints_mm") or []
    if waypoints:
        pts=[(x1,y1)]+[(float(x),float(y)) for x,y in waypoints]+[(x2,y2)]
        if len(pts)==3:
            path=f"M {pts[0][0]} {pts[0][1]} Q {pts[1][0]} {pts[1][1]} {pts[2][0]} {pts[2][1]}"
            return path, pts[1]
        path=f"M {pts[0][0]} {pts[0][1]} " + " ".join(f"L {x} {y}" for x,y in pts[1:])
        return path, pts[len(pts)//2]
    curve=float(rl.get("curve_mm",0))
    dx,dy=x2-x1,y2-y1; le=max(math.hypot(dx,dy),1)
    nx,ny=-dy/le,dx/le
    cx=(x1+x2)/2+nx*curve; cy=(y1+y2)/2+ny*curve
    return f"M {x1} {y1} Q {cx} {cy} {x2} {y2}", (cx,cy)


def _route_point_and_tangent(c, rl, positions, t):
    """Return point and tangent at normalized t for quadratic or polyline route geometry."""
    x1,y1=positions[c["from"]]; x2,y2=positions[c["to"]]
    waypoints=rl.get("waypoints_mm") or []
    if waypoints:
        pts=[(x1,y1)]+[(float(x),float(y)) for x,y in waypoints]+[(x2,y2)]
        if len(pts)==3:
            cx,cy=pts[1]
            px,py=_quad_point(pts[0],pts[1],pts[2],t)
            tx=2*(1-t)*(cx-x1)+2*t*(x2-cx)
            ty=2*(1-t)*(cy-y1)+2*t*(y2-cy)
            return (px,py),(tx,ty)
        lengths=[math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:])]
        total=max(sum(lengths),1e-9)
        target=max(0,min(1,t))*total
        acc=0.0
        for i,L in enumerate(lengths):
            if target<=acc+L or i==len(lengths)-1:
                local=(target-acc)/max(L,1e-9)
                a,b=pts[i],pts[i+1]
                px=a[0]+(b[0]-a[0])*local
                py=a[1]+(b[1]-a[1])*local
                return (px,py),(b[0]-a[0],b[1]-a[1])
            acc+=L
    curve=float(rl.get("curve_mm",0))
    dx,dy=x2-x1,y2-y1
    le=max(math.hypot(dx,dy),1)
    nx,ny=-dy/le,dx/le
    cx=(x1+x2)/2+nx*curve
    cy=(y1+y2)/2+ny*curve
    px,py=_quad_point((x1,y1),(cx,cy),(x2,y2),t)
    tx=2*(1-t)*(cx-x1)+2*t*(x2-cx)
    ty=2*(1-t)*(cy-y1)+2*t*(y2-cy)
    return (px,py),(tx,ty)


def _build_board_variant(theme_name):
    theme=BOARD_THEMES[theme_name]
    palette=theme["palette"]
    typography=theme["typography"]
    decorations=theme["decorations"]
    w=float(BOARD_LAYOUT["page"]["width_mm"])
    h=float(BOARD_LAYOUT["page"]["height_mm"])
    port_layout={p["name"]:p for p in BOARD_LAYOUT["ports"]}
    positions={n:(float(p["x_mm"]),float(p["y_mm"])) for n,p in port_layout.items()}
    route_layout={r["id"]:r for r in BOARD_LAYOUT["routes"]}

    defs = [
        '<filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0.5" dy="0.8" stdDeviation="0.8" flood-color="#20343A" flood-opacity="0.22"/>'
        '</filter>',
        '<pattern id="paperGrain" width="12" height="12" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="3" r="0.18" fill="{palette["muted_ink"]}" opacity="0.10"/>'
        f'<circle cx="9" cy="8" r="0.14" fill="{palette["muted_ink"]}" opacity="0.08"/>'
        '</pattern>',
    ]
    bg_path,bg_cfg=_theme_background_image(theme)
    background=[
        f'<rect width="{w}" height="{h}" fill="{palette["paper"]}"/>',
        f'<rect width="{w}" height="{h}" fill="url(#paperGrain)" opacity="0.55"/>',
        f'<rect x="8" y="31" width="{w-16}" height="{h-39}" rx="4" fill="{palette["sea"]}"/>',
    ]
    if bg_path is not None:
        bg64=base64.b64encode(bg_path.read_bytes()).decode("ascii")
        mime="image/png" if bg_path.suffix.lower()==".png" else "image/jpeg"
        opacity=float(bg_cfg.get("opacity",0.88))
        fit=str(bg_cfg.get("fit","cover"))
        preserve="xMidYMid slice" if fit=="cover" else "xMidYMid meet"
        background=[
            f'<rect width="{w}" height="{h}" fill="{palette["paper"]}"/>',
            f'<image x="0" y="0" width="{w}" height="{h}" preserveAspectRatio="{preserve}" '
            f'opacity="{opacity}" href="data:{mime};base64,{bg64}"/>',
        ]
        wash_color=bg_cfg.get("wash_color","#FFFDF4")
        wash_opacity=float(bg_cfg.get("wash_opacity",0.10))
        if wash_opacity>0:
            background.append(
                f'<rect width="{w}" height="{h}" fill="{wash_color}" opacity="{wash_opacity}"/>'
            )

    terrain=[]
    suppress_generated_terrain=bool((theme.get("background") or {}).get("suppress_generated_terrain",False) and bg_path is not None)
    if not suppress_generated_terrain:
        # Build broad connected island masses first, using internal island routes as land bridges.
        port_to_island={}
        for island in ISLANDS["groups"]:
            for port in island["ports"]:
                port_to_island[port]=island["id"]
        route_by_id={c["id"]:c for c in BOARD["connections"]}
        island_bridge_width=float(ISLANDS.get("land_bridge_width_mm",28))
        for rid,rl in route_layout.items():
            c=route_by_id[rid]
            same_island=port_to_island.get(c["from"])==port_to_island.get(c["to"])
            if not same_island:
                continue
            path,_=_route_path_and_control(c,rl,positions)
            terrain.append(
                f'<path d="{path}" fill="none" stroke="{palette["land_shadow"]}" '
                f'stroke-width="{island_bridge_width+1.2}" stroke-linecap="round" '
                f'stroke-linejoin="round" opacity="0.44"/>'
            )
            terrain.append(
                f'<path d="{path}" fill="none" stroke="{palette["land"]}" '
                f'stroke-width="{island_bridge_width}" stroke-linecap="round" '
                f'stroke-linejoin="round"/>'
            )
        # Add land around every port and beneath every road.
        port_land_radius=float(TERRAIN["port_land_radius_mm"])
        for name,(px,py) in positions.items():
            terrain.append(
                f'<circle cx="{px}" cy="{py}" r="{port_land_radius}" fill="{palette["land"]}" '
                f'stroke="{palette["land_shadow"]}" stroke-width="0.55"/>'
            )
        # Land corridors first.
        for rid,rl in route_layout.items():
            c=route_by_id[rid]
            if c["route_type"]!="landsväg":
                continue
            path,_=_route_path_and_control(c,rl,positions)
            width=float(TERRAIN["land_corridor_width_mm"])
            terrain.append(
                f'<path d="{path}" fill="none" stroke="{palette["land"]}" stroke-width="{width}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )
            terrain.append(
                f'<path d="{path}" fill="none" stroke="{palette["land_shadow"]}" stroke-width="{width+0.8}" '
                f'stroke-linecap="round" stroke-linejoin="round" opacity="0.38"/>'
            )
            terrain.append(
                f'<path d="{path}" fill="none" stroke="{palette["land"]}" stroke-width="{width}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )
        # Sea and coastal corridors carve navigable water through land where required.
        for rid,rl in route_layout.items():
            c=route_by_id[rid]
            if c["route_type"] not in ("sjöled","skärgårdsled"):
                continue
            path,_=_route_path_and_control(c,rl,positions)
            width=float(TERRAIN["water_channel_width_mm"] if c["route_type"]=="sjöled" else TERRAIN["coastal_water_channel_width_mm"])
            terrain.append(
                f'<path d="{path}" fill="none" stroke="{palette["sea"]}" stroke-width="{width}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )
            if c["route_type"]=="skärgårdsled" and theme_name=="standard":
                # Small islands along coastal routes communicate archipelago terrain.
                x1,y1=positions[c["from"]]; x2,y2=positions[c["to"]]
                for frac,side in ((0.34,1),(0.66,-1)):
                    ix=x1+(x2-x1)*frac; iy=y1+(y2-y1)*frac
                    terrain.append(
                        f'<circle cx="{ix+side*2.4}" cy="{iy-side*1.8}" r="{TERRAIN["archipelago_island_radius_mm"]}" '
                        f'fill="{palette["land"]}" stroke="{palette["land_shadow"]}" stroke-width="0.35"/>'
                    )
        # Rivers are explicit water channels with visible banks.
        for rid,rl in route_layout.items():
            c=route_by_id[rid]
            if c["route_type"]!="flodled":
                continue
            path,_=_route_path_and_control(c,rl,positions)
            terrain.append(
                f'<path d="{path}" fill="none" stroke="{palette["land_shadow"]}" '
                f'stroke-width="{TERRAIN["river_bank_width_mm"]}" stroke-linecap="round" opacity="0.5"/>'
            )
            terrain.append(
                f'<path d="{path}" fill="none" stroke="{palette["sea_deep"]}" '
                f'stroke-width="{TERRAIN["river_water_width_mm"]}" stroke-linecap="round"/>'
            )
    deco=[]
    suppress_generated_decorations=bool((theme.get("background") or {}).get("suppress_generated_decorations",False) and bg_path is not None)
    if (not suppress_generated_decorations) and decorations.get("show_wave_pattern"):
        for row in COASTLINE["wave_rows"]:
            y=float(row["y_mm"])
            x=float(row["x_start_mm"])
            while x < float(row["x_end_mm"]):
                deco.append(
                    f'<path d="M {x:.1f} {y:.1f} q 3 -1.6 6 0 q 3 1.6 6 0" '
                    f'fill="none" stroke="{palette["sea_deep"]}" stroke-width="0.5" opacity="0.32"/>'
                )
                x += float(row["step_mm"])
    if (not suppress_generated_decorations) and decorations.get("show_compass"):
        c=COASTLINE["compass"]; x=float(c["x_mm"]); y=float(c["y_mm"]); r=float(c["radius_mm"])
        deco += [
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{palette["label"]}" opacity="0.78" '
            f'stroke="{palette["frame"]}" stroke-width="0.45"/>',
            f'<path d="M {x} {y-r+2} L {x+2} {y-2} L {x+r-2} {y} L {x+2} {y+2} '
            f'L {x} {y+r-2} L {x-2} {y+2} L {x-r+2} {y} L {x-2} {y-2} Z" '
            f'fill="none" stroke="{palette["frame"]}" stroke-width="0.55"/>',
            f'<text x="{x}" y="{y-r+0.5}" text-anchor="middle" font-family="DejaVu Sans" '
            f'font-size="2.5" font-weight="700" fill="{palette["frame"]}">N</text>',
        ]
    if (not suppress_generated_decorations) and decorations.get("show_trade_winds"):
        for wind in COASTLINE["trade_winds"]:
            x1,y1,x2,y2=[float(wind[k]) for k in ("x1","y1","x2","y2")]
            deco.append(
                f'<path d="M {x1} {y1} C {(x1+x2)/2-5} {y1-3}, {(x1+x2)/2+5} {y2+3}, {x2} {y2}" '
                f'fill="none" stroke="{palette["muted_ink"]}" stroke-width="0.55" opacity="0.38"/>'
            )
            deco.append(
                f'<path d="M {x2-4} {y2-1.8} L {x2} {y2} L {x2-4} {y2+1.8}" '
                f'fill="none" stroke="{palette["muted_ink"]}" stroke-width="0.55" opacity="0.38"/>'
            )

    connections=[]; costs=[]; marker_slots=[]
    slot_cfg=BOARD_LAYOUT.get("route_marker_slots") or {}
    for c in BOARD["connections"]:
        x1,y1=positions[c["from"]]; x2,y2=positions[c["to"]]
        rl=route_layout.get(c["id"],{})
        path,(cx,cy)=_route_path_and_control(c,rl,positions)
        style=theme["routes"][c["route_type"]]
        dash=style.get("dash")
        da=f' stroke-dasharray="{dash}"' if dash else ""
        halo_w=float(style["width_mm"])+1.8
        connections.append(
            f'<path d="{path}" fill="none" stroke="{style["halo"]}" stroke-width="{halo_w}" '
            'stroke-linecap="round" stroke-linejoin="round" opacity="0.86"/>'
        )
        connections.append(
            f'<path d="{path}" fill="none" stroke="{style["color"]}" stroke-width="{style["width_mm"]}" '
            f'stroke-linecap="round" stroke-linejoin="round"{da}/>'
        )
        if slot_cfg.get("enabled",False):
            count=int(c["cost"])
            route_slot_cfg=rl.get("marker_slots") or {}
            start_t=float(route_slot_cfg.get("start_t",slot_cfg.get("start_t",0.28)))
            end_t=float(route_slot_cfg.get("end_t",slot_cfg.get("end_t",0.72)))
            normal_off=float(route_slot_cfg.get("normal_offset_mm",0))
            ts=[0.5] if count==1 else [start_t+(end_t-start_t)*i/(count-1) for i in range(count)]
            radius=float(slot_cfg.get("diameter_mm",6.2))/2
            fill=slot_cfg.get("fill",palette["cost_fill"])
            fill_opacity=float(slot_cfg.get("fill_opacity",0.82))
            stroke_w=float(slot_cfg.get("stroke_width_mm",0.55))
            cost_t=float(rl.get("cost_t",0.5))
            cost_slot_index=min(range(len(ts)),key=lambda i:abs(ts[i]-cost_t))
            cost_mode=slot_cfg.get("cost_number_mode","nearest_slot")
            cost_font_size=float(slot_cfg.get("cost_font_size_mm",3.2))
            cost_font_weight=int(slot_cfg.get("cost_font_weight",700))
            for slot_index,st in enumerate(ts):
                (sx,sy),(stx,sty)=_route_point_and_tangent(c,rl,positions,st)
                sl=max(math.hypot(stx,sty),1)
                snx,sny=-sty/sl,stx/sl
                sx,sy=sx+snx*normal_off,sy+sny*normal_off
                marker_slots.append(
                    f'<circle cx="{sx:.3f}" cy="{sy:.3f}" r="{radius:.3f}" fill="{fill}" '
                    f'fill-opacity="{fill_opacity}" stroke="{style["color"]}" stroke-width="{stroke_w}"/>'
                )
                if (
                    slot_cfg.get("show_cost_number",True)
                    and cost_mode=="nearest_slot"
                    and slot_index==cost_slot_index
                ):
                    marker_slots.append(
                        f'<text x="{sx:.3f}" y="{sy+cost_font_size*0.36:.3f}" '
                        f'font-family="DejaVu Sans" font-size="{cost_font_size}" '
                        f'font-weight="{cost_font_weight}" text-anchor="middle" '
                        f'fill="{palette["ink"]}">{c["cost"]}</text>'
                    )

    port_shapes=[]; labels=[]
    pr=float(theme["ports"]["outer_radius_mm"])
    ir=float(theme["ports"]["inner_radius_mm"])
    for name,p in port_layout.items():
        x,y=float(p["x_mm"]),float(p["y_mm"])
        lx=x+float(p.get("label_dx_mm",0)); ly=y+float(p.get("label_dy_mm",-14))
        label_w=max(22,len(name)*2.6+5)
        port_shapes += [
            f'<circle cx="{x}" cy="{y}" r="{pr}" fill="{palette["label"]}" '
            f'stroke="{palette["frame"]}" stroke-width="1.0" filter="url(#softShadow)"/>',
            f'<circle cx="{x}" cy="{y}" r="{ir}" fill="{palette["sea"]}" '
            f'stroke="{palette["frame"]}" stroke-width="0.35"/>',
            _anchor_symbol(x,y,5.3,palette["frame"]),
        ]
        labels += [
            f'<rect x="{lx-label_w/2}" y="{ly-4.4}" width="{label_w}" height="6.8" rx="1.8" '
            f'fill="{palette["label"]}" stroke="{palette["label_border"]}" stroke-width="0.4" '
            'filter="url(#softShadow)"/>',
            f'<text x="{lx}" y="{ly+0.2}" font-family="{typography["port_family"]}" '
            f'font-size="{typography["port_size"]}" font-weight="700" text-anchor="middle" '
            f'fill="{palette["ink"]}">{html.escape(name)}</text>'
        ]

    legend=[]

    title=[]
    frame=[
        f'<rect x="7" y="7" width="{w-14}" height="{h-14}" rx="3.5" fill="none" '
        f'stroke="{palette["frame"]}" stroke-width="0.65"/>',
    ]
    svg=render_template(ROOT/"templates"/"board"/"board-a4.svg",{
        "WIDTH":w,"HEIGHT":h,"DEFS":"\n".join(defs),
        "BACKGROUND":"\n".join(background),"TERRAIN":"\n".join(terrain),
        "DECORATIONS":"\n".join(deco),"CONNECTIONS":"\n".join(connections)+"\n"+"\n".join(marker_slots),
        "COSTS":"\n".join(costs),"PORTS":"\n".join(port_shapes),
        "LABELS":"\n".join(labels),"LEGEND":"\n".join(legend),
        "TITLE":"\n".join(title),"FRAME":"\n".join(frame)
    })
    stem=f"board-a4-{theme_name.replace('_','-')}-{VERSION}"
    svg_path=SVG_BOARD/f"{stem}.svg"
    pdf_path=PDF_BOARD/f"{stem}.pdf"
    png_path=OUT_PREVIEW/f"{stem}.png"
    svg_path.write_text(svg,encoding="utf-8")
    svg_to_pdf(svg_path,pdf_path)
    cairosvg.svg2png(url=str(svg_path),write_to=str(png_path),output_width=1800)
    return {"theme":theme_name,"svg":svg_path,"pdf":pdf_path,"preview":png_path}

def build_board():
    """Build both professional standard and ink-friendly board variants."""
    return [_build_board_variant("standard"),_build_board_variant("ink_friendly")]

def wrap(text, width):
    return textwrap.wrap(text, width=width, break_long_words=False)



def embedded_png_svg(path, x, y, width, height, opacity=1.0):
    """Embed a project PNG into SVG so PDF output is self-contained."""
    p=ROOT/path
    if not p.exists():
        return ""
    payload=base64.b64encode(p.read_bytes()).decode("ascii")
    return (
        f'<image x="{x}" y="{y}" width="{width}" height="{height}" '
        f'preserveAspectRatio="xMidYMid meet" opacity="{opacity}" '
        f'href="data:image/png;base64,{payload}"/>'
    )

def trade_symbol_svg(symbol, x, y, size, color, stroke_width=0.7):
    """Accessible route/card symbol rendered as native SVG."""
    s=float(size)
    if symbol=="circle":
        return f'<circle cx="{x}" cy="{y}" r="{s*0.36}" fill="none" stroke="{color}" stroke-width="{stroke_width}"/>'
    if symbol=="triangle":
        pts=f"{x},{y-s*0.42} {x-s*0.42},{y+s*0.34} {x+s*0.42},{y+s*0.34}"
        return f'<polygon points="{pts}" fill="none" stroke="{color}" stroke-width="{stroke_width}" stroke-linejoin="round"/>'
    if symbol=="square":
        q=s*0.68
        return f'<rect x="{x-q/2}" y="{y-q/2}" width="{q}" height="{q}" fill="none" stroke="{color}" stroke-width="{stroke_width}"/>'
    if symbol=="diamond":
        d=s*0.46
        pts=f"{x},{y-d} {x+d},{y} {x},{y+d} {x-d},{y}"
        return f'<polygon points="{pts}" fill="none" stroke="{color}" stroke-width="{stroke_width}" stroke-linejoin="round"/>'
    # star / Handelsvind
    outer=s*0.46; inner=s*0.20
    pts=[]
    for i in range(10):
        a=-math.pi/2+i*math.pi/5
        r=outer if i%2==0 else inner
        pts.append(f"{x+math.cos(a)*r:.2f},{y+math.sin(a)*r:.2f}")
    return f'<polygon points="{" ".join(pts)}" fill="{color}" stroke="{color}" stroke-width="{stroke_width*0.35}"/>'

def card_svg(card, x,y,w=63,h=88, delivery=False):
    if delivery:
        col="#1F596E"; pale="#E1EFF3"; title=f'{card["cargo"]}'
        lines=[card["from"], "till", card["to"]]; footer=f'{card["points"]} POÄNG'; cid=card["id"]
    else:
        col,pale=COLORS[card["type"]]; title=card["name"]; lines=wrap(card["text"],30); footer="HANDELSSIGILL"; cid=card["id"]
    parts=[f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="#FFFDF8" stroke="#222" stroke-width="0.45"/>',
           f'<rect x="{x+2}" y="{y+2}" width="{w-4}" height="16" rx="2" fill="{col}"/>',
           f'<text x="{x+w/2}" y="{y+11}" text-anchor="middle" font-family="DejaVu Sans" font-size="5" font-weight="700" fill="#FFF">{html.escape(title)}</text>']
    if delivery:
        parts.append(f'<circle cx="{x+w/2}" cy="{y+34}" r="10" fill="{pale}" stroke="{col}" stroke-width="1"/>')
        parts.append(f'<text x="{x+w/2}" y="{y+37}" text-anchor="middle" font-family="DejaVu Sans" font-size="10" font-weight="700" fill="{col}">↔</text>')
    else:
        icon_path=card.get("icon_image")
        if icon_path:
            icon_size=min(w*0.56, 27)
            parts.append(embedded_png_svg(icon_path, x+(w-icon_size)/2, y+20.2, icon_size, icon_size))
        else:
            parts.append(f'<circle cx="{x+w/2}" cy="{y+34}" r="10" fill="{pale}" stroke="{col}" stroke-width="1"/>')
            parts.append(trade_symbol_svg(card.get("symbol","circle"), x+w/2, y+34, 15, col, 1.1))
    yy=y+51 if delivery else y+50
    for ln in lines:
        weight="700" if delivery and ln!="till" else "400"
        parts.append(f'<text x="{x+w/2}" y="{yy}" text-anchor="middle" font-family="DejaVu Sans" font-size="{"4.4" if delivery else "3.5"}" font-weight="{weight}" fill="#203039">{html.escape(ln)}</text>')
        yy+=6 if delivery else 5
    parts += [f'<line x1="{x+5}" y1="{y+h-13}" x2="{x+w-5}" y2="{y+h-13}" stroke="#BCC4C8" stroke-width="0.3"/>']
    if not delivery:
        parts.append(trade_symbol_svg(card.get("symbol","circle"), x+8, y+h-8.2, 4.5, col, 0.55))
    parts += [f'<text x="{x+w/2}" y="{y+h-7}" text-anchor="middle" font-family="DejaVu Sans" font-size="4" font-weight="700" fill="{col}">{footer}</text>',
              f'<text x="{x+w-4}" y="{y+h-3}" text-anchor="end" font-family="DejaVu Sans" font-size="2.4" fill="#6D777C">{cid}</text>']
    return parts


def build_card_sheets(items, stem, delivery=False):
    """Build compact cards using the active profile in data/print-layouts.yaml."""
    layout_data = yaml.safe_load((ROOT/"data"/"print-layouts.yaml").read_text(encoding="utf-8"))
    profile = layout_data["card_profiles"][layout_data["active_card_profile"]]
    page_w, page_h = 210, 297
    cols, rows = profile["columns"], profile["rows"]
    card_w, card_h = profile["card_width_mm"], profile["card_height_mm"]
    margin_x, margin_y = profile["margin_x_mm"], profile["margin_y_mm"]
    gap_x, gap_y = profile["gap_x_mm"], profile["gap_y_mm"]
    xs = [margin_x + i*(card_w+gap_x) for i in range(cols)]
    ys = [margin_y + i*(card_h+gap_y) for i in range(rows)]
    per_page = cols*rows
    page_pdfs = []

    for pg in range((len(items)+per_page-1)//per_page):
        chunk = items[pg*per_page:(pg+1)*per_page]
        s = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{page_w}mm" height="{page_h}mm" viewBox="0 0 {page_w} {page_h}">',
            '<rect width="210" height="297" fill="#FFFFFF"/>'
        ]
        for idx, item in enumerate(chunk):
            x, y = xs[idx % cols], ys[idx // cols]
            s += compact_card_svg(item, x, y, card_w, card_h, delivery)
        s.append("</svg>")
        svg = SVG_CARDS/f"{stem}-p{pg+1:02d}.svg"
        svg.write_text("\n".join(s), encoding="utf-8")
        pdf = PDF_CARDS/f"_{stem}-p{pg+1:02d}.pdf"
        svg_to_pdf(svg, pdf)
        page_pdfs.append(pdf)

    merge_pdfs(page_pdfs, PDF_CARDS/f"{stem}.pdf")
    for p in page_pdfs:
        p.unlink()


def compact_card_svg(card, x, y, w, h, delivery=False):
    """Compact 4x4 card optimized for clear table reading and low toner use."""
    if delivery:
        col, pale = "#1F596E", "#E1EFF3"
        title = card["cargo"].upper()
        main_lines = [card["from"], "TILL", card["to"]]
        footer = f'{card["points"]} POÄNG'
        cid = card["id"]
    else:
        col, pale = COLORS[card["type"]]
        title = card["name"].upper()
        main_lines = [] if card["type"] != "handelsvind" else ["JOKER", "MAX 1 / BYGGE"]
        footer = "HANDELSSIGILL"
        cid = card["id"]

    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2.3" fill="#FFFDF8" stroke="#222" stroke-width="0.4"/>',
        f'<rect x="{x+1.5}" y="{y+1.5}" width="{w-3}" height="12" rx="1.5" fill="{col}"/>',
        f'<text x="{x+w/2}" y="{y+9}" text-anchor="middle" font-family="DejaVu Sans" font-size="4.1" font-weight="700" fill="#FFF">{html.escape(title)}</text>',
    ]
    if delivery:
        parts.append(f'<circle cx="{x+w/2}" cy="{y+27}" r="8.5" fill="{pale}" stroke="{col}" stroke-width="0.9"/>')
        parts.append(
            f'<text x="{x+w/2}" y="{y+30.4}" text-anchor="middle" font-family="DejaVu Sans" font-size="9" font-weight="700" fill="{col}">↔</text>'
        )
    elif card["type"]=="handelsvind":
        parts.append(f'<circle cx="{x+w/2}" cy="{y+27}" r="8.5" fill="{pale}" stroke="{col}" stroke-width="0.9"/>')
        parts.append(
            f'<text x="{x+w/2}" y="{y+30.4}" text-anchor="middle" font-family="DejaVu Sans" font-size="9" font-weight="700" fill="{col}">✦</text>'
        )
    else:
        icon_path=card.get("icon_image")
        if icon_path:
            icon_size=min(w*0.58,26)
            parts.append(embedded_png_svg(icon_path,x+(w-icon_size)/2,y+15.5,icon_size,icon_size))
        else:
            parts.append(f'<circle cx="{x+w/2}" cy="{y+27}" r="8.5" fill="{pale}" stroke="{col}" stroke-width="0.9"/>')
            parts.append(trade_symbol_svg(card.get("symbol","circle"),x+w/2,y+27,13,col,0.9))

    yy = y + 42
    for line in main_lines:
        size = 3.7 if delivery else 3.1
        weight = "700" if line != "TILL" else "400"
        parts.append(
            f'<text x="{x+w/2}" y="{yy}" text-anchor="middle" font-family="DejaVu Sans" font-size="{size}" font-weight="{weight}" fill="#203039">{html.escape(line)}</text>'
        )
        yy += 5.2

    parts += [
        f'<line x1="{x+4}" y1="{y+h-10.5}" x2="{x+w-4}" y2="{y+h-10.5}" stroke="#BCC4C8" stroke-width="0.3"/>',
    ]
    if not delivery:
        parts.append(trade_symbol_svg(card.get("symbol","star"),x+6.5,y+h-6.5,4.0,col,0.5))
    parts += [
        f'<text x="{x+w/2}" y="{y+h-5.7}" text-anchor="middle" font-family="DejaVu Sans" font-size="3.2" font-weight="700" fill="{col}">{footer}</text>',
        f'<text x="{x+w-2.8}" y="{y+h-2.2}" text-anchor="end" font-family="DejaVu Sans" font-size="2" fill="#6D777C">{cid}</text>',
    ]
    return parts


def quick_reference_inner(offset_x=0, offset_y=0):
    """A6 player aid content without an outer SVG wrapper."""
    ox, oy = offset_x, offset_y
    p = [
        f'<rect x="{ox+3}" y="{oy+3}" width="99" height="142" rx="3" fill="#FFFDF8" stroke="#263A43" stroke-width="0.6"/>',
        f'<rect x="{ox+3}" y="{oy+3}" width="99" height="21" rx="3" fill="#1F596E"/>',
        f'<text x="{ox+9}" y="{oy+13}" font-family="DejaVu Sans" font-size="6.7" font-weight="700" fill="#FFF">HANDELSVINDAR</text>',
        f'<text x="{ox+9}" y="{oy+19}" font-family="DejaVu Sans" font-size="3.0" fill="#DDEBF0">SNABBREFERENS {VERSION}</text>',
    ]
    # Approved trade-seal illustrations.
    icon_items=[
        ("blå","assets/icons/trade-seals/blue-trade-seal.png"),
        ("röd","assets/icons/trade-seals/red-trade-seal.png"),
        ("grön","assets/icons/trade-seals/green-trade-seal.png"),
        ("lila","assets/icons/trade-seals/purple-trade-seal.png"),
    ]
    for i,(label,path) in enumerate(icon_items):
        x=ox+17+i*23
        p.append(embedded_png_svg(path,x-6,oy+25,12,12))
        p.append(f'<text x="{x}" y="{oy+40}" text-anchor="middle" font-family="DejaVu Sans" font-size="2.6" fill="#263238">{label.upper()}</text>')
    sections = [
        ("DIN TUR - VÄLJ EN", ["1  Ta två handelssigillkort", "2  Bygg en handelsled", "3  Genomför en leverans"]),
        ("BYGGPOÄNG", ["Kostnad 1 / 2 / 3 / 4", "Poäng   1 / 2 / 4 / 6"]),
        ("HANDELSVIND", ["Joker för valfri ledfärg", "Max 1 joker per bygge", "Öppen joker = bara 1 kort"]),
        ("EFTERFRÅGAN", ["Första leveransen: +2 poäng", "Tredje och senare: -2 poäng"]),
        ("NÄTVERKSBONUS", ["Största sammanhängande nätverk: 7 poäng"]),
        ("SPELETS SLUT", ["5 eller färre ledmarkörer", "Alla får en sista tur"]),
    ]
    y = oy + 47
    for title, lines in sections:
        box_h = 6 + len(lines)*4.0
        p.append(f'<rect x="{ox+8}" y="{y-4}" width="89" height="{box_h}" rx="2" fill="#E7F0F2"/>')
        p.append(f'<text x="{ox+13}" y="{y}" font-family="DejaVu Sans" font-size="3.4" font-weight="700" fill="#1F596E">{title}</text>')
        yy = y + 4.6
        for line in lines:
            p.append(f'<text x="{ox+14}" y="{yy}" font-family="DejaVu Sans" font-size="2.9" fill="#263238">{html.escape(line)}</text>')
            yy += 4.0
        y += box_h + 2.0
    return p


def build_quick_reference():
    # A6 master
    a6 = ['<svg xmlns="http://www.w3.org/2000/svg" width="105mm" height="148mm" viewBox="0 0 105 148">']
    a6 += ['<rect width="105" height="148" fill="#F5F1E7"/>']
    a6 += quick_reference_inner()
    a6.append("</svg>")
    a6_svg = SVG_AIDS/f"quick-reference-a6-{VERSION}.svg"
    a6_svg.write_text("\n".join(a6), encoding="utf-8")
    svg_to_pdf(a6_svg, PDF_AIDS/f"quick-reference-a6-{VERSION}.pdf")

    # Four identical A6 aids imposed on one A4 sheet.
    a4 = ['<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">',
          '<rect width="210" height="297" fill="#FFFFFF"/>']
    for ox, oy in [(0, 0), (105, 0), (0, 148.5), (105, 148.5)]:
        a4 += quick_reference_inner(ox, oy)
    a4 += [
        '<line x1="105" y1="0" x2="105" y2="297" stroke="#888" stroke-width="0.25" stroke-dasharray="2,2"/>',
        '<line x1="0" y1="148.5" x2="210" y2="148.5" stroke="#888" stroke-width="0.25" stroke-dasharray="2,2"/>',
        '</svg>'
    ]
    a4_svg = SVG_AIDS/f"quick-reference-a4-4up-{VERSION}.svg"
    a4_svg.write_text("\n".join(a4), encoding="utf-8")
    svg_to_pdf(a4_svg, PDF_AIDS/f"quick-reference-a4-4up-{VERSION}.pdf")


def markdown_body(md):
    """Convert the limited rulebook Markdown subset into predictable HTML."""
    body = []
    in_list = False
    for line in md.splitlines():
        if line.startswith("# "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{html.escape(line[2:])}</li>")
        elif re.match(r"^\d+\. ", line):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<p class='step'>{html.escape(line)}</p>")
        elif not line.strip():
            if in_list:
                body.append("</ul>")
                in_list = False
        else:
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        body.append("</ul>")
    return "".join(body[1:])


def build_marker_sheet():
    """Build a low-ink A4 marker reference/cut sheet."""
    page_w,page_h=210,297
    parts=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{page_w}mm" height="{page_h}mm" viewBox="0 0 {page_w} {page_h}">',
        '<rect width="210" height="297" fill="#FFFFFF"/>',
        '<text x="15" y="18" font-family="DejaVu Sans" font-size="7" font-weight="700" fill="#26383E">HANDELSVINDAR - MARKÖRARK</text>',
        f'<text x="15" y="25" font-family="DejaVu Sans" font-size="3" fill="#58686B">{VERSION}</text>',
        '<text x="15" y="36" font-family="DejaVu Sans" font-size="4" font-weight="700" fill="#26383E">EFTERFRÅGEMARKÖRER - 16 ST</text>',
    ]
    for i in range(16):
        col,row=i%8,i//8
        x=22+col*22
        y=49+row*19
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="6.5" fill="#F4D37A" stroke="#26383E" stroke-width="0.45"/>'
        )
        parts.append(
            f'<text x="{x}" y="{y+1.4}" text-anchor="middle" font-family="DejaVu Sans" font-size="3.5" font-weight="700" fill="#26383E">E</text>'
        )

    player_colors=[
        ("SPELARE 1","#2A718D"),("SPELARE 2","#B45445"),
        ("SPELARE 3","#4F8461"),("SPELARE 4","#715298")
    ]
    base_y=94
    for pidx,(label,color) in enumerate(player_colors):
        y0=base_y+pidx*45
        parts.append(
            f'<text x="15" y="{y0}" font-family="DejaVu Sans" font-size="4" font-weight="700" fill="#26383E">{label} - 20 LEDMARKÖRER</text>'
        )
        for i in range(20):
            col,row=i%10,i//10
            x=20+col*18
            y=y0+11+row*14
            parts.append(
                f'<circle cx="{x}" cy="{y}" r="4.2" fill="{color}" stroke="#26383E" stroke-width="0.35"/>'
            )
    parts += [
        '<text x="15" y="281" font-family="DejaVu Sans" font-size="2.8" fill="#58686B">Klipp ut markörerna eller använd pärlor/kuber i motsvarande färger.</text>',
        '</svg>'
    ]
    svg_path=SVG_COMPONENTS/f"markers-a4-{VERSION}.svg"
    pdf_path=PDF_COMPONENTS/f"markers-a4-{VERSION}.pdf"
    svg_path.write_text("\n".join(parts),encoding="utf-8")
    svg_to_pdf(svg_path,pdf_path)


def build_rulebook():
    md = (ROOT/"docs"/"rulebook.md").read_text(encoding="utf-8")
    html_doc = render_template(ROOT/"templates"/"rulebook"/"rulebook.html", {
        "CONTENT": markdown_body(md), "VERSION": VERSION
    })
    (OUT_PREVIEW/"rulebook.html").write_text(html_doc, encoding="utf-8")
    out_pdf = PDF_DOCS/f"rulebook-{VERSION}.pdf"
    if HTML is not None and CSS is not None:
        css = (ROOT/"templates"/"rulebook"/"rulebook.css").read_text(encoding="utf-8")
        HTML(string=html_doc, base_url=str(ROOT)).write_pdf(
            str(out_pdf), stylesheets=[CSS(string=css)]
        )
        return

    # Portable PDF build for environments without WeasyPrint system libraries.
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, KeepTogether
    )

    styles = getSampleStyleSheet()
    ink=colors.HexColor("#26383E")
    teal=colors.HexColor("#1F596E")
    muted=colors.HexColor("#58686B")
    pale=colors.HexColor("#E7F0F2")

    styles.add(ParagraphStyle(
        name="HVTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=24, leading=28, alignment=TA_CENTER, textColor=ink,
        spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        name="HVSubtitle", parent=styles["Normal"], fontName="Helvetica",
        fontSize=10, leading=14, alignment=TA_CENTER, textColor=muted,
        spaceAfter=14
    ))
    styles.add(ParagraphStyle(
        name="HVH2", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=14, leading=17, spaceBefore=12, spaceAfter=5,
        textColor=teal, keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name="HVH3", parent=styles["Heading3"], fontName="Helvetica-Bold",
        fontSize=11, leading=14, spaceBefore=8, spaceAfter=3,
        textColor=ink, keepWithNext=True
    ))
    styles.add(ParagraphStyle(
        name="HVBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.2, leading=12.5, textColor=colors.HexColor("#202B30"),
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="HVBullet", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.2, leading=12.5, leftIndent=12, firstLineIndent=-7,
        bulletIndent=3, textColor=colors.HexColor("#202B30"), spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name="HVNumber", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.2, leading=12.5, leftIndent=14, firstLineIndent=-10,
        textColor=colors.HexColor("#202B30"), spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name="HVCallout", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=9.4, leading=13, leftIndent=8, rightIndent=8,
        borderColor=teal, borderWidth=0.6, borderPadding=7,
        backColor=pale, textColor=ink, spaceBefore=5, spaceAfter=7
    ))

    def safe(s):
        return html.escape(s, quote=False)

    story=[]
    first_heading=True
    for raw in md.splitlines():
        s=raw.strip()
        if not s:
            story.append(Spacer(1,3))
            continue
        if s.startswith("# "):
            story.append(Paragraph(safe(s[2:]),styles["HVTitle"]))
            story.append(Paragraph(
                "Regelbok för 2-4 spelare | 30-45 minuter | 8 år och uppåt",
                styles["HVSubtitle"]
            ))
            first_heading=False
        elif s.startswith("## "):
            story.append(Paragraph(safe(s[3:]),styles["HVH2"]))
        elif s.startswith("### "):
            story.append(Paragraph(safe(s[4:]),styles["HVH3"]))
        elif s.startswith("Viktigt:"):
            story.append(Paragraph(safe(s),styles["HVCallout"]))
        elif re.match(r"^\d+\.\s+",s):
            m=re.match(r"^(\d+)\.\s+(.*)",s)
            story.append(Paragraph(f"<b>{m.group(1)}.</b> {safe(m.group(2))}",styles["HVNumber"]))
        elif s.startswith("- "):
            story.append(Paragraph("• "+safe(s[2:]),styles["HVBullet"]))
        elif s.startswith("```"):
            continue
        else:
            story.append(Paragraph(safe(s),styles["HVBody"]))

    def footer(canvas,doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#B8C5C9"))
        canvas.setLineWidth(0.35)
        canvas.line(18*mm,14*mm,192*mm,14*mm)
        canvas.setFont("Helvetica",7.5)
        canvas.setFillColor(muted)
        canvas.drawString(18*mm,9*mm,f"Handelsvindar {VERSION}")
        canvas.drawRightString(192*mm,9*mm,f"Sida {doc.page}")
        canvas.restoreState()

    doc=SimpleDocTemplate(
        str(out_pdf), pagesize=A4,
        rightMargin=18*mm,leftMargin=18*mm,
        topMargin=16*mm,bottomMargin=20*mm,
        title=f"Handelsvindar {VERSION}",
        author="Handelsvindar"
    )
    doc.build(story,onFirstPage=footer,onLaterPages=footer)


def build_trade_seal_icon_reference():
    """Build an A4 visual reference sheet from the approved PNG icon assets."""
    items=[
        ("BLÅTT SIGILL","assets/icons/trade-seals/blue-trade-seal.png","#2A718D"),
        ("RÖTT SIGILL","assets/icons/trade-seals/red-trade-seal.png","#B45445"),
        ("GRÖNT SIGILL","assets/icons/trade-seals/green-trade-seal.png","#4F8461"),
        ("LILA SIGILL","assets/icons/trade-seals/purple-trade-seal.png","#715298"),
    ]
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">',
           '<rect width="210" height="297" fill="#FFFDF8"/>',
           f'<text x="15" y="19" font-family="DejaVu Sans" font-size="8" font-weight="700" fill="#26383E">HANDELSVINDAR – HANDELSSIGILL</text>',
           f'<text x="15" y="26" font-family="DejaVu Sans" font-size="3.2" fill="#58686B">{VERSION} / PNG-ikonreferens</text>']
    positions=[(20,42),(110,42),(20,155),(110,155)]
    for (title,path,color),(x,y) in zip(items,positions):
        parts.append(f'<rect x="{x}" y="{y}" width="80" height="96" rx="4" fill="#FFFFFF" stroke="{color}" stroke-width="0.8"/>')
        parts.append(embedded_png_svg(path,x+12,y+8,56,56))
        parts.append(f'<text x="{x+40}" y="{y+73}" text-anchor="middle" font-family="DejaVu Sans" font-size="5" font-weight="700" fill="{color}">{title}</text>')
        parts.append(f'<text x="{x+40}" y="{y+82}" text-anchor="middle" font-family="DejaVu Sans" font-size="3" fill="#26383E">Transparent PNG, 512 × 512 px</text>')
    parts.append('</svg>')
    svg_path=OUT_SVG/f"trade-seal-icons-reference-{VERSION}.svg"
    pdf_path=OUT_PDF/f"trade-seal-icons-reference-{VERSION}.pdf"
    svg_path.write_text("\n".join(parts),encoding="utf-8")
    svg_to_pdf(svg_path,pdf_path)


def write_manifest():
    pdfs = []
    for p in sorted(OUT_PDF.rglob("*.pdf")):
        pdfs.append({
            "file": str(p.relative_to(ROOT)),
            "pages": len(PdfReader(str(p)).pages),
        })
    manifest = {
        "version": VERSION,
        "build_flow": "YAML/Markdown + templates -> SVG/HTML -> PDF",
        "active_card_profile": "compact_4x4",
        "pdfs": pdfs,
    }
    (ROOT/"output"/"PRINT_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    clean_generated_outputs()
    build_board()
    build_card_sheets(CARDS, f"route-cards-compact-4x4-{VERSION}", False)
    build_card_sheets(DELIVERIES, f"delivery-cards-compact-4x4-{VERSION}", True)
    build_quick_reference()
    build_marker_sheet()
    build_trade_seal_icon_reference()
    build_rulebook()
    write_manifest()
    print("Build complete:", OUT_PDF)


if __name__ == "__main__":
    main()
