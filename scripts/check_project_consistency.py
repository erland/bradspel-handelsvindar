#!/usr/bin/env python3
from pathlib import Path
import json, re, sys, yaml

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.3"
COLORS = {"blå", "röd", "grön", "lila"}
WILD = "handelsvind"

def y(rel):
    return yaml.safe_load((ROOT/rel).read_text(encoding="utf-8"))

errors=[]
warnings=[]

board=y("data/board.yaml")["board"]
layout=y("data/board-layout.yaml")["board_layout"]
cards=y("data/cards.yaml")["route_cards"]
rules=y("data/rules.yaml")["rules"]
game=y("data/game.yaml")["game"]
theme=y("data/board-theme.yaml")["board_theme"]
strategies=y("data/strategies.yaml")["strategic_simulation"]
print_layouts=y("data/print-layouts.yaml")
book=(ROOT/"docs/rulebook.md").read_text(encoding="utf-8")
readme=(ROOT/"README.md").read_text(encoding="utf-8")

# Version alignment for current sources.
versions={
    "board": str(board["version"]),
    "board_layout": str(layout["version"]),
    "rules": str(rules["version"]),
    "game": str(game["version"]),
    "theme": str(theme["version"]),
    "strategies": str(strategies["version"]),
    "print_layouts": str(print_layouts["version"]),
}
for name,value in versions.items():
    if value != VERSION:
        errors.append(f"{name}: version {value}, expected {VERSION}")
if f"v{VERSION}" not in book:
    errors.append("rulebook version heading is not current")
if f"v{VERSION}" not in readme:
    errors.append("README version is not current")

# Ports and routes.
board_ports={p["name"] for p in board["ports"]}
layout_ports={p["name"] for p in layout["ports"]}
if board_ports != layout_ports:
    errors.append("board/layout port sets differ")
board_routes={r["id"] for r in board["connections"]}
layout_routes={r["id"] for r in layout["routes"]}
if board_routes != layout_routes:
    errors.append("board/layout route ID sets differ")

route_colors={r["route_type"] for r in board["connections"]}
if route_colors != COLORS:
    errors.append(f"board route colors {sorted(route_colors)} != {sorted(COLORS)}")

card_types={c["type"] for c in cards}
if not COLORS.issubset(card_types) or WILD not in card_types:
    errors.append("card types do not cover four colors and Handelsvind")

# Canonical card names and counts.
expected_names={
    "blå":"Blått sigill",
    "röd":"Rött sigill",
    "grön":"Grönt sigill",
    "lila":"Lila sigill",
    "handelsvind":"Handelsvind",
}
for c in cards:
    if c["name"] != expected_names[c["type"]]:
        errors.append(f'{c["id"]}: unexpected card name {c["name"]}')

# Rules.
if rules["ruleset_id"] != "handelsvindar_core_v2_3":
    errors.append("ruleset_id is stale")
if "requires_matching_route_type" in rules["build_route"]:
    errors.append("legacy requires_matching_route_type remains")
if not rules["build_route"].get("requires_matching_route_color"):
    errors.append("requires_matching_route_color missing/false")
if rules["final_scoring"]["largest_connected_network_bonus"] != 7:
    errors.append("network bonus differs from canonical 7")


if rules["setup"].get("demand_marker_supply") != 16:
    errors.append("demand marker supply must be 16")
if rules["draw_route_cards"].get("when_deck_empty") != "shuffle_discard_pile_to_new_deck":
    errors.append("route-card deck exhaustion rule missing")
if rules["complete_delivery"].get("when_delivery_deck_empty") != "do_not_refill_empty_slot":
    errors.append("delivery-deck exhaustion rule missing")
if game.get("components",{}).get("demand_markers") != 16:
    errors.append("game component inventory does not list 16 demand markers")
if "16 efterfrågemarkörer" not in book:
    errors.append("rulebook component list does not say 16 demand markers")
