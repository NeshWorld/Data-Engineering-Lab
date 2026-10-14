# Architecture et décisions

## Choix validé

Application personnelle locale, monoprocessus serveur avec threads pour les requêtes et les expériences. Python **3.12.14**, SQLite **3.53.1**, HTML/CSS/JavaScript natifs. Interface en français, ressources et polices système uniquement. Aucun paquet à télécharger pour les fonctions essentielles. pandas disponible sur ce poste et testé, mais facultatif. Node **24.15.0** uniquement pour vérifier la syntaxe JavaScript pendant le développement.

Rust reste une préférence pour une future distribution compilée ; aucune chaîne cargo n'était disponible dans le PATH inspecté. Ajouter Tauri aurait imposé une chaîne Rust/C++ et une étape de distribution supplémentaire sans améliorer immédiatement le moteur SQLite/Python déjà disponible. Une interface navigateur locale permet ici un socle fiable, hors ligne et directement testable. Ce choix a été examiné par un sous-agent indépendant avant les développements parallèles.

## Modules et responsabilités

| Module | Responsabilité |
| --- | --- |
| web/index.html, style.css, app.js | Navigation, éditeurs, inspection, résultats, états et accessibilité |
| lab/datasets.py | Quatre générateurs déterministes, relations, sources CSV/JSON et anomalies |
| lab/sql_engine.py | Vrai SQLite, authorizer, limites, transactions, JSON strict, publication des changements |
| lab/storage.py | Fermeture des connexions, copies bornées et publication de fichiers avec retour arrière |
| lab/engine.py — Lab | Catalogue, environnements, expériences, historique, snapshots et coordination |
| Lab._python | Sous-processus, copie de travail, capture bornée, délais et annulation |
| Lab.validate_pipeline / Lab._worker | Validation des dépendances, ordre stable, étapes et traçabilité |
| lab/server.py | Adaptateur API JSON et liste fermée des ressources web, boucle locale seulement |
| run.py / Start-Lab.cmd | Démarrage Windows et ouverture du navigateur |
| lab_cli.py | Même API et mêmes fichiers depuis le terminal et un IDE |
| tests/ | Génération, moteur, cas adversariaux, HTTP et fixture de validation graphique |

Les contrats d'API sont décrits dans CONTRACTS.md. L'interface ne connaît ni les commandes système ni les détails de connexion SQLite : elle utilise les mêmes payloads JSON que la CLI. Les durées utilisent une horloge monotone ; les dates d'historique sont enregistrées en UTC et affichées en heure locale.

Les données régénérables, les scripts personnels et les copies d'exécution occupent des répertoires distincts. Le verrou du moteur sérialise les modifications d'environnements. Python et les pipelines utilisent une copie capturée au lancement, conservée après succès ou échec. Les écritures manuelles d'un IDE ne passent pas par ce verrou.

La base des expériences est dans data/catalog.sqlite. Les fichiers sauvegardés restent aussi consultables dans experiments/. L'éditeur intégré lit sa version de catalogue ; la CLI lit le fichier réel fourni, ce qui permet de l'éditer et de l'exécuter depuis un IDE. Il n'y a pas de synchronisation automatique de l'éditeur avec les modifications externes.

## Références vérifiées pendant la conception

- [Prérequis Windows Tauri](https://v2.tauri.app/start/prerequisites/)
- [Python sqlite3, authorizer et backup](https://docs.python.org/3/library/sqlite3.html)
- [SQLite authorizer](https://www.sqlite.org/c3ref/set_authorizer.html)
- [SQLite PRAGMA](https://www.sqlite.org/pragma.html)
- [Extensions SQLite](https://www.sqlite.org/loadext.html)
- [Sous-processus Python](https://docs.python.org/3.12/library/subprocess.html)
- [Job Objects Windows, extension possible](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
- [Limites de http.server](https://docs.python.org/3/library/http.server.html)

Ces références ont servi au développement ; l'application n'effectue aucune requête vers ces sites.
