# Gouvernance by design et QA gates

La gouvernance n'est pas une doc à part : elle est **dans le code généré**, et elle est **vérifiée à chaque build**. Si une promesse faite au client n'est plus tenue, le build échoue et la pull request ne peut pas être fusionnée.

## Les trois sources, par client

| Fichier | Rôle | Qui le remplit |
|---|---|---|
| `data/contrat.json` | **Contrat de données** : onglets, colonnes, types, listes, formats, qui écrit, données perso (finalité, conservation) | nous, validé avec le client |
| `gouvernance/gouvernance.json` | **Manifeste** : niveau (demo/prod), hébergement (standard/souverain), IA, sorties autorisées, actions à risque, **exigences du client** | nous, à partir du besoin client |
| `gouvernance/scenarios/*.test.js` | **Scénarios** : une exigence → des tests qui exécutent le vrai code des nodes | nous |
| `gouvernance/validations.json` | Signatures des contrôles manuels (qui, quand, preuve) | nous + le client |

## Ce que le build ajoute tout seul

- Avant **chaque** écriture dans une Sheet : un node **Garde**. Il vérifie les lignes contre le contrat (types, listes, formats, obligatoires), retire ce qui n'est pas au contrat, et **bloque tout le lot** sinon.
- Après **chaque** écriture : un node **Journal**, qui écrit dans l'onglet `Journal` : quand, quel workflow, quelle version, combien de lignes, quelles clés, quel modèle IA, **quel mode de validation**. Jamais de donnée perso.
- Les appels IA passent par l'**adaptateur** (`tools/garde.js`) : modèle et endpoint viennent du manifeste. Pour l'option souveraine, on change `ia` dans le manifeste, rien d'autre.
- Les réponses IA sont lues par `jsonIA` / `texteIA` : JSON vérifié, `null` si illisible, et le code prévoit toujours un repli.
- Deux workflows de gouvernance par client : **Purge des données personnelles** (chaque nuit, selon les durées du contrat) et **Journal des erreurs** (à choisir comme *Error workflow* dans les Settings de chaque workflow n8n).

Écrire dans une Sheet sans passer par `sheet_write(..., validation="…")` n'est pas possible dans `tools/build.py` : il faut dire qui valide ce qui est écrit.

## Les QA gates (`tools/qa.py`)

| Gate | Bloque si… |
|---|---|
| CONTRAT | une colonne n'est pas typée ou classée, les données de démo ou les Excel ne respectent pas le contrat, une clé étrangère est cassée |
| PERSO | une donnée perso n'a ni finalité ni durée, une donnée sensible apparaît, le Journal contient du perso |
| ECRITURE-PROPRIETAIRE | un agent écrit un onglet qui n'est pas le sien, ou un fichier non déclaré |
| GARDE-ECRITURE | une écriture n'a pas sa Garde, ou la Garde date d'un ancien contrat |
| JOURNAL / JOURNAL-ERREURS | une écriture n'est pas tracée, sa validation n'est pas déclarée, ou il n'y a pas de journal des erreurs |
| IA-ADAPTATEUR | un modèle ou un endpoint IA est écrit en dur |
| IA-GARDE | une réponse IA est utilisée sans `jsonIA` / `texteIA` |
| IA-ACTION | un envoi (mail, WhatsApp, Insta, paiement…) est en aval d'une IA sans validation humaine |
| SORTIES | un workflow ou une page appelle un domaine non déclaré |
| SECRETS | une clé, un token ou un credential est dans le repo |
| PURGE | une donnée perso ne peut pas être purgée automatiquement |
| SCENARIOS | un scénario échoue, ou une exigence n'a pas de scénario |

En niveau `demo`, ce qui ne compte qu'en prod (sorties de démo, contrôles manuels non signés, purge manuelle) est un **avertissement**. En niveau `prod`, **tout bloque**.

Le résultat est écrit dans `gouvernance/rapport-qa.md` : c'est le document à montrer au client. Il contient chaque exigence, comment elle est vérifiée, le résultat, et la liste de ce qu'il reste à faire avant la prod.

## La passe QA à partir du besoin client

1. **Besoin → exigences.** Après le diag, écrire les promesses dans `exigences` du manifeste, en mots du client (« aucune réponse ne part sans relecture »). Une exigence = au moins un contrôle automatique ou un contrôle manuel.
2. **Exigences → scénarios.** Pour chaque exigence vérifiable par le code, écrire un test dans `scenarios/` qui joue le cas réel, y compris quand l'IA répond mal ou pas du tout.
3. **Données → contrat.** Chaque colonne : type, liste, données perso, finalité, durée (à faire valider par le client).
4. **Build.** `python3 tools/build.py <client>` : la QA tourne, le rapport se met à jour.
5. **Avant la mise en prod.** Passer `niveau` à `prod`. Traiter tout ce qui bloque, faire signer les contrôles manuels dans `validations.json`, puis remettre le rapport au client.

## Ajouter un client

Copier `data/contrat.json`, `gouvernance/` (sans `n8n/` ni `rapport-qa.md`, qui sont générés) et adapter. Ajouter le client à la matrice de `.github/workflows/qa.yml`.
