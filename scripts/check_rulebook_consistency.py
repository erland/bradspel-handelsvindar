#!/usr/bin/env python3
"""Check selected rulebook statements against data/rules.yaml.

This is intentionally explicit rather than pretending to understand arbitrary prose.
"""
from pathlib import Path
import sys, yaml

ROOT = Path(__file__).resolve().parents[1]
rules = yaml.safe_load((ROOT/"data/rules.yaml").read_text(encoding="utf-8"))["rules"]
book = (ROOT/"docs/rulebook.md").read_text(encoding="utf-8").lower()

checks = [
    (f'ge varje spelare {rules["setup"]["starting_hand_size"]} kort', ["ge varje spelare fyra kort", "ge varje spelare 4 kort"]),
    (f'{rules["setup"]["open_route_card_slots"]} öppna handelssigillkort', ["fem handelssigillkort öppet", "5 handelssigillkort öppet"]),
    (f'{rules["setup"]["open_delivery_slots"]} öppna leveranser', ["fyra leveranskort öppet", "4 leveranskort öppet", "fyra öppet", "4 öppet"]),
    ("en handling per tur", ["exakt en huvudhandling"]),
    (f'max {rules["build_route"]["max_wild_cards_per_build"]} joker per bygge', ["högst ett handelsvindskort", "högst en handelsvind", "max 1 joker"]),
    (f'sluttröskel {rules["end_game"]["trigger_when_route_markers_at_or_below"]}', ["fem eller färre ledmarkörer", "5 eller färre ledmarkörer"]),
    (f'nätverksbonus {rules["final_scoring"]["largest_connected_network_bonus"]}', [f'{rules["final_scoring"]["largest_connected_network_bonus"]} bonuspoäng']),
    ("neutrala ledfärger", ["färgen visar bara vilket handelssigill", "beskriver inte ett särskilt färdsätt"]),
    ("16 efterfrågemarkörer", ["16 efterfrågemarkörer"]),
    ("omblandning av handelssigillkort", ["blandar ni kasthögen"]),
    ("tom leveranslek", ["leveransleken är tom"]),
    ("spelarroll", ["du leder ett av dessa handelsgillen", "du leder ett handelsgille"]),
    ("första partiet", ["första partiet"]),
    ("ordlista", ["ordlista"]),
    ("en handling, inte tre", ["du gör inte alla tre handlingarna"]),
    ("kostnad i ledplatser", ["antalet ledplatser är ledens kostnad"]),
]
failed = []
for label, alternatives in checks:
    if not any(x in book for x in alternatives):
        failed.append(label)

if failed:
    print("RULEBOOK CONSISTENCY WARNINGS")
    for x in failed:
        print("-", x)
    sys.exit(1)
print("RULEBOOK CONSISTENCY OK")
