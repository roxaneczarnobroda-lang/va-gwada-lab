"""Construit tout ce qui est généré pour un client, à partir des sources.

Usage (depuis la racine du repo) :
    pip install openpyxl            # une seule fois
    python3 tools/build.py          # client par défaut : maximum-kite
    python3 tools/build.py maximum-kite

Sources (on ne modifie QUE celles-ci) :
    clients/<client>/data/contrat.json          CONTRAT DE DONNÉES : onglets, colonnes, types, données perso, conservation
    clients/<client>/gouvernance/gouvernance.json  MANIFESTE : IA, sorties autorisées, journal, exigences du client
    clients/<client>/sheets.json                IDs des deux Google Sheets
    clients/<client>/data/matos.json            base Matos : parc, dégâts, utilisations, hypothèses
    clients/<client>/data/reservations.json     base Réservations : règles école, vent, demandes, réservations, messages
    clients/<client>/<agent>/demonstrateur/*.src.html
    clients/<client>/<agent>/n8n/code/*.js

Gouvernance « by design » (rien à faire à la main, tout est ajouté ici) :
    · avant CHAQUE écriture dans une Sheet : un node « Garde » qui vérifie les lignes contre le contrat et bloque sinon ;
    · après CHAQUE écriture : un node « Journal » (onglet Journal : quoi, quand, version, validation) ;
    · les appels IA passent par l'adaptateur de tools/garde.js (modèle/endpoint du manifeste) ;
    · un workflow de purge des données perso et un workflow « Journal des erreurs » par client ;
    · puis tools/qa.py vérifie le tout (QA gates) et écrit gouvernance/rapport-qa.md. Le build échoue si une gate bloque.

Produit :
    clients/<client>/<agent>/demonstrateur/<agent>.html   pages de démo (données + règles intégrées)
    clients/<client>/<agent>/n8n/*.json                   workflows à importer dans n8n
    clients/<client>/data/generes/matos.xlsx, reservations.xlsx
                                                          les deux bases, dates calculées à partir d'aujourd'hui,
                                                          mêmes onglets et colonnes que les Google Sheets

Credentials n8n : jamais dans le repo. Si clients/<client>/credentials.local.json existe
({"anthropicApi": {"id": "...", "name": "..."}, "googleSheetsOAuth2Api": {...}}), le build écrit
en plus des *.local.json déjà branchés (ignorés par git).
"""
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gouvernance import GARDE_JS, Client, empreinte, js_const  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLIENT = sys.argv[1] if len(sys.argv) > 1 else "maximum-kite"
C = ROOT / "clients" / CLIENT
read = lambda p: (C / p).read_text(encoding="utf-8")
SHEETS = {k: v for k, v in json.loads(read("sheets.json")).items() if not k.startswith("_")}
MATOS = json.loads(read("data/matos.json"))
RESAS = json.loads(read("data/reservations.json"))
GOV = Client(CLIENT)
TODAY = date.today()
J = lambda j: (TODAY + timedelta(days=j)).isoformat()


def inject(src, out, **markers):
    s = read(src)
    for marker, value in markers.items():
        assert marker in s, f"{marker} absent de {src}"
        s = s.replace(marker, value)
    (C / out).write_text(s, encoding="utf-8")


js_json = lambda o: json.dumps(o, ensure_ascii=False).replace("<", "\\u003c")

# ---------------------------------------------------------------- 1. Pages de démo
inject("greeur/demonstrateur/greeur.src.html", "greeur/demonstrateur/greeur.html",
       **{"/*__DATA__*/null": js_json(MATOS), "/*__SHEETS__*/null": js_json(SHEETS)})

ACC_REGLES = read("accueil/n8n/code/accueil_regles.js")
assert "</script" not in ACC_REGLES
inject("accueil/demonstrateur/accueil.src.html", "accueil/demonstrateur/accueil.html",
       **{"/*__REGLES__*/": ACC_REGLES,
          "/*__DATA__*/null": js_json({"accueil": RESAS, "greeur": MATOS}),
          "/*__SHEETS__*/null": js_json(SHEETS)})

