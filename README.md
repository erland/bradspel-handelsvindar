# Handelsvindar

## Version

v2.3 - källren print-and-play med godkända handelssigill-PNG som versionshanterade produktionsassets.

## Princip

Repositoryt innehåller källor och **godkända produktionsassets**, men inte genererade PDF-/SVG-/releaseprodukter.

Versionshanteras:

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

De fyra PNG-filerna:

```text
assets/icons/trade-seals/blue-trade-seal.png
assets/icons/trade-seals/red-trade-seal.png
assets/icons/trade-seals/green-trade-seal.png
assets/icons/trade-seals/purple-trade-seal.png
```

är godkända produktionsassets och ska ligga kvar i Git.

`assets/icons/source/trade-seals-generated-sheet-v1.1.png` behålls som ursprungligt AI-genererat källark.

`scripts/build_trade_seal_icons.py` är ett manuellt asset-verktyg. Det körs **inte** automatiskt av preview- eller releasebyggen eftersom normala byggen inte ska skriva över godkända assets.

## GitHub Actions

- **Validate** kontrollerar källor, regler, versioner och de godkända PNG-assetsen.
- **Build Print Preview** bygger samtliga printfiler från incheckade källor/assets och laddar upp dem som artifact.
- **Release Print-and-Play** bygger från den taggade revisionen och publicerar PDF-filer plus en print-and-play-zip på GitHub Release.

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
