# Handelssigill-assets

## Godkända produktionsassets

Följande PNG-filer används direkt av kort- och snabbreferensbyggen:

- `trade-seals/blue-trade-seal.png`
- `trade-seals/red-trade-seal.png`
- `trade-seals/green-trade-seal.png`
- `trade-seals/purple-trade-seal.png`

De är versionshanterade och ska inte skrivas över av normala CI-byggen.

## Ursprung

`source/trade-seals-generated-sheet-v1.1.png` är det ursprungliga AI-genererade 2x2-källarket.

`scripts/build_trade_seal_icons.py` kan användas manuellt för att återskapa separata filer från källarket. Om det görs ska resultatet granskas visuellt innan de godkända produktionsassetsen ersätts.
