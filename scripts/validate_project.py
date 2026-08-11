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
    "VERSION",
    "PROJECT_STATUS.md",
    "CHANGELOG.md",
    ".gitignore",
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
    "assets/icons/trade-seals/blue-trade-seal.png",
    "assets/icons/trade-seals/red-trade-seal.png",
    "assets/icons/trade-seals/green-trade-seal.png",
    "assets/icons/trade-seals/purple-trade-seal.png",
)

SOURCE_VALIDATORS = (
    "scripts/validate_rules.py",
    "scripts/check_rulebook_consistency.py",
    "scripts/check_board_layout.py",
)



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
        help="Optional Git tag, e.g. vX.Y. Must match VERSION.",
    )
    parser.add_argument(
        "--repository-clean",
        action="store_true",
        help="Fail if generated output/release files are present in the source tree.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors: list[str] = []

    # Check the checkout before any validator/build step is allowed to create
    # generated files of its own.
    if args.repository_clean:
        for generated_dir in ("output", "release", "build", "dist"):
            folder = root / generated_dir
            if folder.exists() and any(p.is_file() for p in folder.rglob("*")):
                fail(
                    errors,
                    f"Genererade filer finns i {generated_dir}/ i källcheckouten.",
                )

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
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?(?:-[0-9A-Za-z.-]+)?", version):
        fail(errors, f"Ogiltigt release-versionformat: {version!r}")

    if args.expected_tag:
        expected = f"v{version}"
        if args.expected_tag != expected:
            fail(
                errors,
                f"Git-taggen {args.expected_tag!r} matchar inte projektversionen {expected!r}.",
            )

    # Release version belongs only in VERSION. Content/config sources must not
    # carry a duplicate project release version.
    version_keys = []
    for path in sorted((root / "data").rglob("*.yaml")):
        rel = str(path.relative_to(root))
        raw = load_yaml(path)
        def walk(obj, node_path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    here = f"{node_path}.{key}" if node_path else str(key)
                    if key == "version":
                        version_keys.append(f"{rel}:{here}")
                    walk(value, here)
            elif isinstance(obj, list):
                for idx, value in enumerate(obj):
                    walk(value, f"{node_path}[{idx}]")
        walk(raw)
    if version_keys:
        fail(errors, "Projektversion ska inte dupliceras i YAML: " + ", ".join(version_keys))

    current_tag = f"v{version}"
    duplicated_tag_files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in {"VERSION", "CHANGELOG.md"}:
            continue
        if any(part in {"output", "release", "build", "dist"} for part in path.parts):
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".py", ".txt", ".html", ".css"}:
            continue
        try:
            source_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if current_tag in source_text:
            duplicated_tag_files.append(str(path.relative_to(root)))
    if duplicated_tag_files:
        fail(
            errors,
            "Aktuell releaseversion är hårdkodad utanför VERSION/CHANGELOG: "
            + ", ".join(duplicated_tag_files),
        )

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
    # The four approved PNG files are versioned production assets. The
    # original generated 2x2 sheet is retained as provenance/source material,
    # while normal builds consume the approved PNGs directly.
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
            elif icon_paths.get(typ) != icon_image:
                fail(errors, f"{card['id']} och trade-seal-icons.yaml är osynkroniserade.")
            elif not str(icon_image).startswith("assets/icons/trade-seals/"):
                fail(errors, f"{card['id']} har oväntad ikonplats: {icon_image}")
            else:
                icon_file = root / icon_image
                if not icon_file.exists():
                    fail(errors, f"{card['id']} refererar saknad godkänd PNG: {icon_image}")
                else:
                    try:
                        with Image.open(icon_file) as image:
                            if image.format != "PNG":
                                fail(errors, f"{icon_image} är inte en PNG-fil.")
                            if image.width < 256 or image.height < 256:
                                fail(errors, f"{icon_image} har oväntat låg upplösning.")
                            image.verify()
                    except Exception as exc:
                        fail(errors, f"{icon_image} kan inte läsas: {exc}")

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

    # Repository hygiene.
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    for required_ignore in (
        "/output/",
        "/release/",
        "/build/",
    ):
        if required_ignore not in gitignore:
            fail(errors, f".gitignore saknar {required_ignore}")


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
