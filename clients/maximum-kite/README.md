# Maximum Kite — école de kite & wing, marina du Gosier

Prospect. Trois agents proposés dans le pitch : **Le Gréeur** (matos), **L'Accueil** (vacanciers), **Le Capitaine** (events + Insta). On démarre par le Gréeur.

## Le Gréeur — ce que fait la démo

1. Un moniteur décrit un dégât en une phrase (« le 9 m récent a tapé le récif, trou dans le boudin »).
2. L'IA retrouve la pièce dans le parc, classe le dégât et dit s'il faut immobiliser la pièce.
3. Le coût est estimé à partir de **ce que l'école a déjà payé** pour ce type de dégât (jamais inventé).
4. La ligne s'ajoute au carnet, l'état de la pièce est recalculé et elle apparaît dans « À traiter aujourd'hui ».
5. Le budget de renouvellement sur 12 mois se met à jour, et chaque montant montre son calcul.

Tout se gère sur **une seule page** : pas d'email, pas de WhatsApp. La page lit et écrit dans une Google Sheet (onglets Parc, Dégâts, Brief), sans QR code ni appli à installer.

## Architecture

```
Page web (interface unique) ──lit / écrit──▶ Google Sheet ◀──lit / écrit── n8n
   · À traiter, parc, dégâts,                (Parc, Dégâts,      · formulaire de signalement → IA → Dégâts
     budget, questions                        Brief)             · lundi 7h : calcul du brief → onglet Brief
```

La page passe par le connecteur Google Sheets de la personne qui l'ouvre. Sans ce connecteur (Saskia en rendez-vous, par exemple), elle tourne sur les données de démo.

## Montrer la démo (Saskia)

Ouvrir le lien de l'app sur téléphone ou tablette. Pas besoin du Mac de Roxane. Le déroulé conseillé est dans [docs/script-demo.md](docs/script-demo.md).

## Faire tourner la version n8n (Roxane)

La Google Sheet de démo existe déjà : « Gréeur — démo Maximum Kite (données fictives) » dans le Drive de Roxane (onglets Parc et Dégâts, mêmes données que `data/`). Les workflows pointent dessus.

1. `npx n8n`, puis importer `n8n/greeur-signalement-degat.json` et `n8n/greeur-brief-hebdo.json` (menu ⋯ → Import from File).
2. Choisir les credentials sur les nodes Google Sheets et « Claude analyse le message » (Anthropic). Aucun email n'est envoyé.
   Raccourci : créer `n8n/credentials.local.json` avec les ids de ses credentials (voir `tools/build_n8n.py`) puis relancer le build. Il produit des `*.local.json` déjà branchés, ignorés par git.
3. Le modèle est défini dans `n8n/code/signalement_prompt.js` (`claude-haiku-5-5`).
4. Tester : ouvrir le formulaire (*Test step* sur « Formulaire dégât ») et envoyer un message.

Saskia : pour tester sur son propre n8n, faire une copie de la Google Sheet et remplacer `SHEET_URL` dans `tools/build_n8n.py`.

## À creuser avec l'école
- Son fichier actuel existe-t-il ? Quelles colonnes ? (l'app sait charger un Excel au même format)
- Durées de vie réelles par catégorie, selon son expérience et ses marques.
- Prix de rachat actuels (la démo prend le prix d'achat faute de mieux).
- Qui signale les dégâts, et depuis quoi : la page sur téléphone, le formulaire n8n, l'Excel à la main ?
- Credentials Google en mode Testing pour l'instant : à reconnecter tous les 7 jours tant que l'appli Google n'est pas publiée (il faut une page d'accueil et une politique de confidentialité sur un domaine vérifié).
