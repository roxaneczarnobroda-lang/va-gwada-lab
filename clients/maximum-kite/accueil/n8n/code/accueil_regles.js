// Règles de L'Accueil — UN SEUL fichier, utilisé tel quel par :
//   · la page de démo (injecté par tools/build.py),
//   · les nodes Code n8n (recopié par tools/build.py, précédé de `const R = {...}` tiré du JSON).
// Fonctions pures : elles reçoivent toutes les données en paramètre, rien n'est lu ailleurs.
// Ce qui est décidé ici (créneau, matos, prix) ne vient JAMAIS de l'IA : l'IA lit le message et rédige la réponse.

const A_DAY = 864e5;
const aIso = d => new Date(d.getTime() - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10);
const aDate = s => {
  const t = String(s ?? '').trim(), fr = t.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  const d = fr ? new Date(+fr[3], +fr[2] - 1, +fr[1], 12) : new Date(t.slice(0, 10) + 'T12:00:00');
  return isNaN(d) ? null : d;
};
const aNum = v => { const n = parseFloat(String(v ?? '').replace(/[\s  €]/g, '').replace(',', '.')); return isNaN(n) ? null : n; };
const aYes = v => /^(o|oui|true|1|y)/i.test(String(v ?? ''));
const aList = v => String(v ?? '').split(/[,;\s]+/).map(s => s.trim()).filter(Boolean);

// « Voile kite 9 m » → 9 ; « Aile wing 4,5 m » → 4.5 ; « Planche wingfoil 140 L » → 140 ; « Foil 1800 cm² » → 1800
function aTaille(designation) {
  const m = String(designation).match(/(\d+(?:[.,]\d+)?)\s*(m\b|L\b|cm)/);
  return m ? parseFloat(m[1].replace(',', '.')) : null;
}

// Pièces immobilisées par le Gréeur : un dégât « ne pas sortir » pas encore réparé.
function aImmobilises(degats) {
  return new Set(degats.filter(d => d.statut !== 'Réparé' && aYes(d.immobilise)).map(d => String(d.id).trim()));
}

const aActive = r => !/annul/i.test(r.statut || '');
const aMemeCreneau = (r, date, creneau) => aIso(aDate(r.date) || new Date(0)) === date && r.creneau === creneau && aActive(r);

function aVent(vent, date, creneau) {
  const v = vent.find(x => aIso(aDate(x.date) || new Date(0)) === date);
  if (!v || aNum(v[creneau]) === null) return null;
  return {nds: aNum(v[creneau]), dir: v.dir || ''};
}

function aCible(R, regle, poids, nds) {
  const t = R.tailles[regle];
  if (!t) return null; // « grand » : la plus grande disponible
  const ligne = t.find(l => nds <= l.vent_max) || t[t.length - 1];
  return (ligne.par_poids.find(([max]) => poids <= max) || ligne.par_poids[ligne.par_poids.length - 1])[1];
}

// Choisit une pièce libre de la catégorie, la plus proche de la taille visée.
// Préférence : taille exacte, puis plus proche, puis pièce en bon état (le Gréeur dit « à remplacer » = à contrôler).
function aChoisir(parc, categorie, cible, libres, etat) {
  const c = parc.filter(p => p.categorie === categorie && libres.has(p.id))
    .map(p => ({p, t: aTaille(p.designation), e: etat ? etat(p.id) : 'OK'}));
  if (!c.length) return null;
  c.sort((a, b) => cible === null ? (b.t - a.t) || (a.e === 'OK' ? -1 : 1)
    : (Math.abs(a.t - cible) - Math.abs(b.t - cible)) || ((a.e === 'OK' ? 0 : 1) - (b.e === 'OK' ? 0 : 1)) || (b.t - a.t));
  return c[0];
}

