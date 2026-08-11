# Changelog

## v2.4

- införde `VERSION` som enda kanoniska projektversion
- tog bort releaseversion från YAML-källor och löpande Markdown
- gjorde genererade outputfilnamn versionsfria
- gjorde `ruleset_id` stabilt (`handelsvindar_core`)
- bygg- och releaseverktyg läser version från `VERSION`
- Git-taggen valideras mot `VERSION`
- release-zippen behåller versionsnummer utan att sprida det i källfiler
- spelregler, karta, grafik och balans är oförändrade


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
