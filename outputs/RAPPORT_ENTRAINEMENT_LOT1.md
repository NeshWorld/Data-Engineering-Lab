# Data Engineering Lab — Entraînement et Bac à sable, premier lot

Livraison du 15 octobre 2026. Application existante étendue dans son répertoire imposé. Le serveur local a été relancé sur http://127.0.0.1:8765/. Aucun commit, push ou publication GitHub.

## Résultat livré

- Navigation : « Espace de travail » est un lien vers l’accueil, avec survol/focus clavier et nom de page actif. Un exercice possède un parent Entraînement cliquable. Les dix pages hors accueil ont été contrôlées. Logo conservé.
- Bibliothèque : 55 compétences, huit domaines, recherche, domaine, sélection multiple avec correspondance « au moins une » ou « toutes », filtres de format/niveau. Quatre axes distincts : programme référencé, détail analysé, exercices avec tests, approfondissement restant. La progression indique une pratique locale et ne certifie pas une maîtrise.
- Dix exercices originaux : quatre fonctions Python, quatre requêtes SQL et deux schémas relationnels ; cinq formats et trois niveaux. Énoncés, contrats, prérequis, données téléchargeables, contraintes et critères sont en français. Les points de départ restent à réaliser par l’utilisateur.
- Validation : trois populations/cas réels par exercice, résultat calculé côté serveur, historique, diagnostics, annulation et délais. Une fonction modifiant son entrée échoue. Les compteurs Python doivent être des entiers. Les contraintes de schéma sont testées par INSERT, UPDATE et DELETE réels. Aucune solution complète n’est proposée dans l’interface ni dans les endpoints publics.
- Accompagnement : trois indices progressifs révélés uniquement à la demande ; mode autonomie, brouillons, notes sur les difficultés, état « à reprendre », tentatives et réussites persistants. Une réussite passée reste enregistrée après une tentative ultérieure ratée. L’enregistrement terminal et la progression partagent une transaction SQLite ; la reprise après interruption est explicite.
- Bac à sable : création vide ou générée, duplication indépendante, lecture des anciens environnements, création de table, ajout/renommage/suppression de colonne, types courants, PK simples/composites, FK, NOT NULL, UNIQUE et minimum numérique. Ajout, modification et suppression de lignes sur clé primaire complète, aperçu SQL avec valeurs liées. Les entiers imprécis pour JavaScript sont refusés dans les formulaires.
- Préservation : les formulaires écrivent uniquement dans les environnements personnalisés du bac à sable. Un ancien environnement doit être dupliqué pour ces opérations. Les opérations destructrices structurées demandent confirmation et créent un snapshot automatique ; sauvegarde/restauration manuelles existantes réutilisées.
- Import/export : CSV et JSON réels, import vers une nouvelle table sans écrasement, export sans troncature silencieuse. Les données sont accessibles aux ateliers SQL, Python, pipelines et au diagramme ER par l’environnement actif.
- Générateur : graine, 0 à 8 tables, 0 à 10 000 lignes par table, total maximal 50 000 lignes ; distribution uniforme/normale, période, valeurs manquantes, doublons métier, FK cohérentes et anomalies numériques volontaires. Les clés primaires demeurent uniques.

## Documents pédagogiques et architecture

Les deux PDF fournis ont chacun 14 pages. Ce sont des plans de parcours, pas des cours détaillés. Leurs titres visibles, rubriques et pages ont servi à cartographier les compétences ; aucun contenu pédagogique détaillé n’a été supposé à partir d’un titre. Les 55 compétences portent `detailed_content_analyzed=false`. Aucun score personnel Hyperskill n’est importé et aucun cours ou exercice protégé n’est recopié dans l’application.

