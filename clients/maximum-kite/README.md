# Maximum Kite — école de kite & wing, marina du Gosier

Prospect. Trois agents proposés dans le pitch : **Le Gréeur** (matos), **L'Accueil** (vacanciers), **Le Capitaine** (events + Insta). Démos faites : le Gréeur, puis L'Accueil.

| Agent | Ce que fait la démo | Page | Détails |
|---|---|---|---|
| Le Gréeur | Un moniteur décrit un dégât en une phrase → la pièce est retrouvée, l'état du parc et le budget de renouvellement se recalculent | [lien](https://claude.ai/artifact/8G5RXqhYTsB3GqLTWjxQsu) | [règles](greeur/docs/regles.md) · [script de démo](greeur/docs/script-demo.md) |
| L'Accueil | Un vacancier écrit sur Insta ou par mail → créneau vérifié (vent, moniteur, matos, âge), réponse dans sa langue ; après le cours : utilisations du matos + photos, avis Google, code −10 % | [lien](https://claude.ai/artifact/TrBdK7B3eJTndSf89RuKbB) | [règles](accueil/docs/regles.md) · [script de démo](accueil/docs/script-demo.md) · [prompts](accueil/prompts/README.md) |

Tout se gère depuis les pages : pas d'email ni de WhatsApp à suivre. Instagram et WhatsApp ne sont **pas branchés** (compte Meta Business nécessaire) : l'Accueil tourne sur des messages en dur et marque les envois « simulés ». On met ces blocs en place une fois le projet gagné.

## Les données : deux bases métier + une base de gouvernance

Deux Google Sheets dans le dossier partagé VA Gwada (IDs dans [sheets.json](sheets.json)), schéma dans [data/README.md](data/README.md) :
- **Matos** : Parc, Dégâts, Utilisations, Brief. Le Gréeur l'écrit, l'Accueil la lit et y ajoute les utilisations.
- **Réservations** : Vent, Demandes, Réservations, Messages. Propre à l'Accueil.

```
Insta / email (plus tard)
  └─ pour l'instant : formulaire n8n
          │
          ▼                    lit / écrit
        n8n  ─────────────▶  Matos  ◀──────────── page du Gréeur
          │                    ▲
          └──────────────▶  Réservations ◀─────── page de l'Accueil
```

Sans connecteur Google Sheets (Saskia en rendez-vous, par exemple), les pages tournent sur les données de démo intégrées.

## Montrer une démo (Saskia)

Ouvrir le lien de la page sur téléphone ou tablette, « Revenir aux données de démo », suivre le script de démo de l'agent. Pas besoin du Mac de Roxane.

## Faire tourner n8n (Roxane)

Les 4 workflows sont déjà importés dans le n8n de Roxane (Gréeur : signalement, brief du lundi ; Accueil : demande de réservation, après le cours), branchés sur les deux Google Sheets.

**Depuis la gouvernance by design** (voir [docs/gouvernance.md](../../docs/gouvernance.md)) : le Journal vit dans une 3e Google Sheet, **« Maximum Kite — Gouvernance »** (onglet Journal, en-têtes de `data/generes/gouvernance.xlsx`) : la traçabilité ne se mélange pas aux données métier et a ses propres droits d'accès, réimporter les 4 workflows, importer les 2 workflows de `gouvernance/n8n/` (Purge — ne pas l'activer en démo ; Journal des erreurs), puis choisir « Gouvernance — Journal des erreurs » comme *Error workflow* dans les Settings de chaque workflow. Rapport QA : [gouvernance/rapport-qa.md](gouvernance/rapport-qa.md).

Pour une autre instance (Saskia) :
1. `npx n8n`, puis importer les `*.json` de `greeur/n8n/` et `accueil/n8n/` (menu ⋯ → Import from File).
2. Choisir les credentials Google Sheets et Anthropic sur les nodes. Ou : créer `credentials.local.json` à la racine du client (format en tête de `tools/build.py`), relancer le build et importer les `*.local.json`.
3. Tester l'Accueil : ouvrir « Accueil — Demande de réservation », *Execute workflow*, remplir le formulaire. La demande arrive dans l'onglet Demandes avec la réponse préparée et la proposition de créneau.
4. « Accueil — Après le cours » : *Execute workflow* clôture les cours confirmés jusqu'à aujourd'hui. Ne pas le publier (activer) tant qu'on est en démo : il tournerait chaque soir à 18h.

Credentials Google en mode Testing : à reconnecter tous les 7 jours tant que l'appli Google n'est pas publiée.

## À creuser avec l'école

**Matos (Gréeur)**
- Son fichier actuel existe-t-il ? Quelles colonnes ?
- Durées de vie réelles par catégorie, prix de rachat actuels.
- Qui signale les dégâts, et depuis quoi.

**Accueil**
- **Vent** : brancher une source météo (Windguru ou équivalent, accès automatisé et prix à vérifier) **ou** des cases à remplir par Max chaque matin. Le format de l'onglet Vent reste le même dans les deux cas. *À traiter dès sa réponse.*
- Tarifs, durées, âges et poids minimum, plages de vent par cours.
- Tableaux de tailles de voile et d'aile selon poids et vent (les moniteurs ont les leurs).
- Prise d'acompte aujourd'hui (lien de paiement, sur place ?), politique d'annulation météo.
- Lien d'avis Google de l'école ; comment les photos sont prises et partagées.
- Où arrivent les demandes aujourd'hui (Insta, WhatsApp, mail, téléphone), et qui répond.
