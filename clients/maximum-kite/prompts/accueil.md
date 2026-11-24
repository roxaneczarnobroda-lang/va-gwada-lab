# Prompts — L'Accueil

Les deux consignes sont dans `n8n/code/accueil_regles.js` (fonctions `aPromptLecture` et `aPromptReponse`), utilisées telles quelles par la page et par n8n. On les modifie là, puis on relance les deux builds.

## 1. Lecture du message (`aPromptLecture`) — modèle rapide

Variables : la date du jour et les 8 jours suivants (avec le nom du jour, pour « jeudi », « ce week-end »), la liste des cours, les créneaux, le message.

Sortie : JSON `{langue, client, offre, participants[{prenom, poids, age}], date, moment, question, resume}`.
Vérifié par `aNormReq` : cours, date et moment hors liste → valeur sûre ; si la lecture échoue dans n8n, rien n'est proposé (« à traiter à la main »).

Consignes clés : ne deviner ni poids ni âge ; « autre » pour la location seule, un cours privé ou un autre sport.

## 2. Rédaction de la réponse (`aPromptReponse`)

Variables : les **faits** calculés par `aFaits` (cours, créneau, prix, acompte et lien, vent, conditions météo, question du client, ce qui a bloqué, ce qu'il faut demander) et le message du client.

Consignes clés : langue du client, ton du message reçu, 110 mots, uniquement les faits fournis, liens tels quels.

## Pistes d'amélioration
- Ajouter 3 exemples réels (message → JSON) une fois qu'on aura de vrais messages de l'école.
- Créole guadeloupéen : à tester sur de vrais messages avant de le promettre.
- Garder la conversation (plusieurs messages d'un même client) au lieu de traiter chaque message seul.
