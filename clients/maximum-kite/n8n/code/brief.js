// Node "Calculer le brief" — mode : Run Once for All Items
const today = new Date(); today.setHours(12, 0, 0, 0);
const parc = $('Lire Parc').all().map(i => i.json).filter(r => r.id);
const degats = $('Lire Dégâts').all().map(i => i.json).filter(r => r.id);
const A = parc.map(p => statut(p, degats, today));
const by = s => A.filter(x => x.st === s);
const lim = new Date(today.getTime() + 365 * DAY);
const B = A.filter(x => x.remplacement <= lim);
const net = B.reduce((s, x) => s + x.prix * (1 - HYP.revente_pct / 100), 0);
const fmt = n => Math.round(n).toLocaleString('fr-FR') + ' €';

const lignes = [
  `Bonjour ! ${A.length - by('Immobilisé').length} pièces sur ${A.length} peuvent sortir.`,
  by('Immobilisé').length ? `Ne pas sortir : ${by('Immobilisé').map(x => `${x.id} (${x.designation})`).join(', ')}.` : 'Rien d\'immobilisé.',
  by('À remplacer').length ? `À remplacer : ${by('À remplacer').map(x => `${x.id} — ${x.why.join(', ')}`).join(' ; ')}.` : '',
  by('À surveiller').length ? `À surveiller : ${by('À surveiller').map(x => x.id).join(', ')}.` : '',
  `Budget de renouvellement sur 12 mois : ${fmt(net)} net (${B.length} pièces, revente ${HYP.revente_pct} % déduite).`,
].filter(Boolean);

return [{ json: { sujet: `[Gréeur] Brief matos du ${today.toLocaleDateString('fr-FR')}`, brief: lignes.join('\n') } }];
