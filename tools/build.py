"""Construit tout ce qui est généré pour un client, à partir des sources.

Usage (depuis la racine du repo) :
    pip install openpyxl            # une seule fois
    python3 tools/build.py          # client par défaut : maximum-kite
    python3 tools/build.py maximum-kite

Sources (on ne modifie QUE celles-ci) :
    clients/<client>/sheets.json                IDs des deux Google Sheets
    clients/<client>/data/matos.json            base Matos : parc, dégâts, utilisations, hypothèses
    clients/<client>/data/reservations.json     base Réservations : règles école, vent, demandes, réservations, messages
    clients/<client>/<agent>/demonstrateur/*.src.html
    clients/<client>/<agent>/n8n/code/*.js

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
import sys
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
CLIENT = sys.argv[1] if len(sys.argv) > 1 else "maximum-kite"
C = ROOT / "clients" / CLIENT
read = lambda p: (C / p).read_text(encoding="utf-8")
SHEETS = {k: v for k, v in json.loads(read("sheets.json")).items() if not k.startswith("_")}
MATOS = json.loads(read("data/matos.json"))
RESAS = json.loads(read("data/reservations.json"))
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
# Mêmes onglets et colonnes que les Google Sheets : un seul schéma partout.
SCHEMA = {
    "matos": {
        "Parc": ["id", "categorie", "designation", "date_achat", "prix_achat"],
        "Dégâts": ["date", "id", "type", "description", "gravite", "cout", "statut", "immobilise"],
        "Utilisations": ["date", "resa", "id", "heures", "client"],
        "Brief": ["date", "brief", "ok", "surveiller", "remplacer", "immobilise", "budget_12_mois"],
    },
    "reservations": {
        "Vent": ["date", "matin", "midi", "aprem", "dir", "source"],
        "Demandes": ["id", "recu", "canal", "contact", "langue", "message", "statut", "resume", "reponse", "proposition"],
        "Réservations": ["resa", "date", "creneau", "offre", "client", "canal", "contact", "langue", "nb", "participants",
                         "moniteur", "matos", "prix_total", "acompte", "statut", "code"],
        "Messages": ["date", "resa", "canal", "contact", "type", "texte", "statut"],
    },
}
oui = lambda b: "oui" if b else "non"
ROWS = {
    "Parc": MATOS["parc"],
    "Dégâts": [{**d, "cout": d["cout"] if d["cout"] is not None else "", "immobilise": oui(d["immobilise"])} for d in MATOS["degats"]],
    "Utilisations": [{**u, "date": J(u["j"])} for u in MATOS["utilisations"]],
    "Brief": [],
    "Vent": [{**v, "date": J(v["j"]), "source": "en dur (démo)"} for v in RESAS["vent"]],
    "Demandes": [{**d, "recu": J(0), "statut": "Nouveau"} for d in RESAS["demandes"]],
    "Réservations": [{**r, "date": J(r["j"])} for r in RESAS["reservations"]],
    "Messages": [{**m, "date": J(m["j"])} for m in RESAS["messages"]],
}
LISEZ_MOI = {
    "matos": ["Base MATOS — Maximum Kite — DONNÉES FICTIVES (démo VA Gwada)",
              "Parc : une ligne par pièce, id unique (K-01 = voile kite). Écrit à la main ou par le Gréeur.",
              "Dégâts : une ligne par dégât, id = une pièce du Parc. Écrit par le Gréeur.",
              "Utilisations : une ligne par pièce sortie en cours. Écrit par l'Accueil. resa renvoie à la base Réservations.",
              "Brief : une ligne par passage du brief du lundi (n8n).",
              "Hypothèses : règles de calcul du Gréeur."],
    "reservations": ["Base RÉSERVATIONS — Maximum Kite — DONNÉES FICTIVES (démo VA Gwada)",
                     "Vent : vent prévu par créneau (nœuds). Saisi à la main ou par une source météo (colonne source).",
                     "Demandes : messages reçus (Insta, email), la réponse préparée et son statut.",
                     "Réservations : une ligne par cours. matos = id(s) de la base Matos, séparés par des virgules.",
                     "Messages : tout ce qui a été envoyé (ou simulé) aux clients."],
}
LISTES = {("Dégâts", "C"): MATOS["types_degat"], ("Dégâts", "E"): ["Légère", "Moyenne", "Grave"],
          ("Dégâts", "G"): ["À réparer", "Chez le réparateur", "Réparé"], ("Dégâts", "H"): ["oui", "non"],
          ("Réservations", "C"): [c["code"] for c in RESAS["regles"]["creneaux"]],
          ("Réservations", "D"): [o["code"] for o in RESAS["regles"]["offres"]],
          ("Réservations", "O"): ["Proposé", "Confirmé", "Terminé", "Annulé"]}
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


def sheet_write(name, base, tab, pos, operation="append", match=None):
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


def code_node(name, js, pos):
    return {"parameters": {"jsCode": js}, "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": pos}


def claude(name, pos):
    return with_cred({
        "parameters": {
            "method": "POST", "url": "https://api.anthropic.com/v1/messages",
            "authentication": "predefinedCredentialType", "nodeCredentialType": "anthropicApi",
            "sendHeaders": True, "headerParameters": {"parameters": [{"name": "anthropic-version", "value": "2023-06-01"}]},
            "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}", "options": {},
        },
        "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": pos,
    }, "anthropicApi")


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
         sheet_write("Ajouter au carnet", "matos", "Dégâts", [1320, 0])]
    W[("greeur", "greeur-signalement-degat", "Gréeur — Signalement d'un dégât")] = (n, chain(*names(n)))

    # Gréeur 2 : brief du lundi (→ onglet Brief)
    n = [{"parameters": {"rule": {"interval": [{"field": "weeks", "triggerAtDay": [1], "triggerAtHour": 7}]}},
          "name": "Chaque lundi 7h", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [0, 0]},
         sheet_read("Lire Parc", "matos", "Parc", [220, 0]),
         sheet_read("Lire Dégâts", "matos", "Dégâts", [440, 0], True),
         code_node("Calculer le brief", REGLES_G + "\n" + G("brief.js"), [660, 0]),
         sheet_write("Écrire le brief", "matos", "Brief", [880, 0])]
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
         sheet_write("Ajouter aux Demandes", "reservations", "Demandes", [2200, 0])]
    W[("accueil", "accueil-demande-reservation", "Accueil — Demande de réservation")] = (n, chain(*names(n)))

    # Accueil 2 : après le cours, chaque soir 18h
    flat = lambda key: f"return $input.all().flatMap(i => [].concat(i.json.{key}).map(x => ({{ json: x }})));"
    n = [{"parameters": {"rule": {"interval": [{"field": "days", "triggerAtHour": 18}]}},
          "name": "Chaque soir 18h", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [0, 0]},
         sheet_read("Lire Réservations", "reservations", "Réservations", [220, 0]),
         code_node("Cours à clôturer", ACC + "\n" + A("accueil_apres.js"), [440, 0]),
         code_node("Lignes Utilisations", flat("_utils"), [660, -160]),
         sheet_write("Ajouter aux Utilisations", "matos", "Utilisations", [880, -160]),
         code_node("Lignes Messages", flat("_msg"), [660, 0]),
         sheet_write("Ajouter aux Messages", "reservations", "Messages", [880, 0]),
         code_node("Statut Terminé", "return $input.all().map(i => ({ json: { resa: i.json.resa, statut: i.json.statut, code: i.json.code } }));", [660, 160]),
         sheet_write("Mettre à jour Réservations", "reservations", "Réservations", [880, 160], operation="update", match="resa")]
    conn = chain("Chaque soir 18h", "Lire Réservations", "Cours à clôturer")
    conn["Cours à clôturer"] = {"main": [[{"node": x, "type": "main", "index": 0} for x in ("Lignes Utilisations", "Lignes Messages", "Statut Terminé")]]}
    for a, b in (("Lignes Utilisations", "Ajouter aux Utilisations"), ("Lignes Messages", "Ajouter aux Messages"), ("Statut Terminé", "Mettre à jour Réservations")):
        conn.update(chain(a, b))
    W[("accueil", "accueil-apres-le-cours", "Accueil — Après le cours")] = (n, conn)
    return W


SETTINGS = {"executionOrder": "v1", "timezone": "America/Guadeloupe"}
for local in ([False, True] if CREDS else [False]):
    USE_CREDS = local
    for (agent, fname, title), (nodes, conn) in workflows().items():
        wf = {"name": title, "nodes": nodes, "connections": conn, "settings": SETTINGS, "pinData": {}}
        out = C / agent / "n8n" / (fname + (".local.json" if local else ".json"))
        out.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"OK {CLIENT} : 2 pages, 2 bases Excel (dates à partir du {TODAY}), 4 workflows n8n" + (" (+ versions .local branchées)" if CREDS else ""))
