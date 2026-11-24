# Maximum Kite — les deux bases (données fictives)

Comme une petite base de données : un fichier par sujet, reliés par des identifiants.

```
        Base MATOS                                   Base RÉSERVATIONS
  ┌──────────────┐                            ┌───────────────────┐
  │ Parc         │◀── id ─────────────────────│ Réservations      │  matos = id(s) de pièces
  │  id (clé)    │                            │  resa (clé)       │
  └──────────────┘                            └───────────────────┘
        ▲  ▲                                          ▲
   id   │  │ id                                       │ resa
  ┌─────┴──┴─────┐                            ┌───────┴───────────┐
  │ Dégâts       │   ┌──────────────┐ resa ──▶│ Messages          │
  └──────────────┘   │ Utilisations │─────────┘ Demandes · Vent   │
                     │ id + resa    │          └───────────────────┘
  Brief              └──────────────┘
```

## Base Matos — `matos.json` · Google Sheet « Maximum Kite — Matos »

| Onglet | Une ligne = | Clé | Écrit par | Lu par |
|---|---|---|---|---|
| Parc | une pièce de matos | `id` | l'école (à la main) | Gréeur, Accueil |
| Dégâts | un dégât | `id` → Parc | Gréeur | Gréeur, Accueil (pièces immobilisées) |
| Utilisations | une pièce sortie en cours | `id` → Parc, `resa` → Réservations | Accueil | Gréeur (plus tard : usure à l'heure) |
| Brief | un passage du brief du lundi | `date` | Gréeur (n8n) | page du Gréeur |

## Base Réservations — `reservations.json` · Google Sheet « Maximum Kite — Réservations »

| Onglet | Une ligne = | Clé | Écrit par | Lu par |
|---|---|---|---|---|
| Vent | un jour (vent par créneau) | `date` | en dur pour la démo ; plus tard source météo ou l'école | Accueil |
| Demandes | un message reçu | `id` | Accueil (n8n ou page) | Accueil |
| Réservations | un cours | `resa` | Accueil | Accueil, planning |
| Messages | un message envoyé | `resa` | Accueil | l'équipe |

Les règles de l'école (tarifs, créneaux, moniteurs, tailles) sont dans `reservations.json` → `regles` : ce sont des réglages, pas des données qui bougent.

Les colonnes exactes de chaque onglet sont dans `tools/build.py` (`SCHEMA`), et c'est ce schéma qui génère les Excel de `generes/`.
