"""QA gates VA Gwada : vérifie qu'un client respecte ce qu'on lui promet, à partir de SES exigences.

Usage (depuis la racine du repo, lancé aussi automatiquement à la fin de tools/build.py) :
    python3 tools/qa.py                 # client par défaut : maximum-kite
    python3 tools/qa.py maximum-kite

Lit le contrat de données, le manifeste de gouvernance, les workflows et pages GÉNÉRÉS, le code et les scénarios
de test du client. Écrit clients/<client>/gouvernance/rapport-qa.md (le rapport à montrer au client).
Code de sortie 1 si une gate est bloquante (le build et la CI échouent).

Niveau « demo » : ce qui ne compte qu'en prod (sorties de démo, contrôles manuels non signés…) est un avertissement.
Niveau « prod » : tout est bloquant.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gouvernance import GARDE_JS, ROOT, Client, empreinte  # noqa: E402

CLIENT = sys.argv[1] if len(sys.argv) > 1 else "maximum-kite"
GOV = Client(CLIENT)
C = GOV.dir
M = GOV.manifeste
PROD = M["niveau"] == "prod"
TYPES = {"texte", "entier", "nombre", "date", "horodatage", "oui_non"}
SHEETS = {k: v for k, v in json.loads((C / "sheets.json").read_text(encoding="utf-8")).items() if not k.startswith("_")}
J_BASE, J_TAB = GOV.journal["base"], GOV.journal["onglet"]

GATES = {
    "CONTRAT": "Contrat de données complet ; données de démo et Excel générés conformes (même validateur que n8n)",
    "PERSO": "Chaque donnée personnelle a une finalité et une durée de conservation ; aucune dans le Journal",
    "ECRITURE-PROPRIETAIRE": "Chaque onglet n'est écrit que par l'agent déclaré, dans les fichiers déclarés",
    "GARDE-ECRITURE": "Chaque écriture passe par un node Garde à jour du contrat",
    "JOURNAL": "Chaque écriture est tracée (version, validation) dans l'onglet Journal",
    "JOURNAL-ERREURS": "Un workflow trace les erreurs d'exécution dans le Journal",
    "IA-ADAPTATEUR": "Modèle et endpoint IA viennent du manifeste, jamais du code",
    "IA-GARDE": "Toute réponse IA est relue par du code (lecture prudente, repli) avant usage",
    "IA-ACTION": "Aucune action vers l'extérieur en aval d'une IA sans validation humaine",
    "SORTIES": "Les données ne partent que vers les domaines déclarés",
    "SECRETS": "Aucun secret ni credential dans le repo",
    "PURGE": "Les données personnelles sont purgées automatiquement à échéance",
    "SCENARIOS": "Scénarios de test issus des exigences du client : tous passent",
}
RES = {g: {"bloquant": [], "avertissement": [], "info": []} for g in GATES}
SCEN = {}  # exigence → [(nom, ok, détail)]


def bloque(g, msg, prod_seulement=False):
    RES[g]["avertissement" if (prod_seulement and not PROD) else "bloquant"].append(msg)


def avert(g, msg):
    RES[g]["bloquant" if PROD else "avertissement"].append(msg)


def info(g, msg):
    RES[g]["info"].append(msg)


def statut(g):
    r = RES[g]
    return "bloquant" if r["bloquant"] else "avertissement" if r["avertissement"] else "ok"


def node_js(code, prelude=""):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(prelude + GARDE_JS + "\n" + code)
    p = subprocess.run(["node", f.name], capture_output=True, text=True)
    Path(f.name).unlink()
    if p.returncode:
        raise RuntimeError(p.stderr.strip()[-800:])
    return json.loads(p.stdout)


# ============================================================ chargement des livrables générés
WFS = {}
for p in sorted(C.glob("*/n8n/*.json")):
    if p.name.endswith(".local.json"):
        continue
    WFS[p] = json.loads(p.read_text(encoding="utf-8"))
PAGES = [p for p in sorted(C.glob("*/demonstrateur/*.html")) if not p.name.endswith(".src.html")]
CODE = sorted(C.glob("*/n8n/code/*.js"))
agent_of = lambda p: p.parent.parent.name
rel = lambda p: str(Path(p).relative_to(ROOT))


def graphe(wf):
    by = {n["name"]: n for n in wf["nodes"]}
    succ = {n: [] for n in by}
    pred = {n: [] for n in by}
    for a, d in wf["connections"].items():
        for sortie in d.get("main", []):
            for l in sortie or []:
                succ[a].append(l["node"])
                pred[l["node"]].append(a)
    return by, succ, pred


def ecritures(wf):
    for n in wf["nodes"]:
        if n["type"] == "n8n-nodes-base.googleSheets" and n["parameters"].get("operation") in ("append", "update", "appendOrUpdate", "delete"):
            yield n


def cible(n):
    url = n["parameters"]["documentId"]["value"]
    base = next((b for b, sid in SHEETS.items() if sid in url), None)
    return base, n["parameters"]["sheetName"]["value"]


def const_json(js, nom):
    m = re.search(rf"const {nom} = (.*?);\n", js)
    return json.loads(m.group(1)) if m else None


# ============================================================ CONTRAT
lignes_par_onglet = {}
for base, tab, o in GOV.tous_onglets():
    cols = o["colonnes"]
    if o.get("cle") not in cols:
        bloque("CONTRAT", f"{base}/{tab} : la clé « {o.get('cle')} » n'est pas une colonne")
    if not o.get("ecrit_par"):
        bloque("CONTRAT", f"{base}/{tab} : « ecrit_par » manquant (qui a le droit d'écrire ?)")
    for c, s in cols.items():
        if s.get("type") not in TYPES:
            bloque("CONTRAT", f"{base}/{tab}.{c} : type « {s.get('type')} » inconnu")
        if s.get("perso") not in ("non", "perso", "sensible"):
            bloque("CONTRAT", f"{base}/{tab}.{c} : classification « perso » manquante")
        if "obligatoire" not in s:
            bloque("CONTRAT", f"{base}/{tab}.{c} : « obligatoire » non précisé")
    xlsx = C / "data" / "generes" / f"{base}.xlsx"
    if not xlsx.exists():
        bloque("CONTRAT", f"{rel(xlsx)} absent : lancer tools/build.py")
        continue
    wb = load_workbook(xlsx, read_only=True)
    if tab not in wb.sheetnames:
        bloque("CONTRAT", f"{base}.xlsx : onglet « {tab} » absent")
        continue
    rows = list(wb[tab].iter_rows(values_only=True))
    entete = [h for h in rows[0] if h is not None] if rows else []
    if entete != list(cols):
        bloque("CONTRAT", f"{base}.xlsx/{tab} : colonnes {entete} ≠ contrat {list(cols)}")
    lignes = [{h: ("" if v is None else v) for h, v in zip(entete, r)} for r in rows[1:] if any(v is not None for v in r)]
    lignes_par_onglet[(base, tab)] = lignes

# Validation des lignes de démo par le MÊME garde.js que dans n8n
lots = [{"base": b, "tab": t, "onglet": GOV.onglet(b, t), "items": [{"json": l} for l in ls]} for (b, t), ls in lignes_par_onglet.items()]
res = node_js("const LOTS = " + json.dumps(lots, ensure_ascii=False, default=str) + r""";
const out = LOTS.map(L => ({ base: L.base, tab: L.tab, n: L.items.length,
  erreurs: L.items.flatMap((it, i) => verifierLigne(L.onglet, it.json, 'ajout').erreurs.map(e => `ligne ${i + 2} — ${e}`)) }));
