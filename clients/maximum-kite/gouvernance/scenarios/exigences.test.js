// Scénarios QA de Maximum Kite — un test = une promesse faite à l'école (gouvernance.json → exigences).
// Lancés par tools/qa.py. Ils exécutent le code EXACT des nodes n8n générés (executer), avec des réponses IA
// simulées : on vérifie ce que fait NOTRE code quand l'IA répond bien, mal, ou pas du tout.
// Disponible : test, vrai, egal, echoue, executer, DONNEES (données de démo), CONTRAT, R, fonctions des règles et de garde.js.

const WF_DEMANDE = 'Accueil — Demande de réservation';
const WF_DEGAT = "Gréeur — Signalement d'un dégât";
const WF_PURGE = 'Gouvernance — Purge des données personnelles';
const AUJ = new Date(); AUJ.setHours(12, 0, 0, 0);
const iso = j => aIso(new Date(AUJ.getTime() + j * A_DAY));
const ia = texte => ({ content: [{ type: 'text', text: texte }] });          // réponse IA simulée
const iaJson = o => ia(JSON.stringify(o));

// Les onglets tels que n8n les lit dans les Google Sheets (dates calculées, oui/non en texte).
const feuilles = (degatsEnPlus = []) => ({
  'Lire Parc': DONNEES.matos.parc,
  'Lire Dégâts': DONNEES.matos.degats.map(d => ({ ...d, immobilise: d.immobilise ? 'oui' : 'non' })).concat(degatsEnPlus),
  'Lire Réservations': DONNEES.reservations.reservations.map(r => ({ ...r, date: iso(r.j) })),
  'Lire Vent': DONNEES.reservations.vent.map(v => ({ ...v, date: iso(v.j) })),
});
const message = (texte) => ({ 'Message reçu': [{ Canal: 'Instagram', 'Expéditeur': '@lena.test', Message: texte }] });
const lectureLena = (surcharge = {}) => ({
  langue: 'en', client: 'Lena', offre: 'kite-init', participants: [{ prenom: 'Lena', poids: 58, age: 29 }],
  date: iso(1), moment: '', question: 'How much is it?', resume: 'Débutante, demain', ...surcharge,
});
const verifier = (reponseIA, degatsEnPlus) => executer(WF_DEMANDE, 'Vérifier créneau, matos, vent',
  { input: [reponseIA], refs: { ...feuilles(degatsEnPlus), ...message('Hi! Can I try kitesurf tomorrow? 58 kg') } })[0];
const prixOffre = code => R.offres.find(o => o.code === code).prix;

// ------------------------------------------------------------------ EX-02 : l'IA ne décide ni prix, ni créneau, ni matos
test('EX-02', "Un prix glissé par l'IA est ignoré : le prix vient des tarifs de l'école", () => {
  const v = verifier(iaJson(lectureLena({ prix_total: 1, prix: 1, moniteur: 'Bob', matos: 'K-99' })));
  vrai(!/Lecture IA impossible|Aucun créneau/.test(v._proposition), 'un créneau devait être trouvé : ' + v._proposition);
  vrai(v._proposition.includes(`${prixOffre('kite-init')} €`), `prix attendu ${prixOffre('kite-init')} € dans : ${v._proposition}`);
  vrai(!/\bBob\b|K-99/.test(v._proposition), "moniteur ou matos inventé par l'IA repris : " + v._proposition);
  vrai(R.moniteurs.some(m => v._proposition.includes('moniteur ' + m)), 'moniteur hors équipe');
});

test('EX-02', "Une offre ou une date inventées par l'IA sont ramenées aux valeurs autorisées", () => {
  const req = aNormReq(lectureLena({ offre: 'cours-vip-gratuit', date: '2099-01-01', moment: 'minuit' }), { contact: '@x' }, R, AUJ);
  vrai(R.offres.some(o => o.code === req.offre), 'offre hors catalogue : ' + req.offre);
  egal(req.date, '', 'date hors des 8 prochains jours :');
  egal(req.moment, '', 'créneau inconnu :');
});

test('EX-02', "Les faits envoyés à l'IA pour rédiger contiennent le prix calculé, pas celui de l'IA", () => {
  const v = verifier(iaJson(lectureLena({ prix_total: 1 })));
  const faits = v.body.messages[0].content;
  vrai(faits.includes(`${prixOffre('kite-init')} €`), 'prix des règles absent des faits');
  egal(v.body.model, GOUV_IA_ATTENDU.modele, 'modèle :');
});

// ------------------------------------------------------------------ EX-03 : une pièce immobilisée ne sort pas
test('EX-03', 'Les voiles proposées puis immobilisées par le Gréeur ne sont plus jamais proposées', () => {
  const avant = verifier(iaJson(lectureLena()));
  const ids = (avant._proposition.match(/[A-Z]{1,3}-\d{2}/g) || []);
  vrai(ids.length, 'aucun matos proposé au départ : ' + avant._proposition);
  const blocages = ids.map(id => ({ date: iso(0), id, type: 'Boudin percé', description: 'test', gravite: 'Grave', cout: '', statut: 'À réparer', immobilise: 'oui' }));
  const apres = verifier(iaJson(lectureLena()), blocages);
  for (const id of ids) vrai(!apres._proposition.includes(id), `${id} immobilisée mais proposée : ${apres._proposition}`);
});

