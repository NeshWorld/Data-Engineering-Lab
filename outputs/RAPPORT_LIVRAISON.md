# Rapport de livraison — Data Engineering Lab

**Date : 14 octobre 2026 — poste Windows, fuseau Europe/Paris.**

## Produit livré et lancement

Projet développé et livré dans **C:\Users\apapi\Data Engineering Lab**. Le répertoire existait et était vide avant toute modification. Aucun fichier appartenant à un autre projet n'a été modifié. Code, données fictives, tests, documentation, captures et espaces d'exécution restent dans ce répertoire. Quelques captures ont transité temporairement par un fichier autorisé de la session pour contourner une restriction du navigateur ; elles ont été déplacées dans outputs et aucune copie de projet n'a été créée ailleurs.

L'application est démarrée sur **http://127.0.0.1:8765** et son accueil a été laissé ouvert dans le navigateur intégré. Pour la relancer après arrêt : double-cliquer **Start-Lab.cmd**. Le moteur nécessite Python 3.12 ou plus ; python-path.txt pointe vers l'interpréteur existant vérifié sur ce poste. Laisser la fenêtre du moteur ouverte ; Ctrl+C l'arrête. La distribution est une application locale servie au navigateur, avec lanceur Windows, et non un exécutable Tauri autonome.

### Fonctionnalités opérationnelles

- Quatre environnements fictifs reproductibles : commerce/distribution, logistique, événements applicatifs et données imparfaites. Graine, volume de 0 à 10 000 faits principaux et anomalies choisissables. Sources CSV et JSON générées avec les bases.
- Commerce : magasins, stocks, clients, produits, commandes et lignes de commande ; relations et montants cohérents. Logistique : entrepôts, expéditions et événements horodatés. Événements : utilisateurs fictifs, sessions et actions. Données imparfaites : doublons, NULL, références orphelines, dates impossibles/décalées, formats incohérents, montants aberrants, textes mal décodés et enregistrements incomplets.
- SQL réel : requêtes libres, jointures, agrégations, CTE, sous-requêtes, transactions, vues, index et contraintes SQLite. Coloration SQL, schéma, relations, résultats tabulaires, erreurs, durées, historique et sauvegarde des requêtes.
- Python intégré : scripts personnels, consentement initial, espace propre avec copie de base et sources, stdout/stderr, exceptions, délais, annulation et inspection CSV/JSON. Mode terminal/IDE avec les mêmes fichiers et API. pandas testé réellement.
- Pipelines locaux : CSV, Python, validation, chargement SQLite, SQL et export ; ordre des étapes, dépendances, exécution complète ou isolée, statuts, entrées/sorties, erreurs et journaux. Exemple chargé uniquement à la demande.
- Exploration : lecture des tables, filtre WHERE en lecture seule, profils NULL/distinct/min/max/fréquences. Un filtre ne peut pas modifier la base.
- Environnements : création, injection/retrait des anomalies, reset, snapshots et restauration. Les expériences et historiques sont conservés.
- Observabilité : inspection et comparaison des exécutions, résultats A/B, écarts des lignes affichées par position et indication des résultats tronqués.
- Interface sombre sobre, sept pages, panneaux latéraux masquables, éditeurs et tableaux redimensionnables en hauteur, raccourcis clavier et états vides/erreurs fonctionnels.

### Fonctionnalités partielles et limites

