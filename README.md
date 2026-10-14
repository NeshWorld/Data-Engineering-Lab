# Data Engineering Lab — version 1.1

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

Tous les fichiers propres au laboratoire restent dans **C:\Users\apapi\Data Engineering Lab** :

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

Les tests créent leurs données uniquement sous `work/`, puis les nettoient. Ils ne réinitialisent pas vos environnements personnels. Les contrôles graphiques de livraison ont été effectués dans le navigateur intégré avec l'outil de contrôle du navigateur (CUA). Le lancement de Playwright avec Edge a expiré sur ce poste ; il n'est pas compté comme un test réussi. Les tests Python sont rejouables sans installer de dépendance. La référence avant amélioration comprenait 52 tests réussis. Les tests supplémentaires JavaScript nécessitent Node et se lancent avec `node --test tests/test_themes.cjs tests/test_python_editor.cjs tests/test_er_diagram.cjs tests/test_app_integration.cjs`. Le serveur `tests/serve_v1_1_fixture.py` ouvre une copie de test sur le port 8768, avec clés composites et grand schéma sous `work/v1.1-ui-validation/`. Le parcours graphique vérifié est consigné dans le rapport.

## Étendre le laboratoire

Lire `docs/CONTRACTS.md` pour les payloads et les interfaces. Un nouveau générateur se branche dans `lab/datasets.py` et doit ajouter ses tests de déterminisme/relations/anomalies. Une nouvelle étape de pipeline se branche dans `Lab.validate_pipeline` et `Lab._worker`. Le serveur ne doit servir que les fichiers web explicitement autorisés. Ne pas coupler une réinitialisation à la suppression d'expériences.

Voir `docs/SECURITY.md` pour les limites d'exécution et `outputs/RAPPORT_LIVRAISON.md` pour les preuves de validation et le périmètre final.

## Mise à jour 1.1

Si une ancienne fenêtre du moteur tourne, attendez la fin des exécutions puis arrêtez-la avec Ctrl+C. Relancez **Start-Lab.cmd** dans ce dossier et actualisez le navigateur. Aucun changement d’interpréteur ou installation supplémentaire n’est nécessaire pour utiliser la version 1.1.

Le rapport de la version 1.1 et les 136 tests finaux (59 Python et 77 JavaScript) sont consignés dans `outputs/RAPPORT_V1_1.md`, `outputs/tests-v1.1-python.txt` et `outputs/tests-v1.1-node.txt`.

Le détail des interfaces est dans `docs/V1_1_CONTRACTS.md`. La sauvegarde de référence du code et du catalogue est sous `work/v1.1-baseline/`. Ce dossier contient des données personnelles du laboratoire ; il reste local et n’est jamais servi par HTTP. Ne remplacez pas votre catalogue courant par cette référence sans sauvegarder vos travaux ultérieurs.