// Vérifie UN créneau pour une demande.
// req = {offre, nb, participants:[{prenom, poids, age}]}
// ctx = {R, parc, degats, resas, vent, today, etat?(id) -> état Gréeur}
function aEvaluer(req, date, creneau, ctx) {
  const {R, parc} = ctx;
  const off = R.offres.find(o => o.code === req.offre);
  const cr = R.creneaux.find(c => c.code === creneau);
  const out = {date, creneau, label: cr ? cr.label : creneau, ok: false, bloquant: [], notes: [], matos: [], moniteurs: [], prix_total: 0, acompte: 0};
  if (!off || !cr) { out.bloquant.push('offre ou créneau inconnu'); return out; }
  const d = aDate(date);
  if (!d || d < new Date(ctx.today.getTime() - A_DAY / 2)) { out.bloquant.push('date passée'); return out; }
  const now = ctx.now || new Date();
  if (date === aIso(now) && now.getHours() * 60 + now.getMinutes() >= +cr.debut.slice(0, 2) * 60 + +cr.debut.slice(3)) { out.bloquant.push('créneau déjà commencé'); return out; }

  const parts = (req.participants && req.participants.length ? req.participants : [{}]);
  while (parts.length < (req.nb || 1)) parts.push({});
  for (const p of parts) {
    if (p.age != null && p.age < off.age_min) out.bloquant.push(`${p.prenom || 'un participant'} : ${p.age} ans, âge minimum ${off.age_min} ans pour « ${off.nom} »`);
    if (p.poids != null && p.poids < off.poids_min) out.bloquant.push(`${p.prenom || 'un participant'} : ${p.poids} kg, poids minimum ${off.poids_min} kg`);
  }

  const v = aVent(ctx.vent, date, creneau);
  out.vent = v;
  if (!v) out.bloquant.push('pas encore de prévision de vent pour ce jour');
  else if (v.nds < off.vent_min) out.bloquant.push(`vent prévu ${v.nds} nds, il en faut au moins ${off.vent_min}`);
  else if (v.nds > off.vent_max) out.bloquant.push(`vent prévu ${v.nds} nds, au-delà de ${off.vent_max} nds pour une ${off.nom.toLowerCase()}`);

  const ici = ctx.resas.filter(r => aMemeCreneau(r, date, creneau) && r.resa !== req.sauf);
  const pris = new Set(ici.flatMap(r => aList(r.moniteur)));
  const besoin = Math.ceil(parts.length / off.max_eleves);
  const dispo = R.moniteurs.filter(m => !pris.has(m));
  if (dispo.length < besoin) out.bloquant.push(besoin > 1 ? `il faut ${besoin} moniteurs, ${dispo.length} libre(s)` : 'aucun moniteur libre');
  else out.moniteurs = dispo.slice(0, besoin);

  const immo = aImmobilises(ctx.degats);
  const occupe = new Set(ici.flatMap(r => aList(r.matos)));
  const libres = new Set(parc.map(p => p.id).filter(id => !immo.has(id) && !occupe.has(id)));
  const nds = v ? v.nds : 16;
  for (const p of parts) {
    const poids = p.poids ?? R.tailles.poids_par_defaut;
    const ligne = {prenom: p.prenom || '', poids: p.poids ?? null, ids: [], detail: []};
    for (const m of off.matos) {
      const cible = aCible(R, m.regle, poids, nds);
      const pick = aChoisir(parc, m.categorie, cible, libres, ctx.etat);
      if (!pick) { out.bloquant.push(`plus de ${m.categorie.toLowerCase()} libre sur ce créneau`); continue; }
      libres.delete(pick.p.id);
      ligne.ids.push(pick.p.id);
      let txt = `${pick.p.id} · ${pick.p.designation}`;
      if (cible !== null && pick.t !== cible) {
        const raisons = parc.filter(x => x.categorie === m.categorie && aTaille(x.designation) === cible)
          .map(x => immo.has(x.id) ? `${x.id} immobilisée (Gréeur)` : occupe.has(x.id) ? `${x.id} déjà réservée` : '').filter(Boolean);
        txt += ` (au lieu de ${String(cible).replace('.', ',')}${m.categorie === 'Planche wingfoil' ? ' L' : ' m'}${raisons.length ? ' : ' + raisons.join(', ') : ' : taille absente du parc'})`;
        out.notes.push(`${pick.p.id} remplace la taille idéale`);
      }
      if (pick.e && pick.e !== 'OK') { txt += ` — ${pick.e} selon le Gréeur, à contrôler avant de sortir`; out.notes.push(`${pick.p.id} : ${pick.e}`); }
      ligne.detail.push(txt);
    }
    if (p.poids == null) out.notes.push(`poids inconnu (${p.prenom || 'participant'}) : taille calculée sur ${poids} kg, à confirmer`);
    out.matos.push(ligne);
  }
  out.prix_total = off.prix * parts.length;
  out.acompte = Math.round(out.prix_total * R.acompte_pct / 100);
  out.ok = !out.bloquant.length;
  return out;
}

