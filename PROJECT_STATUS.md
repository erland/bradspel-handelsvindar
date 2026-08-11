# Projektstatus

## Version

v2.1

## Status

Blindtestredo print-and-play med automatiserad GitHub-validering, preview-build och release-publicering.

## Klart

- `.github/` ligger i projektroten bredvid `README.md`
- snabb Validate-workflow för PR och push till `main`
- manuell Build Print Preview-workflow
- taggstyrd Release Print-and-Play-workflow
- `data/release.yaml` definierar exakt vilka printfiler som är kanoniska
- reproducerbara Python-beroenden är versionslåsta
- lokal validator kontrollerar filer, YAML, versioner, speldata, ikoner och printmanifest
- preview/release byggs från källfiler och verifierar varje PDF
- GitHub Release får separata PDF-assets och en komplett print-and-play-zip
- äldre releasekataloger rensas; endast v2.1 behålls i projektzippen

## Nästa steg

Lägg projektet i ett GitHub-repository, pusha till `main` och kör `Build Print Preview` manuellt. När previewn är godkänd skapas taggen `v2.1`.
