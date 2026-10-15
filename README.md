# Data Engineering Lab — entraînement et expérimentation

Un environnement local pour expérimenter, pas une machine qui apprend à votre place.

## Démarrer sous Windows

Double-cliquez sur **Start-Lab.cmd** dans ce répertoire. Laissez sa fenêtre ouverte : elle héberge le moteur. Le navigateur s'ouvre sur http://127.0.0.1:8765. Fermez le moteur avec Ctrl+C, puis fermez le navigateur. Aucun compte, réseau distant, CDN, télémétrie ou installation de service nécessaire.

La première ouverture génère quatre petites bases intégralement fictives. Aucune connexion vers vos données réelles n'est prévue. Le moteur écoute uniquement l'interface de boucle locale de votre ordinateur.

Python 3.12 ou plus est nécessaire. `python-path.txt` contient le chemin de l'interpréteur vérifié sur ce poste, fourni avec Codex. Si vous déplacez l'application ou retirez ce runtime, remplacez cette ligne par le chemin de votre Python. Aucun téléchargement automatique. Toutes les fonctions essentielles utilisent la bibliothèque standard. pandas est disponible avec l'interpréteur vérifié mais reste facultatif.

Pour choisir un autre port, depuis ce répertoire dans PowerShell :

```powershell
$labPython = Get-Content .\python-path.txt
& $labPython .\run.py --port 8766 --open
```


## Entraînement — premier lot

La nouvelle section **Entraînement** propose 55 compétences regroupées dans huit domaines et dix exercices originaux en français : quatre fonctions Python, quatre requêtes SQL et deux mini-projets de conception relationnelle. Les deux documents analysés sont des plans de parcours, sans cours détaillés. Les références documentaires, les exercices disponibles et votre progression locale restent distincts. Les domaines sans outil d’exécution sont indiqués comme références à approfondir.

Recherchez des compétences, cochez-en plusieurs et choisissez « Au moins une compétence » ou « Toutes les compétences choisies ». Ouvrez un exercice, lisez son contrat et ses données d’exemple puis écrivez votre travail. **Tester mon travail** (Ctrl+Entrée) exécute plusieurs cas reproductibles ; le code de départ n’est pas une solution. Les indices se révèlent un par un, uniquement à votre demande. Le mode autonomie les masque. Une réussite correspond à cet exercice et ne certifie pas une maîtrise définitive.

Les brouillons sont enregistrés automatiquement et par Ctrl+S. Le carnet conserve vos difficultés, la case « À reprendre », les indices consultés et les tentatives, même après redémarrage. Le bouton Recommencer remet le point de départ sans effacer l’historique. Les exemples téléchargeables sont distincts des cas du validateur. Les tests sont locaux et consultables dans le dépôt ; il ne s’agit pas d’un examen avec protection contre la triche.

Le Python garde les droits de votre compte et nécessite le consentement existant. Les validations ont des délais, sorties et résultats bornés ; cela ne constitue pas une sandbox de sécurité. Les exercices sont évalués sur des données dédiées sous work/training, jamais en modifiant votre base active. « Ouvrir dans l’atelier » permet un essai libre avec le brouillon et les données de l’environnement sélectionné ; cet essai libre n’est pas une validation guidée.

## Bac à sable

Créez un environnement vide ou un jeu fictif reproductible. Le générateur propose des distributions uniforme ou normale, des dates, des valeurs manquantes, des doublons métier, des relations et des anomalies numériques. Limites de ce lot : huit tables, dix mille lignes par table et cinquante mille lignes au total. Les identifiants restent uniques ; les relations générées sont cohérentes. Les anomalies et volumes observés figurent dans les métadonnées.

Les formulaires du Bac à sable protègent les environnements déjà existants : dupliquez-en un pour le modifier ici. Les nouveaux espaces sont indépendants. Les onglets Données, Structure, Import / export et Relations permettent les opérations visuelles courantes. Un aperçu précède l’application, et les suppressions/modifications destructrices demandent confirmation et créent un snapshot automatique. Les snapshots peuvent être restaurés depuis le même écran.

