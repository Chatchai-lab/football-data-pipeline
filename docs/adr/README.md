# Architekturentscheidungen

Kurze Notizen zu den wichtigsten Entscheidungen: Kontext, Entscheidung, Alternativen und Begründung.

| Nr. | Entscheidung |
|---|---|
| [0001](0001-k3s-lokal-k3d-in-ci.md) | k3s lokal und k3d in der CI statt kind |
| [0002](0002-postgres-im-cluster-nur-fuer-entwicklung.md) | Postgres im Cluster nur für Entwicklung und Test, Neon in Produktion |
| [0003](0003-api-zwischen-dashboard-und-datenbank.md) | API als Zwischenschicht zwischen Dashboard und Datenbank |
| [0004](0004-docker-hub-als-registry.md) | Docker Hub als Registry, Tags mit Commit-ID |
| [0005](0005-deploy-test-baut-images-lokal.md) | Deploy-Test baut die Images im Job, statt sie zu pullen |
