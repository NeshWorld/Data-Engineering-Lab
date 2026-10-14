# Contrats de la version 1.1
Tous les fichiers restent dans C:\Users\apapi\Data Engineering Lab. Référence avant modification : 52 tests réussis.

## Préférences
GET /api/preferences retourne {theme, diagrams:{ENV_ID:{positions:{TABLE:{x,y}},viewport:{x,y,scale}}}} dans l’enveloppe data habituelle.
POST /api/preferences accepte {theme?,diagram?:{env_id,positions?,viewport?,replace_positions?}}. Fusion atomique sous verrou dans settings/ui_preferences. Aucun autre réglage modifié.

## Thèmes
LabThemes.themes catalogue; apply(id); restoreCache(); render(selectedId); bind(container,{theme,onSelect}). Modules classiques chargés avant app.js. Couleurs centralisées dans themes.css. Tests CommonJS possibles.

## Éditeur
LabPythonEditor.createSession(initialText) retourne {attach(textarea):dispose}. Session conservée par document dans app.js. Événements input standard; historique et sélection fiables; composition IME préservée. Module CommonJS pour tests.

## ER
LabER.mount(container,{schema:tables,envId,layout,onSave}) retourne {destroy()}. onSave reçoit {env_id,positions,viewport,replace_positions?}. destroy vide les sauvegardes différées. Les positions sont les coins supérieurs gauches. PRAGMA table_xinfo fournit pk_ordinal, hidden et default; FK conserve id,seq,on_update,on_delete,match. Aucun lien déduit de noms ressemblants.

## Répartition
Orchestrateur: app.js,index.html, moteur/API/tests Python/documentation. Agent thèmes: themes.js,themes.css, substitutions de couleurs style.css,test_themes.cjs. Agent éditeur: python-editor.js,test_python_editor.cjs. Agent ER: er-diagram.js,er-diagram.css,test_er_diagram.cjs. Audit et QA indépendants en lecture seule.
