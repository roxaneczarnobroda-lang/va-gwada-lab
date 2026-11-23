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

1. Créer une Google Sheet « Gréeur — démo » avec deux onglets **Parc** et **Dégâts**. Importer `data/parc.csv` et `data/degats.csv` (Fichier → Importer → Remplacer la feuille actuelle).
2. `npx n8n`, puis importer `n8n/greeur-signalement-degat.json` et `n8n/greeur-brief-hebdo.json`.
3. Dans chaque node Google Sheets, remplacer `COLLE_ICI_L_URL_DE_TA_GOOGLE_SHEET_GREEUR` par l'URL de la feuille et choisir la credential Google Sheets.
4. Sur le node « Claude analyse le message » : credential **Anthropic** (la même clé que pour le workflow email). Le modèle est défini dans `n8n/code/signalement_prompt.js` (`claude-haiku-5-5`).
5. Sur les nodes Gmail : credential Gmail. Le destinataire est dans `tools/build_n8n.py` (`EMAIL`).
6. Tester : ouvrir le formulaire (bouton *Test step* sur « Formulaire dégât ») et envoyer un message.

⚠️ Ces workflows ont été testés hors de n8n (le code des nodes tourne sur les données de démo et donne les mêmes résultats que l'app). L'import dans n8n, lui, n'a pas encore été testé. Si un node s'affiche en erreur après l'import, noter lequel et on corrige le générateur.

## À creuser avec l'école
- Son fichier actuel existe-t-il ? Quelles colonnes ? (l'app sait charger un Excel au même format)
- Durées de vie réelles par catégorie, selon son expérience et ses marques.
- Prix de rachat actuels (la démo prend le prix d'achat faute de mieux).
- Qui signale les dégâts, et comment : formulaire, vocal WhatsApp, Excel à la main ?
- WhatsApp pour les alertes : nécessite un compte Meta Business (chantier séparé).
