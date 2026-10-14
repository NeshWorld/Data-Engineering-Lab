# Data Engineering Lab — livraison 1.1

Le 14 octobre 2026. Projet conservé exclusivement dans **C:\Users\apapi\Data Engineering Lab**. Application existante étendue et relancée sur **http://127.0.0.1:8765/**. Aucun service distant, CDN ou paquet supplémentaire n’est nécessaire pour l’utiliser.

## Améliorations intégrées

- **Paramètres → Apparence** : Émeraude, Arctique, Améthyste et Cuivre, aperçu immédiat et choix persistant. Les couleurs sont centralisées dans les tokens de themes.css : éditeurs, boutons, panneaux, états, tableaux et diagrammes. Navigation clavier des cartes ; contrastes des textes et états testés à au moins 4,5:1.
- **Éditeur Python** : paires, guillemets contextuels, position du curseur, saut des fermants, suppression de paire vide, indentation de quatre espaces, conservation et ajout après deux-points, Entrée sur trois lignes entre délimiteurs, sélection entourée, annulation/rétablissement. Le textarea existant a été étendu ; l’historique texte/sélection est conservé par document après sauvegarde et navigation.
- **Diagramme ER** : nouvelle page dédiée et diagramme dans SQL/Explorateur. Tables, colonnes, ordre PK et marqueurs FK ; déplacement à la souris ou aux flèches, zoom 10–300 %, déplacement du fond, Tout voir, Organiser et recherche/centrage. Sélection d’une table ou d’une relation avec propriétés. Positions conservées par environnement ; la petite vue intégrée garde un zoom adapté sans remplacer celui de la grande vue.
- **Fidélité SQLite** : regroupement des contraintes composites par id/seq, résolution des cibles implicites par ordre réel de PK, relations multiples, réflexives et opposées ; casse ASCII conforme à SQLite. Les colonnes générées sont exposées par table_xinfo. Une référence absente reste non résolue ; aucun lien n’est déduit d’une ressemblance entre noms.

## Préservation

Les tests existants ont été exécutés avant toute modification : **52 réussis**. Une sauvegarde locale du code initial et du catalogue a été créée sous `work/v1.1-baseline/`, avec manifeste SHA-256 des fichiers personnels.

Contrôle final après redémarrage et affichage de la version intégrée : **12 fichiers de bases/sources inchangés**, et contenu des tables catalogue **environments, artifacts, runs et snapshots identique** à la référence. Aucune base personnelle n’a été réinitialisée, aucune expérience supprimée. Seules les préférences UI peuvent ajouter la clé settings/ui_preferences. Le consentement Python reste indépendant.

Les essais graphiques et les créations de tables ont utilisé exclusivement `work/v1.1-ui-validation/`, sur le port 8768. Le serveur de test a été arrêté ; le moteur principal reste lancé. Les captures ont transité brièvement par l’espace temporaire du navigateur avant déplacement immédiat dans outputs ; aucun code, test, document ou donnée du projet n’y a été conservé.

## Tests réellement exécutés

| Suite finale | Résultat |
| --- | --- |
| Python existants + préférences/schéma/API | **59/59**, 71,551 s |
| Thèmes et contrastes | **14/14** |
| Éditeur Python | **30/30**, dont 2 000 documents malformés déterministes |
| Diagramme ER | **27/27**, dont montage et déplacements interrompus |
| Intégration app / sauvegarde / file de préférences | **6/6** |
| **Total automatisé final** | **136/136** |

La syntaxe app.js a été vérifiée avec Node. Les tests Python couvrent notamment le vrai SQL, les contraintes, transactions et retours arrière, les snapshots/restaurations, les exécutions Python, les délais/annulations, les pipelines avec export et la protection des routes HTTP. Les nouveaux tests vérifient la reprise des préférences, la fusion concurrente, les coordonnées invalides et extrêmes, le maintien du consentement, les clés composites et colonnes générées.

**Vérification réelle dans le navigateur intégré** : quatre palettes et persistance après rechargement/redémarrage du serveur de test ; reprise par Actualiser après indisponibilité simulée du premier GET préférences ; saisie, sélections, paires, indentation, Ctrl+Z/Ctrl+Y, historique après Ctrl+S et navigation ; script Python donnant stdout `v1.1` ; SQL DDL puis SELECT 42 et apparition de la nouvelle table/relation ; déplacement de table et du fond à la souris, zoom et recentrage, conservation après navigation et rechargement ; deux FK composites dont une implicite avec CASCADE, colonne générée, cible absente ; recherche dans **53 objets et 51 FK** ; pipeline existant de cinq étapes avec **300 lignes source et 100 lignes résultat SQL**.

Fenêtres vérifiées via dimensions DOM : **1440×1000, 1024×768, 390×844 et 1920×1080**. Sur petite fenêtre, les contrôles restent accessibles et l’inspecteur passe sous le diagramme ; pas de débordement horizontal de document constaté. Les captures sont des pages complètes, leur hauteur peut donc dépasser celle de la fenêtre.

Preuves : `tests-v1.1-python.txt`, `tests-v1.1-node.txt`, `qa-v1.1.json` et captures `v11-*.jpg` dans ce dossier. `v11-main.jpg` montre la version principale ; les autres captures montrent des fixtures de QA. Le serveur de test est relançable par `python tests/serve_v1_1_fixture.py` avec l’interpréteur du projet. Créer le fichier vide `work/v1.1-ui-validation/fail-preferences-once` permet de rejouer l’indisponibilité initiale simulée dans cette fixture uniquement.

## Bugs détectés et corrigés

