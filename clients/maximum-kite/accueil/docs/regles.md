# L'Accueil — ce que l'agent vérifie, et d'où viennent les chiffres

Les règles vivent dans **un seul fichier** : `accueil/n8n/code/accueil_regles.js`. `tools/build.py` l'injecte dans la page de démo et le recopie dans les nodes Code n8n : la page et n8n prennent exactement les mêmes décisions. Les paramètres (tarifs, créneaux, tailles, liens) viennent de la base Réservations : `data/reservations.json` → `regles`.

## Qui fait quoi

| Étape | Qui | Détail |
|---|---|---|
| Lire le message (langue, cours, date, participants, poids, âge) | IA (Haiku) | Réponse JSON vérifiée par le code : cours, date et moment hors liste remplacés par une valeur sûre |
| Choisir le créneau, le moniteur, le matos, le prix | **Code** | Règles ci-dessous. L'IA n'invente aucun horaire ni prix |
| Rédiger la réponse dans la langue du client | IA | Uniquement à partir des « faits » calculés par le code. Modèle de secours FR/EN si l'IA ne répond pas |
| Valider et envoyer | Humain | Bouton dans la page. Rien ne part tout seul tant que les canaux ne sont pas branchés |
| Message d'après-cours | **Modèle fixe** (FR, EN, DE, ES) | Pas d'IA : il part sans relecture, donc il doit être prévisible |

## Les vérifications, dans l'ordre

| Vérification | Règle | Base |
|---|---|---|
| Vent | Vent prévu sur le créneau dans la plage du cours (kite 12–25 nds, wing 12–22 nds) | Onglet **Vent** de la base Réservations (en dur pour la démo, voir « Vent » plus bas) |
| Moniteur | Un groupe par moniteur et par créneau ; au-delà du nombre d'élèves max, il en faut un deuxième | Onglet **Réservations** (Proposé et Confirmé comptent, Annulé non) |
| Âge, poids | En dessous du minimum : pas de réservation. Si un autre cours accepte cet âge (wing dès 10 ans), il est proposé | Tarifs de la démo |
| Matos | Taille visée selon poids et vent. On exclut les pièces **immobilisées par le Gréeur** et celles déjà prises sur le créneau. Si la taille idéale manque, la plus proche, avec la raison. Les pièces « à remplacer » selon le Gréeur sont signalées « à contrôler » | Onglets **Parc** et **Dégâts** de la base Matos (ceux du Gréeur) |
| Prix | Prix par personne × participants ; acompte 30 % | Tarifs de la démo |
| Créneaux | Ceux demandés, puis 2 alternatives sur 7 jours. Un créneau déjà commencé aujourd'hui est exclu | — |

## Hypothèses inventées pour la démo (à caler avec l'école)

Je ne suis pas moniteur : ces valeurs sont des **points de départ plausibles, pas des références**. Elles sont toutes dans `data/reservations.json`.

- Tarifs : initiation kite 130 €, perfectionnement 120 €, initiation wing 120 € (2 h, 2 élèves max).
- Âges minimum : kite 12 ans, wing 10 ans. Poids minimum : kite 40 kg, wing 30 kg.
- Tailles de voile kite selon poids et vent (ex. 16–20 nds : < 60 kg → 7 m, 60–80 kg → 9 m, > 80 kg → 12 m), ailes wing, volume de planche wingfoil, twintip. Poids inconnu : calcul sur 70 kg et demande de confirmation dans la réponse.
- Barres et harnais **ne sont pas comptés** (le parc de démo n'en a pas assez pour que ce soit réaliste).
- Code de réduction : `MK10-PRÉNOM`, −10 %, valable 12 mois. Le code n'est enregistré nulle part côté caisse : à brancher sur l'outil de réservation/paiement de l'école.
- Liens d'acompte, d'avis Google et d'album photo : **factices**, à remplacer par ceux de l'école.
- Messages d'après-cours au tutoiement (habitude des écoles de glisse), réponse aux demandes au ton du client : à valider avec l'école.

## Après le cours

- Un cours **Confirmé** dont la date est passée (ou aujourd'hui) est « à clôturer ».
- Clôture = une ligne **Utilisations** par pièce sortie (durée du cours) + un message dans **Messages** + statut **Terminé** et code de réduction dans **Réservations**.
- Dans la page : bouton « Clôturer » (on peut corriger la liste du matos sorti et le lien de l'album). Dans n8n : automatique chaque soir à 18h.
- Les heures d'utilisation ne changent pas encore les calculs du Gréeur (usure à l'âge). C'est la suite logique.

## Vent : d'où viendront les conditions (à décider avec l'école)

Pour l'instant l'onglet **Vent** est rempli en dur. Deux options, à trancher avec Max dès qu'il répond :
1. **Une source météo branchée** (Windguru ou équivalent) qui remplit l'onglet automatiquement. Je ne sais pas si Windguru propose un accès automatisé utilisable ici, ni à quel prix : à vérifier avant de promettre.
2. **Des cases à remplir par l'école** : le matin, Max saisit le vent prévu par créneau (ou corrige ce qui a été pré-rempli). La colonne `source` dit d'où vient chaque ligne.

Dans les deux cas, le format de l'onglet ne change pas : `date, matin, midi, aprem, dir, source`. Les règles lisent cet onglet, rien d'autre.

## Ce qui reste simulé

- **Réception** : pas d'Instagram ni d'email branché. La page a une boîte de réception de démo + « écrire un message test » ; n8n a un formulaire qui joue le rôle du DM.
- **Envoi** : « envoi simulé » dans la page, « À envoyer (canal pas encore branché) » dans n8n.
- **Photos** : un lien d'album, pas d'envoi de fichiers.
- **Acompte** : le bouton « Acompte reçu » est manuel. Plus tard : lien de paiement réel et confirmation automatique.
