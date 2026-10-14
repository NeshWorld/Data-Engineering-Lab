'use strict';
const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const quoteName = value => '"' + String(value).replace(/"/g, '""') + '"';
const pages = {home:['Accueil','⌂'],sql:['Atelier SQL','⌘'],python:['Atelier Python','>_'],pipeline:['Pipelines','⇢'],explorer:['Explorateur','▦'],observability:['Observabilité','◷'],environments:['Environnements','◈']};
const kinds = {commerce:'E-commerce',logistics:'Logistique',events:'Événements',imperfect:'Données imparfaites'};
const state = {environments:[],artifacts:[],runs:[],schema:[],env:'',page:'home',drafts:{sql:'',python:'',pipeline:'{\n  "name": "Mon pipeline",\n  "steps": []\n}'},artifact:{},names:{sql:'Ma requête',python:'Mon script',pipeline:'Mon pipeline'},results:{},activeRuns:{},explorerTable:'',selectedRun:'',python_ack:false};
let refreshSequence = 0;
let toastTimer;
let pipelineTimer;
async function api(path, body) {
  let response;
  try { response = await fetch(path, body === undefined ? {cache:'no-store'} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); }
  catch { throw new Error('Le serveur local est inaccessible. Vérifiez que le laboratoire est démarré, puis actualisez.'); }
  let json;
  try { json = await response.json(); } catch { throw new Error('Le serveur a renvoyé une réponse illisible.'); }
  if (!response.ok || !json.ok) throw new Error(json.error || `Erreur du serveur (${response.status}).`);
  return json.data;
}
function notify(message, error = false) { clearTimeout(toastTimer); $('#notifications').innerHTML = `<div class="toast${error?' error':''}" role="${error?'alert':'status'}">${esc(message)}</div>`; toastTimer = setTimeout(() => $('#notifications').replaceChildren(), 7000); }
function confirmAction(title, description, action = 'Confirmer') { return new Promise(resolve => { const dialog = $('#confirmation'); $('#confirm-title').textContent = title; $('#confirm-description').textContent = description; $('#confirm-accept').textContent = action; dialog.returnValue = ''; dialog.addEventListener('close', () => resolve(dialog.returnValue === 'accept'), {once:true}); dialog.showModal(); }); }
async function busy(button, task) { if (button?.disabled) return; if(button) {button.disabled=true;button.classList.add('loading');button.setAttribute('aria-busy','true');} try {return await task();} catch(error) {notify(error.message,true);return undefined;} finally {if(button?.isConnected){const kind=button.id?.replace('run-','');button.disabled=Boolean(state.activeRuns[kind]?.status==='running');button.classList.remove('loading');button.removeAttribute('aria-busy');}} }
function empty(message, symbol = '◇') {return `<div class="empty"><span class="empty-symbol" aria-hidden="true">${symbol}</span>${message}</div>`;}
function heading(title, description, actions = '') {return `<div class="page-heading"><div><div class="eyebrow">DATA ENGINEERING LAB</div><h1>${title}</h1><p>${description}</p></div>${actions?`<div class="heading-actions">${actions}</div>`:''}</div>`;}
function badge(status) {const labels={success:'Réussi',error:'Erreur',running:'En cours',cancelled:'Annulé',pending:'En attente',skipped:'Ignoré'};return `<span class="badge ${esc(status)}">${esc(labels[status] || status)}</span>`;}
function date(value) {if(!value)return '—';let d = new Date(typeof value === 'number' && value < 1e12 ? value*1000 : value);return Number.isNaN(d.valueOf())?esc(value):d.toLocaleString('fr-FR');}
function duration(value) {return value == null?'—':Number(value)<1000?`${Math.round(Number(value))} ms`:`${(Number(value)/1000).toFixed(2)} s`;}
function environment() {return state.environments.find(e => e.id === state.env);}
function requireEnvironment() {if(!state.env) {notify('Créez et sélectionnez un environnement pour commencer.',true);return false;}return true;}
function envNeeded() {return empty('Aucun environnement disponible. <a href="#environments">Créer un environnement</a> pour travailler sur vos données fictives.');}
async function refreshState(renderAfter = true) {
  const token = ++refreshSequence;
  const fresh = await api('/api/state');
  if(token !== refreshSequence)return;
  Object.assign(state, {environments:fresh.environments || [],artifacts:fresh.artifacts || [],runs:fresh.runs || [],python_ack:fresh.python_ack,root:fresh.root,python:fresh.python,pandas:fresh.pandas});
  if(!state.environments.some(e => e.id === state.env))state.env = state.environments.find(e=>e.kind==='commerce')?.id || state.environments[0]?.id || '';
  const select = $('#active-environment');
  select.innerHTML = state.environments.length?state.environments.map(e=>`<option value="${esc(e.id)}">${esc(e.name)}</option>`).join(''):'<option value="">Aucun environnement</option>';
  select.value=state.env;
  $('#connection-status').innerHTML='<span class="local-dot"></span> Laboratoire connecté · données locales';
  if(state.env) {const schema=await api('/api/schema?env_id='+encodeURIComponent(state.env));if(token !== refreshSequence)return;state.schema=schema.tables || [];}else state.schema=[];
  if(renderAfter)render();
}
function render() {
  state.page=pages[location.hash.slice(1)]?location.hash.slice(1):'home';
  $('#current-page').textContent=pages[state.page][0];
  $('#navigation').innerHTML=Object.entries(pages).map(([id,[label,icon]])=>`<a href="#${id}" ${state.page===id?'class="active" aria-current="page"':''}><span class="nav-icon" aria-hidden="true">${icon}</span>${label}${id==='sql'?'<span class="nav-badge">SQL</span>':''}</a>`).join('');
  const builders={home:homeView,sql:sqlView,python:pythonView,pipeline:pipelineView,explorer:explorerView,observability:observabilityView,environments:environmentsView};
  $('#main').innerHTML=builders[state.page]();
  bindPage();
  bindInspector();
}
function homeView() {return `<section class="hero"><div><div class="eyebrow">VOTRE LABORATOIRE DE DONNÉES</div><h1>Expérimentez.<br>Comprenez. Recommencez.</h1><p>Un espace local pour explorer des données fictives, écrire du SQL et du Python, puis construire vos propres pipelines.</p><div class="actions"><a class="button primary" href="#${state.env?'sql':'environments'}">${state.env?'Ouvrir l’atelier SQL':'Créer mon environnement'} <span aria-hidden="true">↗</span></a><a class="button ghost" href="#explorer">Explorer les données</a></div></div><div class="hero-art" aria-label="Exemple de parcours de données"><div class="flow-line"><span class="flow-node">source.csv</span><span class="flow-arrow">→</span><span class="flow-node">Python</span></div><div class="flow-line"><span class="flow-node">Validation</span><span class="flow-arrow">→</span><span class="flow-node">SQLite</span></div><div class="flow-note">01 / EXTRAIRE &nbsp; 02 / TRANSFORMER &nbsp; 03 / CHARGER</div></div></section><div class="section-label">CHOISISSEZ VOTRE ATELIER</div><div class="cards">${[['sql','⌘','Interroger en SQL','Explorez le schéma, écrivez une requête et inspectez son résultat.','Écrire une requête'],['python','>_','Transformer en Python','Travaillez avec des fichiers CSV, JSON et une copie de votre base.','Ouvrir un script'],['pipeline','⇢','Assembler un pipeline','Reliez vos étapes, exécutez-les et suivez les données à chaque passage.','Construire un pipeline']].map(([page,icon,title,text,link])=>`<a class="card" href="#${page}"><div class="card-icon" aria-hidden="true">${icon}</div><h2>${title}</h2><p>${text}</p><span class="card-link">${link} &nbsp; ↗</span></a>`).join('')}</div><div class="stat-row"><div class="stat"><span>Environnements disponibles</span><strong>${state.environments.length}</strong></div><div class="stat"><span>Expériences sauvegardées</span><strong>${state.artifacts.length}</strong></div><div class="stat"><span>Exécutions enregistrées</span><strong>${state.runs.length}</strong></div></div><div class="section-label">DERNIÈRES EXÉCUTIONS</div><div class="panel">${runTable(state.runs.slice(0,5))}</div>`;}
function library(kind) {const options=state.artifacts.filter(a=>a.kind===kind);const selected=options.find(a=>a.id===state.artifact[kind]);return `<div class="library-bar"><label>Expérience sauvegardée<select id="artifact-select" aria-label="Expérience sauvegardée"><option value="">Nouvelle expérience</option>${options.map(a=>`<option value="${esc(a.id)}" ${state.artifact[kind]===a.id?'selected':''}>${esc(a.name)}</option>`).join('')}</select></label><label>Nom de l’expérience<input id="artifact-name" value="${esc(state.names[kind])}" maxlength="120"></label><button id="save-artifact" class="small">Sauvegarder</button></div>${selected?`<div class="artifact-path path">Fichier : ${esc(selected.path)}</div>`:""}`;}
function editor(kind, label, actions) {return `<div class="panel editor-panel">${library(kind)}<div class="toolbar"><span class="toolbar-title"><span class="tag">${kind==='pipeline'?'JSON':kind.toUpperCase()}</span>${label}</span><div class="actions">${actions}</div></div><div class="editor-wrap ${kind==='sql'?'highlighted':''}">${kind==='sql'?'<pre class="syntax-layer" aria-hidden="true"></pre>':''}<textarea id="code-editor" class="code-editor" aria-label="${kind==='sql'?'Éditeur SQL':kind==='python'?'Éditeur Python':'Définition JSON du pipeline'}" aria-describedby="editor-help" spellcheck="false" wrap="off" placeholder="${kind==='sql'?'-- Écrivez votre requête SQL ici':kind==='python'?'# Écrivez votre script Python ici':''}">${esc(state.drafts[kind])}</textarea><span class="editor-gutter" aria-hidden="true">1</span></div><div class="editor-footer"><span id="editor-help">Ctrl + Entrée : exécuter · Ctrl + S : sauvegarder · Échap puis Tab : quitter l’éditeur</span><span id="editor-position">Ln 1, Col 1</span></div></div>`;}
function schemaView() {if(!state.env)return envNeeded();return `<div class="panel"><div class="toolbar"><span class="toolbar-title">Schéma de la base</span><span class="tag">${state.schema.length} tables</span></div><div class="schema-list">${state.schema.length?state.schema.map(t=>`<details class="schema-table"><summary><span>${esc(t.name)}</span><span>${t.count??'—'} lignes</span></summary><div class="schema-columns">${(t.columns||[]).map(c=>`<div class="column-row"><span>${c.pk?'<span class="key">PK</span> ':''}${esc(c.name)}</span><span class="type">${esc(c.type || 'ANY')}${c.notnull?' · NN':''}</span></div>`).join('')}${(t.foreign_keys||[]).map(f=>`<div class="meta-line">↗ ${esc(f.from)} → ${esc(f.table)}.${esc(f.to)}</div>`).join('')}${(t.indexes||[]).map(i=>`<div class="meta-line">Index ${esc(i.name)}${i.unique?' · unique':''}</div>`).join('')}<button class="small ghost insert-table" data-table="${esc(t.name)}">Insérer un SELECT</button></div></details>`).join(''):empty('Aucune table dans cette base.')}</div></div><div class="notice">${esc(environment()?.name || '')}<br><span class="subtle">Les requêtes SQL modifient la base active. Python et les pipelines travaillent sur une copie.</span></div>`;}
function relationships() {const relationships=state.schema.flatMap(t=>(t.foreign_keys||[]).map(f=>({source:t.name,...f})));return `<div class="panel"><div class="toolbar"><span>Relations entre tables</span><span class="tag">Clés étrangères</span></div><div class="relationship-map">${relationships.length?relationships.map(f=>`<div class="relation-row"><span class="relation-node">${esc(f.source)}<br><span class="muted">${esc(f.from)}</span></span><span class="relation-arrow" aria-label="référence">──→</span><span class="relation-node">${esc(f.table)}<br><span class="muted">${esc(f.to)}</span></span></div>`).join(''):'<div class="empty-inline">Aucune clé étrangère déclarée dans ce schéma.</div>'}</div></div>`;}
function isTabularResult(result) {return result&&Array.isArray(result.columns)&&Array.isArray(result.rows);}
function resultTable(result) {if(!result)return empty('Votre résultat s’affichera ici après une exécution.','▦');if(result.error)return `<div class="panel-body"><div class="error-box" role="alert">${esc(result.error)}</div></div>`;const cols=result.columns||[];let rows=result.rows||[];return `${cols.length?`<div class="table-scroll"><table class="data-table"><thead><tr>${cols.map(c=>`<th scope="col">${esc(typeof c==='object'?c.name:c)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${cols.map((col,i)=>{const value=Array.isArray(row)?row[i]:row[typeof col==='object'?col.name:col];const text=value==null?'NULL':typeof value==='object'?JSON.stringify(value):String(value);return `<td${value==null?' class="cell-null"':''}><span class="cell-value" title="${esc(text)}">${esc(text)}</span></td>`;}).join('')}</tr>`).join('')}</tbody></table>${!rows.length?'<div class="empty-inline">La requête ne retourne aucune ligne.</div>':''}</div>`:empty('Instructions exécutées. Aucun résultat tabulaire.','✓')}<div class="result-meta">${result.row_count??rows.length} lignes · ${duration(result.duration_ms)}${result.changes!=null?` · ${result.changes} modifications`:''}${result.truncated?' · Affichage tronqué : '+rows.length+' lignes affichées':''}</div>`;}
function sqlView() {return heading('Atelier SQL','Écrivez, exécutez et inspectez vos requêtes sur la base active.')+(!state.env?envNeeded():`<div class="panel-grid"><div class="stack">${editor('sql','Éditeur de requêtes','<button class="primary small" id="run-sql">Exécuter ↗</button>')}<div class="panel"><div class="toolbar"><span>Résultat de la requête</span><span class="tag">SQLite</span></div><div id="sql-result">${resultTable(state.results.sql)}</div></div>${relationships()}<div class="panel"><div class="toolbar">Historique SQL</div>${runTable(state.runs.filter(r=>r.kind==='sql'&&r.env_id===state.env).slice(0,8))}</div></div><aside class="stack" aria-label="Schéma SQL">${schemaView()}</aside></div>`);}
function pythonView() {return heading('Atelier Python','Transformez des données et inspectez les sorties de votre script.')+(!state.env?envNeeded():`<div class="panel-grid"><div class="stack">${editor('python','Script Python','<button class="small danger" id="cancel-python" '+(state.activeRuns.python?.status!=='running'?'disabled':'')+'>Annuler</button><button class="primary small" id="run-python">Exécuter ↗</button>')}<div class="panel"><div class="toolbar"><span>Sorties de l’exécution</span><span class="tag">${esc(typeof state.python==='string'?state.python:'Python local')}</span></div><div id="python-output">${state.activeRuns.python?runDetail(state.activeRuns.python):empty('Lancez votre script pour afficher stdout, stderr et les fichiers de travail.','>_')}</div></div></div><aside class="stack"><div class="panel"><div class="toolbar">Votre espace Python</div><div class="panel-body"><h3>Une copie par exécution</h3><p class="subtle">La base et ses sources sont copiées dans un espace de travail conservé pour inspection.</p><div class="notice mono">LAB_DB<br>LAB_WORKSPACE<br>source.csv · source.json</div><p class="subtle">Lisez les chemins avec <code>os.environ</code>. La bibliothèque standard inclut sqlite3, csv et json.</p><p class="subtle">pandas : ${state.pandas?'disponible':'non installé (facultatif)'}</p></div></div><div class="notice warning">Python peut accéder aux fichiers et au réseau avec les droits de votre compte. Son exécution n’est pas une sandbox. N’exécutez que du code que vous comprenez.</div><div class="panel"><div class="toolbar">Historique Python</div>${runTable(state.runs.filter(r=>r.kind==='python'&&r.env_id===state.env).slice(0,5))}</div></aside></div>`);}
function pipelineDefinition() {const data=JSON.parse(state.drafts.pipeline);const definition=data;if(!definition||!Array.isArray(definition.steps))throw new Error('Le JSON doit contenir un tableau « steps ».');for(const step of definition.steps){if(!step||typeof step!=='object'||Array.isArray(step))throw new Error('Chaque étape doit être un objet JSON.');if(typeof step.id!=='string'||!step.id.trim())throw new Error('Chaque étape doit posséder un id.');if(!['csv','python','validate','load','sql','export'].includes(step.type))throw new Error('Type d’étape inconnu.');if(step.depends_on!==undefined&&(!Array.isArray(step.depends_on)||step.depends_on.some(id=>typeof id!=='string')))throw new Error('depends_on doit être un tableau d’identifiants.');}return definition;}
function pipelineSteps() {let definition;try{definition=pipelineDefinition();}catch(error){return `<div class="error-box">${esc(error.message)}</div>`;}return definition.steps.length?definition.steps.map((s,i)=>`<div class="step-item"><span class="step-number">${String(i+1).padStart(2,'0')}</span><div class="step-info"><strong>${esc(s.name || s.id)}</strong><small>${esc(s.type)} · ${s.depends_on?.length?'après '+esc(s.depends_on.join(', ')):'ordre du pipeline'}</small></div><div class="step-tools"><button class="small ghost run-step" data-index="${i}" title="Exécuter cette étape seule">Exécuter</button><button class="small danger remove-step" data-index="${i}" aria-label="Retirer ${esc(s.name || s.id)}">×</button></div></div>`).join(''):empty('Ajoutez une étape ou chargez l’exemple facultatif.','⇢');}
function pipelineView() {return heading('Pipelines','Composez vos étapes, contrôlez leurs dépendances et suivez chaque exécution.','<button id="pipeline-example" class="ghost">Charger un exemple</button>')+(!state.env?envNeeded():`<div class="panel-grid"><div class="stack">${editor('pipeline','Définition du pipeline','<button class="small danger" id="cancel-pipeline" '+(state.activeRuns.pipeline?.status!=='running'?'disabled':'')+'>Annuler</button><button class="primary small" id="run-pipeline">Exécuter le pipeline ↗</button>')}<div class="panel"><div class="toolbar"><span>Étapes</span><div class="actions"><select id="step-type" aria-label="Type de nouvelle étape">${['csv','python','validate','load','sql','export'].map(t=>`<option>${t}</option>`).join('')}</select><button id="add-step" class="small">Ajouter une étape</button></div></div><div class="step-list" id="pipeline-steps">${pipelineSteps()}</div></div><div class="panel"><div class="toolbar">Exécution du pipeline</div><div id="pipeline-output">${state.activeRuns.pipeline?runDetail(state.activeRuns.pipeline):empty('Vos résultats détaillés apparaîtront ici.','⇢')}</div></div></div><aside class="stack"><div class="panel"><div class="toolbar">Construire une étape</div><div class="panel-body"><p class="subtle">Modifiez le JSON directement. Chaque étape possède un <code>id</code>, un <code>type</code>, un <code>name</code> et des <code>depends_on</code>.</p><div class="meta-line"><b>csv</b> · lit source.csv</div><div class="meta-line"><b>python</b> · transforme et écrit result.csv</div><div class="meta-line"><b>validate</b> · contrôle min_rows</div><div class="meta-line"><b>load</b> · charge une table SQLite</div><div class="meta-line"><b>sql</b> · exécute une requête</div><div class="meta-line"><b>export</b> · écrit le résultat SQL en CSV</div><p class="subtle">Sans dépendances, l’ordre du tableau est utilisé. « Exécuter » lance l’étape seule dans un espace neuf.</p></div></div><div class="notice">La base active est copiée. Les fichiers et sorties de chaque exécution sont conservés.</div><div class="panel"><div class="toolbar">Historique des pipelines</div>${runTable(state.runs.filter(r=>r.kind==='pipeline'&&r.env_id===state.env).slice(0,6))}</div><a href="#observability" class="card-link">Comparer deux exécutions ↗</a></aside></div>`);}
function explorerView() {if(!state.schema.some(t=>t.name===state.explorerTable))state.explorerTable=state.schema[0]?.name || '';return heading('Explorateur','Parcourez les tables, filtrez leurs données et vérifiez leur qualité.')+(!state.env?envNeeded():`<div class="panel-grid"><div class="stack"><div class="panel"><form id="explorer-form" class="filter-bar"><label>Table<select id="explorer-table">${state.schema.map(t=>`<option value="${esc(t.name)}" ${t.name===state.explorerTable?'selected':''}>${esc(t.name)}</option>`).join('')}</select></label><label>Condition SQL (WHERE)<input id="explorer-filter" placeholder="Ex. colonne IS NULL" autocomplete="off"></label><label class="narrow">Limite<input id="explorer-limit" type="number" min="1" max="1000" value="100"></label><button class="primary" type="submit">Afficher</button></form><div id="explorer-query" class="result-meta mono">Sélectionnez une table et cliquez sur Afficher.</div><div id="explorer-result">${empty('Les données sont lues depuis votre base active.','▦')}</div></div>${relationships()}</div><aside class="panel"><div class="toolbar">Profil de la table</div><div id="table-profile" class="panel-body">${empty('Le profil affichera les valeurs nulles, distinctes et fréquentes.')}</div></aside></div>`);}
function runTable(runs) {if(!runs.length)return empty('Aucune exécution enregistrée pour le moment.','◷');return `<div class="table-scroll"><table><thead><tr><th>Expérience</th><th>État</th><th>Début</th><th>Durée</th><th>Lignes</th><th>Détails</th></tr></thead><tbody>${runs.map(r=>`<tr><td><span class="tag">${esc(r.kind?.toUpperCase())}</span><div class="subtle mono" title="${esc(r.id)}">${esc(String(r.id).slice(0,8))}</div></td><td>${badge(r.status)}</td><td>${date(r.started)}</td><td>${duration(r.duration_ms)}</td><td>${esc(r.row_count??'—')}</td><td><button class="small ghost inspect-run" data-run="${esc(r.id)}">Inspecter</button></td></tr>`).join('')}</tbody></table></div>`;}
function runDetail(run) {return `<div class="run-details"><div class="run-summary">${badge(run.status)}<span>${esc(run.kind || '')}</span><span>${duration(run.duration_ms)}</span><span>${esc(run.row_count??'—')} lignes</span><span>${esc(state.environments.find(e=>e.id===run.env_id)?.name || '')}</span></div>${run.error?`<div class="error-box bottom-gap" role="alert">${esc(run.error)}</div>`:''}${run.workspace?`<p class="path">Espace de travail : ${esc(run.workspace)}</p>`:''}${run.steps?.length?`<div class="table-scroll"><table><thead><tr><th>Étape</th><th>État</th><th>Durée</th><th>Entrée</th><th>Sortie</th></tr></thead><tbody>${run.steps.map(s=>`<tr><td>${esc(s.name || s.id)}<div class="subtle">${esc(s.type)}</div>${s.error?`<div class="error-box">${esc(s.error)}</div>`:''}${s.result?`<details><summary>Résultat</summary><pre class="terminal">${esc(JSON.stringify(s.result,null,2))}</pre></details>`:''}</td><td>${badge(s.status)}</td><td>${duration(s.duration_ms)}</td><td>${s.input_rows??'—'}</td><td>${s.output_rows??'—'}</td></tr>`).join('')}</tbody></table></div>`:''}<details open><summary>Sortie standard</summary><pre class="terminal">${esc(run.stdout || (run.status==='running'?'Exécution en cours…':'Aucune sortie standard.'))}</pre></details>${run.stderr?`<details open><summary>Erreurs et diagnostics</summary><pre class="terminal stderr">${esc(run.stderr)}</pre></details>`:''}${run.result?`<details open><summary>Résultat</summary>${isTabularResult(run.result)?resultTable(run.result):`<pre class="terminal">${esc(JSON.stringify(run.result,null,2))}</pre>`}</details>`:''}<div class="subtle mono">Run ${esc(run.id)}</div></div>`;}
function observabilityView() {const choices=state.runs.map(r=>`<option value="${esc(r.id)}">${esc(r.kind)} · ${date(r.started)} · ${esc(r.status)} · ${esc(String(r.id).slice(0,8))}</option>`).join('');return heading('Observabilité','Inspectez les sorties, les erreurs et les écarts entre vos exécutions.','<button id="refresh-runs">Actualiser l’historique</button>')+`<div class="panel bottom-gap"><div class="toolbar"><span>Historique des exécutions</span><span class="tag">${state.runs.length} exécutions</span></div>${runTable(state.runs)}</div><div class="panel bottom-gap"><div class="toolbar">Comparer deux exécutions</div><div class="filter-bar"><label>Exécution A<select id="compare-a"><option value="">Choisir une exécution</option>${choices}</select></label><label>Exécution B<select id="compare-b"><option value="">Choisir une exécution</option>${choices}</select></label><button id="compare-runs">Comparer</button></div><div id="comparison">${empty('Sélectionnez deux exécutions pour comparer leurs métriques et sorties.')}</div></div><div class="panel"><div class="toolbar">Détails d’une exécution</div><div id="run-inspector">${state.selectedRun?'<div class="empty-inline">Chargement de l’exécution…</div>':empty('Cliquez sur Inspecter dans l’historique.')}</div></div>`;}
function environmentsView() {return heading('Environnements','Créez des jeux de données fictifs reproductibles et conservez leurs états.')+`<div class="split-equal"><section class="panel"><div class="toolbar">Créer un environnement</div><form id="create-environment" class="panel-body form-grid"><label class="full">Nom<input name="name" required maxlength="100" placeholder="Ex. Commerce — essai 01"></label><label class="full">Jeu de données<select name="kind">${Object.entries(kinds).map(([key,label])=>`<option value="${key}">${label}</option>`).join('')}</select></label><label>Graine aléatoire<input name="seed" type="number" min="0" max="2147483647" value="42" required></label><label>Taille du jeu<input name="size" type="number" min="0" max="10000" value="100" required></label><label class="check-label full"><input name="anomalies" type="checkbox"> Inclure des anomalies pour tester la qualité des données</label><p class="subtle full">La même graine et les mêmes paramètres produisent les mêmes données. Les fichiers CSV et JSON sont générés avec la base.</p><div class="full"><button type="submit" class="primary">Créer l’environnement</button></div></form></section><section><h2>Vos environnements <span class="tag">${state.environments.length}</span></h2>${state.environments.length?state.environments.map(e=>`<article class="environment-card ${e.id===state.env?'active-env':''}"><h3>${esc(e.name)}${e.id===state.env?'<span class="tag">Actif</span>':`<button class="small choose-env" data-env="${esc(e.id)}">Sélectionner</button>`}</h3><p>${esc(kinds[e.kind] || e.kind)} · graine ${e.seed} · taille ${e.size} · ${e.anomalies?'avec anomalies':'sans anomalies'}</p>${e.stats?.anomalies?.length?`<details class="anomaly-details"><summary>Anomalies présentes (${e.stats.anomalies.length})</summary><ul>${e.stats.anomalies.map(a=>`<li>${esc(a)}</li>`).join('')}</ul></details>`:''}<div class="actions"><button class="small reset-env" data-env="${esc(e.id)}">Réinitialiser</button><button class="small anomaly-env" data-env="${esc(e.id)}">${e.anomalies?'Retirer':'Injecter'} les anomalies</button><button class="small snapshot-env" data-env="${esc(e.id)}">Créer un snapshot</button></div><div class="snapshot-list"><label>Snapshot à restaurer<select class="snapshot-select" data-env="${esc(e.id)}"><option value="">Chargement…</option></select></label><button class="small restore-env" data-env="${esc(e.id)}">Restaurer</button></div><p class="path">${esc(e.db_path)}</p></article>`).join(''):empty('Créez votre premier environnement à gauche.')}</section></div>`;}
function refreshRunHistory(kind) {
  const title=kind==='python'?'Historique Python':'Historique des pipelines';
  const panel=$$('.panel').find(node=>$('.toolbar',node)?.textContent.trim()===title);
  if(!panel)return;
  panel.innerHTML=`<div class="toolbar">${title}</div>${runTable(state.runs.filter(run=>run.kind===kind&&run.env_id===state.env).slice(0,kind==='python'?5:6))}`;
  $$('.inspect-run',panel).forEach(button=>button.addEventListener('click',()=>{state.selectedRun=button.dataset.run;if(state.page!=='observability')location.hash='observability';else inspectRun(state.selectedRun);}));
}
function bindInspector() {
  const grid=$('.panel-grid'),side=grid?.querySelector(':scope > aside');
  if(!grid||!side)return;
  const heading=$('.page-heading');
  let actions=$('.heading-actions',heading);
  if(!actions){actions=document.createElement('div');actions.className='heading-actions';heading.append(actions);}
  const button=document.createElement('button');button.className='small ghost';button.id='toggle-inspector';
  const update=()=>{const visible=state.inspectorVisible!==false;grid.classList.toggle('inspector-hidden',!visible);button.textContent=visible?'Masquer le panneau latéral':'Afficher le panneau latéral';button.setAttribute('aria-expanded',String(visible));};
  button.addEventListener('click',()=>{state.inspectorVisible=state.inspectorVisible===false;update();});actions.append(button);update();
}
function bindPage() {
  $$('.inspect-run').forEach(button=>button.addEventListener('click',()=>{state.selectedRun=button.dataset.run;if(state.page!=='observability')location.hash='observability';else inspectRun(state.selectedRun);}));
  if(['sql','python','pipeline'].includes(state.page) && $('#code-editor'))bindEditor(state.page);
  if(state.page==='sql') {
    $('#run-sql')?.addEventListener('click', event=>busy(event.currentTarget,executeSQL));
    $$('.insert-table').forEach(button=>button.addEventListener('click',()=>{const editor=$('#code-editor');const insertion=`SELECT * FROM ${quoteName(button.dataset.table)} LIMIT 100;`;editor.setRangeText(insertion,editor.selectionStart,editor.selectionEnd,'end');editor.dispatchEvent(new Event('input'));editor.focus();}));
  }
  if(state.page==='python') {
    $('#run-python')?.addEventListener('click',event=>busy(event.currentTarget,executePython));
    $('#cancel-python')?.addEventListener('click',event=>busy(event.currentTarget,()=>cancelRun('python')));
  }
  if(state.page==='pipeline') {
    $('#pipeline-example')?.addEventListener('click',()=>busy($('#pipeline-example'),loadPipelineExample));
    $('#run-pipeline')?.addEventListener('click',event=>busy(event.currentTarget,()=>executePipeline()));
    $('#cancel-pipeline')?.addEventListener('click',event=>busy(event.currentTarget,()=>cancelRun('pipeline')));
    $('#add-step')?.addEventListener('click',addPipelineStep);
    bindPipelineSteps();
  }
  if(state.page==='explorer') {
    $('#explorer-form')?.addEventListener('submit',event=>{event.preventDefault();explore().catch(error=>notify(error.message,true));});
    $('#explorer-table')?.addEventListener('change',()=>{state.explorerTable=$('#explorer-table').value;$('#explorer-filter').value='';explore().catch(error=>notify(error.message,true));});
    if(state.explorerTable)explore().catch(error=>notify(error.message,true));
  }
  if(state.page==='observability') {
    $('#refresh-runs').addEventListener('click',event=>busy(event.currentTarget,()=>refreshState()));
    $('#compare-runs').addEventListener('click',event=>busy(event.currentTarget,compareRuns));
    if(state.selectedRun)inspectRun(state.selectedRun);
  }
  if(state.page==='environments')bindEnvironments();
}
function bindEditor(kind) {
  const editor=$('#code-editor');
  const update = () => {
    state.drafts[kind]=editor.value;
    $('.editor-gutter').textContent=editor.value.split('\n').map((_,index)=>index+1).join('\n');
    if(kind==='sql') {
      const pattern=/(--[^\n]*|\/\*[\s\S]*?\*\/|'(?:''|[^'])*'|"(?:""|[^"])*"|\b(?:SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AS|GROUP|BY|ORDER|HAVING|LIMIT|OFFSET|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|TABLE|DROP|ALTER|INDEX|PRIMARY|KEY|FOREIGN|REFERENCES|NOT|NULL|AND|OR|IS|IN|LIKE|DISTINCT|COUNT|SUM|AVG|MIN|MAX|CASE|WHEN|THEN|ELSE|END|WITH|UNION|ALL|ASC|DESC|BEGIN|COMMIT|ROLLBACK)\b|\b\d+(?:\.\d+)?\b)/gi;
      let output='',last=0;
      for(const match of editor.value.matchAll(pattern)){output+=esc(editor.value.slice(last,match.index));const token=match[0];let type=/^(--|\/\*)/.test(token)?'comment':/^["']/.test(token)?'str':/^\d/.test(token)?'num':'kw';output+=`<span class="${type}">${esc(token)}</span>`;last=match.index+token.length;}
      $('.syntax-layer').innerHTML=output+esc(editor.value.slice(last))+'\n';
    }
    const line=editor.value.slice(0,editor.selectionStart).split('\n');
    $('#editor-position').textContent=`Ln ${line.length}, Col ${line.at(-1).length+1}`;
    if(kind==='pipeline'){clearTimeout(pipelineTimer);pipelineTimer=setTimeout(updatePipelineSteps,350);}
  };
  editor.addEventListener('input',update);
  editor.addEventListener('click',update);
  editor.addEventListener('keyup',update);
  editor.addEventListener('scroll',()=>{const gutter=$('.editor-gutter');if(gutter)gutter.style.transform='translateY(-'+editor.scrollTop+'px)';const layer=$('.syntax-layer');if(layer){layer.scrollTop=editor.scrollTop;layer.scrollLeft=editor.scrollLeft;}});
  editor.addEventListener('keydown',event=>{
    if(event.key==='Escape'){editor.dataset.tabEscape='true';return;}
    if(event.key==='Tab'&&(event.shiftKey||editor.dataset.tabEscape)){delete editor.dataset.tabEscape;return;}
    if(event.key==='Tab'){event.preventDefault();editor.setRangeText('    ',editor.selectionStart,editor.selectionEnd,'end');update();}
  });
  $('#artifact-name').addEventListener('input',()=>state.names[kind]=$('#artifact-name').value);
  $('#save-artifact').addEventListener('click',event=>busy(event.currentTarget,()=>saveArtifact(kind)));
  $('#artifact-select').addEventListener('change',async()=>{
    const id=$('#artifact-select').value;
    const artifact=state.artifacts.find(a=>a.id===id);
    const nextCode=artifact?.code || (kind==='pipeline'?'{\n  "name": "Mon pipeline",\n  "steps": []\n}':'');
    const baseline=state.artifacts.find(a=>a.id===state.artifact[kind]);
    let isDirty=baseline?baseline.code!==state.drafts[kind]||baseline.name!==state.names[kind]:Boolean(state.drafts[kind].trim());
    if(!baseline&&kind==='pipeline'){try{isDirty=pipelineDefinition().steps.length>0;}catch{isDirty=true;}}
    if(isDirty && state.drafts[kind]!==nextCode && !await confirmAction('Ouvrir une autre expérience ?','Le contenu actuel de l’éditeur sera remplacé. Sauvegardez-le avant de poursuivre si vous souhaitez le conserver.','Ouvrir')) {$('#artifact-select').value=state.artifact[kind] || '';return;}
    state.artifact[kind]=id;state.drafts[kind]=nextCode;state.names[kind]=artifact?.name || ({sql:'Ma requête',python:'Mon script',pipeline:'Mon pipeline'}[kind]);
    render();
    if(artifact && artifact.env_id!==state.env)notify('Expérience ouverte. Elle sera exécutée sur l’environnement actuellement sélectionné.');
  });
  update();
  if(state.activeRuns[kind]?.status==='running')setRunControls(kind,true);
}
async function saveArtifact(kind) {
  if(!requireEnvironment())return;
  const name=state.names[kind].trim();if(!name)throw new Error('Donnez un nom à votre expérience.');
  if(kind==='pipeline')pipelineDefinition();
  const saved=await api('/api/artifact',{id:state.artifact[kind] || undefined,name,kind,code:state.drafts[kind],env_id:state.env});
  state.artifact[kind]=saved.id;
  await refreshState(false);render();notify('Expérience sauvegardée dans le projet.');
}
async function executeSQL() {
  if(!requireEnvironment())return;
  if(!state.drafts.sql.trim())throw new Error('Écrivez une requête avant de l’exécuter.');
  const sqlEnv=state.env;
  $('#sql-result').innerHTML=empty('Exécution de votre requête…');
  try {const result=await api('/api/sql',{env_id:sqlEnv,code:state.drafts.sql});if(state.env!==sqlEnv){await refreshState(false);return;}state.results.sql=result;if(state.page==='sql')$('#sql-result').innerHTML=resultTable(result);await refreshState(false);if(state.page==='sql')render();}
  catch(error){if(state.env!==sqlEnv)throw error;state.results.sql={error:error.message};if(state.page==='sql')$('#sql-result').innerHTML=resultTable(state.results.sql);throw error;}
}
async function acknowledgePython() {
  if(state.python_ack)return true;
  const accepted=await confirmAction('Autoriser l’exécution de Python ?','Le code Python s’exécute avec les droits de votre compte. Il peut lire ou modifier des fichiers et accéder au réseau. La base du laboratoire est copiée, mais ce processus n’est pas une sandbox. N’exécutez que du code que vous comprenez et dont vous connaissez la provenance.','J’accepte et j’exécute');
  if(!accepted)return false;
  await api('/api/python_ack',{accepted:true});state.python_ack=true;return true;
}
function setRunControls(kind,running) {const run=$('#run-'+kind),cancel=$('#cancel-'+kind);if(run){run.disabled=running;run.setAttribute('aria-busy',String(running));}if(cancel)cancel.disabled=!running;}
async function executePython() {
  if(state.activeRuns.python?.status==='running')throw new Error('Un script Python est déjà en cours.');
  if(!requireEnvironment())return;
  if(!state.drafts.python.trim())throw new Error('Écrivez un script avant de l’exécuter.');
  if(!await acknowledgePython())return;
  const result=await api('/api/python',{env_id:state.env,code:state.drafts.python,timeout:30});
  state.activeRuns.python={id:result.run_id,kind:'python',status:'running',env_id:state.env};
  setRunControls('python',true);$('#python-output').innerHTML=runDetail(state.activeRuns.python);pollRun('python',result.run_id);
}
async function executePipeline(onlyStep) {
  if(state.activeRuns.pipeline?.status==='running')throw new Error('Un pipeline est déjà en cours.');
  if(!requireEnvironment())return;
  const definition=pipelineDefinition();
  const steps=onlyStep?[{...definition.steps[Number(onlyStep.dataset.index)],depends_on:[]}]:definition.steps;
  if(!steps.length)throw new Error('Ajoutez au moins une étape au pipeline.');
  if(steps.some(s=>s.type==='python')&&!await acknowledgePython())return;
  const result=await api('/api/pipeline',{env_id:state.env,name:definition.name || state.names.pipeline,steps});
  state.activeRuns.pipeline={id:result.run_id,kind:'pipeline',status:'running',env_id:state.env};
  setRunControls('pipeline',true);$('#pipeline-output').innerHTML=runDetail(state.activeRuns.pipeline);pollRun('pipeline',result.run_id);
}
async function pollRun(kind,id) {
  try {
    const run=await api('/api/runs?id='+encodeURIComponent(id));
    if(state.activeRuns[kind]?.id!==id)return;
    state.activeRuns[kind]=run;
    const output=$('#'+kind+'-output');if(output)output.innerHTML=runDetail(run);
    if(run.status==='running') {setRunControls(kind,true);setTimeout(()=>pollRun(kind,id),600);}
    else {setRunControls(kind,false);await refreshState(false);refreshRunHistory(kind);notify(run.status==='success'?'Exécution terminée.':run.status==='cancelled'?'Exécution annulée.':'L’exécution a échoué. Consultez les diagnostics.',run.status==='error');}
  } catch(error) {setRunControls(kind,false);notify(error.message,true);}
}
async function cancelRun(kind) {const run=state.activeRuns[kind];if(!run||run.status!=='running')return;await api('/api/cancel',{run_id:run.id});notify('Annulation demandée.');}
function updatePipelineSteps() {const container=$('#pipeline-steps');if(container){container.innerHTML=pipelineSteps();bindPipelineSteps();}}
function bindPipelineSteps() {
  $$('.remove-step').forEach(button=>button.addEventListener('click',()=>{try{const data=pipelineDefinition();const [removed]=data.steps.splice(Number(button.dataset.index),1);data.steps.forEach(s=>s.depends_on=(s.depends_on||[]).filter(id=>id!==removed.id));setPipelineDraft(data);}catch(error){notify(error.message,true);}}));
  $$('.run-step').forEach(button=>button.addEventListener('click',()=>busy(button,()=>executePipeline(button))));
}
function setPipelineDraft(data) {state.drafts.pipeline=JSON.stringify(data,null,2);const editor=$('#code-editor');if(editor){editor.value=state.drafts.pipeline;editor.dispatchEvent(new Event('input'));}updatePipelineSteps();}
function addPipelineStep() {try{const data=pipelineDefinition(),type=$('#step-type').value;let number=data.steps.length+1;while(data.steps.some(s=>s.id==='step_'+number))number++;const step={id:'step_'+number,name:`Étape ${number} — ${type}`,type,depends_on:[]};if(type==='csv')step.path='source.csv';if(type==='python')step.code='# Écrivez votre transformation ici.\n# Le résultat CSV doit être écrit dans LAB_WORKSPACE/result.csv.\n';if(type==='validate')step.min_rows=1;if(type==='load')step.table='pipeline_output';if(type==='sql')step.code='';data.steps.push(step);setPipelineDraft(data);}catch(error){notify(error.message,true);}}
async function loadPipelineExample() {
  if(!requireEnvironment())return;
  let current;try{current=pipelineDefinition();}catch{current={steps:[{}]};}
  if(current.steps.length&&!await confirmAction('Charger l’exemple ?','Le JSON actuel sera remplacé par un exemple modifiable. Rien ne sera exécuté ni sauvegardé automatiquement.','Charger l’exemple'))return;
  const transform='import os, csv\nfrom pathlib import Path\nworkspace = Path(os.environ["LAB_WORKSPACE"])\nwith (workspace / "source.csv").open(newline="", encoding="utf-8") as source:\n    rows = list(csv.DictReader(source))\nif not rows:\n    raise ValueError("La source est vide")\nwith (workspace / "result.csv").open("w", newline="", encoding="utf-8") as target:\n    writer = csv.DictWriter(target, fieldnames=list(rows[0]))\n    writer.writeheader()\n    writer.writerows(rows)\nprint(f"{len(rows)} lignes copiées")\n';
  state.names.pipeline='Exemple CSV vers SQLite';$('#artifact-name').value=state.names.pipeline;state.artifact.pipeline='';$('#artifact-select').value='';
  setPipelineDraft({name:'Exemple CSV vers SQLite',steps:[{id:'read',name:'Lire le CSV',type:'csv',path:'source.csv',depends_on:[]},{id:'transform',name:'Copier les lignes avec Python',type:'python',code:transform,depends_on:['read']},{id:'validate',name:'Vérifier la présence de données',type:'validate',min_rows:1,depends_on:['transform']},{id:'load',name:'Charger dans SQLite',type:'load',table:'pipeline_output',depends_on:['validate']},{id:'query',name:'Lire la table chargée',type:'sql',code:'SELECT * FROM "pipeline_output" LIMIT 100;',depends_on:['load']}]});
  notify('Exemple chargé dans l’éditeur. Modifiez-le avant de l’exécuter.');
}
async function explore() {
  const sequence=state.explorerSequence=(state.explorerSequence||0)+1;
  const button=$('#explorer-form button');
  if(button){button.disabled=true;button.classList.add('loading');}
  try {
  if(!requireEnvironment())return;
  const table=$('#explorer-table').value;if(!table)return;
  const env=state.env,filter=$('#explorer-filter').value.trim(),limit=Math.max(1,Math.min(1000,Number($('#explorer-limit').value)||100));
  state.explorerTable=table;
  const code=`SELECT * FROM ${quoteName(table)}${filter?' WHERE '+filter:''} LIMIT ${limit};`;
  $('#explorer-query').textContent=code;
  $('#explorer-result').innerHTML=empty('Lecture de la table…');$('#table-profile').innerHTML='<div class="empty-inline">Analyse des colonnes…</div>';
  const settled=await Promise.allSettled([api('/api/sql',{env_id:env,code,read_only:true}),api('/api/profile?env_id='+encodeURIComponent(env)+'&table='+encodeURIComponent(table))]);
  if(sequence!==state.explorerSequence||state.page!=='explorer'||state.env!==env||state.explorerTable!==table)return;
  const [result,profile]=settled;
  $('#explorer-result').innerHTML=result.status==='fulfilled'?resultTable(result.value):resultTable({error:result.reason.message});
  $('#table-profile').innerHTML=profile.status==='fulfilled'?profileView(profile.value):`<div class="error-box">${esc(profile.reason.message)}</div>`;
  await refreshState(false);
  } finally {if(sequence===state.explorerSequence&&button?.isConnected){button.disabled=false;button.classList.remove('loading');}}
}
function profileView(profile) {return `<p class="subtle">${profile.count} lignes dans la table entière.<br>Le profil ne tient pas compte du filtre WHERE.</p><div class="profile-columns">${(profile.columns||[]).map(c=>`<div class="profile-column"><h3>${esc(c.name)} <span class="muted">${esc(c.type)}</span></h3><p>${c.nulls} nulles · ${c.distinct} valeurs distinctes</p><p>Min : ${esc(c.min ?? '—')}<br>Max : ${esc(c.max ?? '—')}</p><details><summary class="subtle">Valeurs fréquentes</summary>${(c.top||[]).map(t=>`<div class="meta-line">${esc(t.value??'NULL')} <span class="muted">(${t.count})</span></div>`).join('')}</details></div>`).join('')}</div>`;}
async function inspectRun(id) {try{const run=await api('/api/runs?id='+encodeURIComponent(id));if(state.page==='observability'&&state.selectedRun===id)$('#run-inspector').innerHTML=runDetail(run);}catch(error){if($('#run-inspector'))$('#run-inspector').innerHTML=`<div class="panel-body"><div class="error-box">${esc(error.message)}</div></div>`;}}
function comparisonValue(value) {
  if(Array.isArray(value))return '['+value.map(comparisonValue).join(',')+']';
  if(value&&typeof value==='object')return '{'+Object.keys(value).sort().map(key=>JSON.stringify(key)+':'+comparisonValue(value[key])).join(',')+'}';
  return JSON.stringify(value);
}
function compareResults(first,second) {
  const a=first.result,b=second.result;
  const tabularA=a&&Array.isArray(a.columns)&&Array.isArray(a.rows);
  const tabularB=b&&Array.isArray(b.columns)&&Array.isArray(b.rows);
  const dataOnly=result=>result&&Array.isArray(result.columns)?{columns:result.columns,rows:result.rows,row_count:result.row_count,truncated:result.truncated}:result;
  const equal=comparisonValue(dataOnly(a))===comparisonValue(dataOnly(b));
  let summary=a==null&&b==null?'Aucune sortie de données enregistrée pour ces exécutions.':equal?'Les résultats de données sont identiques.':'Les résultats de données diffèrent.';
  if(tabularA&&tabularB){
    const names=result=>result.columns.map(column=>typeof column==='object'?column.name:column);
    const colsA=names(a),colsB=names(b);
    const normalizeRow=(row,columns)=>Array.isArray(row)?row:columns.map(name=>row[name]);
    const common=Math.min(a.rows.length,b.rows.length);
    let modified=0;
    for(let index=0;index<common;index++)if(comparisonValue(normalizeRow(a.rows[index],colsA))!==comparisonValue(normalizeRow(b.rows[index],colsB)))modified++;
    summary+=' Colonnes : '+(comparisonValue(colsA)===comparisonValue(colsB)?'identiques.':'différentes.');
    summary+=' Lignes affichées comparées par position : '+modified+' modifiées, '+Math.max(0,b.rows.length-a.rows.length)+' ajoutées, '+Math.max(0,a.rows.length-b.rows.length)+' retirées.';
    if(a.truncated||b.truncated)summary+=' La comparaison porte sur les lignes affichées ; au moins un résultat est tronqué.';
  }
  const display=result=>result==null?empty('Aucun résultat de données enregistré.'):isTabularResult(result)?resultTable(result):`<pre class="terminal">${esc(JSON.stringify(result,null,2))}</pre>`;
  return `<section class="panel-body"><h3>Résultats de données A / B</h3><div class="notice bottom-gap">${esc(summary)}</div><div class="compare-grid"><div class="panel"><div class="toolbar">Résultat A</div>${display(a)}</div><div class="panel"><div class="toolbar">Résultat B</div>${display(b)}</div></div></section>`;
}
async function compareRuns() {
  const a=$('#compare-a').value,b=$('#compare-b').value;if(!a||!b)throw new Error('Choisissez deux exécutions.');if(a===b)throw new Error('Choisissez deux exécutions différentes.');
  const [first,second]=await Promise.all([api('/api/runs?id='+encodeURIComponent(a)),api('/api/runs?id='+encodeURIComponent(b))]);
  if(state.page!=='observability')return;
  const metrics=[['Type',first.kind,second.kind],['État',first.status,second.status],['Durée',duration(first.duration_ms),duration(second.duration_ms)],['Lignes',first.row_count??'—',second.row_count??'—'],['Étapes',first.steps?.length || 0,second.steps?.length || 0]];
  $('#comparison').innerHTML=`<div class="table-scroll"><table><thead><tr><th>Métrique</th><th>Exécution A</th><th>Exécution B</th></tr></thead><tbody>${metrics.map(([name,a,b])=>`<tr><td>${name}</td><td>${esc(a)}</td><td>${esc(b)}</td></tr>`).join('')}</tbody></table></div><div class="panel-body"><div class="notice bottom-gap">${first.stdout===second.stdout?'Les sorties standard sont identiques.':'Les sorties standard diffèrent.'} ${first.error===second.error?'Les erreurs sont identiques.':'Les erreurs diffèrent.'}</div><div class="compare-grid">${[first,second].map((r,i)=>`<section><h3>Exécution ${i?'B':'A'} · ${badge(r.status)}</h3><pre class="terminal">${esc(r.stdout || 'Aucune sortie standard.')}</pre>${r.error||r.stderr?`<pre class="terminal stderr">${esc(r.error || '')}\n${esc(r.stderr || '')}</pre>`:''}${r.steps?.length?`<p class="subtle">Étapes : ${r.steps.map(s=>esc(s.name || s.id)+' ('+esc(s.status)+', '+duration(s.duration_ms)+')').join(' → ')}</p>`:''}</section>`).join('')}</div></div>`;
  $('#comparison').insertAdjacentHTML('beforeend',compareResults(first,second));
}
function bindEnvironments() {
  $('#create-environment').addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;busy($('button[type="submit"]',form),async()=>{const data=new FormData(form);const env=await api('/api/environment',{name:String(data.get('name')).trim(),kind:data.get('kind'),seed:Number(data.get('seed')),size:Number(data.get('size')),anomalies:data.has('anomalies')});state.env=env.id;await refreshState();notify('Environnement créé et sélectionné.');});});
  $$('.choose-env').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{state.env=button.dataset.env;await refreshState();})));
  $$('.reset-env').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{const env=state.environments.find(e=>e.id===button.dataset.env);if(!await confirmAction('Réinitialiser « '+env.name+' » ?','La base sera régénérée avec la même graine et sans anomalies. Les modifications des données seront perdues. Vos scripts et l’historique seront conservés.','Réinitialiser'))return;await api('/api/reset',{env_id:env.id});await refreshState();notify('Environnement réinitialisé.');})));
  $$('.anomaly-env').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{const env=state.environments.find(e=>e.id===button.dataset.env),enabled=!env.anomalies;if(!await confirmAction((enabled?'Injecter':'Retirer')+' les anomalies ?','La base sera entièrement régénérée à partir de sa graine. Vos modifications actuelles des données seront remplacées ; vos scripts seront conservés.',enabled?'Injecter':'Retirer'))return;await api('/api/anomalies',{env_id:env.id,enabled});await refreshState();notify(enabled?'Anomalies injectées.':'Anomalies retirées.');})));
  $$('.snapshot-env').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{await api('/api/snapshot',{env_id:button.dataset.env});await loadSnapshots(button.dataset.env);notify('Snapshot des données créé.');})));
  $$('.restore-env').forEach(button=>button.addEventListener('click',()=>busy(button,async()=>{const env=button.dataset.env,select=$$('.snapshot-select').find(s=>s.dataset.env===env);if(!select.value)throw new Error('Sélectionnez un snapshot à restaurer.');if(!await confirmAction('Restaurer ce snapshot ?','Les données actuelles de cet environnement seront remplacées par celles du snapshot. Vos scripts et l’historique seront conservés.','Restaurer'))return;await api('/api/restore',{env_id:env,snapshot_id:select.value});await refreshState();notify('Snapshot restauré.');})));
  state.environments.forEach(env=>loadSnapshots(env.id));
}
async function loadSnapshots(env) {try{const snapshots=await api('/api/snapshots?env_id='+encodeURIComponent(env));const select=$$('.snapshot-select').find(s=>s.dataset.env===env);if(select)select.innerHTML='<option value="">Choisir un snapshot</option>'+snapshots.map(s=>`<option value="${esc(s.id)}">${esc(s.name)}${s.created?' · '+date(s.created):''}</option>`).join('');}catch(error){const select=$$('.snapshot-select').find(s=>s.dataset.env===env);if(select)select.innerHTML='<option value="">Indisponible</option>';notify(error.message,true);}}
$('.skip-link').addEventListener('click',event=>{event.preventDefault();$('#main').focus();});
window.addEventListener('hashchange',render);
$('#active-environment').addEventListener('change',()=>busy($('#refresh-state'),async()=>{state.env=$('#active-environment').value;state.results={};await refreshState();}));
$('#refresh-state').addEventListener('click',event=>busy(event.currentTarget,()=>refreshState()));
document.addEventListener('keydown',event=>{
  if(!(event.ctrlKey||event.metaKey)||$('#confirmation').open)return;
  if(event.key.toLowerCase()==='s'&&$('#save-artifact')){event.preventDefault();$('#save-artifact').click();}
  if(event.key==='Enter'){const action=$('#run-'+state.page);if(action){event.preventDefault();action.click();}}
});
render();
refreshState().catch(error=>{$('#connection-status').textContent='Serveur local inaccessible';notify(error.message,true);$('#main').innerHTML=heading('Connexion au laboratoire','Le serveur local doit être démarré pour accéder à vos expériences.')+`<div class="error-box">${esc(error.message)}</div><p>Utilisez le bouton Actualiser en haut à droite après avoir démarré le laboratoire.</p>`;});




