// Node "Construire la ligne Dégâts" — mode : Run Once for All Items
// Lit la réponse de Claude, vérifie l'ID, calcule l'estimation à partir de l'historique (jamais inventée par l'IA).
// La ligne va dans l'onglet Dégâts ; la page web l'affiche dans « À traiter ».
const today = new Date(); today.setHours(12, 0, 0, 0);
const form = $('Formulaire dégât').first().json;
const parc = $('Lire Parc').all().map(i => i.json).filter(r => r.id);
const degats = $('Lire Dégâts').all().map(i => i.json).filter(r => r.id);
// Le modèle peut renvoyer un bloc « thinking » avant le texte : on ne garde que les blocs texte.
const raw = ($input.first().json.content || []).filter(b => b.type === 'text').map(b => b.text).join('');

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

// Résumé lisible dans l'historique des exécutions n8n (ignoré par la Google Sheet).
const resume = piece
  ? `${j.immobiliser ? 'NE PAS SORTIR' : 'À contrôler'} : ${piece.id} (${piece.designation}). ${type}, ${String(ligne.gravite).toLowerCase()}. Réparation : ${est.texte}. État : ${avant} → ${apres}.`
  : `Pièce non identifiée, à vérifier à la main. Message : ${form["Ce qui s'est passé"]}`;

return [{ json: { ...ligne, _resume: resume, _question: j.question || '', _candidats: (j.candidats || []).join(', ') } }];