`docs/CURRICULUM.md` contient la matrice, les sources, leurs empreintes, les limites et un glossaire. Le contenu original versionné est séparé des validateurs et de la progression. Ajouter une compétence ou une ressource se fait dans le catalogue ; un nouvel exercice exécutable demande un validateur enregistré et des tests. L’import automatique de PDF et la génération IA restent des évolutions séparées. Les fonctions essentielles n’utilisent aucune API IA et fonctionnent hors ligne.

Le socle Python standard/SQLite et l’interface JavaScript native sont conservés. Deux services sont ajoutés à Lab, sans réécriture des moteurs existants. La migration ajoute les tables `training_progress` et `training_attempts` avec `CREATE TABLE IF NOT EXISTS`. Les nouvelles vues réutilisent l’éditeur, les thèmes, les confirmations, le sélecteur d’environnement et la navigation existants. Le démontage annule les mises à jour visuelles tardives ; les sauvegardes et validations de brouillons partagent une file par exercice pour ne pas écraser une saisie récente.

## Validation exécutée

Référence avant ce lot : **59 tests Python et 77 tests JavaScript réussis**.

Validation finale : **102 tests Python et 96 tests JavaScript réussis**, aucun échec ni test ignoré. Il s’agit de 198 tests automatisés au total. Le test de référence soumet les dix implémentations indépendantes au vrai moteur : **30 cas réussis**. Ces trente cas ne sont pas comptés comme trente tests unitaires supplémentaires. Les dix points de départ ne sont pas validés comme des solutions.

Les tests couvrent notamment moteurs existants, SQLite réel, limites, contraintes, rollback, import/export, duplication, snapshots, générateur, serveur HTTP, consentement Python, notes/indices/progression après redémarrage, mutation des entrées, types de sortie, résultat constant incorrect, PK composite déguisée en simple, données permanentes interdites, trigger bloquant les mises à jour, erreur de construction de fixture distincte d’un échec pédagogique, annulation/délai et rollback commun tentative/progression.

Une revue indépendante pédagogique et technique a signalé plusieurs faux positifs et risques de brouillons concurrents ; ils ont été corrigés et font l’objet de régressions automatisées. Les agents initialement chargés du moteur et des dernières références n’ayant pas livré leurs compléments pendant la reprise, l’orchestrateur a terminé ces modifications et exécuté les contrôles finaux. Aucun résultat non exécuté n’est annoncé comme réussi.

Contrôles réels dans le navigateur, sur une fixture séparée : création de table, INSERT/UPDATE, restauration du snapshot automatique, génération de tables liées, import CSV et téléchargement vérifié d’un export CSV ; sélection multiple des compétences ; soumission Python incorrecte puis correcte, SQL correct et DDL correct ; indices à la demande, notes et état à reprendre persistants après arrêt/reprise du serveur. Le compteur et les boutons d’historique s’actualisent après validation. Les copies de solutions de test restent dans les fixtures et les tests, jamais dans la progression personnelle.

Affichage contrôlé à 1440 × 1000, 1024 × 768 et 390 × 844, sans débordement horizontal du document. La navigation mobile défile horizontalement ; le menu latéral défile verticalement sur écran court. Le débordement latéral du menu à 1024 a été corrigé. Aucun message d’erreur dans la console de la vue finale. Les dimensions temporaires du navigateur ont été réinitialisées.

Preuves : `outputs/tests-training-python.txt`, `outputs/tests-training-node.txt`, `outputs/qa-training.json`, `outputs/training-desktop.png`, `outputs/training-mobile.png`, `outputs/sandbox-1024.png` et `outputs/qa-training-export.csv`. Les captures ont transité temporairement par l’espace technique de la conversation avant déplacement dans le projet. Le téléchargement de test a transité par Downloads puis a été déplacé dans outputs ; aucune copie n’y demeure.

## Données personnelles

