// Règles de calcul du Gréeur — MÊMES règles que le démonstrateur web.
// Hypothèses de départ, à caler avec l'école (voir docs/regles-de-calcul.md).
// Ce bloc est recopié en tête des nodes Code par tools/build_n8n.py.
const HYP = {
  duree_vie_ans: { 'Voile kite': 3, 'Aile wing': 3, 'Planche twintip': 4, 'Planche wingfoil': 5, 'Foil': 5, 'Harnais': 2, 'Barre': 3 },
  seuil_reparations_pct: 50,
  surveiller_age_pct: 80,
  surveiller_reparations_pct: 30,
  surveiller_nb_degats_6_mois: 2,
  revente_pct: 20,
};
const DAY = 864e5;
// Accepte 2024-03-10 et 10/03/2024 (format d'affichage français de Google Sheets)
const toDate = s => {
  const t = String(s ?? '').trim(), fr = t.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  const d = fr ? new Date(+fr[3], +fr[2] - 1, +fr[1], 12) : new Date(t.slice(0, 10) + 'T12:00:00');
  return isNaN(d) ? null : d;
};
const addYears = (d, y) => { const r = new Date(d); r.setMonth(r.getMonth() + Math.round(y * 12)); return r; };
const num = v => { const n = parseFloat(String(v ?? '').replace(',', '.')); return isNaN(n) ? 0 : n; };
const yes = v => /^(o|oui|true|1|y)/i.test(String(v ?? ''));

function statut(it, degats, today) {
  const life = HYP.duree_vie_ans[it.categorie] || 3;
  const achat = toDate(it.date_achat) || today;
  const age = (today - achat) / (365.25 * DAY);
  const fin = addYears(achat, life);
  const dg = degats.filter(d => d.id === it.id);
  const cumul = dg.reduce((s, d) => s + num(d.cout), 0);
  const prix = num(it.prix_achat);
  const pct = prix ? (cumul / prix) * 100 : 0;
  const immo = dg.some(d => d.statut !== 'Réparé' && yes(d.immobilise));
  const recent = dg.filter(d => (today - toDate(d.date)) / DAY <= 183).length;
  const why = [];
  let st = 'OK';
  if (fin <= today) why.push(`fin de vie estimée dépassée (${life} ans)`);
  if (pct >= HYP.seuil_reparations_pct) why.push(`réparations = ${Math.round(pct)} % du prix`);
  if (why.length) st = 'À remplacer';
  else {
    if ((age / life) * 100 >= HYP.surveiller_age_pct) why.push(`${Math.round((age / life) * 100)} % de sa durée de vie`);
    if (pct >= HYP.surveiller_reparations_pct) why.push(`réparations = ${Math.round(pct)} % du prix`);
    if (recent >= HYP.surveiller_nb_degats_6_mois) why.push(`${recent} dégâts en 6 mois`);
    if (why.length) st = 'À surveiller';
  }
  if (immo) { st = 'Immobilisé'; why.unshift('réparation en attente, ne pas sortir'); }
  const remplacement = pct >= HYP.seuil_reparations_pct ? today : fin;
  return { ...it, prix, age, cumul, pct, st, why, remplacement };
}

function estimation(type, degats) {
  const c = degats.filter(d => d.type === type && num(d.cout) > 0).map(d => num(d.cout)).sort((a, b) => a - b);
  if (!c.length) return { montant: null, texte: 'à chiffrer (aucune réparation de ce type dans l\'historique)' };
  const m = c.length % 2 ? c[(c.length - 1) / 2] : (c[c.length / 2 - 1] + c[c.length / 2]) / 2;
  return { montant: m, texte: `≈ ${Math.round(m)} € (médiane de ${c.length} réparation(s) du même type)` };
}
