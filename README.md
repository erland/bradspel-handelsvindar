# Handelsvindar

## Version

v2.0 - nybörjarvänlig blindtestrelease.

## Spelidé

Du leder ett handelsgille i ett växande örike. Samla handelssigill, etablera handelsleder och använd ditt eget nätverk för att leverera varor. Flest poäng vinner.

## Rekommenderade filer

Använd endast filerna i:

```text
release/v2.0/
```

PDF är rekommenderat utskriftsformat. YAML, Markdown, mallar och script är projektets källor.

## Bygg

```bash
python scripts/build_trade_seal_icons.py
python scripts/validate_rules.py
python scripts/check_rulebook_consistency.py
python scripts/build_all.py
python scripts/check_project_consistency.py
```

Byggsteget rensar äldre genererad output innan aktuella filer skapas.

## Projektzipens storlek

Den levererade zippen behåller aktuella PDF-filer och spelbrädets SVG-overlay. Stora mellanliggande SVG-filer för kort och spelarhjälp samt förhandsbilder är borttagna eftersom de kan genereras om med `scripts/build_all.py`.
