# Cartographie pédagogique et contenus originaux — premier lot

## Nature des sources et limites de l’analyse

Deux documents fournis par l’utilisateur ont été analysés intégralement : **Data Engineering and ETL** et **Python Developer**, chacun sur 14 pages. Ce sont des plans de parcours, et non des cours détaillés. Le premier présente 36 grandes sections et le second 28. Les intitulés visibles dans les pages font foi : les métadonnées PDF contiennent des noms de projets différents.

L’analyse a combiné extraction du texte et contrôle visuel. Une première extraction omettait certaines lignes grisées ; une seconde extraction avec PDFium a récupéré ces intitulés sur les 28 pages. Les listes détaillées de notions disponibles restent des intitulés : elles ne prouvent ni la profondeur d’enseignement ni la présence d’un cours complet.

Les fichiers sources ne sont pas copiés dans le dépôt. Le catalogue conserve leur titre visible, leur nombre de pages et une empreinte SHA-256 afin de distinguer une future version du document. Il ne contient aucun chemin personnel et n’importe aucun compteur de progression Hyperskill.

Les formulations des compétences, énoncés, contextes, données et indices de ce lot sont originales. Les références indiquent les pages ayant motivé le regroupement ; elles ne présentent pas les exercices du Lab comme des exercices Hyperskill. Certaines applications, notamment les clés composites, sont des prolongements pratiques originaux de la modélisation relationnelle référencée.

## Les quatre dimensions de couverture

1. **Référencée dans le programme** : une ou plusieurs pages du plan mentionnent la notion ou son groupe.
2. **Contenu détaillé analysé** : faux pour les 55 compétences ; aucun cours détaillé n’a été fourni.
3. **Entraînement disponible et validé** : la disponibilité se déduit du lien entre exercices et compétences. La validation technique dépend des tests des véritables validateurs ; le catalogue seul ne suffit pas à l’affirmer.
4. **À approfondir** : vrai actuellement. Une réussite à un exercice ne prouve pas une maîtrise définitive.

La progression locale est enregistrée par le moteur d’entraînement à partir des brouillons, indices et tentatives. Elle reste distincte de la couverture documentaire et des anciens compteurs de la plateforme source. Les compétences sans exercice ne sont jamais présentées comme validées par un outil simulé.

## Matrice compétences, sources et entraînements

Abréviations : **DE** = plan Data Engineering and ETL ; **PY** = plan Python Developer. Les numéros sont les pages physiques du PDF, de 1 à 14. Une cellule « Référence seulement » signifie que le premier lot ne fournit pas d’exercice dédié. La disponibilité d’un atelier libre ne vaut pas validation guidée d’une compétence.

