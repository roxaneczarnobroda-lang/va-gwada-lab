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

// ---------- Journal chaîné : chaque ligne porte l'empreinte de la précédente (preuve d'intégrité) ----------
// SHA-256 en JS pur : le node Code de n8n n'a pas accès au module crypto par défaut.
function sha256(texte) {
  const K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  const o = [];
  for (const ch of unescape(encodeURIComponent(String(texte)))) o.push(ch.charCodeAt(0));
  const l = o.length * 8;
  o.push(0x80);
  while (o.length % 64 !== 56) o.push(0);
  for (let i = 7; i >= 0; i--) o.push(i >= 4 ? 0 : (l >>> (i * 8)) & 0xff);
  let H = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  const r = (x, n) => (x >>> n) | (x << (32 - n));
  for (let i = 0; i < o.length; i += 64) {
    const w = new Array(64);
    for (let t = 0; t < 16; t++) w[t] = (o[i + 4 * t] << 24) | (o[i + 4 * t + 1] << 16) | (o[i + 4 * t + 2] << 8) | o[i + 4 * t + 3];
    for (let t = 16; t < 64; t++) {
      const s0 = r(w[t - 15], 7) ^ r(w[t - 15], 18) ^ (w[t - 15] >>> 3), s1 = r(w[t - 2], 17) ^ r(w[t - 2], 19) ^ (w[t - 2] >>> 10);
      w[t] = (w[t - 16] + s0 + w[t - 7] + s1) | 0;
    }
    let [a, b, c, d, e, f, g, h] = H;
    for (let t = 0; t < 64; t++) {
      const t1 = (h + (r(e, 6) ^ r(e, 11) ^ r(e, 25)) + ((e & f) ^ (~e & g)) + K[t] + w[t]) | 0;
      const t2 = ((r(a, 2) ^ r(a, 13) ^ r(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) | 0;
      h = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
    }
    H = H.map((v, k) => (v + [a, b, c, d, e, f, g, h][k]) | 0);
  }
  return H.map(v => (v >>> 0).toString(16).padStart(8, '0')).join('');
}

const CHAINE_DEBUT = 'GENESE';
// Forme canonique : les colonnes du contrat dans l'ordre, sauf « empreinte », en texte, séparées par \u001f.
function empreinteLigne(onglet, ligne) {
  const cols = Object.keys(onglet.colonnes).filter(c => c !== 'empreinte');
  return sha256(cols.map(c => String(ligne[c] === undefined || ligne[c] === null ? '' : ligne[c])).join('\u001f'));
}
// lignes = le Journal tel qu'il est lu (dans l'ordre) ; renvoie la ligne complétée de « precedent » et « empreinte ».
function chainer(onglet, lignes, ligne) {
  const derniere = [...lignes].reverse().find(l => l && l.empreinte);
  const l = { ...ligne, precedent: derniere ? String(derniere.empreinte) : CHAINE_DEBUT };
  return { ...l, empreinte: empreinteLigne(onglet, l) };
}
// Vérifie toute la chaîne. Renvoie {ok, n, derniere, ruptures: [{ligne, raison}]} (ligne = n° de ligne dans la Sheet).
function verifierChaine(onglet, lignes) {
  const ruptures = [];
  let prec = CHAINE_DEBUT;
  lignes.forEach((l, i) => {
    const n = i + 2;
    if (String(l.precedent) !== prec) ruptures.push({ ligne: n, raison: `« precedent » ne correspond pas à la ligne d'avant (ligne supprimée, insérée ou déplacée ?)` });
    if (empreinteLigne(onglet, l) !== String(l.empreinte)) ruptures.push({ ligne: n, raison: 'contenu modifié depuis son écriture' });
    prec = String(l.empreinte);
  });
  return { ok: !ruptures.length, n: lignes.length, derniere: lignes.length ? prec : CHAINE_DEBUT, ruptures };
}

if (typeof module !== 'undefined') module.exports = { corpsIA, texteIA, jsonIA, verifierLigne, garderLot, sha256, chainer, verifierChaine };
// =================================== fin garde.js ===================================
