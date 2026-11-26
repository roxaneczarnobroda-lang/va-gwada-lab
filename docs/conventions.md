# Conventions communes

## Données
- Données fictives uniquement dans le repo. Le marquer en tête de chaque fichier (`_note`) et dans chaque démo.
- **Une base = un fichier.** Un client a autant de Google Sheets que de sujets (ex. Maximum Kite : Matos, Réservations). On ne mélange pas les sujets dans un même fichier.
- Les bases se relient par des identifiants, comme des tables : un `id` de pièce, un numéro de `resa`. Jamais de copie d'une même info dans deux fichiers.
- Chaque onglet a **un agent qui l'écrit** (les autres le lisent). C'est écrit dans `clients/<client>/data/README.md`.
- Une source par base : `clients/<client>/data/<base>.json`. Pages, Excel et workflows sont générés par `tools/build.py`.
- **Un seul schéma partout** : mêmes onglets et mêmes noms de colonnes dans le JSON, l'Excel et la Google Sheet. Colonnes en minuscules sans accent (`date_achat`, `prix_total`), plus simples dans n8n.
- Les IDs des Google Sheets d'un client sont dans `clients/<client>/sheets.json`, nulle part ailleurs.

- **Une colonne n'existe que dans `data/contrat.json`** : type, liste de valeurs, donnée perso ou non (finalité + durée de conservation si oui). Les Excel, les listes déroulantes et les Gardes n8n en sont générés.

## Gouvernance
- Détail dans [gouvernance.md](gouvernance.md). En bref : on ne contourne jamais `sheet_write(..., validation=…)`, on n'écrit jamais un modèle ou un endpoint IA dans le code (`corpsIA`), on lit toujours une réponse IA avec `jsonIA` / `texteIA`.
- Chaque promesse au client = une exigence dans `gouvernance/gouvernance.json` + un scénario dans `gouvernance/scenarios/`.
- Un domaine appelé par un workflow ou une page doit être déclaré dans `sorties` du manifeste.

## IA
- L'IA **lit et reformule**. Elle ne calcule pas de prix, ne choisit pas un créneau et ne décide pas. Ce sont des règles écrites ou l'historique du client.
- Toujours demander une réponse JSON et la vérifier côté code (ID existant, valeur dans une liste autorisée).
- Toujours un repli à la main si l'IA ne répond pas.
- Un message qui part sans relecture (ex. après le cours) est un modèle fixe, pas un texte généré.
- Appels IA depuis n8n : `corpsIA(prompt)` (modèle du manifeste, `thinking` désactivé) et `jsonIA` / `texteIA` pour lire la réponse (blocs `text` seulement, le premier bloc peut être une réflexion vide).

## n8n (rappels issus de nos workflows)
- Lancement en local : `npx n8n` → http://localhost:5678.
- Import : menu ⋯ → *Import from File*. Les credentials ne sont jamais dans les JSON du repo. Avec `clients/<client>/credentials.local.json` (ignoré par git), le build écrit aussi des `*.local.json` déjà branchés.
- Timezone des workflows : `America/Guadeloupe`.
- Gmail : désactiver *Append n8n Attribution*.
- Google Sheets : activer l'API Sheets **et** l'API Drive dans le projet Google Cloud.
- Un node à 0 item coupe l'exécution → *Always Output Data* sur les lectures de Sheets.
- Lire plusieurs onglets à la suite : *Execute Once* à partir de la deuxième lecture.
- Comparer un texte généré par IA : *contains*, jamais *equals*.
- Le code des nodes Code vit dans `<agent>/n8n/code/*.js` ; on modifie là, puis `python3 tools/build.py`.
- Quand la page et n8n doivent décider pareil, les règles sont dans un seul `.js` (ex. `accueil_regles.js`), injecté dans les deux par le build.
- Les canaux pas encore branchés (Instagram, WhatsApp) sont remplacés par un *Form Trigger* qui joue le message entrant.

## Git
**Un seul repo** (pas un par agent) : les agents d'un client partagent les mêmes bases et une partie des règles (l'Accueil lit l'état du matos calculé par le Gréeur). Les séparer obligerait à synchroniser plusieurs repos à chaque changement de schéma.

- `main` = ce qui marche, et la version montrée aux clients.
- **Une branche courte par changement**, partie de `main` à jour : `<client>/<agent>-<sujet>` (ex. `maximum-kite/accueil-vent-saisi`). Quelques jours maximum.
- Avant de commencer : `git switch main && git pull`, puis `git switch -c <branche>`.
- Pull request vers `main`, l'autre relit, puis **Squash and merge** (un commit propre par changement) et suppression de la branche.
- Ne jamais empiler une branche sur une autre branche pas encore fusionnée : on fusionne d'abord.
- Relancer `python3 tools/build.py` avant de committer (les fichiers générés font partie du commit). La CI refait le build et refuse la PR si une QA gate bloque ou si un fichier généré n'est pas à jour.
- Messages de commit en français, à l'impératif : « Ajoute la saisie du vent par l'école ».
