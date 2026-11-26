# Rapport QA — Maximum Kite

> Généré par `tools/qa.py` à chaque build. Ne pas modifier à la main.

**⚠️ QA passée avec réserves** · niveau **demo** · hébergement **standard** · contrat de données `54dbe54363`

Cahier de tests `2f85385e92` : **non validé par un testeur**

## Ce que nous vous garantissons

| | Exigence | Comment c'est vérifié | Résultat |
|---|---|---|---|
| EX-01 | Aucune réponse rédigée par l'IA n'est envoyée à un vacancier sans relecture de l'équipe. | IA-ACTION · JOURNAL · 1/1 scénarios | ✅ respectée |
| EX-02 | Les prix, créneaux, moniteurs et le matos sont décidés par les règles de l'école, jamais par l'IA. | IA-GARDE · 3/3 scénarios | ✅ respectée |
| EX-03 | Une pièce immobilisée par le Gréeur n'est jamais proposée pour un cours. | 2/2 scénarios | ✅ respectée |
| EX-04 | Si l'IA ne répond pas ou répond n'importe quoi, rien n'est réservé et l'équipe reprend la main. | IA-GARDE · 4/4 scénarios | ✅ respectée |
| EX-05 | Seules des données conformes au format convenu sont écrites dans les fichiers de l'école. | CONTRAT · GARDE-ECRITURE · ECRITURE-PROPRIETAIRE · 3/3 scénarios | ✅ respectée |
| EX-06 | Chaque écriture automatique est traçable : quoi, quand, quelle version des règles, quelle validation. | JOURNAL · 4/4 scénarios | ✅ respectée |
| EX-07 | Les données personnelles des vacanciers sont limitées au nécessaire et purgées passé leur durée de conservation. | PERSO · PURGE · 2/2 scénarios | ⚠️ avec réserves |
| EX-08 | Les données ne partent que vers les services déclarés, aucun secret n'est stocké dans le code. | SORTIES · SECRETS · IA-ADAPTATEUR | ⚠️ avec réserves |
| EX-09 | Durées de conservation validées par l'école ; contrat de sous-traitance (RGPD) signé. | manuel : Validation écrite de l'école + contrat signé, référencés dans validations.json | 🕓 contrôle manuel à faire |
| EX-10 | Les accès (Google, n8n, IA) sont nominatifs et retirables en fin de contrat ; l'appli Google est publiée (plus de mode Testing). | manuel : Liste des accès revue + procédure de sortie testée | 🕓 contrôle manuel à faire |
| EX-11 | Une erreur d'exécution est journalisée dans l'onglet Journal, visible par l'équipe. | JOURNAL-ERREURS · manuel : Dans n8n, chaque workflow a « Gouvernance — Journal des erreurs » comme Error workflow (Settings) | 🕓 contrôle manuel à faire |
| EX-12 | L'historique d'exécutions de n8n ne conserve pas les données des vacanciers au-delà du nécessaire. | manuel : Instance n8n réglée pour ne garder que les exécutions en erreur, avec une durée de rétention courte (variables EXECUTIONS_DATA_*) — à vérifier sur la version installée | 🕓 contrôle manuel à faire |

## QA gates

| Gate | Ce qui est vérifié | Résultat |
|---|---|---|
| VALIDATION-TESTEUR | Le cahier de tests (exigences, scénarios, contrat) est validé par un testeur indépendant et n'a pas changé depuis | ⚠️ 1 constat(s) |
| CONTRAT | Contrat de données complet ; données de démo et Excel générés conformes (même validateur que n8n) | ✅ |
| PERSO | Chaque donnée personnelle a une finalité et une durée de conservation ; aucune dans le Journal | ⚠️ 1 constat(s) |
| ECRITURE-PROPRIETAIRE | Chaque onglet n'est écrit que par l'agent déclaré, dans les fichiers déclarés | ✅ |
| GARDE-ECRITURE | Chaque écriture passe par un node Garde à jour du contrat | ✅ |
| JOURNAL | Chaque écriture est tracée (version, validation) dans l'onglet Journal | ✅ |
| JOURNAL-ERREURS | Un workflow trace les erreurs d'exécution dans le Journal | ✅ |
| IA-ADAPTATEUR | Modèle et endpoint IA viennent du manifeste, jamais du code | ✅ |
| IA-GARDE | Toute réponse IA est relue par du code (lecture prudente, repli) avant usage | ✅ |
| IA-ACTION | Aucune action vers l'extérieur en aval d'une IA sans validation humaine | ✅ |
| SORTIES | Les données ne partent que vers les domaines déclarés | ⚠️ 6 constat(s) |
| SECRETS | Aucun secret ni credential dans le repo | ✅ |
| PURGE | Les données personnelles sont purgées automatiquement à échéance | ⚠️ 2 constat(s) |
| SCENARIOS | Scénarios de test issus des exigences du client : tous passent | ✅ |

## Constats

**VALIDATION-TESTEUR**
- ⚠️ Cahier de tests 2f85385e92 pas encore validé par un testeur (python3 tools/qa.py maximum-kite --signer "Prénom")

