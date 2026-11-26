"""Vérifie l'intégrité du Journal réel d'un client (chaîne d'empreintes) et l'ancre dans git.

Usage (depuis la racine du repo) :
    python3 tools/verifier_journal.py maximum-kite journal.csv            # vérifie
    python3 tools/verifier_journal.py maximum-kite journal.csv --ancrer   # vérifie puis ajoute une ancre

journal.csv : l'onglet Journal exporté (Fichier → Télécharger → CSV), ou un JSON {"values": [[en-têtes], [ligne], …]}
tel que le renvoie l'API Google Sheets.

Deux contrôles :
  1. la chaîne : chaque ligne porte l'empreinte de la précédente et sa propre empreinte est juste ;
  2. les ancres (clients/<client>/gouvernance/ancres.json, versionnées dans git) : la ligne n°N du Journal doit
     toujours avoir l'empreinte relevée lors de l'ancrage. Sans ancre, quelqu'un pourrait réécrire TOUTE la chaîne
     en recalculant les empreintes ; avec, il faudrait aussi réécrire l'historique git.
Code de sortie 1 si le Journal a été altéré.
"""
import csv
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gouvernance import GARDE_JS, Client  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 2:
    sys.exit(__doc__)
client, fichier = args
GOV = Client(client)
onglet = GOV.onglet(GOV.journal["base"], GOV.journal["onglet"])

p = Path(fichier)
if p.suffix == ".json":
    values = json.loads(p.read_text(encoding="utf-8"))["values"]
else:
    values = list(csv.reader(p.open(encoding="utf-8")))
entete, rows = values[0], [r for r in values[1:] if any(r)]
lignes = [dict(zip(entete, r + [""] * (len(entete) - len(r)))) for r in rows]

with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(GARDE_JS + f"\nconsole.log(JSON.stringify(verifierChaine({json.dumps(onglet, ensure_ascii=False)}, "
            f"{json.dumps(lignes, ensure_ascii=False)})));")
res = json.loads(subprocess.run(["node", f.name], capture_output=True, text=True, check=True).stdout)
Path(f.name).unlink()

ancres_p = GOV.dir / "gouvernance" / "ancres.json"
ancres = json.loads(ancres_p.read_text(encoding="utf-8")) if ancres_p.exists() else []
for a in ancres:
    if a["n"] > len(lignes):
        res["ruptures"].append({"ligne": a["n"] + 1, "raison": f"ancre du {a['date']} : le Journal avait {a['n']} lignes, il n'en a plus que {len(lignes)}"})
    elif lignes[a["n"] - 1].get("empreinte") != a["empreinte"]:
        res["ruptures"].append({"ligne": a["n"] + 1, "raison": f"ancre du {a['date']} : empreinte différente (chaîne réécrite ?)"})

if res["ruptures"]:
    print(f"❌ Journal ALTÉRÉ ({len(lignes)} lignes) :")
    for r in res["ruptures"][:20]:
        print(f"   ligne {r['ligne']} : {r['raison']}")
    sys.exit(1)
print(f"✅ Journal intègre : {len(lignes)} lignes, {len(ancres)} ancre(s) respectée(s), dernière empreinte {res['derniere'][:12]}…")
if "--ancrer" in sys.argv and lignes:
    ancres.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "n": len(lignes), "empreinte": res["derniere"]})
    ancres_p.write_text(json.dumps(ancres, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Ancre ajoutée dans {ancres_p.relative_to(GOV.dir.parent.parent)} : à commiter.")
