# Handelsvindar

## Version

v2.1 - blindtestredo print-and-play med GitHub Actions för validering, preview och release.

## Spelidé

Du leder ett handelsgille i ett växande örike. Samla handelssigill, etablera handelsleder och använd ditt eget nätverk för att leverera varor. Flest poäng vinner.

## Projektstruktur

```text
README.md
.github/
  workflows/
    01-validate.yml
    02-build-preview.yml
    03-release.yml
assets/
data/
docs/
schemas/
scripts/
templates/
output/
release/
```

`.github/` ligger alltså på samma nivå som `README.md`.

## GitHub Actions

- **Validate** kör snabb käll- och konsistensvalidering på PR och push till `main`.
- **Build Print Preview** startas manuellt och skapar ett artifact med alla PDF-filer som ska kunna skrivas ut.
- **Release Print-and-Play** triggas av taggen `vX.Y` och publicerar separata PDF-assets plus en komplett print-and-play-zip som GitHub Release.

Se `docs/github-actions.md`.

## Kanoniskt printpaket

`data/release.yaml` anger exakt vilka PDF-filer som ska ingå i preview och release.

## Lokalt bygge

Validering:

```bash
python -m pip install -r requirements-validation.txt
python scripts/validate_project.py .
```

Komplett printbygge:

```bash
python -m pip install -r requirements-build.txt
python scripts/build_print_package.py --output-dir build/preview
```

PDF är rekommenderat utskriftsformat. YAML, Markdown, mallar, script och källgrafik är projektets källor.
