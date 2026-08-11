# Handelsvindar

## Versionsprincip

Projektets aktuella releaseversion finns endast i filen:

```text
VERSION
```

Övriga källfiler ska normalt inte innehålla projektets releaseversion. Bygg- och releaseverktygen läser `VERSION` när versionsmetadata behövs.

`CHANGELOG.md` innehåller naturligtvis historiska versionsrubriker. Se även `docs/versioning.md`.

## Princip

Repositoryt innehåller källor och **godkända produktionsassets**, men inte genererade PDF-/SVG-/releaseprodukter.

Versionshanteras:

- `VERSION`
- `data/`
- `docs/`
- `templates/`
- `scripts/`
- masterbakgrunden
- AI-källarket för handelssigillen
- de fyra godkända PNG-filerna i `assets/icons/trade-seals/`

Versionshanteras inte:

- `output/`
- `release/`
- lokala `build/`- och `dist/`-mappar

## Handelssigill

De fyra PNG-filerna i `assets/icons/trade-seals/` är godkända produktionsassets och ska ligga kvar i Git.

`assets/icons/source/trade-seals-generated-sheet-v1.1.png` behålls som ursprungligt AI-genererat källark. Versionsdelen i det filnamnet avser själva grafikasseten, inte projektets releaseversion.

`scripts/build_trade_seal_icons.py` är ett manuellt asset-verktyg och körs inte automatiskt av preview- eller releasebyggen.

## GitHub Actions

- **Validate** kontrollerar källor, regler, versionsfil, sammanhang och godkända PNG-assets.
- **Build Print Preview** bygger samtliga printfiler med stabila, versionsfria filnamn.
- **Release Print-and-Play** läser versionen från `VERSION`, kontrollerar Git-taggen och publicerar printfiler samt en versionsmärkt print-and-play-zip.

## Lokalt

Källren validering:

```bash
python -m pip install -r requirements-validation.txt
python scripts/validate_project.py . --repository-clean
```

Komplett preview-build:

```bash
python -m pip install -r requirements-build.txt
python scripts/build_print_package.py --output-dir build/preview
```

Efter ett lokalt bygge kan `output/`, `build/` och `release/` raderas. De fyra godkända handelssigill-PNG:erna ska däremot behållas.