- L'éditeur Python est volontairement simple. La coloration syntaxique est fournie pour SQL ; Python et JSON restent des éditeurs texte. Le constructeur de pipeline utilise un JSON modifiable et une liste d'étapes, sans graphe déplaçable à la souris.
- La validation de pipeline porte sur le CSV, le nombre de lignes et les colonnes requises ; il n'existe pas encore de moteur de règles métier extensif.
- Les résultats SQL affichent au plus 1 000 lignes et environ 2 Mo, avec cellules limitées ; le nombre réel est calculé jusqu'à interruption. Les exports tronqués sont refusés. La comparaison porte sur les résultats enregistrés et les lignes affichées, pas sur un rapprochement par clé métier.
- Les transactions sont locales à un appel SQL. Les modifications ne sont publiées que si le lot complet réussit. Les mesures locales incluent le fonctionnement de ce moteur et ne constituent pas des benchmarks scientifiques de disque.
- **Python n'est pas une sandbox.** Il conserve les droits du compte et peut accéder à des fichiers externes ou au réseau. La copie de travail protège des écrasements accidentels, pas d'un script malveillant. Pas de plafond strict de mémoire/disque ; des descendants volontairement détachés peuvent échapper à taskkill. Voir docs/SECURITY.md.
- Les modifications externes d'un fichier de script ne sont pas automatiquement réimportées dans l'éditeur intégré. La CLI lit directement le fichier modifié. Les éditions SQLite externes simultanées ne sont pas coordonnées par le verrou du moteur.
- La publication des fichiers gère le retour arrière sur erreur ordinaire, mais n'est pas atomique face à une panne système entre plusieurs remplacements. Les sauvegardes de récupération sont conservées si un retour arrière échoue aussi.
- PostgreSQL, Parquet/pyarrow, packaging Rust/Tauri, orchestration distribuée, import/export complet d'expériences et visualisations statistiques avancées sont reportés. Aucun service distant, compte ou télémétrie n'est nécessaire.

## Architecture

Python **3.12.14**, SQLite **3.53.1**, interface native HTML/CSS/JavaScript sans CDN. Bibliothèque standard pour le socle ; pandas facultatif disponible. Node **24.15.0** employé pour la validation syntaxique du code d'interface. Rust/cargo absent du PATH inspecté ; Tauri aurait imposé une chaîne de compilation supplémentaire. Le choix simple et hors ligne a été validé avant la délégation parallèle.

Modules distincts : génération (datasets), stockage/fermeture/retour arrière (storage), SQL et JSON strict (sql_engine), coordination/persistance/Python/pipelines (engine), adaptateur HTTP (server), interface (web), CLI et tests. Les interfaces et choix sont décrits dans docs/CONTRACTS.md et docs/ARCHITECTURE.md.

Les quatre bases principales ont été régénérées avec le générateur **1.1** avant livraison, après vérification de l'absence de travaux personnels dans ce catalogue. Le commerce livré contient 300 commandes, 774 lignes de commande, 60 clients, 30 produits, 2 magasins et 60 stocks. Les autres environnements contiennent chacun 300 faits principaux. Les essais personnels de QA restent dans work/ui-validation, distinct du catalogue principal.

## Orchestration réelle

Trois sous-agents indépendants ont réellement été exécutés, avec quatre places de concurrence incluant l'orchestrateur :

| Agent | Contributions réelles | Vérification et intégration |
| --- | --- | --- |
| architecture_research | Comparaison technique, documentation officielle ; puis QA adversariale et audit indépendant | Contrats validés par l'orchestrateur ; 19 tests moteur et 8 tests HTTP conçus indépendamment ; audit readonly des catalogues et preuves |
| datasets | Quatre générateurs, anomalies, sources et 13 tests | Tests exécutés par l'agent, puis rejoués par l'orchestrateur ; schémas, données et relations relus ; magasins/stocks et anomalies enrichis par l'orchestrateur |
| ui | Prototype et trois fichiers web, sept espaces, raccordements API ; correctif ciblé d'historique et comparaison | Syntaxe Node vérifiée ; parcours navigateur et captures inspectés par l'orchestrateur ; erreurs de concurrence et accès clavier corrigés |

L'orchestrateur a défini les contrats, développé le moteur/API/CLI, intégré les contributions, écrit 12 régressions supplémentaires, exécuté la suite finale et le parcours complet, corrigé les défauts et produit la documentation. Il n'a pas créé d'agents fictifs pour chaque rôle demandé : recherche/architecture puis QA/audit ont été regroupés dans le même agent, indépendant des implémentations moteur et UI.

