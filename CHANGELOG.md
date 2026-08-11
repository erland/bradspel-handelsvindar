# Changelog

## v2.1

- införde `.github/workflows/01-validate.yml`
- införde `.github/workflows/02-build-preview.yml`
- införde `.github/workflows/03-release.yml`
- lade till snabb CI-validator i `scripts/validate_project.py`
- lade till reproducerbar printbyggare i `scripts/build_print_package.py`
- lade till `data/release.yaml` som kanoniskt publiceringsmanifest
- lade till låsta validation- och build-beroenden
- preview-artifact innehåller samtliga kanoniska printfiler
- taggad release publicerar separata PDF-filer och en komplett print-and-play-zip
- dokumenterade lokal och GitHub-baserad build/release
- spelregler, karta och balans är oförändrade från v2.0

## v2.0

- skrev om regelboken för nybörjare och blindtest