# ---------------------------------------------------------------- 2. Les deux bases en Excel
# Mêmes onglets et colonnes que les Google Sheets : un seul schéma partout, celui du CONTRAT (data/contrat.json).
SCHEMA = {base: {tab: GOV.colonnes(base, tab) for tab in tabs} for base, tabs in GOV.contrat.items()}
oui = lambda b: "oui" if b else "non"
ROWS = {
    "Parc": MATOS["parc"],
    "Dégâts": [{**d, "cout": d["cout"] if d["cout"] is not None else "", "immobilise": oui(d["immobilise"])} for d in MATOS["degats"]],
    "Utilisations": [{**u, "date": J(u["j"])} for u in MATOS["utilisations"]],
    "Brief": [],
    "Vent": [{**v, "date": J(v["j"]), "source": "en dur (démo)"} for v in RESAS["vent"]],
    "Demandes": [{**d, "recu": (datetime.now() - timedelta(minutes=d.get("recu_min", 0))).strftime("%Y-%m-%d %H:%M"), "statut": "Nouveau"}
                 for d in RESAS["demandes"]],
    "Réservations": [{**r, "date": J(r["j"])} for r in RESAS["reservations"]],
    "Messages": [{**m, "date": J(m["j"])} for m in RESAS["messages"]],
    "Journal": [],
}
LISEZ_MOI = {base: [f"{GOV.contrat_brut['bases'][base]['description']} — {GOV.manifeste['client']} — DONNÉES FICTIVES (démo VA Gwada)",
                    "Colonnes, types et données personnelles : voir data/contrat.json (source unique)."]
             + [f"{tab} : {o['description']}" for tab, o in GOV.contrat_brut["bases"][base]["onglets"].items()]
             + (["Hypothèses : règles de calcul du Gréeur."] if base == "matos" else [])
             for base in SCHEMA}
# Listes déroulantes : toutes les colonnes du contrat qui ont une liste de valeurs.
LISTES = {(tab, get_column_letter(i + 1)): spec["valeurs"]
          for base, tab, o in GOV.tous_onglets()
          for i, (col, spec) in enumerate(o["colonnes"].items()) if spec.get("valeurs")}
LISTES.update({(tab, get_column_letter(i + 1)): ["oui", "non"]
               for base, tab, o in GOV.tous_onglets()
               for i, (col, spec) in enumerate(o["colonnes"].items()) if spec["type"] == "oui_non"})
head, fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="0C4A55")
(C / "data" / "generes").mkdir(exist_ok=True)
for base, tabs in SCHEMA.items():
    wb = Workbook()
    wl = wb.active
    wl.title = "Lisez-moi"
    for line in LISEZ_MOI[base]:
        wl.append([line])
    wl.column_dimensions["A"].width = 100
    for tab, cols in tabs.items():
        ws = wb.create_sheet(tab)
        ws.append(cols)
        for r in ROWS[tab]:
            ws.append([r.get(c, "") for c in cols])
        for cell in ws[1]:
            cell.font, cell.fill = head, fill
        ws.freeze_panes = "A2"
        for (t, col), values in LISTES.items():
            if t == tab:
                dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
                ws.add_data_validation(dv)
                dv.add(f"{col}2:{col}1000")
    if base == "matos":
        wh = wb.create_sheet("Hypothèses")
        wh.append(["parametre", "valeur"])
        for k, v in MATOS["hypotheses"]["duree_vie_ans"].items():
            wh.append([f"duree_vie_ans · {k}", v])
        for k, v in MATOS["hypotheses"].items():
            if k != "duree_vie_ans":
                wh.append([k, v])
    wb.save(C / "data" / "generes" / f"{base}.xlsx")

