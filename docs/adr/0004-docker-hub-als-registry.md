# 0004: Docker Hub als Registry, Tags mit Commit-ID

**Status:** angenommen

## Kontext
Images wurden nur lokal gebaut und von Hand in den Cluster importiert. Die CI soll sie reproduzierbar bauen und ablegen.

## Entscheidung
Die CI veröffentlicht die drei Images (`matchlytics-api`, `-dashboard`, `-pipeline`) bei jedem Push auf `main` in Docker Hub. Jedes bekommt zwei Tags: die volle Commit-ID und `latest`. Der Zugang läuft über ein Access Token als Repository-Secret.

## Alternativen
- **GitHub Container Registry (ghcr.io):** ohne zusätzliches Konto und mit dem Workflow-Token nutzbar, ein naheliegender Gegenkandidat.
- **Eigene Registry im Cluster:** zusätzlicher Betrieb ohne Mehrwert.

## Begründung
Docker Hub ist der Standard, den Kubernetes ohne Zusatzkonfiguration auflösen kann, und das Konto existierte schon. Ein Token mit begrenzten Rechten ist besser als ein Passwort, weil es einzeln widerrufbar ist. Commit-ID-Tags machen jedes Image einem Stand des Codes zuordenbar, `latest` allein wäre das nicht.

## Folgen
Pull-Limits für anonyme Nutzer, Pull Requests pushen nichts (Fork-PRs bekommen keine Secrets). Wer ein Image exakt festlegen will, nutzt den Digest statt eines Tags.
