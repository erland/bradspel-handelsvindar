# Simulering och strukturerade regler

## Syfte

`data/rules.yaml` är den maskinläsbara källan för de centrala spelregler som simulatorn behöver.

Regelboken i `docs/rulebook.md` är fortfarande den mänskligt läsbara spelkomponenten. Filerna ska hållas synkroniserade.

## Filer

- `data/rules.yaml` – setup, handlingar, poäng, efterfrågan och slutvillkor
- `schemas/rules.schema.json` – grundschema för regeldata
- `data/simulation.yaml` – simuleringsinställningar
- `scripts/validate_rules.py` – validerar schema och korsreferenser
- `scripts/check_rulebook_consistency.py` – kontrollerar utvalda regelvärden mot regelboken
- `scripts/simulate_game.py` – kör slumpmässiga lagliga spelare

## Körning

```bash
python scripts/validate_rules.py
python scripts/check_rulebook_consistency.py
python scripts/simulate_game.py --games 250
```

Resultatet skrivs till `output/simulation-summary.json`.

## Begränsning

Simulatorn använder slumpmässiga men lagliga handlingar. Den kan hitta uppenbara dödlägen, extrema speltider och resursproblem. Den kan inte avgöra om besluten känns meningsfulla, om blockering är rolig eller om spelet är attraktivt för målgruppen.