# ---------------------------------------------------------------- 3. Workflows n8n
_cred = C / "credentials.local.json"
CREDS = json.loads(_cred.read_text(encoding="utf-8")) if _cred.exists() else {}
URL = {k: f"https://docs.google.com/spreadsheets/d/{v}/edit" for k, v in SHEETS.items()}
USE_CREDS = False


def with_cred(node, kind):
    if USE_CREDS and kind in CREDS:
        node["credentials"] = {kind: CREDS[kind]}
    return node


def doc(base):
    return {"__rl": True, "mode": "url", "value": URL[base]}


def sheet_read(name, base, tab, pos, execute_once=False):
    n = {"parameters": {"documentId": doc(base), "sheetName": {"__rl": True, "mode": "name", "value": tab}, "options": {}},
         "name": name, "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5, "position": pos, "alwaysOutputData": True}
    if execute_once:
        n["executeOnce"] = True
    return with_cred(n, "googleSheetsOAuth2Api")


OPERATIONS = {"append": "ajout", "update": "mise à jour"}


def sheet_write(name, base, tab, pos, operation="append", match=None, *, validation, purge=False):
    """Écriture dans une Sheet. `validation` est OBLIGATOIRE : dire qui valide ce qui est écrit
    (ex. « humaine — à valider dans la page », « non requise — calcul », « modèle fixe »).
    gouverner() ajoute ensuite le node Garde avant et le Journal après."""
    assert validation, f"{name} : préciser la validation"
    assert tab in GOV.contrat[base], f"{name} : onglet {base}/{tab} absent du contrat"
    if match:
        assert match == GOV.onglet(base, tab)["cle"], f"{name} : on met à jour par la clé du contrat"
    n = _sheet_write(name, base, tab, pos, operation, match)
    n["_gouv"] = {"base": base, "onglet": tab, "operation": "purge" if purge else OPERATIONS[operation], "validation": validation}
    return n


def _sheet_write(name, base, tab, pos, operation="append", match=None):
    cols = {"mappingMode": "autoMapInputData", "value": {}}
    if match:
        cols["matchingColumns"] = [match]
    opts = {"cellFormat": "RAW"}
    if operation == "append":
        opts["handlingExtraData"] = "ignoreIt"
    return with_cred({
        "parameters": {"documentId": doc(base), "sheetName": {"__rl": True, "mode": "name", "value": tab},
                       "operation": operation, "columns": cols, "options": opts},
        "name": name, "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5, "position": pos,
    }, "googleSheetsOAuth2Api")


IA_PUBLIC = {k: GOV.ia[k] for k in ("modele", "max_tokens")}


def code_node(name, js, pos):
    # Adaptateur IA : tout node qui prépare ou lit un appel IA reçoit garde.js + la config IA du manifeste.
    if any(f in js for f in ("corpsIA(", "texteIA(", "jsonIA(")):
        js = js_const("GOUV_IA", IA_PUBLIC) + GARDE_JS + "\n" + js
    return {"parameters": {"jsCode": js}, "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": pos}


def claude(name, pos):
    return with_cred({
        "parameters": {
            "method": "POST", "url": GOV.ia["endpoint"],
            "authentication": "predefinedCredentialType", "nodeCredentialType": GOV.ia["credential_n8n"],
            "sendHeaders": True, "headerParameters": {"parameters": [{"name": "anthropic-version", "value": "2023-06-01"}]},
            "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}", "options": {},
        },
        "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": pos,
    }, GOV.ia["credential_n8n"])


def form(name, title, desc, fields, hook):
    return {"parameters": {"formTitle": title, "formDescription": desc, "formFields": {"values": fields}, "options": {}},
            "name": name, "type": "n8n-nodes-base.formTrigger", "typeVersion": 2.2, "position": [0, 0], "webhookId": hook}


def chain(*names):
    return {a: {"main": [[{"node": b, "type": "main", "index": 0}]]} for a, b in zip(names, names[1:])}


def names(nodes):
    return [n["name"] for n in nodes]


G = lambda f: read(f"greeur/n8n/code/{f}")
A = lambda f: read(f"accueil/n8n/code/{f}")


def workflows():
    REGLES_G = G("regles.js")
    ACC = "const R = " + json.dumps(RESAS["regles"], ensure_ascii=False) + ";\n" + A("accueil_regles.js")
    W = {}

    # Gréeur 1 : signalement d'un dégât (formulaire → IA → onglet Dégâts)
    n = [form("Formulaire dégât", "Le Gréeur — signaler un dégât", "Dis en une phrase ce qui est arrivé au matos.",
              [{"fieldLabel": "Moniteur", "requiredField": True},
               {"fieldLabel": "Ce qui s'est passé", "fieldType": "textarea", "requiredField": True}], "greeur-signalement"),
         sheet_read("Lire Parc", "matos", "Parc", [220, 0]),
         sheet_read("Lire Dégâts", "matos", "Dégâts", [440, 0], True),
         code_node("Préparer la demande IA", G("signalement_prompt.js"), [660, 0]),
         claude("Claude analyse le message", [880, 0]),
         code_node("Construire la ligne Dégâts", REGLES_G + "\n" + G("signalement_ligne.js"), [1100, 0]),
         sheet_write("Ajouter au carnet", "matos", "Dégâts", [1320, 0],
                     validation="humaine — dégât « À traiter » dans la page du Gréeur")]
    W[("greeur", "greeur-signalement-degat", "Gréeur — Signalement d'un dégât")] = (n, chain(*names(n)))

    # Gréeur 2 : brief du lundi (→ onglet Brief)
    n = [{"parameters": {"rule": {"interval": [{"field": "weeks", "triggerAtDay": [1], "triggerAtHour": 7}]}},
          "name": "Chaque lundi 7h", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [0, 0]},
         sheet_read("Lire Parc", "matos", "Parc", [220, 0]),
         sheet_read("Lire Dégâts", "matos", "Dégâts", [440, 0], True),
         code_node("Calculer le brief", REGLES_G + "\n" + G("brief.js"), [660, 0]),
         sheet_write("Écrire le brief", "matos", "Brief", [880, 0], validation="non requise — calcul par les règles, sans IA")]
    W[("greeur", "greeur-brief-hebdo", "Gréeur — Brief matos du lundi")] = (n, chain(*names(n)))

    # Accueil 1 : demande de réservation. Le formulaire simule un DM Instagram / un email.
    n = [form("Message reçu", "L'Accueil — simuler un message de vacancier",
              "Ce que le vacancier écrirait sur Instagram ou par email, dans n'importe quelle langue.",
              [{"fieldLabel": "Canal", "fieldType": "dropdown", "requiredField": True,
                "fieldOptions": {"values": [{"option": "Instagram"}, {"option": "Email"}]}},
               {"fieldLabel": "Expéditeur", "requiredField": True, "placeholder": "@pseudo ou adresse email"},
               {"fieldLabel": "Message", "fieldType": "textarea", "requiredField": True}], "accueil-demande"),
         sheet_read("Lire Parc", "matos", "Parc", [220, 0]),
         sheet_read("Lire Dégâts", "matos", "Dégâts", [440, 0], True),
         sheet_read("Lire Réservations", "reservations", "Réservations", [660, 0], True),
         sheet_read("Lire Vent", "reservations", "Vent", [880, 0], True),
         code_node("Préparer la lecture IA", ACC + "\n" + A("accueil_lecture.js"), [1100, 0]),
         claude("Claude lit le message", [1320, 0]),
         code_node("Vérifier créneau, matos, vent", REGLES_G + "\n" + ACC + "\n" + A("accueil_verifier.js"), [1540, 0]),
         claude("Claude rédige la réponse", [1760, 0]),
         code_node("Construire la ligne Demandes", A("accueil_ligne_demande.js"), [1980, 0]),
         sheet_write("Ajouter aux Demandes", "reservations", "Demandes", [2200, 0],
                     validation="humaine — réponse IA en attente de validation dans la page, rien n'est envoyé")]
    W[("accueil", "accueil-demande-reservation", "Accueil — Demande de réservation")] = (n, chain(*names(n)))

    # Accueil 2 : après le cours, chaque soir 18h
    flat = lambda key: f"return $input.all().flatMap(i => [].concat(i.json.{key}).map(x => ({{ json: x }})));"
    n = [{"parameters": {"rule": {"interval": [{"field": "days", "triggerAtHour": 18}]}},
          "name": "Chaque soir 18h", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [0, 0]},
         sheet_read("Lire Réservations", "reservations", "Réservations", [220, 0]),
         code_node("Cours à clôturer", ACC + "\n" + A("accueil_apres.js"), [440, 0]),
         code_node("Lignes Utilisations", flat("_utils"), [660, -320]),
         sheet_write("Ajouter aux Utilisations", "matos", "Utilisations", [880, -320], validation="non requise — calcul par les règles"),
         code_node("Lignes Messages", flat("_msg"), [660, 0]),
         sheet_write("Ajouter aux Messages", "reservations", "Messages", [880, 0], validation="modèle fixe — pas de texte généré par l'IA"),
         code_node("Statut Terminé", "return $input.all().map(i => ({ json: { resa: i.json.resa, statut: i.json.statut, code: i.json.code } }));", [660, 320]),
         sheet_write("Mettre à jour Réservations", "reservations", "Réservations", [880, 320], operation="update", match="resa",
                     validation="non requise — changement de statut par les règles")]
    conn = chain("Chaque soir 18h", "Lire Réservations", "Cours à clôturer")
    conn["Cours à clôturer"] = {"main": [[{"node": x, "type": "main", "index": 0} for x in ("Lignes Utilisations", "Lignes Messages", "Statut Terminé")]]}
    for a, b in (("Lignes Utilisations", "Ajouter aux Utilisations"), ("Lignes Messages", "Ajouter aux Messages"), ("Statut Terminé", "Mettre à jour Réservations")):
        conn.update(chain(a, b))
    W[("accueil", "accueil-apres-le-cours", "Accueil — Après le cours")] = (n, conn)
    return W


# ---------------------------------------------------------------- 4. Gouvernance by design
CONTRAT_V = empreinte(GOV.contrat)
JOURNAL_ONGLET = GOV.onglet(GOV.journal["base"], GOV.journal["onglet"])
is_ia = lambda n: n["type"] == "n8n-nodes-base.httpRequest" and n["parameters"].get("url") == GOV.ia["endpoint"]


def garde_node(name, base, tab, operation, pos):
    js = (f"// Garde contrat — {base}/{tab} ({operation}). Généré par tools/build.py depuis data/contrat.json.\n"
          "// Vérifie chaque ligne (types, listes, formats, obligatoires), retire ce qui n'est pas au contrat, bloque tout le lot sinon.\n"
          + js_const("GOUV_ONGLET", GOV.onglet(base, tab)) + GARDE_JS
          + f"\nreturn garderLot(GOUV_ONGLET, $input.all(), {json.dumps(operation, ensure_ascii=False)});")
    return {"parameters": {"jsCode": js}, "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": pos}


def journal_node(name, entete, pos):
    js = ("// Journal — une ligne par écriture. Généré par tools/build.py. Aucune donnée personnelle : seulement les clés.\n"
          + js_const("GOUV_ONGLET", JOURNAL_ONGLET) + js_const("E", entete) + GARDE_JS + r"""
const lignes = $input.all();
let h; try { h = $now.toFormat('yyyy-MM-dd HH:mm:ss'); } catch (e) { h = new Date().toISOString().slice(0, 19).replace('T', ' '); }
const cles = [...new Set(lignes.map(i => i.json[E.cle]).filter(v => v !== undefined && v !== null && v !== ''))];
return garderLot(GOUV_ONGLET, [{ json: {
  horodatage: h, execution: String($execution.id), workflow: $workflow.name, version: E.version, agent: E.agent,
  base: E.base, onglet: E.onglet, operation: E.operation, nb_lignes: lignes.length, cles: cles.join(', ').slice(0, 500),
  ia_modele: E.ia_modele, controle: 'conforme au contrat ' + E.contrat, validation: E.validation, statut: 'ok',
} }], 'ajout');""")
    return {"parameters": {"jsCode": js}, "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": pos}


def lien(name):
    return {"node": name, "type": "main", "index": 0}


def gouverner(agent, nodes, conn):
    """Ajoute Garde avant et Journal après chaque écriture ; calcule la version du workflow."""
    version = empreinte(nodes, conn, CONTRAT_V, GOV.ia)
    ia_modele = GOV.ia["modele"] if any(is_ia(n) for n in nodes) else ""
    out = []
    for w in nodes:
        meta = w.pop("_gouv", None)
        if not meta:
            out.append(w)
            continue
        x, y = w["position"]
        g = garde_node(f"Garde — {w['name']}", meta["base"], meta["onglet"], meta["operation"], [x, y])
        w["position"] = [x + 220, y]
        o = GOV.onglet(meta["base"], meta["onglet"])
        entete = {"version": version, "contrat": CONTRAT_V, "agent": agent, "base": meta["base"], "onglet": meta["onglet"],
                  "operation": meta["operation"], "cle": o["cle"], "ia_modele": ia_modele, "validation": meta["validation"]}
        j = journal_node(f"Journal — {w['name']}", entete, [x + 440, y])
        jw = _sheet_write(f"Tracer — {w['name']}", GOV.journal["base"], GOV.journal["onglet"], [x + 660, y])
        for d in conn.values():
            for sortie in d["main"]:
                for l in sortie:
                    if l["node"] == w["name"]:
                        l["node"] = g["name"]
        conn[g["name"]] = {"main": [[lien(w["name"])]]}
        conn.setdefault(w["name"], {"main": [[]]})["main"][0].append(lien(j["name"]))
        conn[j["name"]] = {"main": [[lien(jw["name"])]]}
        out += [g, w, j, jw]
    return out, conn, version


def workflows_gouvernance():
    W = {}
    # Purge : chaque nuit, les colonnes perso dont la durée de conservation est dépassée passent à « [purgé] ».
    trig = {"parameters": {"rule": {"interval": [{"field": "days", "triggerAtHour": 3}]}},
            "name": "Chaque nuit 3h", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [0, 0]}
    n, conn, y = [trig], {"Chaque nuit 3h": {"main": [[]]}}, 0
    for base, tab, o in GOV.tous_onglets():
        perso = {c: s["conservation_jours"] for c, s in o["colonnes"].items() if s["perso"] != "non" and s.get("conservation_jours")}
        if not perso or not o.get("cle_unique") or not o.get("date_reference"):
            continue
        cfg = {"cle": o["cle"], "date_ref": o["date_reference"], "perso": perso}
        sel = (js_const("P", cfg) + r"""// Sélectionne les lignes dont au moins une colonne perso a dépassé sa durée de conservation.
const age = v => { const d = new Date(String(v).trim().replace(' ', 'T').slice(0, 16)); return isNaN(d) ? null : (Date.now() - d) / 864e5; };
const out = [];
for (const r of $input.all().map(i => i.json)) {
  const a = r[P.cle] ? age(r[P.date_ref]) : null;
  if (a === null) continue;
  const p = {};
  for (const [c, jours] of Object.entries(P.perso)) if (a > jours && r[c] !== '' && r[c] !== '[purgé]' && r[c] !== undefined) p[c] = '[purgé]';
  if (Object.keys(p).length) out.push({ json: { [P.cle]: r[P.cle], ...p } });
}
return out;""")
        n += [sheet_read(f"Lire {tab}", base, tab, [220, y]),
              code_node(f"À purger — {tab}", sel, [440, y]),
              sheet_write(f"Purger {tab}", base, tab, [660, y], operation="update", match=o["cle"], purge=True,
                          validation="non requise — durées de conservation du contrat")]
        conn["Chaque nuit 3h"]["main"][0].append(lien(f"Lire {tab}"))
        conn.update(chain(f"Lire {tab}", f"À purger — {tab}", f"Purger {tab}"))
        y += 220
    W[("gouvernance", "gouvernance-purge", "Gouvernance — Purge des données personnelles")] = (n, conn)

    # Erreurs : à choisir comme « Error workflow » dans les Settings de chaque workflow.
    err = js_const("GOUV_ONGLET", JOURNAL_ONGLET) + GARDE_JS + r"""
// Le message d'erreur peut contenir des valeurs (« … ») : on les masque, le Journal ne garde aucune donnée perso.
const x = $input.first().json, ex = x.execution || {}, er = ex.error || {};
const msg = String(er.message || 'erreur').replace(/«[^»]*»/g, '«…»').slice(0, 200);
let h; try { h = $now.toFormat('yyyy-MM-dd HH:mm:ss'); } catch (e) { h = new Date().toISOString().slice(0, 19).replace('T', ' '); }
return garderLot(GOUV_ONGLET, [{ json: {
  horodatage: h, execution: String(ex.id || ''), workflow: (x.workflow && x.workflow.name) || '?', version: '—', agent: 'gouvernance',
  base: '—', onglet: String(ex.lastNodeExecuted || ''), operation: 'erreur', nb_lignes: 0, cles: '', ia_modele: '',
  controle: msg, validation: 'à reprendre par l\'équipe', statut: 'erreur',
} }], 'ajout');"""
    n = [{"parameters": {}, "name": "Erreur d'un workflow", "type": "n8n-nodes-base.errorTrigger", "typeVersion": 1, "position": [0, 0]},
         {"parameters": {"jsCode": err}, "name": "Ligne Journal erreur", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [220, 0]},
         _sheet_write("Tracer l'erreur", GOV.journal["base"], GOV.journal["onglet"], [440, 0])]
    W[("gouvernance", "gouvernance-journal-erreurs", "Gouvernance — Journal des erreurs")] = (n, chain(*names(n)))
    return W


SETTINGS = {"executionOrder": "v1", "timezone": "America/Guadeloupe"}
VERSIONS = {}
for local in ([False, True] if CREDS else [False]):
    USE_CREDS = local
    for (agent, fname, title), (nodes, conn) in {**workflows(), **workflows_gouvernance()}.items():
        if agent == "gouvernance" and fname.endswith("erreurs"):
            version = empreinte(nodes, conn)
        else:
            nodes, conn, version = gouverner(agent, nodes, conn)
        VERSIONS[fname] = version
        note = {"parameters": {"content": f"## Gouvernance VA Gwada\nVersion **{version}** · contrat **{CONTRAT_V}**\n\n"
                               "Généré par `tools/build.py` : ne pas modifier ici. Chaque écriture passe par un node **Garde** "
                               "(contrat de données) puis un node **Journal** (onglet Journal).\n\n"
                               "Settings → Error workflow : « Gouvernance — Journal des erreurs ».",
                               "height": 220, "width": 420, "color": 4},
                "name": "Gouvernance", "type": "n8n-nodes-base.stickyNote", "typeVersion": 1, "position": [-520, -120]}
        wf = {"name": title, "nodes": nodes + [note], "connections": conn, "settings": SETTINGS, "pinData": {}}
        dossier = C / agent / "n8n"
        dossier.mkdir(parents=True, exist_ok=True)
        out = dossier / (fname + (".local.json" if local else ".json"))
        out.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"OK {CLIENT} : 2 pages, 2 bases Excel (dates à partir du {TODAY}), {len(VERSIONS)} workflows n8n gouvernés"
      + (" (+ versions .local branchées)" if CREDS else ""))

# ---------------------------------------------------------------- 5. QA gates
r = subprocess.run([sys.executable, str(ROOT / "tools" / "qa.py"), CLIENT])
sys.exit(r.returncode)