| Compétence | Domaine | Pages sources | Exercices du premier lot |
|---|---|---|---|
| Manipuler les valeurs et les types | Python et programmation | DE p. 1, 2 ; PY p. 1, 2 | Référence seulement |
| Prendre des décisions dans un programme | Python et programmation | DE p. 2 ; PY p. 1, 2 | Référence seulement |
| Parcourir des données et raisonner sur un algorithme | Python et programmation | DE p. 2, 3 ; PY p. 2, 3 | `py-normaliser-evenements` |
| Décomposer un traitement en fonctions | Python et programmation | DE p. 2, 3 ; PY p. 2, 3, 4, 9 | `py-total-categories`, `py-bilan-qualite` |
| Nettoyer et découper des chaînes | Python et programmation | DE p. 2, 5 ; PY p. 2, 3 | `py-normaliser-evenements`, `py-total-categories`, `py-extraire-journal` |
| Choisir et transformer des collections | Python et programmation | DE p. 2, 5 ; PY p. 4, 5 | `py-normaliser-evenements`, `py-total-categories`, `py-bilan-qualite` |
| Exprimer des transformations de collections | Python et programmation | PY p. 5 | Référence seulement |
| Produire des données progressivement | Python et programmation | PY p. 5, 6 | Référence seulement |
| Lire et écrire des fichiers de façon maîtrisée | Python et programmation | DE p. 5, 6 ; PY p. 7, 8 | Référence seulement |
| Diagnostiquer les erreurs et journaliser | Python et programmation | PY p. 8 | `py-extraire-journal` |
| Structurer un modèle avec des objets | Python et programmation | DE p. 6 ; PY p. 8, 9 | Référence seulement |
| Décrire les contrats avec les types | Python et programmation | PY p. 13 | Référence seulement |
| Tester, relire et mesurer son code | Python et programmation | PY p. 3, 6, 13 | Référence seulement |
| Distinguer concurrence et parallélisme | Python et programmation | PY p. 12 | Référence seulement |
| Reconnaître des motifs textuels | Python et programmation | PY p. 13, 14 | Référence seulement |
| Projeter les données utiles | SQL et conception de bases | DE p. 9 ; PY p. 11 | `sql-filtrer-alertes` |
| Filtrer sans perdre le sens de NULL | SQL et conception de bases | DE p. 9, 10 ; PY p. 11 | `sql-filtrer-alertes`, `sql-agreger-ventes` |
| Rendre un résultat SQL déterministe | SQL et conception de bases | DE p. 10, 12 | `sql-filtrer-alertes`, `sql-agreger-ventes`, `sql-debug-classement` |
| Relier des tables sans perdre des lignes | SQL et conception de bases | DE p. 10 | `sql-joindre-commandes` |
| Résumer des groupes de lignes | SQL et conception de bases | DE p. 10 | `sql-joindre-commandes`, `sql-agreger-ventes` |
| Calculer dans une partition SQL | SQL et conception de bases | DE p. 10 | `sql-debug-classement` |
| Modifier les données et composer des requêtes | SQL et conception de bases | DE p. 10 ; PY p. 11, 12 | `schema-atelier`, `schema-stocks` |
| Concevoir un schéma relationnel | SQL et conception de bases | DE p. 9, 10, 11 ; PY p. 11, 12 | `schema-atelier`, `schema-stocks` |
| Faire respecter l’intégrité des données | SQL et conception de bases | DE p. 10, 11, 12 ; PY p. 11 | `schema-atelier`, `schema-stocks` |
| Raisonner sur transactions et index | SQL et conception de bases | DE p. 12 | Référence seulement |
| Relier objets Python et tables | SQL et conception de bases | PY p. 12 | Référence seulement |
| Échanger des données CSV et JSON | Manipulation et analyse des données | DE p. 5, 6 ; PY p. 7 | Référence seulement |
| Manipuler des tableaux numériques | Manipulation et analyse des données | DE p. 5 | Référence seulement |
| Transformer et agréger des DataFrame | Manipulation et analyse des données | DE p. 6, 7 | Référence seulement |
| Détecter et traiter les défauts de données | Manipulation et analyse des données | DE p. 7 | `py-bilan-qualite`, `py-extraire-journal` |
| Interpréter et formater des dates | Manipulation et analyse des données | DE p. 7 ; PY p. 8 | `py-extraire-journal` |
| Choisir une représentation des données | Manipulation et analyse des données | DE p. 7 | Référence seulement |
| Lire fonctions et coordonnées | Statistiques et mathématiques | DE p. 3, 4 | Référence seulement |
| Raisonner sur des vecteurs | Statistiques et mathématiques | DE p. 4 | Référence seulement |
| Raisonner sur des matrices | Statistiques et mathématiques | DE p. 4, 5 | Référence seulement |
| Décrire un événement probabiliste | Statistiques et mathématiques | DE p. 5 | Référence seulement |
| Résumer une distribution | Statistiques et mathématiques | DE p. 5 | Référence seulement |
| Situer les étapes d’une chaîne ETL | Data Engineering et ETL | DE p. 1, 13 | Référence seulement |
| Repérer les composants d’une orchestration | Data Engineering et ETL | DE p. 13 | Référence seulement |
| Diagnostiquer qualité et coût d’un traitement | Data Engineering et ETL | DE p. 14 | Référence seulement |
| Comprendre un modèle documentaire | NoSQL et systèmes de données | DE p. 11, 12 ; PY p. 12 | Référence seulement |
| Comprendre un stockage clé-valeur | NoSQL et systèmes de données | DE p. 13, 14 ; PY p. 12 | Référence seulement |
| Comparer les modèles non relationnels | NoSQL et systèmes de données | DE p. 13, 14 | Référence seulement |
| Repérer les compromis des systèmes distribués | NoSQL et systèmes de données | DE p. 12 | Référence seulement |
| Se repérer dans un système et son terminal | Linux, Docker et outils | DE p. 1, 12 ; PY p. 6, 9, 10 | Référence seulement |
| Comprendre les échanges réseau | Linux, Docker et outils | DE p. 3 ; PY p. 10 | Référence seulement |
| Versionner un projet avec Git | Linux, Docker et outils | DE p. 12, 13 ; PY p. 6 | Référence seulement |
| Décrire un environnement conteneurisé | Linux, Docker et outils | DE p. 13 ; PY p. 10 | Référence seulement |
| Organiser modules et environnements Python | Linux, Docker et outils | DE p. 3, 6 ; PY p. 6 | Référence seulement |
| Repérer les données dans des documents Web | Linux, Docker et outils | PY p. 7, 10, 11 | Référence seulement |
| Situer modèles et régression | Intelligence artificielle et technologies associées | DE p. 1, 7, 9 | Référence seulement |
| Repérer une chaîne de préparation textuelle | Intelligence artificielle et technologies associées | DE p. 8 | Référence seulement |
| Formuler une demande et en vérifier le résultat | Intelligence artificielle et technologies associées | DE p. 8 | Référence seulement |
| Identifier API, outils IA et intégrations | Intelligence artificielle et technologies associées | DE p. 8, 9, 11 ; PY p. 6, 7 | Référence seulement |
| Comprendre une recherche augmentée par des documents | Intelligence artificielle et technologies associées | DE p. 8, 9, 11 | Référence seulement |

## Premier ensemble d’exercices

Le lot contient quatre fonctions Python, quatre requêtes SQL de lecture et deux créations de schéma. Il couvre les cinq formats demandés : exercice ciblé, défi pratique, scénario professionnel, débogage et mini-projet. Les niveaux restent relatifs à ce premier lot : le dernier schéma combine davantage de contraintes, sans prétendre couvrir tout le niveau avancé du parcours.

