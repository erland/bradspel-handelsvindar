#!/usr/bin/env python3
"""Validate structured Handelsvindar rules and cross-file references."""
from pathlib import Path
import json, sys, yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

def load_yaml(name):
    return yaml.safe_load((ROOT/name).read_text(encoding="utf-8"))

def main():
    errors = []
    rules_doc = load_yaml("data/rules.yaml")
    schema = json.loads((ROOT/"schemas/rules.schema.json").read_text(encoding="utf-8"))
    for err in Draft202012Validator(schema).iter_errors(rules_doc):
        errors.append("schema: " + " / ".join(map(str, err.path)) + ": " + err.message)

    rules = rules_doc["rules"]
    board = load_yaml("data/board.yaml")["board"]
    cards = load_yaml("data/cards.yaml")["route_cards"]
    deliveries = load_yaml("data/deliveries.yaml")["deliveries"]
    ports = {p["name"] for p in board["ports"]}
    route_colors = {c["route_type"] for c in board["connections"]}
    card_types = {c["type"] for c in cards}

    if rules["players"]["min"] > rules["players"]["max"]:
        errors.append("players.min får inte vara större än players.max")
    if rules["turn"]["actions_per_turn"] != 1:
        errors.append("regelboken förutsätter exakt en handling per tur")
    if rules["build_route"]["wild_card_type"] not in card_types:
        errors.append("wild_card_type saknas i cards.yaml")
    missing_route_card_types = sorted(route_colors - card_types)
    if missing_route_card_types:
        errors.append("ledfärger utan motsvarande handelssigillkort: " + ", ".join(missing_route_card_types))
    for delivery in deliveries:
        if delivery["from"] not in ports or delivery["to"] not in ports:
            errors.append(f'{delivery["id"]}: okänd hamn i leveransen')
    if set(rules["setup"]["route_markers_by_player_count"]) != {"2","3","4"}:
        errors.append("route_markers_by_player_count måste innehålla 2, 3 och 4 spelare")

    if rules["setup"].get("demand_marker_supply") != len(deliveries):
        errors.append("antal efterfrågemarkörer ska matcha antal leveranskort")
    if not rules["draw_route_cards"].get("discard_pile_used"):
        errors.append("kasthögen måste användas för handelssigillkort")
    if rules["draw_route_cards"].get("when_deck_empty") != "shuffle_discard_pile_to_new_deck":
        errors.append("regel för tom handelssigillkortlek saknas eller är fel")
    if rules["complete_delivery"].get("when_delivery_deck_empty") != "do_not_refill_empty_slot":
        errors.append("regel för tom leveranslek saknas eller är fel")

    if errors:
        print("VALIDATION FAILED")
        for e in errors:
            print("-", e)
        return 1
    print("VALIDATION OK")
    print(f'- {len(ports)} hamnar')
    print(f'- {len(board["connections"])} rutter')
    print(f'- {len(cards)} handelssigillkort')
    print(f'- {len(deliveries)} leveranser')
    return 0

if __name__ == "__main__":
    sys.exit(main())
