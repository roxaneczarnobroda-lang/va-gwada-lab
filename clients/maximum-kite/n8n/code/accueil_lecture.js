// Node "Préparer la lecture IA" — mode : Run Once for All Items
// Précédé (par tools/build_n8n.py) de : const R = {...règles du JSON...} + accueil_regles.js
// Le formulaire simule un DM Instagram ou un email : on le remplacera par le vrai canal une fois le projet lancé.
const today = new Date(); today.setHours(12, 0, 0, 0);
const f = $('Message reçu').first().json;
const message = String(f['Message'] || '');
return [{ json: { body: { model: 'claude-haiku-5-5', max_tokens: 500, messages: [{ role: 'user', content: aPromptLecture(R, today, message) }] } } }];
