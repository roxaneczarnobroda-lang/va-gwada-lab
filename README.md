# VA Gwada — lab

L'environnement de dev de VA Gwada (Roxane & Saskia) : démonstrateurs, données fictives, prompts et workflows n8n, rangés par client puis par agent.

**Secure & governed by design** : chaque écriture passe par une Garde (contrat de données) et un Journal, l'IA passe par un adaptateur unique, et des **QA gates** vérifient à chaque build les exigences du client. Voir [docs/gouvernance.md](docs/gouvernance.md).

> Tout ce qui est dans `data/` est **fictif**. Les données réelles d'un client ne vont jamais dans ce repo.

## Organisation

```
clients/
  maximum-kite/                 un dossier par client
    sheets.json                 IDs des Google Sheets du client (une par base)
    gouvernance/
      gouvernance.json            manifeste : IA, sorties autorisées, exigences du client
      scenarios/*.test.js         tests des exigences (exécutent le vrai code des nodes)
      validations.json            signatures des contrôles manuels
      n8n/                        workflows Purge + Journal des erreurs (générés)
      rapport-qa.md               rapport QA à remettre au client (généré)
    data/                       LES SOURCES de données fictives, une par base
      contrat.json                CONTRAT DE DONNÉES : colonnes, types, données perso, conservation
      matos.json                  base Matos : parc, dégâts, utilisations
      reservations.json           base Réservations : règles école, vent, demandes, réservations, messages
      README.md                   le schéma : onglets, colonnes, clés, qui écrit quoi
      generes/                    Excel générés (ne pas modifier à la main)
    greeur/                     un dossier par agent, toujours la même forme :
      demonstrateur/              page de démo (*.src.html = source, *.html = construite)
      n8n/                        workflows importables + leur code (n8n/code/*.js)
      prompts/                    consignes données à l'IA, en clair
      docs/                       règles de calcul, script de démo
    accueil/                    (même forme)
tools/
  build.py                      construit tout ce qui est généré, pour un client, puis lance la QA
  qa.py                         QA gates (aussi en CI : .github/workflows/qa.yml)
  garde.js                      socle runtime : adaptateur IA, lecture IA prudente, validation au contrat
  gouvernance.py                chargement du contrat et du manifeste
docs/
  conventions.md                règles communes (données, IA, n8n, git)
  gouvernance.md                gouvernance by design, QA gates, passe QA à partir du besoin client
```

## Construire

Une seule commande, après chaque modification d'une source (données, règles, page, code n8n) :

```bash
pip install openpyxl            # une seule fois
python3 tools/build.py          # client par défaut : maximum-kite
```

Elle produit les pages de démo, les workflows n8n et les deux bases en Excel, puis lance les QA gates : **si une gate bloque, le build échoue** (et la pull request aussi). Les fichiers générés sont versionnés : Saskia peut ouvrir une page ou importer un workflow sans rien lancer.

## Démonstrateurs en ligne

| Client | Agent | Lien |
|---|---|---|
| Maximum Kite | Le Gréeur (matos) | https://claude.ai/artifact/8G5RXqhYTsB3GqLTWjxQsu |
| Maximum Kite | L'Accueil (vacanciers) | https://claude.ai/artifact/TrBdK7B3eJTndSf89RuKbB |

Privés : à partager avec Saskia depuis claude.ai.

## Travailler à deux (git)

Un seul repo pour tout, `main` toujours propre. Le détail est dans [docs/conventions.md](docs/conventions.md#git). En bref : une branche courte par changement, une pull request, l'autre relit, on fusionne en « Squash and merge », on supprime la branche.

## Ajouter un client

Copier `clients/maximum-kite/` vers `clients/<client>/`, remplacer les données fictives et `sheets.json`, garder les agents utiles. Puis `python3 tools/build.py <client>`.