// Propose des créneaux : d'abord ceux demandés, puis jusqu'à 2 alternatives sur les 7 jours suivants.
// req.date (ISO ou '') et req.moment ('matin' | 'midi' | 'aprem' | '').
function aProposer(req, ctx) {
  const {R} = ctx, today = ctx.today, demandes = [], alternatives = [];
  const cr = R.creneaux.map(c => c.code);
  const voulu = req.moment && cr.includes(req.moment) ? [req.moment] : cr;
  if (req.date) for (const c of voulu) demandes.push(aEvaluer(req, req.date, c, ctx));
  const debut = req.date ? aDate(req.date) : today;
  for (let k = 0; k <= 7 && alternatives.length < 2; k++) {
    const day = aIso(new Date(Math.max(debut.getTime(), today.getTime()) + k * A_DAY));
    for (const c of (k === 0 && req.date ? cr : voulu.concat(cr.filter(x => !voulu.includes(x))))) {
      if (demandes.some(e => e.date === day && e.creneau === c)) continue;
      const e = aEvaluer(req, day, c, ctx);
      if (e.ok) alternatives.push(e);
      if (alternatives.length >= 2) break;
    }
  }
  const retenu = demandes.find(e => e.ok) || alternatives[0] || null;
  // Autre offre possible quand la seule chose qui bloque est l'âge (ex. kite à 10 ans → wingfoil)
  let autre = null;
  const bloqueAge = (demandes[0] || alternatives[0] || aEvaluer(req, aIso(today), 'matin', ctx)).bloquant.some(b => /âge minimum/.test(b));
  if (!retenu || bloqueAge) {
    const ages = (req.participants || []).map(p => p.age).filter(a => a != null);
    const o = R.offres.find(x => x.code !== req.offre && ages.every(a => a >= x.age_min));
    if (o && ages.length) {
      const r2 = aProposer({...req, offre: o.code, _sansAutre: true}, ctx);
      if (!req._sansAutre && r2.retenu) autre = {offre: o, retenu: r2.retenu};
    }
  }
  return {demandes, alternatives, retenu: (bloqueAge ? null : retenu), autre};
}

// Message après le cours : modèle fixe par langue (pas d'IA : il part sans relecture).
const A_APRES = {
  fr: (x) => `Merci pour le cours, ${x.prenom} ! Voici les photos de ta séance : ${x.album}. Si tu as aimé, tu nous laisses un avis Google ? ${x.avis}. Pour ta prochaine session : −${x.pct} % avec le code ${x.code} (valable ${x.mois} mois). À bientôt sur l'eau ! — ${x.ecole}`,
  en: (x) => `Thanks for today's lesson, ${x.prenom}! Here are the photos from your session: ${x.album}. If you enjoyed it, would you leave us a Google review? ${x.avis}. For your next session: ${x.pct}% off with code ${x.code} (valid ${x.mois} months). See you on the water! — ${x.ecole}`,
  de: (x) => `Danke für die Stunde heute, ${x.prenom}! Hier sind die Fotos deiner Session: ${x.album}. Wenn es dir gefallen hat, hinterlässt du uns eine Google-Bewertung? ${x.avis}. Für deine nächste Session: −${x.pct} % mit dem Code ${x.code} (${x.mois} Monate gültig). Bis bald auf dem Wasser! — ${x.ecole}`,
  es: (x) => `¡Gracias por la clase de hoy, ${x.prenom}! Aquí tienes las fotos de tu sesión: ${x.album}. Si te gustó, ¿nos dejas una reseña en Google? ${x.avis}. Para tu próxima sesión: −${x.pct} % con el código ${x.code} (válido ${x.mois} meses). ¡Hasta pronto en el agua! — ${x.ecole}`,
};
function aCode(R, client) {
  const p = String(client || 'CLIENT').split(/[\s&,]/)[0].normalize('NFD').replace(/[^A-Za-z]/g, '').toUpperCase().slice(0, 10);
  return R.reduction.prefixe + (p || 'CLIENT');
}
function aMessageApres(R, resa, album) {
  const f = A_APRES[resa.langue] || A_APRES.en;
  return f({prenom: resa.client, album: album || R.lien_album_defaut, avis: R.lien_avis, pct: R.reduction.pct, code: resa.code || aCode(R, resa.client), mois: R.reduction.validite_mois, ecole: R.ecole});
}

