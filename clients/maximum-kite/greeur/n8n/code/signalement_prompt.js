// Node "Préparer la demande IA" — mode : Run Once for All Items
// Entrées : le formulaire, l'onglet Parc et l'onglet Dégâts lus juste avant.
const form = $('Formulaire dégât').first().json;
const parc = $('Lire Parc').all().map(i => i.json).filter(r => r.id);
const types = ['Déchirure toile', 'Boudin percé', 'Bride / ligne', 'Choc planche / délaminage', 'Foil (mât, fuselage, ailes)', 'Harnais (sangle, boucle)', 'Autre'];
const message = form["Ce qui s'est passé"] || '';

const prompt = `Tu es "Le Gréeur", l'agent qui tient le fichier matos d'une école de kitesurf et de wingfoil.
Un moniteur signale un dégât en langage courant. Associe-le à UNE pièce du parc et structure-le.

PARC (JSON) : ${JSON.stringify(parc.map(p => ({ id: p.id, designation: p.designation, achat: p.date_achat })))}
TYPES DE DÉGÂT AUTORISÉS : ${JSON.stringify(types)}
GRAVITÉS AUTORISÉES : ["Légère","Moyenne","Grave"]

Règles :
- "id" : l'ID de la pièce visée. S'il reste un doute, mets la plus probable et liste les autres dans "candidats".
- "immobiliser" : true si la pièce ne doit pas ressortir avant réparation (sécurité, prise d'eau, structure, boudin percé, toile très déchirée, boucle de harnais cassée).
- "description" : reformulation courte et factuelle, en français.
- "question" : une question courte à poser au moniteur s'il manque une info importante, sinon "".
- N'invente aucun prix.
Réponds UNIQUEMENT avec un objet JSON : {"id":"...","candidats":["..."],"type":"...","gravite":"...","immobiliser":true,"description":"...","question":""}

MESSAGE DU MONITEUR : """${message}"""`;

// Modèle et endpoint : manifeste du client (gouvernance.json), via corpsIA de tools/garde.js.
return [{ json: { body: corpsIA(prompt) } }];
