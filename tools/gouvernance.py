"""Socle de gouvernance commun à tools/build.py et tools/qa.py.

Charge, pour un client :
  data/contrat.json              le contrat de données (colonnes, types, données perso, conservation, qui écrit)
  gouvernance/gouvernance.json   le manifeste (IA, sorties autorisées, journal, exigences client)
et résout les listes de valeurs qui renvoient vers les données du client (« valeurs_ref »).
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GARDE_JS = (ROOT / "tools" / "garde.js").read_text(encoding="utf-8")


def _get(obj, chemin):
    """'regles.creneaux.code' : descend dans l'objet ; une liste d'objets donne la liste des valeurs ;
    '@cles' donne les clés d'un dictionnaire."""
    cur = obj
    for part in chemin.split("."):
        if part == "@cles":
            cur = list(cur.keys())
        elif isinstance(cur, list):
            cur = [x[part] for x in cur]
        else:
            cur = cur[part]
    return cur


class Client:
    def __init__(self, nom):
        self.nom = nom
        self.dir = ROOT / "clients" / nom
        self.manifeste = self._json("gouvernance/gouvernance.json")
        self.contrat_brut = self._json("data/contrat.json")
        self.donnees = {b: self._json(f"data/{b}.json") for b in self.contrat_brut["bases"] if (self.dir / f"data/{b}.json").exists()}
        self.contrat = self._resoudre()

    def _json(self, p):
        return json.loads((self.dir / p).read_text(encoding="utf-8"))

    def _resoudre(self):
        out = {}
        for base, b in self.contrat_brut["bases"].items():
            out[base] = {}
            for onglet, o in b["onglets"].items():
                cols = {}
                for nom, spec in o["colonnes"].items():
                    s = {k: v for k, v in spec.items()}
                    if "valeurs_ref" in spec:
                        src, chemin = spec["valeurs_ref"].split(":", 1)
                        s["valeurs"] = [str(v) for v in _get(self.donnees[src], chemin)]
                    if "valeurs" in s and "valeurs_extra" in spec:
                        s["valeurs"] = s["valeurs"] + spec["valeurs_extra"]
                    cols[nom] = s
                out[base][onglet] = {**{k: v for k, v in o.items() if k != "colonnes"}, "nom": onglet, "base": base, "colonnes": cols}
        return out

    # ---- accès pratiques
    def onglet(self, base, onglet):
        return self.contrat[base][onglet]

    def colonnes(self, base, onglet):
        return list(self.contrat[base][onglet]["colonnes"].keys())

    def tous_onglets(self):
        for base, tabs in self.contrat.items():
            for nom, o in tabs.items():
                yield base, nom, o

    @property
    def ia(self):
        return self.manifeste["ia"]

    @property
    def journal(self):
        return self.manifeste["journal"]

    def sorties_autorisees(self, niveau=None):
        """Domaines autorisés → (raison, catégorie)."""
        m = self.manifeste
        niveau = niveau or m["niveau"]
        cats = ["souverain"] if m["hebergement"] == "souverain" else ["standard"]
        if niveau == "demo":
            cats.append("demo_seulement")
        return {d: (r, c) for c in cats for d, r in m["sorties"].get(c, {}).items() if not d.startswith("_")}


def js_const(nom, obj):
    return f"const {nom} = " + json.dumps(obj, ensure_ascii=False) + ";\n"


def empreinte(*objs):
    h = hashlib.sha256()
    for o in objs:
        h.update(json.dumps(o, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return h.hexdigest()[:10]