Les droits d'écriture supplémentaires n'étaient pas propagés uniformément aux sous-agents et certaines reprises étaient refusées. Les tests QA et derniers correctifs UI ont donc été transmis en messages puis écrits par l'orchestrateur avec ses droits autorisés. Aucun emplacement alternatif permanent n'a été utilisé. Les propriétaires de fichiers étaient séparés avant l'intégration ; aucun conflit d'édition concurrent n'a été observé.

L'audit indépendant a contrôlé le code corrigé, l'intégrité des deux catalogues, les exécutions réellement persistées et les journaux de tests. Il n'a pas prétendu rejouer les tests avec écritures depuis son environnement restreint.

## Tests exécutés et résultats

**Suite finale : 52 tests exécutés, 52 réussis, 0 échec, 0 test ignoré, en 30,852 secondes.** Preuve : outputs/tests-python.txt.

- **13 tests génération** : déterminisme des dumps/exports, tailles 0 et 10 000 dans les quatre types, relations et intégrité, montants, chronologie, anomalies réversibles, validation des paramètres, préservation de l'état aléatoire global et nettoyage sur échec.
- **29 tests moteur** : SQL réel, transactions et commentaires, triggers avec points-virgules, FK, vues/index, rollback des lots même après COMMIT interne, limites de résultats, délais, vue récursive, refus ATTACH/VACUUM INTO/extensions/PRAGMA dangereux, profils et identifiants inhabituels, persistance/reset/snapshots, Python/JSON/pandas, consentement, sorties massives, exception, délai et annulation, copie de base, pipeline complet, DAG/cycles, CSV malformé, chemins externes, échec partiel et export tronqué.
- **10 tests HTTP réels** : création/requête/sauvegarde/reset, Host/Origin et requêtes intersites, doublons Host/Content-Length, JSON et taille, ressources statiques fermées, traversées de chemin, consentement et identifiants.
- Les cas JSON `NaN`, `Infinity`, nombres syntaxiquement valides débordant comme `1e999`, données JSON arbitraires et falsification du champ row_count sont couverts.
- Les remplacements de CSV volontairement défaillants vérifient la préservation de la base et des sources lors d'une génération ou restauration échouée ; les copies SQLite sont aussi bornées en présence d'un verrou externe.
- **Trois exécutions terminal supplémentaires réussies**, code de retour 0 pour SQL, Python et pipeline, sur les expériences sauvegardées de la fixture. Preuve : outputs/cli-checks.json. Les résultats retrouvent 24 commandes, 17 lignes après transformation et le compte final 17.
- La syntaxe du JavaScript final a été vérifiée par `node --check` après les dernières corrections.

### Parcours de bout en bout réellement vérifié

Contrôle du navigateur via CUA, sur une fixture séparée dans le projet : lancement ; création d'un commerce de 24 commandes avec graine 123 ; exploration des tables et profils ; requête SQL (24, somme 10 385,15) ; sauvegarde SQL par Ctrl+S ; script Python sauvegardé et consentement initial vérifié ; transformation vers 17 commandes non annulées ; pipeline de six étapes CSV → Python → validation → chargement SQLite → SQL → export ; inspection et comparaison des journaux ; snapshot ; injection d'un montant -42,5 et observation SQL ; réinitialisation ; retour au résultat initial ; vérification des trois expériences conservées ; restauration ; arrêt réel du moteur et redémarrage ; réouverture des expériences et historiques ; nouvelle exécution reproductible et comparaison A/B identique.

La fixture de ce premier parcours conserve une base créée avant l'enrichissement du générateur 1.1. Cela permet de vérifier que les données sauvegardées restent utilisables après mise à jour. Les bases principales livrées sont toutes en 1.1 ; la requête graphique finale par magasin a retourné 150 commandes par magasin, avec montants 175 190,17 et 172 245,95.

### Défauts détectés puis corrigés

