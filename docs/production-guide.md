# Produktions- och buildguide v2.1

## Rekommenderat utskriftspaket

Använd PDF-filerna i `release/v2.1/print/`.

## Byggflöde

```text
data/*.yaml + docs/*.md + templates/* + assets/*
                |
                v
          scripts/build_all.py
                |
                v
       output/svg och output/preview
                |
                v
              output/pdf
                |
                v
          release/v2.1/print
```

## Kortprofiler

`data/print-layouts.yaml` innehåller:

- `compact_4x4` - aktiv profil, 16 små kort per A4
- `large_3x3` - reservprofil för större kort

Kortinnehållet ligger i `data/cards.yaml` och `data/deliveries.yaml`.

## Ledmarkörer

Pärlplattepärlor på cirka 5 mm fungerar som ledmarkörer. Spelbrädets ledplatser är 6,2 mm. Varje spelare behöver markörer i en egen färg.

## Poäng

Använd papper och penna. Något separat poängspår krävs inte.

## Testutskrift

1. Skriv ut utan skalning i 100 procent.
2. Kontrollera att pärlorna passar i ledplatserna.
3. Skriv ut en sida handelssigillkort och kontrollera ikonernas detaljrikedom.
4. Kontrollera regelbokens textstorlek och sidbrytningar.
5. Jämför standardkartan med ink-friendly-kartan.

## Rensning

`python scripts/build_all.py` raderar äldre genererad PDF-, SVG- och PNG-output innan nya filer skapas. Källfiler i `data/`, `docs/`, `templates/`, `scripts/` och `assets/` påverkas inte.

## GitHub-publicering

`data/release.yaml` är källan för vilka PDF-filer som publiceras.

- PR/push till `main`: snabb validering
- manuell workflow: preview-artifact
- `v*`-tagg: GitHub Release med PDF-assets och komplett print-and-play-zip

Se `docs/github-actions.md`.
