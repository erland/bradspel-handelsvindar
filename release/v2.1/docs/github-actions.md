# GitHub Actions och print-publicering v2.1

`.github/` ligger i repositoryts rot på samma nivå som `README.md`.

## 01 - Validate

Fil:

`.github/workflows/01-validate.yml`

Körs:

- vid pull request när relevanta projektfiler ändras
- vid push till `main` när relevanta projektfiler ändras

Syfte:

- kontrollera att obligatoriska källfiler finns
- kontrollera att YAML går att läsa
- kontrollera versionssynk
- kontrollera board/layout-rutter och platser
- kontrollera handelssigill och PNG-ikoner
- kontrollera att alla obligatoriska printfiler finns i publiceringsmanifestet
- köra befintlig regel-, regelbok- och layoutvalidering
- kontrollera att byggskriptet kan kompileras

Workflowen bygger inte PDF och ska därför vara snabb.

## 02 - Build Print Preview

Fil:

`.github/workflows/02-build-preview.yml`

Startas manuellt med `workflow_dispatch`.

Workflowen:

1. installerar de låsta byggberoendena
2. validerar projektet
3. regenererar handelssigill-ikoner från källarket
4. bygger samtliga printfiler
5. kör full projektkonsistens efter bygget
6. verifierar att varje PDF går att läsa och har minst en sida
7. kopierar printfilerna till en ren previewkatalog
8. laddar upp ett GitHub Actions-artifact med namnet `handelsvindar-print-preview`

Artifactet innehåller de åtta kanoniska PDF-filerna, `PRINT_MANIFEST.json` och `README.txt`.

Retention är 7 dagar.

## 03 - Release Print-and-Play

Fil:

`.github/workflows/03-release.yml`

Triggas av en Git-tag som börjar med `v`, exempelvis:

```bash
git tag v2.1
git push origin v2.1
```

Taggen måste exakt matcha versionen i `data/release.yaml`.

Workflowen bygger allt från källorna och publicerar:

- varje kanonisk PDF som separat GitHub Release-asset
- `PRINT_MANIFEST.json`
- `README.txt`
- en komplett `handelsvindar-print-and-play-v2.1.zip`

Om releasen redan finns uppdateras filerna med `--clobber`.

## Kanoniskt printpaket

`data/release.yaml` är publiceringskällan. En fil som ska vara med i preview och release ska finnas under `printables`.

Detta skiljer:

- innehållskällor: `data/`, `docs/`, `templates/`, `assets/`
- generatorer: `scripts/`
- lokal genererad output: `output/`
- GitHub-publicering: `data/release.yaml` + Actions-workflows

## Lokala kommandon

Snabb validering:

```bash
python -m pip install -r requirements-validation.txt
python scripts/validate_project.py .
```

Komplett preview-build:

```bash
python -m pip install -r requirements-build.txt
python scripts/build_print_package.py --output-dir build/preview
```

Test av releasepaket:

```bash
python scripts/build_print_package.py   --output-dir build/release   --expected-tag v2.1   --package
```

## Versionsprincip

Vid en ny release ska versionen höjas i projektets strukturerade källor och i `data/release.yaml`. `scripts/validate_project.py` stoppar releasen om Git-taggen inte matchar.