| Identifiant | Format | Niveau | Moteur | Durée indicative |
|---|---|---|---|---|
| `py-normaliser-evenements` | Exercice ciblé | Débutant | python | 10 min |
| `py-total-categories` | Défi pratique | Débutant | python | 15 min |
| `py-bilan-qualite` | Scénario professionnel | Intermédiaire | python | 20 min |
| `py-extraire-journal` | Débogage | Intermédiaire | python | 25 min |
| `sql-filtrer-alertes` | Exercice ciblé | Débutant | sql | 8 min |
| `sql-joindre-commandes` | Scénario professionnel | Intermédiaire | sql | 20 min |
| `sql-agreger-ventes` | Défi pratique | Intermédiaire | sql | 15 min |
| `sql-debug-classement` | Débogage | Intermédiaire | sql | 20 min |
| `schema-atelier` | Mini-projet | Intermédiaire | schema | 30 min |
| `schema-stocks` | Mini-projet | Avancé dans ce lot | schema | 40 min |

Les exercices Python définissent des fonctions qui reçoivent leurs données en argument. Les entrées de référence sont des exemples autonomes, pas des fichiers installés implicitement sur le poste. La validation appelle les fonctions avec plusieurs jeux différents : un résultat recopié depuis l’exemple ne doit pas suffire. Les exercices SQL fournissent un fichier de démonstration contenant CREATE TABLE et INSERT ; le moteur utilise ses propres bases de validation isolées. Les exercices de schéma partent d’une base vide et vérifient les contraintes en réalisant de vraies opérations.

Les énoncés et exemples sont publics. Les validateurs et oracles sont dans des modules Python distincts qui ne sont pas servis comme fichiers statiques. Les trois indices de chaque exercice sont révélés sur demande par le service ; aucune solution ne s’affiche automatiquement. Un starter de débogage contient volontairement une erreur ; ce code n’est pas une solution recommandée.

## Format pour les ajouts futurs

`content/catalog.json` contient `version`, `sources`, `domains` et `skills`. Une source possède un identifiant stable, un titre, le type `study_plan`, un nombre de pages et une empreinte. Une compétence possède un identifiant stable, un domaine, une description, des références page par page et des prérequis par identifiant. Le graphe de prérequis ne doit pas comporter de cycle.

`content/exercises.json` contient `version` et `exercises`. Chaque exercice porte les champs documentés dans `TRAINING_CONTRACTS.md` : objectifs et consignes en français, contrat explicite, code de départ, exemple autonome avec nom de fichier, contraintes, critères de réussite, trois indices progressifs et identifiant de validateur. `sample.content` et `input_contract` sont des chaînes. Les types de moteur réellement disponibles sont `python`, `sql` et `schema`.

Pour ajouter un entraînement : créer son contenu original, choisir ses compétences et prérequis, implémenter un validateur avec plusieurs cas distincts, écrire une solution de référence réservée aux tests et des réponses incorrectes à refuser, puis exécuter la suite. Ajouter un JSON seul ne suffit pas à annoncer un exercice exécutable.

Pour ajouter un document : conserver une nouvelle source et son empreinte, contrôler les pages et mettre à jour les références. Passer `detailed_content_analyzed` à vrai exige un véritable document détaillé analysé. La première version ne propose ni téléversement automatique de PDF ni génération par IA. Ces fonctions peuvent être développées séparément, sans rendre la bibliothèque locale dépendante d’une API payante.

## Réutilisation et couverture future

Les ateliers Python, SQL, pipelines, explorateur et ER sont conservés et utilisés librement dans le Bac à sable. Le premier lot ne fournit pas de serveur MongoDB, Redis, Airflow, Docker, PGVector ou de ML. Ces technologies sont référencées honnêtement pour préparer la progression future. Les imports et environnements libres ne sont pas utilisés comme bases d’évaluation des exercices guidés.

Une exécution Python conserve les droits du compte local : les fixtures isolent les données d’évaluation, elles ne constituent pas une isolation de sécurité du système. La validation continue donc de respecter le consentement Python de l’application.

## Petit glossaire

- **ETL** : Extract, Transform, Load ; enchaînement d’extraction, transformation et chargement de données.
- **DataFrame** : structure tabulaire proposée notamment par pandas.
- **JOIN** : opération SQL qui relie des lignes de plusieurs sources selon une condition.
- **Grain** : ce que représente une ligne d’une table ou d’un résultat.
- **Clé composite** : clé composée de plusieurs colonnes dont la combinaison identifie une ligne.
- **DAG** : graphe orienté sans cycle, utilisé notamment pour décrire les dépendances d’un workflow.
- **Oracle de test** : méthode indépendante qui détermine le résultat attendu d’un cas de validation.
- **RAG** : génération augmentée par récupération de documents ; uniquement référencée dans ce lot.
- **Embedding** : représentation numérique d’un contenu, souvent utilisée pour comparer sa similarité à d’autres contenus.
