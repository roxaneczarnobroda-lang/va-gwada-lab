# Maximum Kite — école de kite & wing, marina du Gosier

Prospect. Trois agents proposés dans le pitch : **Le Gréeur** (matos), **L'Accueil** (vacanciers), **Le Capitaine** (events + Insta). Démos faites : le Gréeur, puis L'Accueil. Les deux partagent la même Google Sheet (le parc et les dégâts du Gréeur servent à l'Accueil).

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


---

## L'Accueil — ce que fait la démo

1. Un vacancier écrit sur Instagram ou par email, dans sa langue (« demain après-midi, on est deux, 58 et 82 kg »).
2. L'IA lit le message : cours, date, participants, poids, âge.
3. Le code vérifie le créneau : **vent prévu**, **moniteur libre**, **matos libre** à la bonne taille (en excluant ce que le Gréeur a immobilisé), âge et poids minimum. Il propose des alternatives si ça ne tient pas, ou un autre cours (wing pour un enfant de 10 ans).
4. L'IA rédige la réponse dans la langue du client, à partir de ces faits seulement (prix, acompte, lien). On valide : le créneau est bloqué en « Proposé », puis « Confirmé » à réception de l'acompte.
5. Après le cours : une ligne **Utilisations** par pièce sortie, et un message avec l'album photo, le lien d'avis Google et un code −10 % pour la prochaine session.

Instagram, WhatsApp et l'envoi réel ne sont **pas branchés** (compte Meta Business nécessaire) : la démo tourne sur des messages en dur et marque les envois « simulés ». On met les blocs en place une fois le projet gagné.

Détail des règles et hypothèses : [docs/regles-accueil.md](docs/regles-accueil.md). Déroulé de démo : [docs/script-demo-accueil.md](docs/script-demo-accueil.md). Prompts : [prompts/accueil.md](prompts/accueil.md).

### Architecture

```
Insta / email (plus tard)        Page web (interface unique)
   └─ pour l'instant : formulaire n8n   · messages reçus, vérification, réponse à valider
          │                              · planning 7 jours, après le cours, utilisations
          ▼                                        │ lit / écrit
        n8n ──lit / écrit──▶ Google Sheet ◀────────┘
   · message → IA lit → règles → IA rédige     Parc, Dégâts (Gréeur) + Vent, Demandes,
     → onglet Demandes (réponse prête)          Réservations, Utilisations, Messages
   · chaque soir 18h : cours confirmés → Utilisations + Messages + statut Terminé
```

### Faire tourner la version n8n (Roxane)

La Google Sheet de démo a maintenant les onglets **Vent, Demandes, Réservations, Utilisations, Messages** (données fictives, dates à partir du 24/11/2026 ; le vent n'est rempli que sur 7 jours : relancer `python3 tools/build_accueil.py` et recoller `data/accueil-vent.csv` pour décaler).

1. `npx n8n`, puis importer `n8n/accueil-demande-reservation.json` et `n8n/accueil-apres-le-cours.json`.
2. Choisir les credentials Google Sheets et Anthropic sur les nodes (ou utiliser `credentials.local.json` + le build, comme pour le Gréeur).
3. Tester la demande : *Test step* sur « Message reçu », remplir le formulaire. La ligne arrive dans **Demandes** avec la réponse préparée ; dans la page (Google Sheet chargée), elle apparaît dans les messages reçus avec « Réponse préparée par n8n ».
4. Tester l'après-cours : *Execute workflow* sur « Accueil — Après le cours ». Les cours confirmés jusqu'à aujourd'hui passent en Terminé.

### À creuser avec l'école
- Tarifs, durées, âges et poids minimum, plages de vent par cours.
- Tableaux de tailles de voile et d'aile selon poids et vent (les moniteurs ont les leurs).
- Comment l'acompte est pris aujourd'hui (lien de paiement, sur place ?), politique d'annulation météo.
- Le lien d'avis Google de l'école, et comment les photos sont prises et partagées.
- Où arrivent les demandes aujourd'hui (Insta, WhatsApp, mail, téléphone), et qui répond.