1. Une sauvegarde A terminant après ouverture du document B pouvait réaffecter l’identifiant A au contenu B. Les sauvegardes capturent désormais l’identité et la révision du document ; elles préservent le document actuellement ouvert.
2. Le rendu initial pouvait afficher la sélection de thème par défaut avant réception des préférences. Le premier rendu attend leur chargement ; une reprise après erreur les recharge aussi.
3. Des sauvegardes concurrentes de thème et de disposition risquaient de perdre des changements : file FIFO côté navigateur et fusion atomique sous verrou côté moteur.
4. Des FK déclarées avec une casse différente des tables/colonnes étaient marquées à tort non résolues : comparaison ASCII conforme à SQLite.
5. Des FK opposées pouvaient partager exactement le même trait : trajectoires distinctes.
6. Une navigation pendant un déplacement sans relâchement pouvait perdre les coordonnées : sauvegarde à la destruction, capture libérée, y compris un déplacement d’un pixel.
7. Un entier JSON excessivement grand pouvait provoquer une erreur interne de validation : refus propre et préférences intactes.
8. Les changements synthétiques d’édition et la saisie native utilisent le même historique borné ; les anciens gestionnaires Tab ne s’appliquent plus deux fois à Python.

## Agents réellement mobilisés

| Agent | Rôle et vérification |
| --- | --- |
| architecture_research | Audit d’architecture, puis QA indépendante en lecture seule ; reproduction des courses et cas adversariaux, exécution indépendante des suites modules |
| themes | Quatre palettes, tokens, cohérence et tests de contraste |
| python_editor | Extension du textarea, historique et tests de saisie |
| er_diagram | Modèle SQLite, SVG, interactions et tests géométriques/lifecycle |
| Orchestrateur | Contrats, séparation des fichiers, sauvegarde, moteur/API, intégration, tests d’ensemble, navigateur réel et préservation des données |

Les agents ont travaillé sur des fichiers distincts. Aucun nouveau projet ou worktree externe n’a été créé. Le choix SVG local est volontaire : il apporte les interactions nécessaires sans moteur physique ni refonte de framework. L’éditeur existant est également conservé.

## Fichiers ajoutés ou modifiés

| Fichiers | Contenu |
| --- | --- |
| `lab/engine.py` | Préférences atomiques, validation et métadonnées de schéma enrichies |
| `lab/server.py` | GET/POST préférences, ressources web explicitement autorisées, version 1.1 |
| `web/app.js` | Paramètres, intégration des trois modules, sessions, file de sauvegarde et corrections de course |
| `web/index.html` | Chargement des modules et feuilles de style |
| `web/style.css` | Substitutions de couleurs uniquement ; structure existante conservée |
| `web/themes.js`, `web/themes.css` | Gestion des palettes, rendu et tokens centralisés |
| `web/python-editor.js` | Ergonomie et historique de l’éditeur |
| `web/er-diagram.js`, `web/er-diagram.css` | Diagramme et interactions |
| `tests/test_preferences.py`, `tests/test_server.py` | Persistance, schéma et API |
| `tests/test_themes.cjs`, `tests/test_python_editor.cjs`, `tests/test_er_diagram.cjs`, `tests/test_app_integration.cjs` | Tests JavaScript |
| `tests/serve_v1_1_fixture.py` | Serveur et données de QA isolés |
| `README.md`, `docs/ARCHITECTURE.md`, `docs/V1_1_CONTRACTS.md` | Utilisation, décisions et contrats |
| `outputs/` | Présent rapport, journaux, manifeste, résultats structurés et captures |

Les générateurs, l’exécution SQL, les étapes de pipeline, les scripts de lancement et les expériences personnelles n’ont pas été réécrits.

## Limites connues

- L’éditeur utilise une analyse lexicale légère. Les expressions internes des f-strings sont traitées comme du texte ; ce n’est pas un parseur Python ni un IDE complet. Les événements IME sont testés par simulation, sans validation d’une méthode de saisie matérielle sur ce poste.
- Le diagramme est vérifié en navigateur jusqu’à 53 objets. Des schémas beaucoup plus grands ne sont pas mesurés ; utilisez recherche et zoom pour lire les colonnes. Les noms longs sont abrégés dans les nœuds, complets dans les infobulles/propriétés. Les courbes ne garantissent pas l’absence de croisements.
- Les contrôles visuels portent sur le navigateur intégré de ce poste. Aucun résultat Chrome/Firefox/Safari supplémentaire n’est revendiqué. Le lancement Edge/Playwright ayant expiré lors de la livraison initiale, il n’est pas compté comme un succès.
- Les préférences sont locales au catalogue. Les modifications simultanées depuis plusieurs onglets suivent l’ordre d’arrivée du serveur ; il n’y a pas de synchronisation visuelle en temps réel entre onglets. Les limites d’exécution Python déjà documentées dans SECURITY.md restent applicables.

## Relancer

Le moteur principal a été relancé avec la version intégrée. Pour une prochaine ouverture, double-cliquer **C:\Users\apapi\Data Engineering Lab\Start-Lab.cmd**. Garder sa fenêtre ouverte. Si un ancien moteur tourne encore, attendre la fin des exécutions, l’arrêter avec Ctrl+C puis relancer et actualiser le navigateur. Aucun reset des données n’est nécessaire.

Pour rejouer les tests depuis ce répertoire :

```powershell
$labPython = Get-Content .\python-path.txt
& $labPython -B -m unittest discover -s tests -v
node --test tests/test_themes.cjs tests/test_python_editor.cjs tests/test_er_diagram.cjs tests/test_app_integration.cjs
```

Node n’est nécessaire que pour les tests JavaScript, pas pour utiliser le laboratoire.
