// Node "Vérifier créneau, matos, vent" — mode : Run Once for All Items
// Précédé de : regles.js (Gréeur) + const R = {...} + accueil_regles.js
// L'IA a lu le message ; ICI le code décide : créneau, moniteur, matos, prix. Puis on prépare la demande de rédaction.
const today = new Date(); today.setHours(12, 0, 0, 0);
const f = $('Message reçu').first().json;
const demande = { canal: f['Canal'] || 'Instagram', contact: f['Expéditeur'] || '', message: String(f['Message'] || '') };
const rows = n => $(n).all().map(i => i.json);
const parc = rows('Lire Parc').filter(r => r.id).map(r => ({ ...r, id: String(r.id).trim(), prix_achat: num(r.prix_achat) }));
const degats = rows('Lire Dégâts').filter(r => r.id);
const resas = rows('Lire Réservations').filter(r => r.resa);
const vent = rows('Lire Vent').filter(r => r.date);

const raw = $input.first().json.content?.[0]?.text || '';
let j = null;
try { j = JSON.parse(raw.slice(raw.indexOf('{'), raw.lastIndexOf('}') + 1)); } catch (e) { j = null; }
const req = aNormReq(j, demande, R, today);
if (!j) req.offre = 'autre'; // lecture impossible : on ne réserve rien, l'équipe reprend la main

// État Gréeur : une pièce « À remplacer » peut sortir, mais l'Accueil le signale.
const etat = id => { const p = parc.find(x => x.id === id); return p && statut(p, degats, today).st === 'À remplacer' ? 'À remplacer' : 'OK'; };
const prop = req.offre === 'autre' ? null : aProposer({ ...req, nb: req.participants.length }, { R, parc, degats, resas, vent, today, etat });
const e = aRetenu(prop);
const F = aFaits(R, req, prop, e);

const proposition = !j ? 'Lecture IA impossible : à traiter à la main' : !e ? (req.offre === 'autre' ? 'Hors offre : à traiter par l\'équipe' : 'Aucun créneau possible sur 7 jours')
  : `${aFrLong(e.date)} ${e.label} · ${R.offres.find(o => o.code === (e._offre || req.offre)).nom} · moniteur ${e.moniteurs.join(', ')} · matos ${e.matos.map(m => m.ids.join('+')).join(' / ')} · ${e.prix_total} € (acompte ${e.acompte} €)`
    + (e.notes.length ? ` · à noter : ${e.notes.join(' ; ')}` : '');

return [{ json: {
  body: { model: 'claude-haiku-5-5', max_tokens: 600, messages: [{ role: 'user', content: aPromptReponse(F, demande.message) }] },
  _demande: demande, _req: req, _proposition: proposition, _lecture_ok: !!j,
} }];
