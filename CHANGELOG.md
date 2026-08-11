# Changelog

## v2.3

- återställde de fyra godkända handelssigill-PNG:erna som versionshanterade produktionsassets
- tog bort trade-seal-PNG:erna från `.gitignore`
- validatorn kräver och verifierar PNG-filerna
- preview- och releasebyggen använder incheckade PNG-assets direkt
- tog bort automatisk körning av `build_trade_seal_icons.py` från normala byggen
- behöll AI-källarket som proveniens/källmaterial
- `output/` och `release/` är fortsatt helt genererade

## v2.2

- gjorde projektet källrent och flyttade genererad output till CI/release
