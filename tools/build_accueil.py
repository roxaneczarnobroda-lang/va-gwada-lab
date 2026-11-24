"""Construit les livrables de L'Accueil à partir des sources uniques.

Usage (depuis la racine du repo) :
    python3 tools/build_accueil.py

Sources :
- clients/maximum-kite/data/accueil-demo.json   (offres, vent, demandes, réservations… dates relatives)
- clients/maximum-kite/data/parc-matos-demo.json (parc et dégâts : le même fichier que le Gréeur)
- clients/maximum-kite/n8n/code/accueil_regles.js (règles, partagées avec n8n)

Produit :
- clients/maximum-kite/demonstrateur/accueil.html (app web, données et règles intégrées)
- clients/maximum-kite/data/accueil-*.csv          (onglets à coller dans la Google Sheet de test,
                                                    dates calculées à partir du jour du build)
"""
import csv
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MK = ROOT / "clients" / "maximum-kite"
acc = json.loads((MK / "data" / "accueil-demo.json").read_text(encoding="utf-8"))
gre = json.loads((MK / "data" / "parc-matos-demo.json").read_text(encoding="utf-8"))
regles_js = (MK / "n8n" / "code" / "accueil_regles.js").read_text(encoding="utf-8")

# 1. App web
data = {"accueil": acc, "greeur": {"parc": gre["parc"], "degats": gre["degats"], "hypotheses": gre["hypotheses"]}}
payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
src = (MK / "demonstrateur" / "accueil.src.html").read_text(encoding="utf-8")
assert "/*__DATA__*/null" in src and "/*__REGLES__*/" in src
assert "</script" not in regles_js
out = src.replace("/*__REGLES__*/", regles_js).replace("/*__DATA__*/null", payload)
(MK / "demonstrateur" / "accueil.html").write_text(out, encoding="utf-8")

# 2. CSV pour la Google Sheet (dates réelles à partir d'aujourd'hui)
today = date.today()
J = lambda j: (today + timedelta(days=j)).isoformat()
TABS = {
    "vent": (["date", "matin", "midi", "aprem", "dir"], [{**v, "date": J(v["j"])} for v in acc["vent"]]),
    "demandes": (["id", "recu", "canal", "contact", "langue", "message", "statut", "resume", "reponse"],
                 [{**d, "recu": J(0), "statut": "Nouveau"} for d in acc["demandes"]]),
    "reservations": (["resa", "date", "creneau", "offre", "client", "canal", "contact", "langue", "nb", "participants",
                      "moniteur", "matos", "prix_total", "acompte", "statut", "code"],
                     [{**r, "date": J(r["j"])} for r in acc["reservations"]]),
    "utilisations": (["date", "resa", "id", "heures", "client"], [{**u, "date": J(u["j"])} for u in acc["utilisations"]]),
    "messages": (["date", "resa", "canal", "contact", "type", "texte", "statut"], [{**m, "date": J(m["j"])} for m in acc["messages"]]),
}
for name, (cols, rows) in TABS.items():
    with open(MK / "data" / f"accueil-{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])

print("OK : accueil.html + accueil-*.csv (dates à partir du", today.isoformat() + ")")
