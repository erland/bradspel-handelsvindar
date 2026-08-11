# Versionshantering

## En kanonisk projektversion

Projektets aktuella releaseversion lagras endast i rotfilen:

```text
VERSION
```

Exempel:

```text
2.4
```

Detta är metadata för release/build och ska inte dupliceras i speldata, layoutdata eller löpande dokumentation.

## Historik

`CHANGELOG.md` får och ska innehålla historiska versionsrubriker.

## Lokala revisionsnummer

Om en enskild asset eller datamodell behöver egen revisionshistorik används ett tydligt namn som:

- `asset_revision`
- `data_revision`
- `config_revision`

Dessa är inte projektets releaseversion.

## Genererad output

Lokala arbetsfilnamn är stabila och versionsfria, exempelvis:

```text
output/pdf/board/board-a4-standard.pdf
output/pdf/docs/rulebook.pdf
```

Versionen kan däremot injiceras i själva PDF-innehållet vid build.

## GitHub Release

Vid release:

1. ändra `VERSION`
2. uppdatera `CHANGELOG.md`
3. skapa en Git-tagg som exakt matchar, exempelvis `vX.Y`
4. GitHub Actions bygger all output från källorna
5. releasepaketets zip får versionsnummer automatiskt

Det innebär att en ren versionshöjning inte behöver ändra speldata, dokumentrubriker, scripts eller outputmanifest.
