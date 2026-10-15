# Premier lot Entraînement et Bac à sable

## Audit et périmètre
Le code existant est conservé : Python stdlib/SQLite, interface locale, quatre thèmes, éditeur Python et SVG ER. Référence exécutée avant modification : 59 tests Python + 77 tests Node réussis. Stockage additif uniquement ; aucune donnée existante réinitialisée. Aucune publication GitHub.

Les deux PDF de parcours ont été analysés sur leurs 28 pages : plans seulement, aucun cours détaillé. Matrice initiale : Python (DE p1–3,5–6 ; Python p1–9,12–14) ; SQL/modélisation (DE p9–12,14 ; Python p11–12) ; analyse (DE p5–7 ; Python p5,7–8) ; maths/statistiques (DE p3–5,9) ; ETL (DE p1,12–14) ; NoSQL (DE p11–14) ; infrastructure (DE p1,3,12–13 ; Python p6,9–10) ; IA (DE p1,7–9,11 ; Python p6–7). Les compteurs Hyperskill ne sont pas importés en progression locale. Détail analysé=false pour toutes les compétences.

Lot : dix exercices originaux (4 fonctions Python,4 requêtes SQL,2 DDL), bibliothèque de compétences par domaines, recherche et sélection multiple, formats/niveaux, indices sans solution, progression durable ; environnements personnalisés vides/générés/dupliqués, DDL/CRUD visuel, imports CSV/JSON, export, restauration existante, accès libre SQL/Python/pipelines/ER. PDF et IA automatiques futurs, aucune dépendance IA.

## Contenu versionné
`content/catalog.json` : {version,sources:[{id,title,kind:study_plan,pages,sha256}],domains:[{id,name}],skills:[{id,name,domain,description,program_referenced,detailed_content_analyzed:false,sources:[{source_id,pages:[]}],prerequisites:[],needs_deepening:true}]}. Libellés originaux français, termes standards préservés. Aucun chemin personnel/progression Hyperskill ni PDF protégé dans le dépôt.
`content/exercises.json` : tableau ou enveloppe {version,exercises:[...]}, à convenir entre auteurs. Exercice {id,version,title,domain,skill_ids,prerequisite_skill_ids,level:beginner|intermediate|advanced,kind:targeted|challenge|mini_project|professional|debug,engine:python|sql|schema,objective,statement,input_contract,starter,sample:{filename,content},constraints:[],success_criteria:[],hints:[3 indices],validator_id,estimated_minutes}. Pas de solution dans contenu public. Validateurs/oracles séparés en Python ; pas servis par HTTP.
Dix IDs stables : py-normaliser-evenements,py-total-categories,py-bilan-qualite,py-extraire-journal,sql-filtrer-alertes,sql-joindre-commandes,sql-agreger-ventes,sql-debug-classement,schema-atelier,schema-stocks. Auteurs contenus et moteur arrêtent ensemble les contrats exacts des fonctions/schémas avant rédaction finale.

## Service Training(lab)
Fichiers lab/training.py et lab/training_validators.py, tests dédiés. Catalogue source depuis dossier du code (__file__), données runtime depuis lab.root, pour fixtures Lab temporaires sans copie du contenu. Migrations CREATE TABLE IF NOT EXISTS training_progress et training_attempts (id/payload), sous verrou catalogue. Jobs partagés lab.jobs et plafond3, consentement Python existant, _python réutilisé sans modifier moteur. Les fonctions Python sont importées/exécutées dans sous-processus, résultats comparés par hôte à oracle ; multi-cas déterministes distincts. SQL sur copies fixtures, read_only pour requêtes, vrai DDL et contraintes pour schéma. Erreur technique distincte de réponse incorrecte. États running/success/failed/error/cancelled. Interruption redémarrage explicite. L’historique des tentatives ne prétend pas mesurer une maîtrise définitive.
GET /api/training/catalog -> {sources,domains,skills,exercises,progress,...} ; exercices publics sans hints ni validators/solutions.
GET /api/training/exercise?id=ID -> {exercise,progress,attempts}.
POST /api/training/start {exercise_id} -> même détail, initialise brouillon starter sans écraser ancien.
POST /api/training/save {exercise_id,code,notes?,needs_review?} -> progress.
POST /api/training/hint {exercise_id} -> {hints:[indices révélés],revealed_count}.
POST /api/training/validate {exercise_id,code} -> {attempt_id}.
GET /api/training/attempt?id=ID -> tentative avec feedback réel, cases et comptes.
POST /api/training/cancel {attempt_id} -> {cancelled}.
Noms exacts méthodes .catalog(),.exercise(id),.start(args),.save(args),.hint(args),.validate(args),.attempt(id),.cancel(args). Les identifiants exercice sont des slugs allowlist catalogue, tentative UUID validé. Aucun chemin client. Brouillons, notes, reprise et indices persistés.