if "blandar ni kasthögen" not in book:
    errors.append("rulebook lacks route-card reshuffle rule")
if "leveransleken är tom" not in book:
    errors.append("rulebook lacks empty delivery-deck rule")


expected_symbols={"blå":"circle","röd":"triangle","grön":"square","lila":"diamond","handelsvind":"star"}
for card in cards:
    if card.get("symbol") != expected_symbols.get(card["type"]):
        errors.append(f'wrong or missing symbol on {card["id"]}')
    if card["type"]!="handelsvind" and "handelssigill" in card["name"].lower():
        errors.append(f'route card title not shortened: {card["id"]}')
qr_svg=ROOT/"output/svg/player-aids/quick-reference-a6-v2.3.svg"
if not qr_svg.exists() or "BYGGPOÄNG" not in qr_svg.read_text(encoding="utf-8"):
    errors.append("quick reference lacks build points")


icon_manifest=ROOT/"data/trade-seal-icons.yaml"
if not icon_manifest.exists():
    errors.append("trade-seal icon manifest missing")
else:
    icon_data=yaml.safe_load(icon_manifest.read_text(encoding="utf-8"))
    for typ,item in icon_data.get("icons",{}).items():
        path=ROOT/item["file"]
        if not path.exists():
            errors.append(f"missing PNG icon for {typ}: {item['file']}")
        elif path.suffix.lower()!=".png":
            errors.append(f"icon for {typ} is not PNG")
for card in cards:
    if card["type"] in {"blå","röd","grön","lila"} and not card.get("icon_image"):
        errors.append(f'missing icon_image on {card["id"]}')

# Current prose must not revive terrain-specific route concepts.
current_text="\n".join(
    (ROOT/rel).read_text(encoding="utf-8")
    for rel in ["README.md","docs/design-brief.md","docs/rulebook.md","docs/production-guide.md"]
)
legacy_patterns=[
    r"\blandsväg\b", r"\bsjöled\b", r"\bskärgårdsled\b", r"\bflodled\b",
    r"\bfärdkort\b", r"\bruttyp(?:er|en)?\b",
]
for pat in legacy_patterns:
    if re.search(pat,current_text,re.I):
        errors.append(f"legacy current-doc term found: {pat}")

# Board SVGs intentionally have no visible version text.
# Verify the generated filename instead.
svg_dir=ROOT/"output/svg/board"
for svg in svg_dir.glob("*.svg"):
    if f"v{VERSION}" not in svg.name:
        errors.append(f"{svg.name}: stale version filename")
    

# Integrated route-cost layout.
standard_svg=svg_dir/f"board-a4-standard-v{VERSION}.svg"
if standard_svg.exists():
    board_svg=standard_svg.read_text(encoding="utf-8")
    expected_slots=sum(int(route["cost"]) for route in board["connections"])
    slot_count=board_svg.count('fill-opacity="0.82"')
    if slot_count != expected_slots:
        errors.append(f"marker slot count mismatch: {slot_count} != {expected_slots}")
    old_cost_circles=re.findall(
        r'<circle[^>]*r="3\.6"[^>]*stroke-width="0\.85"[^>]*filter="url\(#softShadow\)"[^>]*/>',
        board_svg,
    )
    if old_cost_circles:
        errors.append("separate cost circles remain on board")
    integrated_numbers=re.findall(
        r'<text x="[^"]+" y="[^"]+" font-family="DejaVu Sans" font-size="3\.2" '
        r'font-weight="700" text-anchor="middle" fill="[^"]+">([1-4])</text>',
        board_svg,
    )
    if len(integrated_numbers) != len(board["connections"]):
        errors.append(
            f"integrated cost number count mismatch: {len(integrated_numbers)} "
            f'!= {len(board["connections"])}'
        )

result={"version":VERSION,"errors":errors,"warnings":warnings,"count":len(errors)}
print(json.dumps(result,ensure_ascii=False,indent=2))
sys.exit(1 if errors else 0)