Fermeture insuffisante des connexions SQLite sous Windows ; erreurs HTTP initialement dues au blocage des sockets par le bac à sable ; vue récursive bloquant le schéma ; CSV avec guillemet non refermé accepté ; lots SQL partiellement publiés ; transactions précédées de commentaires ; JSON non fini empoisonnant l'historique ; remplacement partiel de base/sources ; historique latéral non actualisé ; résultat JSON arbitraire interprété comme tableau ; concurrence de changement de table laissant un chargement figé ; annulation affichée active après fin ; sortie clavier de l'éditeur et lien d'accès au contenu ; encodage de sortie CLI Windows.

Le premier passage global n'était pas un succès : il avait 40 tests avec erreurs de fermeture et permissions réseau. Après correction et autorisation des échanges locaux, les suites successives ont réussi jusqu'aux 52 tests finaux. Les erreurs volontaires des scénarios adversariaux sont des comportements attendus, pas des tests échoués.

### Vérifications non réalisées ou échouées

Le lancement Playwright avec Edge existant a expiré après 180 secondes ; aucun test graphique Playwright n'est annoncé réussi. Le navigateur intégré a ensuite permis les contrôles effectifs et les captures. Pas d'audit WCAG complet, pas d'essai avec lecteur d'écran, pas de validation de plusieurs moniteurs physiques/DPI Windows, pas de benchmark intensif au-delà des volumes générateurs testés, ni de test de coupure de courant. L'interruption de descendants volontairement détachés n'est pas garantie.

## Qualité graphique et accessibilité

Vues réellement inspectées à **1920×1080**, **1280×800**, **960×720** et **760×640**. Les mesures DOM ont confirmé l'absence de débordement horizontal de page dans les contrôles ciblés ; les tableaux possèdent leur propre défilement. Les panneaux se réorganisent en fenêtre compacte, avec navigation horizontale défilable. Les dimensions full-page des images dépassent naturellement la hauteur du viewport et excluent parfois les 15 pixels de barre de défilement.

Captures conservées dans outputs :

| Fichier | Dimensions du fichier | Contenu |
| --- | --- | --- |
| accueil-1920.jpg | 1920×1080 | Accueil principal complet, quatre environnements |
| sql-1920.jpg | 1905×1642 | SQL final par magasin, six tables et relations |
| sql-1280.jpg | 1265×1772 | SQL de la fixture, requête sauvegardée et historique |
| explorer-960.jpg | 945×1614 | Explorer de la fixture, table et profil |
| pipeline-1920.jpg | 1905×2157 | Pipeline final à six étapes et résultats réels |
| pipeline-760.jpg | 745×1916 | Réorganisation compacte et bibliothèque persistée |

Les images ont été ouvertes/inspectées pendant la QA. Une première capture d'accueil rognée a été identifiée par l'audit puis remplacée par la capture complète ci-dessus.

Contrôles clavier : Ctrl+Entrée, Ctrl+S, Échap puis Tab pour quitter l'éditeur, lien Aller au contenu avec conservation de la page, focus du dialogue et panneau latéral masquable. L'annulation Python a aussi été déclenchée depuis l'interface (statut Annulé en 516 ms), ainsi que l'ajout, l'exécution isolée d'une étape CSV (24 lignes) et son retrait. Les tableaux ont été ajustés pour conserver les dates et valeurs sur une ligne avec défilement horizontal interne. Les noms de contrôles et états sont présents dans l'arbre d'accessibilité observé ; focus visible et préférence de mouvement réduit pris en charge. Contrastes calculés sur les couleurs réellement lues : texte principal/fond **15,36:1**, texte secondaire/surface **6,48:1**. Ces mesures ne constituent pas une certification complète de tous les états.

## Pistes d'évolution

Priorités raisonnables : import de modifications externes d'expériences ; règles de validation configurables ; graphiques de distributions plus riches ; packaging bureau et contrôle Windows des processus par Job Objects ; export/import versionné d'expériences ; Parquet avec dépendance facultative ; environnement PostgreSQL local seulement si son coût d'installation est justifié. Ces extensions n'ont pas été ajoutées au détriment du socle livré.
