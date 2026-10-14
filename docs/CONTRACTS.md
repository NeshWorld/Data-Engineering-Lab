# Contrats — Data Engineering Lab

Décision de l'orchestrateur : Python 3.12+, SQLite standard, interface HTML/CSS/JavaScript autonome. Aucun téléchargement nécessaire pour l'exécution. Serveur lié à 127.0.0.1 uniquement. Rust/Tauri différé : aucune chaîne Rust installée, gain insuffisant pour une première version portable. pandas facultatif, aucune dépendance côté interface.

## Générateur
`lab.datasets.generate(path: Path, kind: str, seed: int, size: int, anomalies: bool = False) -> dict` crée une base SQLite neuve au chemin fourni. Types : `commerce`, `logistics`, `events`, `imperfect`. Taille entre 0 et 10000, graine entre 0 et 2147483647. Retour JSON `{tables: {name: count}, anomalies: [...descriptions...]}`. Relations propres valides sauf anomalies explicites. Fichiers CSV et JSON fictifs dans le répertoire de la base : `source.csv`, `source.json`. Répétition déterministe. Agent données seul propriétaire de datasets.py et tests/test_datasets.py.

## API interface
Toutes les réponses : `{ok: true, data: ...}` ou `{ok: false, error: message}` avec code HTTP approprié. GET `/api/state` retourne `{environments, artifacts, runs, python_ack, root, python, pandas}`. Environnement `{id,name,kind,seed,size,anomalies,db_path}`. Artefact `{id,name,kind,code,env_id,path,updated}`. Run `{id,kind,env_id,status,started,duration_ms,row_count,stdout,stderr,error,result,steps,workspace}` ; status `running|success|error|cancelled`.

GET `/api/schema?env_id=ID` -> `{tables:[{name,type,count,columns:[{name,type,notnull,pk}],foreign_keys:[{from,table,to}],indexes:[{name,unique}]}]}`.
GET `/api/profile?env_id=ID&table=NAME` -> `{count,columns:[{name,type,nulls,distinct,min,max,top:[{value,count}]}]}`.
GET `/api/runs?id=ID` -> un run ; sans id liste des runs. GET `/api/artifacts` liste des artefacts.

POST `/api/environment` `{name,kind,seed,size,anomalies}` -> environnement.
POST `/api/reset` `{env_id}` -> environnement régénéré même graine, anomalies retirées ; scripts conservés.
POST `/api/anomalies` `{env_id,enabled}` -> régénération avec anomalies bool (UI explique remplacement des données).
POST `/api/snapshot` `{env_id}` -> `{id,name}`. GET `/api/snapshots?env_id=ID` liste. POST `/api/restore` `{env_id,snapshot_id}` restaure uniquement données.
POST `/api/sql` `{env_id,code,read_only?:false}` -> `{columns,rows,row_count,truncated,duration_ms,changes,run_id}`. Vraies opérations SQLite, plusieurs instructions acceptées. Dernier résultat tabulaire présenté. Limite d'affichage 1000 lignes, nombre exact jusqu'à la limite de temps ; rollback sur erreur. Interdiction ATTACH, DETACH, chargement extensions et pragmas dangereux.
POST `/api/artifact` `{id?,name,kind,code,env_id}` -> artefact. kind `sql|python|pipeline`. Scripts SQL/Python fichiers dans experiments/, pipeline code JSON.
POST `/api/python_ack` `{accepted:true}` -> `{accepted:true}`. Première exécution Python exige consentement explicite UI.
POST `/api/python` `{env_id,code,timeout?:30}` -> `{run_id}`. Async, poll GET runs. DB copiée dans work/runs/ID, LAB_DB et LAB_WORKSPACE fournis ; CSV/JSON source copiés. Python isolé -I mais PAS sandbox. Sorties limitées, annulation POST `/api/cancel` `{run_id}`.
POST `/api/pipeline` `{env_id,name,steps:[...]}` -> `{run_id}` async. Chaque étape `{id,name,type,depends_on:[],code?,path?,table?,min_rows?}`. Types : `csv` (source.csv par défaut), `python` (écrit result.csv), `validate` (min_rows, vérifie CSV), `load` (charge CSV dans table SQLite `pipeline_output` par défaut), `sql` (code), `export` (export dernier résultat SQL en result.csv). Dépendances tri topologique stable ; absence deps = ordre fourni. DB copiée par exécution. Étape isolée : soumettre seulement l'étape (les fichiers source et DB existent). Sortie run.steps `{id,name,type,status,duration_ms,input_rows,output_rows,error,result}`. Aucun pipeline ni code personnel généré automatiquement à la place de l'utilisateur : seul exemple facultatif modifiable.

## Interface
Agent UI propriétaire exclusif web/index.html, web/style.css, web/app.js. Pages : accueil, SQL, Python, pipeline, explorer, observabilité, environnements. Interface française sombre graphite, accent menthe limité, navigation clavier, résultats vrais, aucune dépendance distante. JS fetch avec JSON Content-Type same-origin ; serveur contrôle Host/Origin. Tokens non requis (Host/Origin et absence CORS). Éditeur SQL avec calque syntaxe ou coloration simple accessible. Redimensionnement CSS resize/panneaux. Confirmation explicite avant régénération/restauration.

## Persistance
data/catalog.sqlite : métadonnées environnements, artefacts, runs, snapshots, réglages. data/environments/ID/lab.sqlite et sources ; data/snapshots/ID.sqlite. experiments/ scripts jamais effacés par reset. work/runs/ espaces isolés conservés pour inspection. Tests exclusivement dans work/test-* sous le projet (pas dossiers temporaires externes).

L’Explorer utilise read_only:true : seules les opérations de lecture SQLite sont autorisées. Le générateur courant est versionné (1.1) dans les métadonnées. Les JSON entrants refusent les constantes et nombres non finis. Les fichiers DB/CSV/JSON sont publiés avec sauvegardes de retour arrière sur erreur ; une panne système entre remplacements ne constitue pas une transaction atomique.
