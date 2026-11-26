// Node "Construire la ligne Demandes" — mode : Run Once for All Items
// La réponse n'est PAS envoyée : elle attend dans l'onglet Demandes, la page web la montre pour validation.
const v = $('Vérifier créneau, matos, vent').first().json;
// texteIA (tools/garde.js) : blocs texte seulement ; vide si l'IA n'a pas répondu → statut « Nouveau », l'équipe reprend.
const reponse = texteIA($input.first().json);
const now = new Date();
const pad = n => String(n).padStart(2, '0');
return [{ json: {
  id: 'D-' + String(now.getTime()).slice(-6),
  recu: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`,
  canal: v._demande.canal,
  contact: v._demande.contact,
  langue: v._req.langue,
  message: v._demande.message,
  statut: reponse ? 'Réponse prête' : 'Nouveau',
  resume: v._req.resume || (v._lecture_ok ? '' : 'Lecture IA impossible : à traiter à la main'),
  reponse,
  proposition: v._proposition,
} }];