Une sauvegarde préalable du catalogue et un manifeste privé existent sous `work/training-lot1/baseline/`, ignoré par Git. Les quinze fichiers de données déjà présents ont une empreinte SHA-256 identique après intervention. Les cinq environnements, les expériences sauvegardées et les 29 exécutions historiques sont inchangés. Deux exécutions SQL de lecture ont été ajoutées par l’aperçu réel du bac à sable lors de la vérification finale (`SELECT * FROM customers LIMIT 50`), sans modification de table ou de données. Le catalogue actuel contient donc 31 exécutions. Aucun historique n’a été effacé.

La bibliothèque personnelle affiche zéro exercice réussi et aucune progression d’entraînement avant votre première utilisation. Les essais sont sous `work/`, indépendants des bases personnelles. Les environnements existants n’ont pas été régénérés.

## Fichiers modifiés ou ajoutés

| Ensemble | Fichiers |
| --- | --- |
| Intégration | `lab/engine.py`, `lab/server.py`, `web/app.js`, `web/index.html`, `web/style.css` |
| Nouveaux services | `lab/training.py`, `lab/training_validators.py`, `lab/sandbox.py` |
| Nouvelles vues | `web/practice.js`, `web/practice.css`, `web/sandbox.js` |
| Contenus | `content/catalog.json`, `content/exercises.json` |
| Tests | `tests/test_content.py`, `tests/test_training.py`, `tests/reference_training.py`, `tests/test_training_reference.py`, `tests/test_sandbox.py`, `tests/test_practice.cjs`, `tests/test_sandbox_ui.cjs`, `tests/test_server.py`, `tests/serve_training_fixture.py` |
| Documentation | `README.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/TRAINING_CONTRACTS.md`, `docs/CURRICULUM.md` |
| Livraison | présent rapport, journaux, captures, QA JSON et manifeste de sources dans `outputs/` |

## Limites connues et suites

- Python garde les droits du compte Windows. Le Bac à sable n’est pas un confinement de sécurité. Les règles pédagogiques ne bloquent pas les accès système. Ne soumettre que du code compris. Les tests locaux ne sont pas un système anti-triche.
- Le premier lot valide dix exercices, pas l’ensemble des 55 compétences. Les thèmes NoSQL, Docker, Linux, statistiques et IA sont référencés sans simuler des outils absents. Les niveaux sont relatifs à ce lot.
- La sélection multiple filtre des exercices transversaux déjà écrits ; elle ne génère pas un nouvel exercice à la volée. Les tests utilisent leurs propres fixtures reproductibles, indépendantes des bases personnelles.
- Le générateur utilise un schéma de colonnes fixé et documenté ; la composition libre des champs et distributions supplémentaires reste à développer. Les plafonds protègent une utilisation personnelle et ne constituent pas un outil de benchmark à grand volume.
- L’import est limité à 750 Kio et 10 000 lignes ; l’export à 10 000 lignes et 5 Mo, sans BLOB. Les types sont inférés pour JSON ; le CSV conserve ses textes. Des cellules supérieures à 20 000 caractères sont refusées à l’export.
- Les sources CSV/JSON initiales ne se synchronisent pas automatiquement avec les tables SQLite modifiées ; exporter la table produit un état actuel. Les opérations avancées restent disponibles dans l’atelier SQL.
- Les snapshots automatiques concernent les formulaires destructifs ; le SQL libre suit les protections existantes. Les répertoires de travail et tentatives ne sont pas purgés automatiquement. Pas d’isolation multi-utilisateur, de synchronisation cloud ou d’import PDF/IA automatique dans ce lot.
- Priorités suivantes : intégrer des cours détaillés fournis avec revue de la matrice, enrichir graduellement la bibliothèque et ses cas limites, élargir les générateurs et formats, puis concevoir séparément l’import documentaire et une assistance IA facultative soumise à validation.

Lancer normalement avec `Start-Lab.cmd`. Les commandes de reproduction et la fixture graphique isolée sont documentées dans le README. Aucune installation supplémentaire n’est requise pour utiliser les fonctions essentielles.