// Les lignes « Utilisations » d'un cours terminé : une par pièce sortie.
function aUtilisations(R, resa) {
  const off = R.offres.find(o => o.code === resa.offre);
  return aList(resa.matos).map(id => ({date: aIso(aDate(resa.date)), resa: resa.resa, id, heures: off ? off.duree_h : 2, client: resa.client}));
}

// ---------- Ce qu'on demande à l'IA (mêmes consignes dans la page et dans n8n) ----------
const aFrLong = s => { const d = aDate(s); return d ? d.toLocaleDateString('fr-FR', {weekday: 'long', day: 'numeric', month: 'long'}) : String(s); };
const aJours = today => Array.from({length: 8}, (_, j) => aIso(new Date(today.getTime() + j * A_DAY)));

// 1. Lire le message : l'IA extrait la demande en JSON, rien d'autre.
function aPromptLecture(R, today, msg) {
  const ds = aJours(today).map(x => `${x} (${aDate(x).toLocaleDateString('fr-FR', {weekday: 'long'})})`);
  return `Tu es "L'Accueil", l'assistant de réservation d'une école de kitesurf et de wingfoil en Guadeloupe (${R.ecole}, ${R.lieu}).
Un vacancier écrit sur Instagram ou par email. Extrais sa demande en JSON. Tu ne réponds pas au client ici.

AUJOURD'HUI : ${aIso(today)}. Les 8 prochains jours : ${ds.join(', ')}.
COURS PROPOSÉS : ${JSON.stringify(R.offres.map(o => ({code: o.code, nom: o.nom})))}
CRÉNEAUX : ${JSON.stringify(R.creneaux.map(c => ({code: c.code, horaire: c.label})))}

Règles :
- "langue" : code ISO à 2 lettres de la langue du message (fr, en, de, es…).
- "client" : prénom ou pseudo de la personne qui écrit, sinon "".
- "offre" : le code du cours le plus adapté. Débutant kite → "kite-init". Déjà autonome en kite et veut progresser → "kite-perf". Wing ou wingfoil → "wing-init". Location seule, cours privé, autre sport ou demande hors de ces cours → "autre".
- "participants" : une entrée par personne qui naviguerait (pas l'expéditeur s'il réserve seulement pour un autre), avec "prenom" (ou "" ou un rôle comme "fils"), "poids" en kg (nombre ou null) et "age" (nombre ou null). Ne devine ni poids ni âge.
- "date" : la date voulue au format AAAA-MM-JJ, calculée à partir d'aujourd'hui ("demain", "jeudi", "ce week-end" = le samedi), sinon "".
- "moment" : "matin", "midi", "aprem" ou "" si non précisé.
- "question" : toute autre question posée (prix, matériel, lieu…), sinon "".
- "resume" : une phrase en français qui résume la demande.
Réponds UNIQUEMENT avec un objet JSON : {"langue":"","client":"","offre":"","participants":[{"prenom":"","poids":null,"age":null}],"date":"","moment":"","question":"","resume":""}

MESSAGE : """${msg}"""`;
}

