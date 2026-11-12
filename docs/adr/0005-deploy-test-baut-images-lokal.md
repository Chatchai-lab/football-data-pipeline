# 0005: Deploy-Test baut die Images im Job, statt sie zu pullen

**Status:** angenommen

## Kontext
Der Deploy-Test in k3d braucht die frisch gebauten Images im Cluster. Pull Requests dürfen nichts nach Docker Hub pushen.

## Entscheidung
Der Job `deploy-test` baut die drei Images selbst (mit demselben Dockerfile und Layer-Cache wie der Job `build`), lädt sie lokal und importiert sie per `k3d image import`.

## Alternativen
- **Aus Docker Hub pullen:** entspricht dem Release-Weg, geht aber nur nach einem Push auf `main`. Pull Requests könnten ihren eigenen Code nicht testen.
- **Image als Artefakt zwischen Jobs weitergeben:** funktioniert, das Dashboard-Image ist aber rund 660 MB groß.

## Begründung
So testet auch ein Pull Request seinen eigenen Code, ohne Secrets und ohne Push. Der Layer-Cache macht den zweiten Build schnell.

## Folgen
Die getesteten Images sind nicht Bit für Bit die gepushten. Für einen echten Release-Prozess wäre der nächste Schritt, das gepushte Image per Commit-ID zu ziehen und genau dieses zu testen. Wichtig: Die Builds laufen ohne Provenance-Attestation (`provenance: false`), sonst scheitert der Import in den Cluster mit `unexpected EOF`.
