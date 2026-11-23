// Node "Construire la ligne Dégâts" — mode : Run Once for All Items
// Lit la réponse de Claude, vérifie l'ID, calcule l'estimation à partir de l'historique (jamais inventée par l'IA).
const today = new Date(); today.setHours(12, 0, 0, 0);
const form = $('Formulaire dégât').first().json;
const parc = $('Lire Parc').all().map(i => i.json).filter(r => r.id);
const degats = $('Lire Dégâts').all().map(i => i.json).filter(r => r.id);
const raw = $input.first().json.content?.[0]?.text || '';

let j = {};
try { j = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1)); } catch (e) { j = {}; }
const piece = parc.find(p => p.id === j.id);
const type = j.type || 'Autre';
const est = estimation(type, degats);
const avant = piece ? statut(piece, degats, today).st : '?';

const ligne = {
  date: today.toISOString().slice(0, 10),
  id: piece ? piece.id : 'A_VERIFIER',
  type,
  description: (j.description || form["Ce qui s'est passé"] || '').trim(),
  gravite: j.gravite || 'Moyenne',
  cout: '',
  statut: 'À réparer',
  immobilise: j.immobiliser ? 'oui' : 'non',
};
const apres = piece ? statut(piece, [...degats, ligne], today).st : '?';

const alerte = piece
  ? `${j.immobiliser ? 'NE PAS SORTIR' : 'À contrôler'} : ${piece.id} (${piece.designation}).\n` +
    `${type}, gravité ${String(ligne.gravite).toLowerCase()} : ${ligne.description}\n` +
    `Signalé par ${form['Moniteur'] || 'un moniteur'}.\nRéparation : ${est.texte}.\nÉtat : ${avant} → ${apres}.` +
    (j.question ? `\nQuestion à poser : ${j.question}` : '') +
    (j.candidats?.length ? `\nAutres pièces possibles : ${j.candidats.join(', ')}` : '')
  : `Dégât signalé mais pièce non identifiée — à vérifier à la main.\nMessage : ${form["Ce qui s'est passé"]}`;

return [{ json: { ...ligne, _alerte: alerte, _envoyer: j.immobiliser === true || !piece, _sujet: piece ? `[Gréeur] ${piece.id} — ${type}` : '[Gréeur] Dégât à vérifier' } }];
