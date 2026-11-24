// Node "Cours à clôturer" — mode : Run Once for All Items
// Précédé de : const R = {...} + accueil_regles.js
// Chaque soir : les cours confirmés du jour (ou d'avant) passent à « Terminé ».
// Pour chacun : lignes Utilisations (une par pièce) + message d'après-cours (photos, avis Google, code de réduction).
const today = aIso(new Date());
const resas = $('Lire Réservations').all().map(i => i.json)
  .filter(r => r.resa && r.statut === 'Confirmé' && aIso(aDate(r.date) || new Date(8.64e15)) <= today);
return resas.map(r => {
  const resa = { ...r, date: aIso(aDate(r.date)), code: r.code || aCode(R, r.client) };
  return { json: {
    resa: r.resa, statut: 'Terminé', code: resa.code,
    _utils: aUtilisations(R, resa),
    _msg: { date: today, resa: r.resa, canal: r.canal, contact: r.contact, type: 'Après le cours',
            texte: aMessageApres(R, resa, r.album || ''), statut: 'À envoyer (canal pas encore branché)' },
  } };
});
