# Projektstatus

## Version

v2.3

## Status

Källrent GitHub-projekt där godkända handelssigill-PNG:er behandlas som versionshanterade produktionsassets.

## Klart

- de fyra godkända trade-seal-PNG:erna är återställda och checkas in
- `.gitignore` ignorerar inte längre trade-seal-PNG:erna
- validatorn kräver att alla fyra PNG-filer finns och går att läsa
- preview/release använder PNG-filerna direkt
- `build_trade_seal_icons.py` körs inte automatiskt i CI eller release
- AI-källarket behålls som käll-/proveniensmaterial
- `output/`, `release/`, `build/` och `dist/` är fortsatt genererade och ignorerade
- spelregler, karta och balans är oförändrade

## Nästa steg

Pusha v2.3 och kontrollera att Validate, Build Print Preview och en taggad release fungerar med de incheckade produktionsassetsen.