L’édition visuelle des lignes exige une clé primaire complète qui identifie exactement une ligne. Pour les autres tables et les opérations plus complexes, utilisez l’atelier SQL. Les limites SQLite sur ALTER TABLE sont affichées par de vrais messages d’erreur ; aucun changement n’est simulé. Python, SQL, pipelines et ER réutilisent l’environnement actif du Bac à sable. Les sources CSV/JSON produites à la création sont des fichiers d’entrée initiaux ; une modification SQL de la base ne réécrit pas automatiquement ces sources.

L’import accepte CSV ou une liste JSON d’objets dans une **table nouvelle uniquement**, au plus 750 Kio et dix mille lignes. Le CSV conserve ses champs comme texte ; les types primitifs JSON sont respectés. L’export est limité à dix mille lignes et 5 Mo, sans troncature silencieuse. Les BLOB et nombres non finis nécessitent une conversion SQL explicite avant un export CSV/JSON fidèle. Les très grands entiers ne sont pas édités visuellement lorsque JavaScript ne peut pas les représenter exactement.

Le fil d’Ariane **Espace de travail** est cliquable sur toutes les pages ; il ramène à l’accueil. Depuis un exercice, le niveau Entraînement ramène à la bibliothèque. Le logo d’origine est conservé.

## Ajouter des contenus

`content/catalog.json` référence les sources, domaines et compétences ; `content/exercises.json` décrit les énoncés, contrats, données d’exemple, prérequis et indices. Les validateurs restent séparés dans `lab/training_validators.py`. Le moteur et les formulaires n’ont pas besoin d’être reconstruits pour ajouter des compétences ou de nouveaux exercices utilisant les formats existants et un validateur enregistré. Lire `docs/CURRICULUM.md` pour la matrice, le glossaire et les règles de provenance, puis `docs/TRAINING_CONTRACTS.md` pour les interfaces.

L’import automatique de nouveaux PDF et la génération par IA sont des évolutions distinctes, non livrées dans ce lot. Aucune API IA payante n’est requise ; la bibliothèque fonctionne hors ligne.

## Utiliser le laboratoire

- **Accueil** : sélectionnez un environnement et retrouvez vos expériences enregistrées.
- **SQL Lab** : écrivez du vrai SQL SQLite, puis Exécuter ou Ctrl+Entrée. Échap puis Tab quitte l'éditeur ; Maj+Tab revient au contrôle précédent. Le panneau latéral peut être masqué, l'éditeur et les tableaux peuvent être redimensionnés en hauteur. Le schéma expose colonnes, clés étrangères et index. Enregistrez votre requête avec un nom (Ctrl+S). Les résultats et erreurs sont conservés dans l'historique.
- **Python Lab** : écrivez votre script. Les délimiteurs se ferment automatiquement, Entrée conserve l’indentation et ajoute quatre espaces après `:`. Les sélections peuvent être entourées, une paire vide se supprime ensemble, Ctrl+Z et Ctrl+Y (ou Ctrl+Maj+Z) annulent et rétablissent les éditions. Échap puis Tab quitte l’éditeur. La première exécution nécessite une confirmation des risques. Chaque exécution reçoit une copie de la base et des sources ; les chemins sont accessibles par `LAB_DB` et `LAB_WORKSPACE`. stdout et stderr sont capturés. Écrivez un éventuel tableau dans `result.csv`, ou une sortie JSON dans `result.json`, pour l'inspecter. Le bouton Arrêter interrompt une exécution.
- **Pipeline Lab** : chargez, si vous le souhaitez, l'exemple facultatif, puis modifiez les étapes. Enregistrez votre configuration. Les étapes CSV, Python, validation, chargement SQLite, SQL et export fonctionnent sur des données réelles fictives ; chaque étape garde son statut, sa durée et ses volumes. Exécutez toutes les étapes ou une étape isolée. Une étape isolée ne reçoit pas les fichiers intermédiaires d'une ancienne exécution : elle commence avec la base et les sources initiales.
- **Data Explorer** : consultez les tables, filtrez leurs valeurs et inspectez les types, valeurs manquantes et distributions.
- **Diagramme ER** : déplacez les tables, zoomez, déplacez la vue et utilisez Recentrer pour retrouver le schéma. Sélectionnez une table ou une relation pour consulter ses propriétés. Les positions et la vue sont enregistrées par environnement. Les traits correspondent uniquement aux contraintes étrangères SQLite, y compris les clés composites. Après une modification de schéma en SQL, le diagramme se met à jour ; après une édition externe, utilisez Actualiser.
- **Paramètres → Apparence** : choisissez Émeraude, Arctique, Améthyste ou Cuivre. L’aperçu est immédiat et le choix est enregistré pour les sessions suivantes.
- **Observabilité** : consultez les exécutions, sorties, erreurs, étapes et comparez deux résultats.
- **Environnements** : créez une base avec type, graine et volume ; injectez ou retirez les anomalies, sauvegardez, restaurez ou réinitialisez. Les actions de remplacement demandent confirmation. Une réinitialisation régénère les données propres avec la même graine et la version courante du générateur et conserve tous les scripts, requêtes, configurations et journaux personnels.