console.log(JSON.stringify(out));""")
for r in res:
    for e in r["erreurs"][:8]:
        bloque("CONTRAT", f"{r['base']}.xlsx/{r['tab']} {e}")
    if r["n"]:
        info("CONTRAT", f"{r['base']}/{r['tab']} : {r['n']} lignes de démo validées")

# Intégrité référentielle (comme des clés étrangères)
for base, tab, o in GOV.tous_onglets():
    for c, s in o["colonnes"].items():
        if "ref" not in s:
            continue
        rb, rt, rc = s["ref"].split(".")
        ok = {str(l.get(rc)) for l in lignes_par_onglet.get((rb, rt), [])} | set(s.get("valeurs_extra", []))
        for l in lignes_par_onglet.get((base, tab), []):
            if l.get(c) not in ("", None) and str(l[c]) not in ok:
                bloque("CONTRAT", f"{base}/{tab}.{c} = « {l[c]} » : absent de {rb}/{rt}.{rc}")

# ============================================================ PERSO
journalises = set()
for base, tab, o in GOV.tous_onglets():
    for c, s in o["colonnes"].items():
        if s.get("perso") == "sensible":
            bloque("PERSO", f"{base}/{tab}.{c} : donnée sensible (RGPD art. 9) — interdite sans exigence client explicite")
        if s.get("perso") in ("perso", "sensible"):
            if not s.get("finalite"):
                bloque("PERSO", f"{base}/{tab}.{c} : donnée perso sans finalité")
            if not s.get("conservation_jours"):
                bloque("PERSO", f"{base}/{tab}.{c} : donnée perso sans durée de conservation")
            if s.get("doublon_de"):
                avert("PERSO", f"{base}/{tab}.{c} : copie de {s['doublon_de']} — minimisation : le lien par clé suffit, colonne à supprimer")
for c, s in GOV.onglet(J_BASE, J_TAB)["colonnes"].items():
    if s.get("perso") != "non":
        bloque("PERSO", f"Journal.{c} : le Journal ne doit contenir aucune donnée personnelle")
nb_perso = sum(1 for _, _, o in GOV.tous_onglets() for s in o["colonnes"].values() if s.get("perso") != "non")
info("PERSO", f"{nb_perso} colonnes de données personnelles déclarées, chacune avec finalité et durée")
info("PERSO", f"Des messages de vacanciers sont envoyés au fournisseur IA ({GOV.ia['fournisseur']}) : couvert par le contrat de sous-traitance (EX-09)")

# ============================================================ Workflows : écritures, garde, journal, IA
ia_hosts = {"api.anthropic.com", "api.openai.com", "api.mistral.ai", "generativelanguage.googleapis.com"}
ia_hosts.add(urlparse(GOV.ia["endpoint"]).hostname)
risque = set(M["actions_a_risque"]["types"])
CONTRAT_V = empreinte(GOV.contrat)
erreurs_wf = False

for p, wf in WFS.items():
    agent = agent_of(p)
    by, succ, pred = graphe(wf)
    nom = f"{rel(p)}"
    if agent == "gouvernance" and any(n["type"] == "n8n-nodes-base.errorTrigger" for n in wf["nodes"]):
        erreurs_wf = any(cible(w) == (J_BASE, J_TAB) for w in ecritures(wf))
    for w in ecritures(wf):
        base, tab = cible(w)
        if base is None:
            bloque("ECRITURE-PROPRIETAIRE", f"{nom} « {w['name']} » : écrit dans un fichier absent de sheets.json")
            continue
        if tab not in GOV.contrat.get(base, {}):
            bloque("ECRITURE-PROPRIETAIRE", f"{nom} « {w['name']} » : onglet {base}/{tab} absent du contrat")
            continue
        o = GOV.onglet(base, tab)
        est_journal = (base, tab) == (J_BASE, J_TAB)
        est_purge = agent == "gouvernance" and w["parameters"]["operation"] == "update"
        if not (agent in o["ecrit_par"] or est_journal or est_purge):
            bloque("ECRITURE-PROPRIETAIRE", f"{nom} « {w['name']} » : l'agent « {agent} » n'a pas le droit d'écrire {tab} (réservé à {', '.join(o['ecrit_par'])})")
        if w["parameters"].get("columns", {}).get("mappingMode") != "autoMapInputData":
            avert("GARDE-ECRITURE", f"{nom} « {w['name']} » : mapping manuel des colonnes — le contrat ne s'applique qu'en auto-mapping")
        # La garde : seul prédécesseur, code qui appelle garderLot avec le contrat À JOUR de cet onglet
        ps = pred[w["name"]]
        g = by.get(ps[0]) if len(ps) == 1 else None
        js = g["parameters"].get("jsCode", "") if g and g["type"] == "n8n-nodes-base.code" else ""
        if "garderLot(" not in js:
            bloque("GARDE-ECRITURE", f"{nom} « {w['name']} » : pas de node Garde juste avant l'écriture")
        elif const_json(js, "GOUV_ONGLET") != o:
            bloque("GARDE-ECRITURE", f"{nom} « {w['name']} » : la Garde n'est pas à jour du contrat — relancer tools/build.py")
        if est_journal:
            journalises.add(nom)
            continue
        # Le journal : un node Journal qui écrit dans l'onglet Journal
        js_j = [by[s] for s in succ[w["name"]] if "garderLot(" in by[s]["parameters"].get("jsCode", "")]
        trace = [t for j in js_j for t in succ[j["name"]] if by[t]["type"] == "n8n-nodes-base.googleSheets" and cible(by[t]) == (J_BASE, J_TAB)]
        if not trace:
            bloque("JOURNAL", f"{nom} « {w['name']} » : écriture non tracée dans le Journal")
            continue
        E = const_json(js_j[0]["parameters"]["jsCode"], "E")
        if not E or not E.get("validation"):
            bloque("JOURNAL", f"{nom} « {w['name']} » : mode de validation non déclaré")
        elif E.get("contrat") != CONTRAT_V:
            bloque("JOURNAL", f"{nom} « {w['name']} » : Journal construit sur un ancien contrat — relancer tools/build.py")
        else:
            info("JOURNAL", f"{tab} ← {agent} · validation : {E['validation']}")
        if GOV.onglet(base, tab)["colonnes"][o["cle"]]["perso"] != "non":
            bloque("PERSO", f"{tab} : sa clé « {o['cle']} » est une donnée perso, or elle est recopiée dans le Journal")

    for n in wf["nodes"]:
        prm = n.get("parameters", {})
        if "credentials" in n:
            bloque("SECRETS", f"{nom} « {n['name']} » : credential référencé dans un workflow versionné")
        if n["type"] == "n8n-nodes-base.httpRequest":
            host = urlparse(str(prm.get("url", ""))).hostname
            if host in ia_hosts:
                if prm.get("url") != GOV.ia["endpoint"]:
                    bloque("IA-ADAPTATEUR", f"{nom} « {n['name']} » : endpoint IA {prm.get('url')} ≠ manifeste")
                # IA-GARDE : tout successeur direct relit la réponse avec jsonIA/texteIA
                for s in succ[n["name"]]:
                    sj = by[s]["parameters"].get("jsCode", "")
                    if not re.search(r"\b(jsonIA|texteIA)\(\$input", sj):
                        bloque("IA-GARDE", f"{nom} : la réponse de « {n['name']} » est utilisée par « {s} » sans jsonIA/texteIA")
                # IA-ACTION : rien d'« à risque » en aval
                vus, pile = set(), list(succ[n["name"]])
                while pile:
                    x = pile.pop()
                    if x in vus:
                        continue
                    vus.add(x)
                    if by[x]["type"] in risque:
                        bloque("IA-ACTION", f"{nom} : « {x} » ({by[x]['type']}) en aval de l'IA « {n['name']} » sans validation humaine")
                    pile += succ[x]
        if n["type"] in risque:
            info("IA-ACTION", f"{nom} : action vers l'extérieur « {n['name']} »")
        js = prm.get("jsCode", "")
        if "corpsIA(" in js.replace(GARDE_JS, "") and const_json(js, "GOUV_IA") != {k: GOV.ia[k] for k in ("modele", "max_tokens")}:
            bloque("IA-ADAPTATEUR", f"{nom} « {n['name']} » : config IA différente du manifeste — relancer tools/build.py")

nb_ia = sum(1 for wf in WFS.values() for n in wf["nodes"] if n["type"] == "n8n-nodes-base.httpRequest"
            and urlparse(str(n["parameters"].get("url", ""))).hostname in ia_hosts)
info("IA-GARDE", f"{nb_ia} appels IA, tous suivis d'une relecture par le code")
info("IA-ADAPTATEUR", f"Modèle : {GOV.ia['modele']} · {GOV.ia['fournisseur']}")
if not erreurs_wf:
    bloque("JOURNAL-ERREURS", "Pas de workflow « Journal des erreurs » qui écrit dans le Journal")
if not journalises:
    bloque("JOURNAL", "Aucune écriture dans l'onglet Journal")

# Code source : aucun modèle ni endpoint en dur
MOTIFS_IA = re.compile(r"api\.anthropic\.com|api\.openai\.com|api\.mistral\.ai|generativelanguage\.googleapis|['\"](claude-[a-z0-9.-]+|gpt-[0-9a-z.-]+|mistral-[a-z0-9-]+)['\"]")
for p in CODE + sorted(C.glob("*/demonstrateur/*.src.html")):
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        m = MOTIFS_IA.search(line)
        if m:
            bloque("IA-ADAPTATEUR", f"{rel(p)}:{i} : « {m.group(0)} » en dur — passer par corpsIA / le manifeste")

# ============================================================ SORTIES
autorise_now = GOV.sorties_autorisees()
autorise_prod = GOV.sorties_autorisees("prod")
URL = re.compile(r"https?://[^\s\"'`<>()\\]+")


def ok_host(h, autorise):
    return next((d for d in autorise if h == d or h.endswith("." + d)), None)


vus = {}
for p in list(WFS) + PAGES:
    txt = p.read_text(encoding="utf-8")
    hosts = {urlparse(u).hostname for u in URL.findall(txt)} - {None}
    if "window.claude" in txt:
        hosts.add("claude.ai")
    for h in hosts:
        vus.setdefault(h, set()).add(rel(p))
for h, fichiers in sorted(vus.items()):
    if h.endswith(".gwada.test") or h in ("localhost",):
        continue
    d = ok_host(h, autorise_now)
    if not d:
        bloque("SORTIES", f"{h} : domaine non déclaré dans le manifeste (vu dans {', '.join(sorted(fichiers))})")
    elif not ok_host(h, autorise_prod):
        avert("SORTIES", f"{h} : autorisé en démo seulement — {autorise_now[d][0]}")
    else:
        info("SORTIES", f"{h} : {autorise_now[d][0]}")
if M["hebergement"] == "souverain":
    info("SORTIES", "Hébergement souverain : seuls les domaines de l'environnement du client sont autorisés")

# ============================================================ SECRETS
fichiers = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout.split()
SECRET = re.compile(r"sk-ant-[A-Za-z0-9_-]{16,}|sk-[A-Za-z0-9]{32,}|AIza[0-9A-Za-z_-]{35}|ya29\.[0-9A-Za-z_-]{20,}|ghp_[A-Za-z0-9]{36}"
                    r"|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|\"(client_secret|refresh_token|access_token|password|apiKey)\"\s*:\s*\"[^\"]{6,}\"")
for f in fichiers:
    p = ROOT / f
    if p.suffix in (".xlsx", ".png", ".jpg", ".pdf") or not p.is_file() or ".local." in p.name:
        continue
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        m = SECRET.search(line)
        if m:
            bloque("SECRETS", f"{f}:{i} : ressemble à un secret ({m.group(0)[:12]}…)")
gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
if "*.local.*" not in gi:
    bloque("SECRETS", ".gitignore ne protège pas les fichiers *.local.* (credentials)")
info("SECRETS", f"{len(fichiers)} fichiers du repo scannés")

# ============================================================ PURGE
purge = next((wf for p, wf in WFS.items() if p.name == "gouvernance-purge.json"), None)
purges = {cible(w)[1] for w in ecritures(purge)} if purge else set()
for base, tab, o in GOV.tous_onglets():
    perso = [c for c, s in o["colonnes"].items() if s.get("perso") != "non"]
    if not perso:
        continue
    if tab in purges:
        durees = ", ".join(f"{c} {o['colonnes'][c]['conservation_jours']} j" for c in perso)
        info("PURGE", f"{tab} : purge automatique ({durees})")
    else:
        pourquoi = "pas de clé unique" if not o.get("cle_unique") else "pas de date de référence"
        avert("PURGE", f"{tab} ({', '.join(perso)}) : purge automatique impossible ({pourquoi}) — purge manuelle à prévoir")

# ============================================================ SCENARIOS
prelude = ""
for x in M.get("scenarios", {}).get("prelude", []):
    if x.startswith("@"):
        var, ref = x[1:].split("=")
        src, chemin = ref.split(":")
        val = GOV.donnees[src]
        for k in chemin.split("."):
            val = val[k]
        prelude += f"const {var} = {json.dumps(val, ensure_ascii=False)};\n"
    else:
        prelude += (C / x).read_text(encoding="utf-8") + "\n"
prelude += "const DONNEES = " + json.dumps(GOV.donnees, ensure_ascii=False) + ";\n"
prelude += "const GOUV_IA_ATTENDU = " + json.dumps(GOV.ia, ensure_ascii=False) + ";\n"
prelude += "const CONTRAT = " + json.dumps(GOV.contrat, ensure_ascii=False) + ";\n"
# Le code EXACT des nodes générés, pour l'exécuter dans les scénarios (executer(workflow, node, {...})).
prelude += "const WORKFLOWS = " + json.dumps({wf["name"]: {n["name"]: n["parameters"]["jsCode"] for n in wf["nodes"] if n["type"] == "n8n-nodes-base.code"}
                                             for wf in WFS.values()}, ensure_ascii=False) + ";\n"
HARNAIS = r"""
const __R = [];
function test(exigence, nom, fn) { try { fn(); __R.push({exigence, nom, ok: true}); } catch (e) { __R.push({exigence, nom, ok: false, detail: String(e.message || e).slice(0, 300)}); } }
function vrai(c, msg) { if (!c) throw new Error(msg || 'attendu vrai'); }
// Exécute le code d'un node Code tel qu'il sera dans n8n. ctx = {input: [objets], refs: {"Nom du node": [objets]}}.
function executer(wf, noeud, ctx) {
  const code = (WORKFLOWS[wf] || {})[noeud];
  if (!code) throw new Error(`node « ${noeud} » introuvable dans « ${wf} »`);
  ctx = ctx || {};
  const items = x => (x || []).map(j => ({ json: j }));
  const $ = n => { const v = (ctx.refs || {})[n]; if (!v) throw new Error(`le scénario ne fournit pas « ${n} »`); const it = items(v); return { first: () => it[0], all: () => it }; };
  const inp = items(ctx.input); const $input = { first: () => inp[0], all: () => inp };
  const $now = { toFormat: () => '2026-01-01 12:00:00' };
  return new Function('$', '$input', '$now', '$execution', '$workflow', code)($, $input, $now, { id: 'scenario' }, { name: wf }).map(i => i.json);
}
function echoue(fn, motif, msg) { try { fn(); } catch (e) { if (motif && !motif.test(String(e.message))) throw new Error(`${msg || ''} erreur inattendue : ${e.message}`); return; } throw new Error(msg || 'une erreur était attendue'); }
function egal(a, b, msg) { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${msg || ''} attendu ${JSON.stringify(b)}, obtenu ${JSON.stringify(a)}`); }
"""
scen_files = sorted((C / "gouvernance" / "scenarios").glob("*.test.js"))
for f in scen_files:
    try:
        out = node_js(HARNAIS + f.read_text(encoding="utf-8") + "\nconsole.log(JSON.stringify(__R));", prelude)
    except RuntimeError as e:
        bloque("SCENARIOS", f"{rel(f)} : le fichier ne s'exécute pas — {e}")
        continue
    for r in out:
        SCEN.setdefault(r["exigence"], []).append((r["nom"], r["ok"], r.get("detail", "")))
        if not r["ok"]:
            bloque("SCENARIOS", f"{r['exigence']} — {r['nom']} : {r['detail']}")
nb = sum(len(v) for v in SCEN.values())
info("SCENARIOS", f"{nb} scénarios dans {len(scen_files)} fichier(s), {sum(ok for v in SCEN.values() for _, ok, _ in v)} réussis")

# ============================================================ EXIGENCES → verdict
VALID = json.loads((C / "gouvernance" / "validations.json").read_text(encoding="utf-8"))
ORDRE = {"ok": 0, "à faire": 1, "avertissement": 1, "bloquant": 2}
LIB = {"ok": "✅ respectée", "avertissement": "⚠️ avec réserves", "à faire": "🕓 contrôle manuel à faire", "bloquant": "❌ non respectée"}
exig = []
for e in M["exigences"]:
    etats, preuves = [], []
    for g in e.get("controles", []):
        if g not in GATES:
            etats.append("bloquant")
            preuves.append(f"contrôle inconnu {g}")
            continue
        st = statut(g)
        if g == "SCENARIOS":
            mine = SCEN.get(e["id"], [])
            st = "bloquant" if not mine or not all(ok for _, ok, _ in mine) else "ok"
            preuves.append(f"{sum(ok for _, ok, _ in mine)}/{len(mine)} scénarios" if mine else "aucun scénario écrit")
        else:
            preuves.append(g)
        etats.append(st)
    if e.get("manuel"):
        v = VALID.get(e["id"])
        if v and v.get("par") and v.get("date"):
            preuves.append(f"signé {v['par']} le {v['date']}")
            etats.append("ok")
        else:
            preuves.append("manuel : " + e["manuel"])
            etats.append("bloquant" if PROD else "à faire")
    pire = max(etats or ["à faire"], key=ORDRE.get)
    exig.append((e, pire, preuves))

bloquants = [g for g in GATES if statut(g) == "bloquant"] + [e["id"] for e, st, _ in exig if st == "bloquant"]
reserves = [g for g in GATES if statut(g) == "avertissement"]
verdict = "❌ QA bloquée" if bloquants else ("⚠️ QA passée avec réserves" if reserves or any(st != "ok" for _, st, _ in exig) else "✅ QA passée")

# ============================================================ rapport
versions = []
for p, wf in WFS.items():
    note = next((n for n in wf["nodes"] if n["type"] == "n8n-nodes-base.stickyNote"), None)
    v = re.search(r"Version \*\*(\w+)\*\*", note["parameters"]["content"]).group(1) if note else "?"
    versions.append(f"| {wf['name']} | `{v}` |")
ICONE = {"ok": "✅", "avertissement": "⚠️", "bloquant": "❌"}
L = [f"# Rapport QA — {M['client']}", "",
     "> Généré par `tools/qa.py` à chaque build. Ne pas modifier à la main.", "",
     f"**{verdict}** · niveau **{M['niveau']}** · hébergement **{M['hebergement']}** · contrat de données `{CONTRAT_V}`", "",
     "## Ce que nous vous garantissons", "",
     "| | Exigence | Comment c'est vérifié | Résultat |", "|---|---|---|---|"]
for e, st, preuves in exig:
    L.append(f"| {e['id']} | {e['besoin']} | {' · '.join(preuves)} | {LIB[st]} |")
L += ["", "## QA gates", "", "| Gate | Ce qui est vérifié | Résultat |", "|---|---|---|"]
for g, desc in GATES.items():
    r = RES[g]
    n = len(r["bloquant"]) + len(r["avertissement"])
    L.append(f"| {g} | {desc} | {ICONE[statut(g)]}{f' {n} constat(s)' if n else ''} |")
L += ["", "## Constats", ""]
for g in GATES:
    r = RES[g]
    if not any(r.values()):
        continue
    L.append(f"**{g}**")
    L += [f"- ❌ {x}" for x in r["bloquant"]] + [f"- ⚠️ {x}" for x in r["avertissement"]] + [f"- {x}" for x in r["info"]]
    L.append("")
if not PROD:
    a_faire = [x for g in GATES for x in RES[g]["avertissement"]] + [f"{e['id']} : {e.get('manuel')}" for e, st, _ in exig if st == "à faire"]
    L += ["## Avant la mise en production", "", "Passer `niveau` à `prod` dans `gouvernance/gouvernance.json` rend tout ceci bloquant :", ""]
    L += [f"- [ ] {x}" for x in a_faire] + [""]
L += ["## Versions livrées", "", "| Workflow | Version |", "|---|---|"] + versions + [""]
(C / "gouvernance" / "rapport-qa.md").write_text("\n".join(L), encoding="utf-8")

# ============================================================ console
print(f"\nQA {CLIENT} ({M['niveau']}) : {verdict}")
for g in GATES:
    r = RES[g]
    print(f"  {ICONE[statut(g)]} {g:<22} {len(r['bloquant'])} bloquant(s), {len(r['avertissement'])} avertissement(s)")
    for x in r["bloquant"]:
        print(f"      ❌ {x}")
for e, st, _ in exig:
    if st == "bloquant":
        print(f"  ❌ {e['id']} {e['besoin']}")
print(f"Rapport : {rel(C / 'gouvernance' / 'rapport-qa.md')}")
sys.exit(1 if bloquants else 0)
