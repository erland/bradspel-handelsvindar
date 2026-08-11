# Projektstatus

## Status

Källrent GitHub-projekt med en enda kanonisk projektversion i `VERSION`.

## Klart

- projektversionen är borttagen från speldata, layoutdata, regler och dokumentrubriker
- `VERSION` är enda kanoniska källa för aktuell releaseversion
- `ruleset_id` är stabilt och inte kopplat till releaseversion
- lokala outputfilnamn är versionsfria
- `data/release.yaml` och `data/print-layouts.yaml` är versionsfria
- regelbokens Markdown är versionsfri; PDF-generatorn kan lägga in releaseversion vid build
- Git-taggen kontrolleras mot `VERSION`
- release-zippen versionsmärks automatiskt
- godkända handelssigill-PNG:er ligger kvar som produktionsassets
- `output/`, `release/`, `build/` och `dist/` är genererade och ignorerade

## Nästa steg

Pusha ändringen och kontrollera att en framtida versionshöjning i normalfallet bara kräver en ändring i `VERSION`, en changelogpost och en ny Git-tagg.