// Vérifie la réponse de l'IA : tout ce qui sort des listes autorisées est remplacé par une valeur sûre.
function aNormReq(j, demande, R, today) {
  j = j || {};
  const parts = Array.isArray(j.participants) && j.participants.length
    ? j.participants.slice(0, 6).map(p => ({prenom: String(p.prenom || '').slice(0, 30), poids: aNum(p.poids), age: aNum(p.age)}))
    : [{prenom: '', poids: null, age: null}];
  return {
    langue: /^[a-z]{2}$/.test(j.langue) ? j.langue : (demande.langue || 'fr'),
    client: String(j.client || '').slice(0, 40) || String(demande.contact || '').replace(/^@/, '').split(/[._@]/)[0],
    offre: R.offres.some(o => o.code === j.offre) ? j.offre : (j.offre === 'autre' ? 'autre' : 'kite-init'),
    participants: parts,
    date: aJours(today).includes(j.date) ? j.date : '',
    moment: ['matin', 'midi', 'aprem'].includes(j.moment) ? j.moment : '',
    question: String(j.question || ''), resume: String(j.resume || ''),
  };
}

// Les faits vérifiés que l'IA a le droit d'utiliser pour répondre. e = le créneau retenu (ou null).
function aFaits(R, req, prop, e) {
  const eur = n => Math.round(n).toLocaleString('fr-FR') + ' €';
  const off = c => R.offres.find(o => o.code === c);
  const f = {ecole: R.ecole, lieu: R.lieu, client: req.client, langue: req.langue, question_du_client: req.question};
  if (req.offre === 'autre') return {...f, cas: 'hors_offre', a_dire: 'demande hors de nos cours : un membre de l\'équipe revient vers lui rapidement'};
  const first = prop && prop.demandes.find(x => !x.ok);
  if (first && !prop.demandes.some(x => x.ok)) f.creneau_demande_impossible = {quand: aFrLong(first.date) + ' ' + first.label, pourquoi: first.bloquant};
  if (!e) return {...f, cas: 'aucun_creneau', a_dire: 'pas de créneau possible sur 7 jours, proposer de revenir vers lui dès que le vent ou le planning change'};
  const o = off(e._offre || req.offre);
  return {...f, cas: e._offre ? 'autre_cours_propose' : 'creneau_ok', cours: o.nom, duree: o.duree_h + ' h', quand: aFrLong(e.date) + ', ' + e.label, participants: e.matos.length,
    prix_par_personne: eur(o.prix), prix_total: eur(e.prix_total), acompte: `${eur(e.acompte)} (${R.acompte_pct} %) pour bloquer le créneau`, lien_acompte: R.lien_acompte,
    vent_prevu: e.vent ? e.vent.nds + ' nœuds' : '', meteo: R.annulation, materiel: 'tout le matériel est fourni',
    a_demander: e.notes.some(n => /poids/.test(n)) ? 'son poids (pour préparer la bonne taille de matériel)' : '',
    pourquoi_autre_cours: e._offre ? `l'âge minimum du cours demandé est ${off(req.offre).age_min} ans, ${o.nom} est possible dès ${o.age_min} ans` : ''};
}

// 2. Rédiger la réponse : l'IA reformule les faits, dans la langue du client.
function aPromptReponse(F, message) {
  return `Tu es "L'Accueil", qui répond aux vacanciers pour l'école ${F.ecole} (${F.lieu}, Guadeloupe).
Écris la réponse au message ci-dessous, dans la langue "${F.langue}", sur le ton du message reçu (tutoiement si la personne tutoie, sinon vouvoiement ; chaleureux, simple). 110 mots maximum, sans markdown, signé "${F.ecole}".
Utilise UNIQUEMENT les faits fournis : n'invente ni prix, ni horaire, ni condition, ni promesse. Si un fait manque pour répondre à une question du client, dis que l'équipe lui répond très vite. Écris les liens tels quels.
FAITS : ${JSON.stringify(F)}
MESSAGE DU CLIENT : """${message}"""`;
}

// Le créneau retenu par défaut : celui demandé s'il tient, sinon la 1re alternative, sinon l'autre cours possible.
function aRetenu(prop) {
  if (!prop) return null;
  const ok = prop.demandes.find(e => e.ok) || prop.alternatives[0];
  return ok || (prop.autre ? {...prop.autre.retenu, _offre: prop.autre.offre.code} : null);
}
