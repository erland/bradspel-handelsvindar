#!/usr/bin/env python3
"""Fast source validation for Handelsvindar, usable locally and in GitHub Actions."""

from __future__ import annotations

import argparse
import json
import re
import runpy
import sys
from pathlib import Path

import yaml
from PIL import Image

REQUIRED_PATHS = (
    "README.md",
    "PROJECT_STATUS.md",
    "CHANGELOG.md",
    "data/board.yaml",
    "data/board-layout.yaml",
    "data/board-theme.yaml",
    "data/cards.yaml",
    "data/deliveries.yaml",
    "data/game.yaml",
    "data/rules.yaml",
    "data/print-layouts.yaml",
    "data/release.yaml",
    "data/trade-seal-icons.yaml",
    "docs/rulebook.md",
    "docs/production-guide.md",
    "scripts/build_all.py",
    "scripts/validate_rules.py",
    "scripts/check_rulebook_consistency.py",
    "assets/backgrounds/master/board-background-master-v0.24.png",
)

SOURCE_VALIDATORS = (
    "scripts/validate_rules.py",
    "scripts/check_rulebook_consistency.py",
    "scripts/check_board_layout.py",
)

VERSIONED_SOURCES = {
    "board": ("data/board.yaml", "board"),
    "board_layout": ("data/board-layout.yaml", "board_layout"),
    "board_theme": ("data/board-theme.yaml", "board_theme"),
    "game": ("data/game.yaml", "game"),
    "rules": ("data/rules.yaml", "rules"),
    "strategies": ("data/strategies.yaml", "strategic_simulation"),
}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)
    print(f"ERROR: {message}", file=sys.stderr)


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument(
        "--expected-tag",
        default="",
        help="Optional Git tag, e.g. v2.1. Must match the project version.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors: list[str] = []

    for rel in REQUIRED_PATHS:
        if not (root / rel).exists():
            fail(errors, f"Obligatorisk projektsökväg saknas: {rel}")

    if errors:
        return 1

    # YAML parse check.
    for path in sorted((root / "data").rglob("*.yaml")):
        try:
            load_yaml(path)
        except Exception as exc:
            fail(errors, f"Ogiltig YAML i {path.relative_to(root)}: {exc}")

    if errors:
        return 1

    release_cfg = load_yaml(root / "data/release.yaml")
    version = str(release_cfg.get("version", ""))
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?(?:-[0-9A-Za-z.-]+)?", version):
        fail(errors, f"Ogiltigt release-versionformat: {version!r}")

    if args.expected_tag:
        expected = f"v{version}"
        if args.expected_tag != expected:
            fail(
                errors,
                f"Git-taggen {args.expected_tag!r} matchar inte projektversionen {expected!r}.",
            )

    # Version alignment.
    for label, (rel, key) in VERSIONED_SOURCES.items():
        obj = load_yaml(root / rel)[key]
        found = str(obj.get("version", ""))
        if found != version:
            fail(errors, f"{label}: version {found!r}, väntat {version!r}")

    print_layouts = load_yaml(root / "data/print-layouts.yaml")
    if str(print_layouts.get("version", "")) != version:
        fail(errors, "data/print-layouts.yaml har fel version.")

    rulebook = (root / "docs/rulebook.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    if f"v{version}" not in rulebook:
        fail(errors, "Regelboken saknar aktuell version i rubriken.")
    if f"v{version}" not in readme:
        fail(errors, "README saknar aktuell version.")

    # Printables are source-of-truth for preview/release publishing.
    printables = release_cfg.get("printables") or []
    if not printables:
        fail(errors, "data/release.yaml innehåller inga printfiler.")

    ids: set[str] = set()
    names: set[str] = set()
    sources: set[str] = set()
    for item in printables:
        pid = str(item.get("id", ""))
        name = str(item.get("release_name", ""))
        source = str(item.get("source", ""))
        if not pid or not name or not source:
            fail(errors, f"Ofullständig printpost: {item}")
            continue
        if pid in ids:
            fail(errors, f"Dubblett-id i printfiler: {pid}")
        if name in names:
            fail(errors, f"Dubblettfilnamn i release: {name}")
        if source in sources:
            fail(errors, f"Samma output används två gånger: {source}")
        ids.add(pid)
        names.add(name)
        sources.add(source)
        if not name.lower().endswith(".pdf"):
            fail(errors, f"Releasefil är inte PDF: {name}")
        if f"v{version}" not in Path(source).name:
            fail(errors, f"Printkälla har fel version: {source}")

    required_print_ids = {
        "board_standard",
        "board_ink_friendly",
        "trade_seal_cards",
        "delivery_cards",
        "markers",
        "quick_reference_a6",
        "quick_reference_a4_4up",
        "rulebook",
    }
    missing_ids = sorted(required_print_ids - ids)
    if missing_ids:
        fail(errors, "Obligatoriska printfiler saknas: " + ", ".join(missing_ids))

    # Board data/layout must describe the same graph.
    board = load_yaml(root / "data/board.yaml")["board"]
    layout = load_yaml(root / "data/board-layout.yaml")["board_layout"]
    board_ports = {p["name"] for p in board["ports"]}
    layout_ports = {p["name"] for p in layout["ports"]}
    if board_ports != layout_ports:
        fail(errors, "Portmängden skiljer sig mellan board.yaml och board-layout.yaml.")

    board_routes = {r["id"] for r in board["connections"]}
    layout_routes = {r["id"] for r in layout["routes"]}
    if board_routes != layout_routes:
        fail(errors, "Rutt-ID skiljer sig mellan board.yaml och board-layout.yaml.")

    # Card/icon coherence.
    cards = load_yaml(root / "data/cards.yaml")["route_cards"]
    icon_cfg = load_yaml(root / "data/trade-seal-icons.yaml")
    icon_paths = {
        typ: item["file"] for typ, item in (icon_cfg.get("icons") or {}).items()
    }
    for card in cards:
        typ = card["type"]
        icon_image = card.get("icon_image")
        if typ in {"blå", "röd", "grön", "lila"}:
            if not icon_image:
                fail(errors, f"{card['id']} saknar icon_image.")
            elif not (root / icon_image).exists():
                fail(errors, f"{card['id']} refererar saknad ikon: {icon_image}")
            elif icon_paths.get(typ) != icon_image:
                fail(errors, f"{card['id']} och trade-seal-icons.yaml är osynkroniserade.")

    # Check master background is readable.
    bg = root / "assets/backgrounds/master/board-background-master-v0.24.png"
    try:
        with Image.open(bg) as image:
            image.verify()
    except Exception as exc:
        fail(errors, f"Bakgrundsbilden kan inte läsas: {exc}")

    # Compile build script and run fast source validators in-process.
    try:
        build_source = (root / "scripts/build_all.py").read_text(encoding="utf-8")
        compile(build_source, str(root / "scripts/build_all.py"), "exec")
    except Exception as exc:
        fail(errors, f"scripts/build_all.py kan inte kompileras: {exc}")

    for validator in SOURCE_VALIDATORS:
        try:
            runpy.run_path(str(root / validator), run_name="__main__")
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            if code:
                fail(errors, f"{validator} misslyckades.")
        except Exception as exc:
            fail(errors, f"{validator} kunde inte köras: {exc}")

    # Only one release directory may be committed.
    release_root = root / "release"
    if release_root.exists():
        release_dirs = sorted(p.name for p in release_root.iterdir() if p.is_dir())
        if len(release_dirs) > 1:
            fail(errors, "Fler än en releasekatalog finns: " + ", ".join(release_dirs))
        if release_dirs and release_dirs[0] != f"v{version}":
            fail(errors, f"Releasekatalog {release_dirs[0]} matchar inte v{version}.")

    if errors:
        print(f"\nValidation failed: {len(errors)} error(s).", file=sys.stderr)
        return 1

    print(
        f"OK: Handelsvindar v{version} är källmässigt konsistent. "
        f"{len(board_ports)} platser, {len(board_routes)} rutter, "
        f"{len(printables)} printfiler."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