test('EX-03', 'Le calcul des pièces immobilisées ignore les dégâts réparés', () => {
  const s = aImmobilises([{ id: 'K-01', statut: 'Réparé', immobilise: 'oui' }, { id: 'K-02', statut: 'À réparer', immobilise: 'oui' }]);
  egal([...s], ['K-02']);
});

// ------------------------------------------------------------------ EX-04 : IA en panne → rien n'est réservé
test('EX-04', "Réponse IA illisible : aucune proposition, l'équipe reprend la main", () => {
  const v = verifier(ia("Désolé, je n'ai pas compris."));
  vrai(/Lecture IA impossible/.test(v._proposition), v._proposition);
  egal(v._lecture_ok, false);
});

test('EX-04', "IA muette : la demande est enregistrée « Nouveau », sans réponse préparée", () => {
  const v = verifier({ content: [] });
  const ligne = executer(WF_DEMANDE, 'Construire la ligne Demandes', { input: [{ content: [] }], refs: { 'Vérifier créneau, matos, vent': [v] } })[0];
  egal(ligne.statut, 'Nouveau');
  egal(ligne.reponse, '');
});

test('EX-04', 'Lecture prudente : JSON noyé dans du texte, bloc de réflexion, réponse vide', () => {
  egal(jsonIA(ia('Voici : {"id":"K-01"} voilà')), { id: 'K-01' });
  egal(jsonIA({ content: [{ type: 'thinking', thinking: '' }, { type: 'text', text: '{"a":1}' }] }), { a: 1 });
  egal(jsonIA(null), null); egal(jsonIA(ia('[1,2]')), null); egal(jsonIA(ia('{cassé')), null);
});

test('EX-04', "Gréeur : pièce non reconnue par l'IA → « A_VERIFIER », jamais une pièce au hasard", () => {
  const ligne = executer(WF_DEGAT, 'Construire la ligne Dégâts', {
    input: [iaJson({ id: 'K-99', type: 'Boudin percé', gravite: 'Grave', immobiliser: true, description: 'x' })],
    refs: { 'Formulaire dégât': [{ Moniteur: 'Théo', "Ce qui s'est passé": 'boudin percé sur une voile' }], ...feuilles() },
  })[0];
  egal(ligne.id, 'A_VERIFIER');
});

// ------------------------------------------------------------------ EX-01 : rien ne part sans relecture
test('EX-01', 'Une réponse rédigée par l\'IA attend dans Demandes (« Réponse prête »), elle n\'est pas envoyée', () => {
  const v = verifier(iaJson(lectureLena()));
  const ligne = executer(WF_DEMANDE, 'Construire la ligne Demandes', { input: [ia('Hi Lena! ...')], refs: { 'Vérifier créneau, matos, vent': [v] } })[0];
  egal(ligne.statut, 'Réponse prête');
  vrai(!Object.values(WORKFLOWS[WF_DEMANDE]).some(js => /sendMessage|\/messages\/send|graph\.facebook/.test(js.replace(/api\.anthropic\.com\/v1\/messages/g, ''))), 'un envoi direct existe');
});

// ------------------------------------------------------------------ EX-05 : écritures conformes au contrat
test('EX-05', "La Garde bloque une valeur hors liste (gravité inventée) et n'écrit rien", () => {
  const bonne = { date: iso(0), id: 'K-01', type: 'Boudin percé', description: 'x', gravite: 'Moyenne', cout: '', statut: 'À réparer', immobilise: 'oui' };
  echoue(() => executer(WF_DEGAT, 'Garde — Ajouter au carnet', { input: [bonne, { ...bonne, gravite: 'Catastrophique' }] }), /hors liste/);
});

test('EX-05', 'La Garde retire les champs techniques et refuse une colonne inconnue', () => {
  const bonne = { date: iso(0), id: 'K-01', type: 'Boudin percé', description: 'x', gravite: 'Moyenne', cout: '', statut: 'À réparer', immobilise: 'non' };
  const out = executer(WF_DEGAT, 'Garde — Ajouter au carnet', { input: [{ ...bonne, _resume: 'note interne' }] });
  egal(Object.keys(out[0]), Object.keys(CONTRAT.matos['Dégâts'].colonnes));
  echoue(() => executer(WF_DEGAT, 'Garde — Ajouter au carnet', { input: [{ ...bonne, telephone_moniteur: '0690' }] }), /absente du contrat/);
});

