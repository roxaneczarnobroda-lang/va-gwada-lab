# Maximum Kite — école de kite & wing, marina du Gosier

Prospect. Trois agents proposés dans le pitch : **Le Gréeur** (matos), **L'Accueil** (vacanciers), **Le Capitaine** (events + Insta). On démarre par le Gréeur.

## Le Gréeur — ce que fait la démo

1. Un moniteur décrit un dégât en une phrase (« le 9 m récent a tapé le récif, trou dans le boudin »).
2. L'IA retrouve la pièce dans le parc, classe le dégât et dit s'il faut immobiliser la pièce.
3. Le coût est estimé à partir de **ce que l'école a déjà payé** pour ce type de dégât (jamais inventé).
4. La ligne s'ajoute au carnet, l'état de la pièce est recalculé et l'alerte WhatsApp est prête.
5. Le budget de renouvellement sur 12 mois se met à jour, et chaque montant montre son calcul.

Tout repose sur un fichier à trois onglets (Parc, Dégâts, Hypothèses), sans QR code ni appli à installer.

## Montrer la démo (Saskia)

Ouvrir le lien de l'app sur téléphone ou tablette. Pas besoin du Mac de Roxane. Le déroulé conseillé est dans [docs/script-demo.md](docs/script-demo.md).

## Faire tourner la version n8n (Roxane)

La Google Sheet de démo existe déjà : « Gréeur — démo Maximum Kite (données fictives) » dans le Drive de Roxane (onglets Parc et Dégâts, mêmes données que `data/`). Les workflows pointent dessus.

1. `npx n8n`, puis importer `n8n/greeur-signalement-degat.json` et `n8n/greeur-brief-hebdo.json` (menu ⋯ → Import from File).
2. Choisir les credentials sur les nodes Google Sheets, « Claude analyse le message » (Anthropic) et Gmail.
   Raccourci : créer `n8n/credentials.local.json` avec les ids de ses credentials (voir `tools/build_n8n.py`) puis relancer le build. Il produit des `*.local.json` déjà branchés, ignorés par git.
3. Le modèle est défini dans `n8n/code/signalement_prompt.js` (`claude-haiku-5-5`). Le destinataire des emails est dans `tools/build_n8n.py` (`EMAIL`).
4. Tester : ouvrir le formulaire (*Test step* sur « Formulaire dégât ») et envoyer un message.

Saskia : pour tester sur son propre n8n, faire une copie de la Google Sheet et remplacer `SHEET_URL` dans `tools/build_n8n.py`.

## À creuser avec l'école
- Son fichier actuel existe-t-il ? Quelles colonnes ? (l'app sait charger un Excel au même format)
- Durées de vie réelles par catégorie, selon son expérience et ses marques.
- Prix de rachat actuels (la démo prend le prix d'achat faute de mieux).
- Qui signale les dégâts, et comment : formulaire, vocal WhatsApp, Excel à la main ?
- WhatsApp pour les alertes : nécessite un compte Meta Business (chantier séparé).
