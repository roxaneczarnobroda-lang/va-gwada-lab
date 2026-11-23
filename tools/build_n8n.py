"""Assemble les workflows n8n importables du Gréeur à partir des fichiers de code.

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

SHEET_URL = "https://docs.google.com/spreadsheets/d/1s32iebX2wKko-Ax9UkXIcGONCsv6nh8iqgGmIet5xU8/edit"
EMAIL = "roxane.czarnobroda@gmail.com"

# Credentials propres à chaque instance n8n : dans n8n/credentials.local.json (ignoré par git).
# Format : {"anthropicApi": {"id": "...", "name": "..."}, "gmailOAuth2": {...}, "googleSheetsOAuth2Api": {...}}
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


def gmail(name, subject, body, pos):
    return with_cred({
        "parameters": {
            "sendTo": EMAIL, "subject": subject, "emailType": "text", "message": body,
            "options": {"appendAttribution": False},
        },
        "name": name, "type": "n8n-nodes-base.gmail", "typeVersion": 2.1, "position": pos,
    }, "gmailOAuth2")


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
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
                    "conditions": [{
                        "id": "envoyer", "leftValue": "={{ $('Construire la ligne Dégâts').item.json._envoyer }}",
                        "rightValue": "", "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                    }],
                    "combinator": "and",
                },
                "options": {},
            },
            "name": "Alerte nécessaire ?", "type": "n8n-nodes-base.if", "typeVersion": 2, "position": [1540, 0],
        },
        gmail("Envoyer l'alerte", "={{ $('Construire la ligne Dégâts').item.json._sujet }}",
              "={{ $('Construire la ligne Dégâts').item.json._alerte }}", [1760, -80]),
    ]
    wf1_conn = link("Formulaire dégât", "Lire Parc", "Lire Dégâts", "Préparer la demande IA",
                    "Claude analyse le message", "Construire la ligne Dégâts", "Ajouter au carnet", "Alerte nécessaire ?")
    wf1_conn["Alerte nécessaire ?"] = {"main": [[{"node": "Envoyer l'alerte", "type": "main", "index": 0}], []]}

    # --- Workflow 2 : brief matos du lundi ----------------------------------------------------
    wf2_nodes = [
        {
            "parameters": {"rule": {"interval": [{"field": "weeks", "triggerAtDay": [1], "triggerAtHour": 7}]}},
            "name": "Chaque lundi 7h", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [0, 0],
        },
        sheet_read("Lire Parc", "Parc", [220, 0]),
        sheet_read("Lire Dégâts", "Dégâts", [440, 0], execute_once=True),
        code_node("Calculer le brief", REGLES + "\n" + code("brief.js"), [660, 0]),
        gmail("Envoyer le brief", "={{ $json.sujet }}", "={{ $json.brief }}", [880, 0]),
    ]
    wf2_conn = link("Chaque lundi 7h", "Lire Parc", "Lire Dégâts", "Calculer le brief", "Envoyer le brief")

    return wf1_nodes, wf1_conn, wf2_nodes, wf2_conn


SETTINGS = {"executionOrder": "v1", "timezone": "America/Guadeloupe"}
for local in ([False, True] if CREDS else [False]):
    USE_CREDS = local
    w1n, w1c, w2n, w2c = build()
    for fname, title, nodes, conn in (
        ("greeur-signalement-degat", "Gréeur — Signalement d'un dégât", w1n, w1c),
        ("greeur-brief-hebdo", "Gréeur — Brief matos du lundi", w2n, w2c),
    ):
        wf = {"name": title, "nodes": nodes, "connections": conn, "settings": SETTINGS, "pinData": {}}
        out = N8N / (fname + (".local.json" if local else ".json"))
        out.write_text(json.dumps(wf, ensure_ascii=False, indent=2), encoding="utf-8")
print("OK : workflows n8n écrits dans", N8N.relative_to(ROOT))
