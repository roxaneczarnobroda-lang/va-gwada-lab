# Conventions communes

## Données
- Données fictives uniquement dans le repo. Le marquer en tête de chaque fichier (`_note`) et dans chaque démo.
- Une source de vérité par client : `clients/<client>/data/*.json`. Excel, CSV et HTML sont générés.
- En-têtes de colonnes des Google Sheets de test en minuscules sans accent (`date_achat`, `prix_achat`) : plus simple dans n8n. Le fichier Excel montré au client garde des en-têtes lisibles.

## IA
- L'IA **classe et reformule**. Elle ne calcule pas de prix et ne décide pas. Les montants viennent de règles écrites ou de l'historique du client.
- Toujours demander une réponse JSON et la vérifier côté code (ID existant, valeur dans une liste autorisée).
- Toujours un repli à la main si l'IA ne répond pas.
- Un message qui part sans relecture (ex. après le cours) est un modèle fixe, pas un texte généré.

## n8n (rappels issus de nos premiers workflows)
- Lancement en local : `npx n8n` → http://localhost:5678.
- Import : menu ⋯ → *Import from File*. Les credentials ne sont jamais dans le JSON : à reconnecter après import.
- Timezone des workflows : `America/Guadeloupe`.
- Gmail : désactiver *Append n8n Attribution* (déjà fait dans nos JSON).
- Google Sheets : activer l'API Sheets **et** l'API Drive dans le projet Google Cloud « VA Gwada ».
- Un node à 0 item coupe l'exécution → *Always Output Data* sur les lectures de Sheets.
- Lire deux onglets à la suite : mettre *Execute Once* sur la deuxième lecture, sinon elle tourne une fois par ligne de la première.
- Comparer un texte généré par IA : *contains*, jamais *equals*.
- Le code des nodes Code vit dans `n8n/code/*.js` ; on modifie là, puis `python3 tools/build_n8n.py`.
- Quand la page et n8n doivent décider pareil, les règles sont dans un seul `.js` (ex. `accueil_regles.js`) : relancer les deux builds après modification.
- Les canaux pas encore branchés (Instagram, WhatsApp) sont remplacés par un *Form Trigger* qui joue le message entrant.

## Git
- Une branche par chantier (`maximum-kite/greeur-v2`, `maximum-kite/accueil-v1`), puis une pull request que l'autre relit.
- Messages de commit en français, à l'impératif : « Ajoute la liste À traiter au Gréeur ».
