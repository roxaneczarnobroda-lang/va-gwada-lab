# Le Gréeur — d'où viennent les chiffres

Réponse à la question « sur quoi s'appuient les estimations de réparation et le budget de renouvellement ? ». Les mêmes règles tournent dans l'app de démo (`demonstrateur/greeur.src.html`) et dans n8n (`n8n/code/regles.js`).

## Ce que l'école fournit
- **Parc** : pour chaque pièce, catégorie, date d'achat et prix d'achat.
- **Dégâts** : date, pièce, type, gravité, coût payé, statut, immobilisée ou non.

## Ce que l'agent calcule

| Calcul | Règle | Base |
|---|---|---|
| Estimation d'une réparation | Médiane des coûts déjà payés par l'école pour le **même type** de dégât | Son historique. Sans historique : « à chiffrer », pas de prix inventé |
| À remplacer | Âge ≥ durée de vie de la catégorie, **ou** réparations payées ≥ 50 % du prix d'achat | Hypothèses ci-dessous |
| À surveiller | Âge ≥ 80 % de la durée de vie, **ou** réparations ≥ 30 % du prix, **ou** ≥ 2 dégâts en 6 mois | Hypothèses ci-dessous |
| Immobilisé | Un dégât marqué « ne pas sortir » et pas encore réparé | Saisie du moniteur, proposée par l'IA |
| Budget 12 mois | Prix d'achat des pièces à renouveler dans les 12 mois, moins 20 % de revente | Prix d'achat (pas de prix catalogue actuel) |

## Hypothèses de départ (à valider avec l'école)

| Catégorie | Durée de vie |
|---|---|
| Aile kite | 3 ans |
| Aile wing | 3 ans |
| Planche twintip | 4 ans |
| Planche wingfoil | 5 ans |
| Foil | 5 ans |
| Harnais | 2 ans |
| Barre | 3 ans |

Ces durées et ces seuils sont des **points de départ que j'ai choisis pour la démo**, pas des références du secteur. Je ne connais pas de source fiable sur la durée de vie du matériel en école (elle dépend beaucoup de l'usage, de l'eau, du stockage et des marques). Elles sont modifiables dans l'onglet *Règles de calcul* de l'app, et dans l'onglet *Hypothèses* du fichier Excel.

## Ce que l'IA fait, et ce qu'elle ne fait pas
- Elle **fait** : comprendre le message du moniteur, retrouver la pièce, choisir le type et la gravité dans une liste fermée, proposer d'immobiliser, poser une question si une info manque.
- Elle **ne fait pas** : chiffrer, décider de racheter, modifier les règles. L'ID qu'elle propose est vérifié par le code. Le moniteur valide avant que la ligne soit ajoutée (dans l'app).