La taille contrôle le nombre de faits principaux ; les dimensions et relations secondaires ont leurs propres volumes. Les anomalies sont décrites dans les métadonnées de l'environnement. Les dates de génération partent d'une référence fixe, pas de l'heure de l'ordinateur.

## Fichiers et IDE

Tous les fichiers propres au laboratoire restent dans **le répertoire du projet** :

```text
lab/                  moteur modulaire, génération, adaptateur HTTP
web/                  interface autonome sans dépendance distante
data/catalog.sqlite   environnements, expériences, historique, consentement et préférences
data/environments/    bases fictives et sources CSV/JSON
data/snapshots/       sauvegardes des bases et des sources
experiments/          vos fichiers .sql, .py, .json enregistrés
work/runs/            copie des entrées, scripts, sorties de chaque exécution
work/                 espaces des tests, sans données personnelles
outputs/              captures et rapport de livraison
tests/                tests automatisés indépendants
docs/                 architecture, contrats et limites
```

Ouvrez **ce répertoire** dans VS Code ou PyCharm et sélectionnez l'interpréteur de `python-path.txt`. Les chemins exacts des bases et des expériences sont affichés dans l'application. Les fichiers sont standards : SQLite, CSV UTF-8, JSON UTF-8, Python et SQL. Après une modification depuis un IDE, la CLI lit directement le fichier modifié. L'éditeur intégré conserve la version enregistrée dans le catalogue : il ne synchronise pas automatiquement les modifications externes.

Pour un script Python externe, utilisez `sqlite3.connect(chemin_de_la_base)` ou `pandas.read_sql_query(...)`. Pour préserver l'environnement initial, préférez une copie dans votre espace d'expérience. Évitez de modifier directement une base au même moment qu'une opération de l'interface : les éditions externes ne sont pas coordonnées par le verrou du moteur.

La CLI utilise la même API locale et les mêmes journaux que l'interface, pendant que l'application tourne :

```powershell
$labPython = Get-Content .\python-path.txt
& $labPython .\lab_cli.py list
& $labPython .\lab_cli.py schema IDENTIFIANT_ENVIRONNEMENT
& $labPython .\lab_cli.py sql IDENTIFIANT_ENVIRONNEMENT .\experiments\VOTRE_FICHIER.sql
& $labPython .\lab_cli.py python IDENTIFIANT_ENVIRONNEMENT .\experiments\VOTRE_SCRIPT.py
& $labPython .\lab_cli.py pipeline IDENTIFIANT_ENVIRONNEMENT .\experiments\VOTRE_PIPELINE.json
```

La confirmation Python doit avoir été donnée dans l'interface avant un lancement par la CLI. `--port 8766` se place avant la sous-commande si vous utilisez un autre port. Les identifiants se trouvent dans `list` et les chemins de l'interface.

