#!/usr/bin/env python3
"""Build and package every canonical printable Handelsvindar PDF."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import runpy
import sys
import zipfile
from pathlib import Path

import yaml
from pypdf import PdfReader


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_pdf(path: Path) -> int:
    if not path.is_file() or path.stat().st_size < 1000:
        raise RuntimeError(f"PDF saknas eller är orimligt liten: {path}")
    reader = PdfReader(str(path))
    if len(reader.pages) < 1:
        raise RuntimeError(f"PDF saknar sidor: {path}")
    return len(reader.pages)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--package",
        action="store_true",
        help="Skapa även en print-and-play-zip i output-dir.",
    )
    parser.add_argument(
        "--expected-tag",
        default="",
        help="Kontrollera att taggen matchar projektversionen.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Validate in-process.
    old_argv = sys.argv[:]
    try:
        sys.argv = ["validate_project.py", str(root)]
        if args.expected_tag:
            sys.argv += ["--expected-tag", args.expected_tag]
        try:
            runpy.run_path(str(root / "scripts/validate_project.py"), run_name="__main__")
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            if code:
                return code
    finally:
        sys.argv = old_argv

    # Build printable artifacts from the approved, versioned production
    # assets. build_trade_seal_icons.py is deliberately NOT run here because
    # it is a manual asset-preparation tool and must not overwrite approved
    # PNG assets during preview/release builds.
    for script_name in (
        "build_all.py",
        "check_project_consistency.py",
    ):
        old_argv = sys.argv[:]
        try:
            sys.argv = [script_name]
            try:
                runpy.run_path(str(root / "scripts" / script_name), run_name="__main__")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                if code:
                    raise RuntimeError(f"{script_name} misslyckades med kod {code}")
        finally:
            sys.argv = old_argv

    cfg = yaml.safe_load((root / "data/release.yaml").read_text(encoding="utf-8"))
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    printables = cfg["printables"]

    # Clean output directory to avoid stale release assets.
    for child in output_dir.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)

    files = []
    for item in printables:
        source = root / item["source"]
        pages = verify_pdf(source)
        destination = output_dir / item["release_name"]
        shutil.copy2(source, destination)
        files.append(
            {
                "id": item["id"],
                "label": item["label"],
                "file": destination.name,
                "pages": pages,
                "size_bytes": destination.stat().st_size,
                "sha256": sha256(destination),
            }
        )

    manifest = {
        "project": cfg.get("project", "Handelsvindar"),
        "version": version,
        "ruleset_id": yaml.safe_load(
            (root / "data/rules.yaml").read_text(encoding="utf-8")
        )["rules"]["ruleset_id"],
        "files": files,
    }
    manifest_path = output_dir / "PRINT_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    readme = output_dir / "README.txt"
    readme.write_text(
        f"Handelsvindar v{version} - print-and-play\n\n"
        "PDF-filerna i denna katalog är det kanoniska utskriftspaketet.\n"
        "Välj standard- eller ink-friendly-kartan; övriga PDF-filer används "
        "efter behov enligt regelboken.\n",
        encoding="utf-8",
    )

    if args.package:
        package_name = f"{cfg['release_package_basename']}-v{version}.zip"
        package_path = output_dir / package_name
        members = [
            p for p in sorted(output_dir.iterdir())
            if p.is_file() and p != package_path
        ]
        with zipfile.ZipFile(
            package_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            for path in members:
                archive.write(path, arcname=path.name)
        print(f"OK: releasepaket skapat: {package_path}")

    print(
        f"OK: {len(files)} verifierade printfiler för Handelsvindar v{version} "
        f"skapade i {output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
