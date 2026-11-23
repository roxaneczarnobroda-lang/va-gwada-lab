# VA Gwada — lab

L'environnement de dev de VA Gwada (Roxane & Saskia) : démonstrateurs, jeux de données fictifs, prompts et workflows n8n, rangés par client.

> Tout ce qui est dans `data/` est **fictif**. Les données réelles d'un client ne vont jamais dans ce repo.

## Organisation

```
clients/
  maximum-kite/            école de kite & wing, marina du Gosier
    demonstrateur/         app web montrée en rendez-vous (greeur.html = version construite)
    data/                  données fictives : source unique en JSON + Excel/CSV générés
    n8n/                   workflows importables + leur code JS (n8n/code/)
    prompts/               les consignes données à l'IA, en clair
    docs/                  règles de calcul, mode d'emploi de la démo
tools/                     scripts de build (Python)
docs/                      conventions communes à tous les clients
```

## Le principe

Une seule source de données par client (`data/*.json`). Les scripts de `tools/` en tirent :
- l'app de démo (données intégrées dans le HTML),
- le fichier Excel à montrer et à faire remplir au client,
- les CSV à importer dans une Google Sheet de test pour n8n.

Si on change une donnée ou une règle, on relance les scripts. L'app et les workflows restent alignés.

```bash
pip install openpyxl          # une seule fois
python3 tools/build_greeur.py # app + Excel + CSV
python3 tools/build_n8n.py    # workflows n8n
```

## Démonstrateurs en ligne

| Client | Agent | Lien |
|---|---|---|
| Maximum Kite | Le Gréeur (matos) | https://claude.ai/artifact/8G5RXqhYTsB3GqLTWjxQsu (privé : à partager avec Saskia depuis claude.ai) |

## Ajouter un client

Copier `clients/maximum-kite/` vers `clients/<nom-client>/`, remplacer les données fictives, adapter les prompts. Voir [docs/conventions.md](docs/conventions.md).