## Tests

Depuis le répertoire du projet :

```powershell
$labPython = Get-Content .\python-path.txt
& $labPython -m unittest discover -s tests -v
```

Les tests créent leurs données uniquement sous `work/`, puis les nettoient. Ils ne réinitialisent pas vos environnements personnels. Les contrôles graphiques de livraison ont été effectués dans le navigateur intégré avec l'outil de contrôle du navigateur (CUA). Le lancement de Playwright avec Edge a expiré sur ce poste ; il n'est pas compté comme un test réussi. Les tests Python sont rejouables sans installer de dépendance. Le socle 1.1 avant ce lot comprenait 59 tests Python et 77 tests JavaScript réussis. Les tests supplémentaires JavaScript nécessitent Node et se lancent avec `node --test tests/test_themes.cjs tests/test_python_editor.cjs tests/test_er_diagram.cjs tests/test_app_integration.cjs tests/test_practice.cjs tests/test_sandbox_ui.cjs`. Le serveur `tests/serve_v1_1_fixture.py` ouvre une copie de test sur le port 8768, avec clés composites et grand schéma sous `work/v1.1-ui-validation/`. Le parcours graphique vérifié est consigné dans le rapport.

## Étendre le laboratoire

Lire `docs/CONTRACTS.md` pour les payloads et les interfaces. Un nouveau générateur se branche dans `lab/datasets.py` et doit ajouter ses tests de déterminisme/relations/anomalies. Une nouvelle étape de pipeline se branche dans `Lab.validate_pipeline` et `Lab._worker`. Le serveur ne doit servir que les fichiers web explicitement autorisés. Ne pas coupler une réinitialisation à la suppression d'expériences.

Voir `docs/SECURITY.md` pour les limites d'exécution et `outputs/RAPPORT_LIVRAISON.md` pour les preuves de validation et le périmètre final.

## Mise à jour 1.1

Si une ancienne fenêtre du moteur tourne, attendez la fin des exécutions puis arrêtez-la avec Ctrl+C. Relancez **Start-Lab.cmd** dans ce dossier et actualisez le navigateur. Aucun changement d’interpréteur ou installation supplémentaire n’est nécessaire pour utiliser la version 1.1.

Le rapport de la version 1.1 et les 136 tests finaux (59 Python et 77 JavaScript) sont consignés dans `outputs/RAPPORT_V1_1.md`, `outputs/tests-v1.1-python.txt` et `outputs/tests-v1.1-node.txt`.

Le détail des interfaces est dans `docs/V1_1_CONTRACTS.md`. La sauvegarde de référence du code et du catalogue est sous `work/v1.1-baseline/`. Ce dossier contient des données personnelles du laboratoire ; il reste local et n’est jamais servi par HTTP. Ne remplacez pas votre catalogue courant par cette référence sans sauvegarder vos travaux ultérieurs.


## Tests du nouveau lot

La référence avant cette évolution est de 59 tests Python et 77 tests JavaScript réussis. Les tests supplémentaires vérifient les contenus, les véritables validateurs, la progression, les formulaires et le Bac à sable. Lancer les mêmes commandes de test ci-dessus. Les données temporaires restent sous work et ne réinitialisent pas vos environnements.

Pour les essais graphiques isolés : `python tests/serve_training_fixture.py` avec l’interpréteur du projet, puis ouvrir le port 8769. Ce serveur utilise uniquement work/training-lot1/ui-validation ; il ne représente pas votre progression personnelle.

Le premier lot Entraînement et Bac à sable est décrit dans `outputs/RAPPORT_ENTRAINEMENT_LOT1.md`. Sa validation finale comprend 102 tests Python et 96 tests JavaScript, avec journaux `outputs/tests-training-python.txt` et `outputs/tests-training-node.txt`. Les dix exercices ont aussi été exécutés avec des soumissions de référence indépendantes, soit trente cas réels.