test('EX-05', 'La Garde refuse un horodatage mal formé et un nombre de participants hors limites', () => {
  const ok = { id: 'D-1', recu: '2026-11-26 10:00', canal: 'Instagram', contact: '@a', langue: 'fr', message: 'm', statut: 'Nouveau', resume: '', reponse: '', proposition: '' };
  egal(executer(WF_DEMANDE, 'Garde — Ajouter aux Demandes', { input: [ok] }).length, 1);
  echoue(() => executer(WF_DEMANDE, 'Garde — Ajouter aux Demandes', { input: [{ ...ok, recu: 'hier' }] }), /horodatage/);
  egal(verifierLigne(CONTRAT.reservations['Réservations'], { resa: 'R-1', nb: 9 }, 'mise à jour').erreurs.length, 1);
});

// ------------------------------------------------------------------ EX-06 : traçabilité
const JOURNAL = CONTRAT.gouvernance.Journal;
const ecrireJournal = (journal, ecrites) => executer(WF_DEGAT, 'Journal — Ajouter au carnet', { input: journal, refs: { 'Ajouter au carnet': ecrites } })[0];

test('EX-06', 'Chaque écriture produit une ligne de Journal : version, validation, clés, sans donnée perso', () => {
  const j = ecrireJournal([], [{ id: 'K-02' }, { id: 'K-02' }, { id: 'W-01' }]);
  egal(j.operation, 'ajout'); egal(j.nb_lignes, 3); egal(j.cles, 'K-02, W-01'); egal(j.statut, 'ok');
  vrai(/^[0-9a-f]{10}$/.test(j.version), 'version absente'); vrai(j.validation.startsWith('humaine'), j.validation);
  egal(j.ia_modele, GOUV_IA_ATTENDU.modele);
});

test('EX-06', "Le Journal des erreurs masque les valeurs citées dans le message d'erreur", () => {
  const j = executer('Gouvernance — Journal des erreurs', 'Ligne Journal erreur', { input: [], refs: {
    "Erreur d'un workflow": [{ execution: { id: '42', lastNodeExecuted: 'Garde — Ajouter aux Demandes', error: { message: 'contact : « @lena.privee » hors liste' } }, workflow: { name: WF_DEMANDE } }],
  } })[0];
  egal(j.statut, 'erreur'); vrai(!j.controle.includes('lena'), 'donnée perso dans le Journal : ' + j.controle);
});

// ------------------------------------------------------------------ EX-07 : purge des données perso
test('EX-07', 'Demandes de plus de 180 jours : contact et message purgés ; demandes récentes intactes', () => {
  const vieux = { id: 'D-1', recu: iso(-200) + ' 10:00', contact: '@vieux', message: 'm', resume: 'r', reponse: 'x' };
  const recent = { id: 'D-2', recu: iso(-10) + ' 10:00', contact: '@recent', message: 'm', resume: 'r', reponse: 'x' };
  const out = executer(WF_PURGE, 'À purger — Demandes', { input: [vieux, recent] });
  egal(out.length, 1); egal(out[0].id, 'D-1'); egal(out[0].contact, '[purgé]'); egal(out[0].message, '[purgé]');
  egal(executer(WF_PURGE, 'Garde — Purger Demandes', { input: out }).length, 1);
});

test('EX-07', 'Réservations : le poids des participants est purgé à 30 jours, le nom du client conservé', () => {
  const r = { resa: 'R-1', date: iso(-45), client: 'Ana', contact: '@ana', participants: 'Ana 55 kg' };
  const out = executer(WF_PURGE, 'À purger — Réservations', { input: [r] });
  egal(out, [{ resa: 'R-1', participants: '[purgé]' }]);
});

test('EX-06', 'Journal chaîné : chaque ligne porte l\'empreinte de la précédente, la chaîne se vérifie', () => {
  const journal = [];
  for (const id of ['K-01', 'K-02', 'W-01']) journal.push(ecrireJournal(journal, [{ id }]));
  egal(journal[0].precedent, 'GENESE');
  egal(journal[1].precedent, journal[0].empreinte);
  vrai(verifierChaine(JOURNAL, journal).ok, 'la chaîne intacte doit être valide');
});

test('EX-06', 'Une ligne de Journal modifiée, supprimée ou insérée à la main est détectée', () => {
  const journal = [];
  for (const id of ['K-01', 'K-02', 'W-01', 'B-01']) journal.push(ecrireJournal(journal, [{ id }]));
  const modifie = journal.map((l, i) => i === 1 ? { ...l, validation: 'non requise' } : l);
  egal(verifierChaine(JOURNAL, modifie).ruptures.map(r => r.ligne), [3]);
  const supprime = journal.filter((_, i) => i !== 2);
  vrai(!verifierChaine(JOURNAL, supprime).ok, 'suppression non détectée');
  const insere = [...journal.slice(0, 2), { ...journal[1], execution: 'faux' }, ...journal.slice(2)];
  vrai(!verifierChaine(JOURNAL, insere).ok, 'insertion non détectée');
});