## Bac à sable (Sandbox(lab), root)
Les environnements créés/dupliqués sont kind=custom,sandbox=true ; les données anciennes ne sont pas modifiées par les formulaires sandbox. Lire/exporter possible ; pour écrire un ancien environnement, le dupliquer. Source.csv et source.json présents pour moteurs existants. Les opérations destructrices structurées font un snapshot avant publication ; l’UI demande confirmation. SQL libre dans atelier existant et module.
GET /api/sandbox/info?env_id=ID -> {environment,tables,is_sandbox,limits}.
POST /api/sandbox/create {name,seed?,table_count:0..8,row_count:0..10000,distribution:uniform|normal,start_date,end_date,null_rate:0..0.8,duplicate_rate:0..0.5,related:boolean,anomalies:boolean}. Plafond50000 lignes total ; 0 tables=vide ; colonnes générées id,label,value,event_date,category et parent_id si relation. Distributions numériques, période, valeurs manquantes, doublons métier (PK uniques), anomalies numériques réelles.
POST /api/sandbox/duplicate {env_id,name} -> environnement nouveau.
POST /api/sandbox/action {env_id,operation,table,...} -> résultat avec snapshot_id si destructive.
Opérations create_table {columns:[{name,type,primary_key,not_null,unique,min?,references?:{table,column}}]}, add_column {column:{...}}, rename_column {column,new_name}, drop_column {column}, drop_table, insert_row {values:{col:value}}, update_row {key:{PK:value},values:{...}}, delete_row {key:{PK:value}}. Types INTEGER,REAL,TEXT,BLOB,NUMERIC. Plusieurs primary_key créent une PK composite. update/delete uniquement sur clé PK complète identifiant exactement une ligne ; sinon SQL libre. Noms quotés et valeurs liées, transactions et délai.
POST /api/sandbox/import {env_id,table,format:csv|json,text} -> table nouvelle uniquement ; contenu max750Kio et10000 lignes, pas de chemin disque client.
GET /api/sandbox/export?env_id=ID&table=TABLE&format=csv|json -> {filename,content,format,row_count}. 10000 lignes maximum sans troncature silencieuse.
GET /api/snapshots, POST /api/snapshot et /api/restore existants réutilisés. Données sandbox disponibles dans les ateliers par environnement actif. Validation guidée utilise fixtures indépendantes, jamais les bases personnelles.

## UI et responsabilités
LabPractice.mount(container,host), LabSandbox.mount(container,host) retournent {destroy()}. host {api,esc,notify,confirmAction,resultTable,runDetail,getState:()=>state,refreshState,navigate:(page,options?)=>...,acknowledgePython,savePreferences}. Les modules possèdent brouillons/sessions/polling et gardes de montage. Aucun id des ateliers existants réutilisé. Éditeur et thèmes existants réutilisés. Tout texte utilisateur français, aucun changement logo.
Orchestrateur : engine.py/server.py/app.js/index.html, lab/sandbox.py et tests, intégration/docs/QA. Agent architecture_research : training.py,training_validators.py,tests/test_training.py,tests/training_solutions.py. Agent curriculum : content/catalog.json,content/exercises.json,docs/CURRICULUM.md,tests/test_content.py. Agent ui : web/practice.js,web/sandbox.js,web/practice.css et tests/test_practice.cjs/test_sandbox_ui.cjs. Pas de modification croisée.
Fil d’Ariane par root : Espace de travail lien #home, page courante aria-current, lien parent Entraînement si détail. Tous les fichiers du projet restent dans son répertoire imposé. Les documents de code ne doivent pas intégrer de chemins personnels publics.
