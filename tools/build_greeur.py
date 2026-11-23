"""Construit les livrables du Gréeur à partir de la source unique de données.

Usage (depuis la racine du repo) :
    python3 tools/build_greeur.py

Produit :
- clients/maximum-kite/demonstrateur/greeur.html  (app web, données intégrées)
- clients/maximum-kite/data/parc-matos-demo.xlsx  (fichier Excel 3 onglets)
- clients/maximum-kite/data/parc.csv, degats.csv  (pour Google Sheets / n8n)
"""
import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
MK = ROOT / "clients" / "maximum-kite"
data = json.loads((MK / "data" / "parc-matos-demo.json").read_text(encoding="utf-8"))

# 1. App web : on remplace le marqueur par les données (en échappant "<" pour la balise script)
src = (MK / "demonstrateur" / "greeur.src.html").read_text(encoding="utf-8")
payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
assert "/*__DATA__*/null" in src
(MK / "demonstrateur" / "greeur.html").write_text(src.replace("/*__DATA__*/null", payload), encoding="utf-8")

# 2. Excel
H_P = ["ID", "Catégorie", "Désignation", "Date d'achat", "Prix d'achat (€)"]
H_D = ["Date", "ID matériel", "Type", "Description", "Gravité", "Coût (€)", "Statut", "Immobilisé"]
head = Font(bold=True, color="FFFFFF")
fill = PatternFill("solid", fgColor="0C4A55")

wb = Workbook()
ws = wb.active
ws.title = "Parc"
ws.append(H_P)
for it in data["parc"]:
    ws.append([it["id"], it["categorie"], it["designation"], it["date_achat"], it["prix_achat"]])
for c, w in zip("ABCDE", (10, 18, 26, 14, 16)):
    ws.column_dimensions[c].width = w

wd = wb.create_sheet("Dégâts")
wd.append(H_D)
for d in data["degats"]:
    wd.append([d["date"], d["id"], d["type"], d["description"], d["gravite"], d["cout"], d["statut"], "oui" if d["immobilise"] else "non"])
for c, w in zip("ABCDEFGH", (12, 12, 26, 44, 10, 10, 18, 11)):
    wd.column_dimensions[c].width = w
# Listes déroulantes pour que la saisie à la main reste propre
for col, values in (("C", data["types_degat"]), ("E", ["Légère", "Moyenne", "Grave"]),
                    ("G", ["À réparer", "Chez le réparateur", "Réparé"]), ("H", ["oui", "non"])):
    dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=True)
    wd.add_data_validation(dv)
    dv.add(f"{col}2:{col}500")

wh = wb.create_sheet("Hypothèses")
wh.append(["Paramètre", "Valeur", "Commentaire"])
for k, v in data["hypotheses"]["duree_vie_ans"].items():
    wh.append([f"Durée de vie (ans) · {k}", v, "Hypothèse à valider avec l'école"])
labels = {
    "seuil_reparations_pct": "À remplacer si réparations ≥ x % du prix d'achat",
    "surveiller_age_pct": "À surveiller si âge ≥ x % de la durée de vie",
    "surveiller_reparations_pct": "À surveiller si réparations ≥ x % du prix d'achat",
    "surveiller_nb_degats_6_mois": "À surveiller si ≥ x dégâts sur 6 mois",
    "revente_pct": "Revente estimée en % du prix d'achat",
}
for k, lab in labels.items():
    wh.append([k, data["hypotheses"][k], lab])
for c, w in zip("ABC", (38, 10, 52)):
    wh.column_dimensions[c].width = w

wl = wb.create_sheet("Lisez-moi")
for line in [
    "Fichier du Gréeur — DONNÉES FICTIVES (démo VA Gwada pour Maximum Kite)",
    "",
    "Parc : une ligne par pièce de matos. L'ID doit être unique (ex. K-01 pour une aile kite).",
    "Dégâts : une ligne par dégât. 'ID matériel' doit correspondre à un ID du Parc.",
    "Coût : laisser vide tant que la réparation n'est pas payée.",
    "Immobilisé : 'oui' si la pièce ne doit pas sortir avant réparation.",
    "Hypothèses : les règles de calcul utilisées par l'agent. Modifiables.",
]:
    wl.append([line])
wl.column_dimensions["A"].width = 90

for sheet in (ws, wd, wh):
    for cell in sheet[1]:
        cell.font, cell.fill = head, fill
    sheet.freeze_panes = "A2"
wb.move_sheet("Lisez-moi", offset=-3)
wb.save(MK / "data" / "parc-matos-demo.xlsx")

# 3. CSV
with open(MK / "data" / "parc.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "categorie", "designation", "date_achat", "prix_achat"])
    for it in data["parc"]:
        w.writerow([it["id"], it["categorie"], it["designation"], it["date_achat"], it["prix_achat"]])
with open(MK / "data" / "degats.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "id", "type", "description", "gravite", "cout", "statut", "immobilise"])
    for d in data["degats"]:
        w.writerow([d["date"], d["id"], d["type"], d["description"], d["gravite"], d["cout"] if d["cout"] is not None else "", d["statut"], "oui" if d["immobilise"] else "non"])

print("OK : greeur.html, parc-matos-demo.xlsx, parc.csv, degats.csv")
