"""Assemble les workflows n8n importables (Gréeur et Accueil) à partir des fichiers de code.

Usage (depuis la racine du repo) :
    python3 tools/build_n8n.py

Le code JavaScript vit dans clients/maximum-kite/n8n/code/*.js (lisible, testable).
Ce script l'injecte dans les nodes Code et écrit les .json à importer dans n8n
(menu ⋯ → Import from File). Les credentials ne sont PAS dans les fichiers :
il faut les choisir dans n8n après l'import.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
N8N = ROOT / "clients" / "maximum-kite" / "n8n"
code = lambda name: (N8N / "code" / name).read_text(encoding="utf-8")
REGLES = code("regles.js")
# L'Accueil : règles tirées du JSON de démo (une seule source) + fonctions partagées avec la page web
_acc = json.loads((ROOT / "clients" / "maximum-kite" / "data" / "accueil-demo.json").read_text(encoding="utf-8"))
ACC = "const R = " + json.dumps(_acc["regles"], ensure_ascii=False) + ";\n" + code("accueil_regles.js")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1s32iebX2wKko-Ax9UkXIcGONCsv6nh8iqgGmIet5xU8/edit"

# Credentials propres à chaque instance n8n : dans n8n/credentials.local.json (ignoré par git).
# Format : {"anthropicApi": {"id": "...", "name": "..."}, "googleSheetsOAuth2Api": {...}}
_cred_file = N8N / "credentials.local.json"
CREDS = json.loads(_cred_file.read_text(encoding="utf-8")) if _cred_file.exists() else {}


USE_CREDS = False  # basculé plus bas : le repo reçoit des fichiers sans credentials


def with_cred(node, kind):
    if USE_CREDS and kind in CREDS:
        node["credentials"] = {kind: CREDS[kind]}
    return node


def sheet_read(name, tab, pos, execute_once=False):
    n = {
        "parameters": {
            "documentId": {"__rl": True, "mode": "url", "value": SHEET_URL},
            "sheetName": {"__rl": True, "mode": "name", "value": tab},
            "options": {},
        },
        "name": name, "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5, "position": pos,
        "alwaysOutputData": True,
    }
    if execute_once:
        n["executeOnce"] = True
    return with_cred(n, "googleSheetsOAuth2Api")


def code_node(name, js, pos):
    return {"parameters": {"jsCode": js}, "name": name, "type": "n8n-nodes-base.code", "typeVersion": 2, "position": pos}


def sheet_write(name, tab, pos, operation="append", match=None):
    cols = {"mappingMode": "autoMapInputData", "value": {}}
    if match:
        cols["matchingColumns"] = [match]
    return with_cred({
        "parameters": {
            "documentId": {"__rl": True, "mode": "url", "value": SHEET_URL},
            "sheetName": {"__rl": True, "mode": "name", "value": tab},
            "operation": operation,
            "columns": cols,
            "options": {"handlingExtraData": "ignoreIt", "cellFormat": "RAW"} if operation == "append" else {"cellFormat": "RAW"},
        },
        "name": name, "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5, "position": pos,
    }, "googleSheetsOAuth2Api")


def claude(name, pos):
    return with_cred({
        "parameters": {
            "method": "POST", "url": "https://api.anthropic.com/v1/messages",
            "authentication": "predefinedCredentialType", "nodeCredentialType": "anthropicApi",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "anthropic-version", "value": "2023-06-01"}]},
            "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}",
            "options": {},
        },
        "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": pos,
    }, "anthropicApi")


def link(*names):
    return {a: {"main": [[{"node": b, "type": "main", "index": 0}]]} for a, b in zip(names, names[1:])}


def build():
    # --- Workflow 1 : signalement d'un dégât -------------------------------------------------
    wf1_nodes = [
        {
            "parameters": {
                "formTitle": "Le Gréeur — signaler un dégât",
                "formDescription": "Dis en une phrase ce qui est arrivé au matos.",
                "formFields": {"values": [
                    {"fieldLabel": "Moniteur", "requiredField": True},
                    {"fieldLabel": "Ce qui s'est passé", "fieldType": "textarea", "requiredField": True},
                ]},
                "options": {},
            },
            "name": "Formulaire dégât", "type": "n8n-nodes-base.formTrigger", "typeVersion": 2.2, "position": [0, 0],
            "webhookId": "greeur-signalement",
        },
        sheet_read("Lire Parc", "Parc", [220, 0]),
        sheet_read("Lire Dégâts", "Dégâts", [440, 0], execute_once=True),
        code_node("Préparer la demande IA", code("signalement_prompt.js"), [660, 0]),
        with_cred({
            "parameters": {
                "method": "POST", "url": "https://api.anthropic.com/v1/messages",
                "authentication": "predefinedCredentialType", "nodeCredentialType": "anthropicApi",
                "sendHeaders": True,
                "headerParameters": {"parameters": [{"name": "anthropic-version", "value": "2023-06-01"}]},
                "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}",
                "options": {},
            },
            "name": "Claude analyse le message", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [880, 0],
        }, "anthropicApi"),
        code_node("Construire la ligne Dégâts", REGLES + "\n" + code("signalement_ligne.js"), [1100, 0]),
        with_cred({
            "parameters": {
                "documentId": {"__rl": True, "mode": "url", "value": SHEET_URL},
                "sheetName": {"__rl": True, "mode": "name", "value": "Dégâts"},
                "operation": "append",
                "columns": {"mappingMode": "autoMapInputData", "value": {}},
                "options": {"handlingExtraData": "ignoreIt", "cellFormat": "RAW"},
            },
            "name": "Ajouter au carnet", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5, "position": [1320, 0],
        }, "googleSheetsOAuth2Api"),
    ]
    wf1_conn = link("Formulaire dégât", "Lire Parc", "Lire Dégâts", "Préparer la demande IA",
                    "Claude analyse le message", "Construire la ligne Dégâts", "Ajouter au carnet")

    # --- Workflow 2 : brief matos du lundi ----------------------------------------------------
    wf2_nodes = [
        {
            "parameters": {"rule": {"interval": [{"field": "weeks", "triggerAtDay": [1], "triggerAtHour": 7}]}},
            "name": "Chaque lundi 7h", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [0, 0],
        },
        sheet_read("Lire Parc", "Parc", [220, 0]),
        sheet_read("Lire Dégâts", "Dégâts", [440, 0], execute_once=True),
        code_node("Calculer le brief", REGLES + "\n" + code("brief.js"), [660, 0]),
        with_cred({
            "parameters": {
                "documentId": {"__rl": True, "mode": "url", "value": SHEET_URL},
                "sheetName": {"__rl": True, "mode": "name", "value": "Brief"},
                "operation": "append",
                "columns": {"mappingMode": "autoMapInputData", "value": {}},
                "options": {"handlingExtraData": "ignoreIt", "cellFormat": "RAW"},
            },
            "name": "Écrire le brief", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.5, "position": [880, 0],
        }, "googleSheetsOAuth2Api"),
    ]
    wf2_conn = link("Chaque lundi 7h", "Lire Parc", "Lire Dégâts", "Calculer le brief", "Écrire le brief")

    # --- Workflow 3 : L'Accueil, demande de réservation ------------------------------------------
    # Le formulaire simule un DM Instagram / un email (canaux pas encore branchés).
    wf3_nodes = [
        {
            "parameters": {
                "formTitle": "L'Accueil — simuler un message de vacancier",
                "formDescription": "Ce que le vacancier écrirait sur Instagram ou par email, dans n'importe quelle langue.",
                "formFields": {"values": [
                    {"fieldLabel": "Canal", "fieldType": "dropdown", "requiredField": True,
                     "fieldOptions": {"values": [{"option": "Instagram"}, {"option": "Email"}]}},
                    {"fieldLabel": "Expéditeur", "requiredField": True, "placeholder": "@pseudo ou adresse email"},
                    {"fieldLabel": "Message", "fieldType": "textarea", "requiredField": True},
                ]},
                "options": {},
            },
            "name": "Message reçu", "type": "n8n-nodes-base.formTrigger", "typeVersion": 2.2, "position": [0, 0],
            "webhookId": "accueil-demande",
        },
        sheet_read("Lire Parc", "Parc", [220, 0]),
        sheet_read("Lire Dégâts", "Dégâts", [440, 0], execute_once=True),
        sheet_read("Lire Réservations", "Réservations", [660, 0], execute_once=True),
        sheet_read("Lire Vent", "Vent", [880, 0], execute_once=True),
        code_node("Préparer la lecture IA", ACC + "\n" + code("accueil_lecture.js"), [1100, 0]),
        claude("Claude lit le message", [1320, 0]),
        code_node("Vérifier créneau, matos, vent", REGLES + "\n" + ACC + "\n" + code("accueil_verifier.js"), [1540, 0]),
        claude("Claude rédige la réponse", [1760, 0]),
        code_node("Construire la ligne Demandes", code("accueil_ligne_demande.js"), [1980, 0]),
        sheet_write("Ajouter aux Demandes", "Demandes", [2200, 0]),
    ]
    wf3_conn = link("Message reçu", "Lire Parc", "Lire Dégâts", "Lire Réservations", "Lire Vent", "Préparer la lecture IA",
                    "Claude lit le message", "Vérifier créneau, matos, vent", "Claude rédige la réponse",
                    "Construire la ligne Demandes", "Ajouter aux Demandes")

    # --- Workflow 4 : L'Accueil, après le cours (chaque soir 18h) --------------------------------
    flat = lambda key: f"return $input.all().flatMap(i => [].concat(i.json.{key}).map(x => ({{ json: x }})));"
    wf4_nodes = [
        {
            "parameters": {"rule": {"interval": [{"field": "days", "triggerAtHour": 18}]}},
            "name": "Chaque soir 18h", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [0, 0],
        },
        sheet_read("Lire Réservations", "Réservations", [220, 0]),
        code_node("Cours à clôturer", ACC + "\n" + code("accueil_apres.js"), [440, 0]),
        code_node("Lignes Utilisations", flat("_utils"), [660, -160]),
        sheet_write("Ajouter aux Utilisations", "Utilisations", [880, -160]),
        code_node("Lignes Messages", flat("_msg"), [660, 0]),
        sheet_write("Ajouter aux Messages", "Messages", [880, 0]),
        code_node("Statut Terminé", "return $input.all().map(i => ({ json: { resa: i.json.resa, statut: i.json.statut, code: i.json.code } }));", [660, 160]),
        sheet_write("Mettre à jour Réservations", "Réservations", [880, 160], operation="update", match="resa"),
    ]
    wf4_conn = link("Chaque soir 18h", "Lire Réservations", "Cours à clôturer")
    wf4_conn["Cours à clôturer"] = {"main": [[{"node": n, "type": "main", "index": 0} for n in ("Lignes Utilisations", "Lignes Messages", "Statut Terminé")]]}
    wf4_conn.update(link("Lignes Utilisations", "Ajouter aux Utilisations"))
    wf4_conn.update(link("Lignes Messages", "Ajouter aux Messages"))
    wf4_conn.update(link("Statut Terminé", "Mettre à jour Réservations"))

    return wf1_nodes, wf1_conn, wf2_nodes, wf2_conn, wf3_nodes, wf3_conn, wf4_nodes, wf4_conn


SETTINGS = {"executionOrder": "v1", "timezone": "America/Guadeloupe"}
for local in ([False, True] if CREDS else [False]):
    USE_CREDS = local
    w1n, w1c, w2n, w2c, w3n, w3c, w4n, w4c = build()
    for fname, title, nodes, conn in (
        ("greeur-signalement-degat", "Gréeur — Signalement d'un dégât", w1n, w1c),
        ("greeur-brief-hebdo", "Gréeur — Brief matos du lundi", w2n, w2c),
        ("accueil-demande-reservation", "Accueil — Demande de réservation", w3n, w3c),
        ("accueil-apres-le-cours", "Accueil — Après le cours", w4n, w4c),
    ):
        wf = {"name": title, "nodes": nodes, "connections": conn, "settings": SETTINGS, "pinData": {}}
        out = N8N / (fname + (".local.json" if local else ".json"))
        out.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
print("OK : workflows n8n écrits dans", N8N.relative_to(ROOT))
