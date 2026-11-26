// ===================== garde.js — socle de gouvernance VA Gwada =====================
// Injecté par tools/build.py dans les nodes Code qui en ont besoin. Ne pas recopier à la main.
// Trois rôles :
//   1. Adaptateur IA : le modèle et l'endpoint viennent du manifeste du client (GOUV_IA), jamais du code.
//   2. Lecture prudente des réponses IA : texte seul, JSON vérifié, null si illisible (le code appelant prévoit le repli).
//   3. Contrat de données : chaque ligne est vérifiée AVANT d'être écrite (types, listes, formats, obligatoires),
//      et réduite aux seules colonnes du contrat (minimisation).

/* global GOUV_IA */

function corpsIA(prompt, opts) {
  opts = opts || {};
  if (typeof GOUV_IA === 'undefined') throw new Error('Garde IA : GOUV_IA absent — ce node doit être construit par tools/build.py');
  return {
    model: GOUV_IA.modele,
    max_tokens: opts.max_tokens || GOUV_IA.max_tokens,
    thinking: { type: 'disabled' },
    messages: [{ role: 'user', content: String(prompt) }],
  };
}

// Le modèle peut renvoyer un bloc « thinking » avant le texte : on ne garde que les blocs texte.
function texteIA(resp) {
  const blocs = (resp && Array.isArray(resp.content)) ? resp.content : [];
  return blocs.filter(b => b && b.type === 'text').map(b => String(b.text || '')).join('').trim();
}

// Renvoie l'objet JSON produit par l'IA, ou null. Ne lève jamais d'erreur : l'appelant décide du repli.
function jsonIA(resp) {
  const t = texteIA(resp);
  const a = t.indexOf('{'), b = t.lastIndexOf('}');
  if (a < 0 || b <= a) return null;
  try {
    const o = JSON.parse(t.slice(a, b + 1));
    return (o && typeof o === 'object' && !Array.isArray(o)) ? o : null;
  } catch (e) { return null; }
}

const GARDE_FORMATS = {
  date: /^\d{4}-\d{2}-\d{2}$/,
  horodatage: /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/,
};

function gardeValeur(nom, spec, v) {
  const vide = v === undefined || v === null || v === '';
  if (vide) return spec.obligatoire ? [`${nom} : obligatoire`] : [];
  const e = [];
  const s = String(v);
  switch (spec.type) {
    case 'entier': if (!Number.isInteger(Number(v)) || s.trim() === '') e.push(`${nom} : entier attendu (« ${s.slice(0, 30)} »)`); break;
    case 'nombre': if (!isFinite(Number(v)) || s.trim() === '') e.push(`${nom} : nombre attendu (« ${s.slice(0, 30)} »)`); break;
    case 'date': case 'horodatage': if (!GARDE_FORMATS[spec.type].test(s)) e.push(`${nom} : ${spec.type} attendu (« ${s.slice(0, 30)} »)`); break;
    case 'oui_non': if (s !== 'oui' && s !== 'non') e.push(`${nom} : « oui » ou « non » attendu`); break;
    case 'texte': if (typeof v === 'object') e.push(`${nom} : texte attendu`); break;
    default: e.push(`${nom} : type inconnu dans le contrat (${spec.type})`);
  }
  if (e.length) return e;
  if ((spec.type === 'entier' || spec.type === 'nombre')) {
    if (spec.min !== undefined && Number(v) < spec.min) e.push(`${nom} : ${v} < minimum ${spec.min}`);
    if (spec.max !== undefined && Number(v) > spec.max) e.push(`${nom} : ${v} > maximum ${spec.max}`);
  } else if (spec.max !== undefined && s.length > spec.max) e.push(`${nom} : ${s.length} caractères > ${spec.max}`);
  if (spec.valeurs && !spec.valeurs.includes(s)) e.push(`${nom} : « ${s.slice(0, 40)} » hors liste autorisée`);
  if (spec.format && !new RegExp(spec.format).test(s)) e.push(`${nom} : « ${s.slice(0, 40)} » ne respecte pas le format`);
  return e;
}

// onglet = contrat d'un onglet (colonnes résolues), mode = 'ajout' | 'mise à jour' | 'purge'.
// En mise à jour, seules les colonnes présentes sont vérifiées, mais la clé est obligatoire.
function verifierLigne(onglet, ligne, mode) {
  const erreurs = [], propre = {};
  const cols = onglet.colonnes;
  for (const nom of Object.keys(ligne || {})) {
    if (nom.startsWith('_')) continue;                      // champs techniques n8n : jamais écrits
    if (!cols[nom]) erreurs.push(`${nom} : colonne absente du contrat`);
  }
  for (const [nom, spec] of Object.entries(cols)) {
    const present = Object.prototype.hasOwnProperty.call(ligne || {}, nom);
    if (mode !== 'ajout' && !present && nom !== onglet.cle) continue;
    let v = present ? ligne[nom] : '';
    if (mode === 'purge' && v === '[purgé]' && spec.perso !== 'non') { propre[nom] = v; continue; }
    if (mode !== 'ajout' && nom === onglet.cle && (v === '' || v === undefined || v === null)) { erreurs.push(`${nom} : clé obligatoire pour une ${mode}`); continue; }
    erreurs.push(...gardeValeur(nom, spec, v));
    propre[nom] = v === undefined || v === null ? '' : v;
  }
  if (onglet.perso_interdit) for (const [nom, spec] of Object.entries(cols)) if (spec.perso !== 'non') erreurs.push(`${nom} : donnée personnelle interdite dans ${onglet.nom}`);
  return { ligne: propre, erreurs };
}

// Vérifie un lot ; bloque TOUT le lot à la première non-conformité (on n'écrit jamais à moitié).
function garderLot(onglet, items, mode) {
  const sortie = [], erreurs = [];
  items.forEach((it, i) => {
    const r = verifierLigne(onglet, it.json, mode);
    if (r.erreurs.length) erreurs.push(`ligne ${i + 1} — ${r.erreurs.join(' ; ')}`);
    else sortie.push({ json: r.ligne });
  });
  if (erreurs.length) throw new Error(`Garde contrat « ${onglet.nom} » : écriture bloquée. ${erreurs.slice(0, 5).join(' | ')}`);
  return sortie;
}

if (typeof module !== 'undefined') module.exports = { corpsIA, texteIA, jsonIA, verifierLigne, garderLot };
// =================================== fin garde.js ===================================