**CONTRAT**
- matos/Parc : 18 lignes de démo validées
- matos/Dégâts : 10 lignes de démo validées
- matos/Utilisations : 7 lignes de démo validées
- reservations/Vent : 7 lignes de démo validées
- reservations/Demandes : 4 lignes de démo validées
- reservations/Réservations : 8 lignes de démo validées
- reservations/Messages : 1 lignes de démo validées

**PERSO**
- ⚠️ matos/Utilisations.client : copie de reservations.Réservations.client — minimisation : le lien par clé suffit, colonne à supprimer
- 10 colonnes de données personnelles déclarées, chacune avec finalité et durée
- Des messages de vacanciers sont envoyés au fournisseur IA (Anthropic (API directe)) : couvert par le contrat de sous-traitance (EX-09)

**JOURNAL**
- Utilisations ← accueil · validation : non requise — calcul par les règles
- Messages ← accueil · validation : modèle fixe — pas de texte généré par l'IA
- Réservations ← accueil · validation : non requise — changement de statut par les règles
- Demandes ← accueil · validation : humaine — réponse IA en attente de validation dans la page, rien n'est envoyé
- Demandes ← gouvernance · validation : non requise — durées de conservation du contrat
- Réservations ← gouvernance · validation : non requise — durées de conservation du contrat
- Brief ← greeur · validation : non requise — calcul par les règles, sans IA
- Dégâts ← greeur · validation : humaine — dégât « À traiter » dans la page du Gréeur

**IA-ADAPTATEUR**
- Modèle : claude-haiku-5-5 · Anthropic (API directe)

**IA-GARDE**
- 3 appels IA, tous suivis d'une relecture par le code

**SORTIES**
- ⚠️ cdnjs.cloudflare.com : autorisé en démo seulement — librairie Excel des pages de démo — à embarquer avant la prod
- ⚠️ claude.ai : autorisé en démo seulement — pages de démo hébergées en artefact (window.claude) — remplacées par l'hébergement du client en prod
- ⚠️ exemple-paiement.fr : autorisé en démo seulement — lien d'acompte fictif
- ⚠️ fonts.googleapis.com : autorisé en démo seulement — polices des pages de démo — à embarquer avant la prod
- ⚠️ g.page : autorisé en démo seulement — lien d'avis Google fictif
- ⚠️ photos.app.goo.gl : autorisé en démo seulement — album photo fictif
- api.anthropic.com : IA — lecture et rédaction (aucune décision)
- docs.google.com : Google Sheets du client (bases)

**SECRETS**
- 49 fichiers du repo scannés

**PURGE**
- ⚠️ Utilisations (client) : purge automatique impossible (pas de clé unique) — purge manuelle à prévoir
- ⚠️ Messages (contact, texte) : purge automatique impossible (pas de clé unique) — purge manuelle à prévoir
- Demandes : purge automatique (contact 180 j, message 180 j, resume 180 j, reponse 180 j)
- Réservations : purge automatique (client 1095 j, contact 1095 j, participants 30 j)

**SCENARIOS**
- 19 scénarios dans 1 fichier(s), 19 réussis

## Avant la mise en production

Passer `niveau` à `prod` dans `gouvernance/gouvernance.json` rend tout ceci bloquant :

- [ ] Cahier de tests 2f85385e92 pas encore validé par un testeur (python3 tools/qa.py maximum-kite --signer "Prénom")
- [ ] matos/Utilisations.client : copie de reservations.Réservations.client — minimisation : le lien par clé suffit, colonne à supprimer
- [ ] cdnjs.cloudflare.com : autorisé en démo seulement — librairie Excel des pages de démo — à embarquer avant la prod
- [ ] claude.ai : autorisé en démo seulement — pages de démo hébergées en artefact (window.claude) — remplacées par l'hébergement du client en prod
- [ ] exemple-paiement.fr : autorisé en démo seulement — lien d'acompte fictif
- [ ] fonts.googleapis.com : autorisé en démo seulement — polices des pages de démo — à embarquer avant la prod
- [ ] g.page : autorisé en démo seulement — lien d'avis Google fictif
- [ ] photos.app.goo.gl : autorisé en démo seulement — album photo fictif
- [ ] Utilisations (client) : purge automatique impossible (pas de clé unique) — purge manuelle à prévoir
- [ ] Messages (contact, texte) : purge automatique impossible (pas de clé unique) — purge manuelle à prévoir
- [ ] EX-09 : Validation écrite de l'école + contrat signé, référencés dans validations.json
- [ ] EX-10 : Liste des accès revue + procédure de sortie testée
- [ ] EX-11 : Dans n8n, chaque workflow a « Gouvernance — Journal des erreurs » comme Error workflow (Settings)
- [ ] EX-12 : Instance n8n réglée pour ne garder que les exécutions en erreur, avec une durée de rétention courte (variables EXECUTIONS_DATA_*) — à vérifier sur la version installée

## Versions livrées

| Workflow | Version |
|---|---|
| Accueil — Après le cours | `4edbf296df` |
| Accueil — Demande de réservation | `7fe0ac54bc` |
| Gouvernance — Journal des erreurs | `a908b2ef3a` |
| Gouvernance — Purge des données personnelles | `0f1a224471` |
| Gréeur — Brief matos du lundi | `7f72705c53` |
| Gréeur — Signalement d'un dégât | `789494c7bd` |
