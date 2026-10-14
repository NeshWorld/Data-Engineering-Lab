# Sécurité et limites réelles

## Données et réseau

Les quatre générateurs produisent uniquement des données fictives déterministes. Aucune source métier réelle, aucun ERP, aucun secret et aucune connexion distante ne sont intégrés. Le serveur écoute 127.0.0.1, vérifie Host/Origin et refuse les requêtes intersites. Les mutations exigent un objet JSON avec taille explicite. Aucun CORS permissif. La liste des fichiers servis est fermée : le serveur n'expose ni bases, ni scripts, ni chemins arbitraires. Le serveur local repose sur http.server, adapté à ce laboratoire personnel ; il ne doit pas être exposé sur un réseau ou utilisé comme serveur de production.

## SQL

Le SQL est réellement exécuté par SQLite. ATTACH, DETACH, VACUUM INTO, load_extension et les PRAGMA non autorisés sont refusés. trusted_schema est désactivé. Les opérations SQLite s'exécutent sur une copie mémoire de la base ; les changements sont publiés dans la base locale seulement si toute la requête réussit. Cela préserve les données même lorsqu'un COMMIT interne précède une erreur ultérieure dans le même lot. Une transaction ne survit pas entre deux clics Exécuter ; toute transaction encore ouverte est validée à la fin d'une requête réussie. Pour tester BEGIN/COMMIT/ROLLBACK, fournissez les instructions dans la même requête.

Les instructions SQL sont interrompues après cinq secondes via un gestionnaire de progression. Les copies SQLite ont aussi un délai sur leurs tentatives de reprise ; les verrous externes peuvent ajouter un délai d'entrée/sortie borné. Maximum 256 colonnes ; 1 000 lignes et environ 2 Mo affichés, cellules texte limitées à 20 000 caractères. Le nombre total est compté jusqu'au délai maximal. Un indicateur signale toute troncature. Une requête trop coûteuse produit une erreur et ne publie aucun changement. Les durées sont des mesures locales de cette exécution, pas des benchmarks scientifiques de stockage disque. Le schéma et le profilage possèdent aussi un délai d'interruption.

## Python personnel : PAS une sandbox

La confirmation avant la première exécution est enregistrée localement. **Un sous-processus Python conserve les droits de votre compte Windows.** `-I`, un environnement réduit et un répertoire propre ne constituent pas une barrière de sécurité. Un script peut lire/écrire ailleurs, utiliser le réseau, lancer des descendants ou endommager des fichiers s'il le demande explicitement. Exécutez seulement du code que vous comprenez. L'application n'ajoute aucune connexion distante ; un script personnel peut en effectuer.

Chaque exécution travaille par défaut dans `work/runs/ID` avec une copie de la base et des sources. Cette séparation prévient l'écrasement accidentel de l'environnement courant ; elle n'empêche pas les chemins absolus ou `..` dans le code Python. Le moteur de pipeline contrôle ses propres chemins de fichiers, pas ceux écrits par Python. Aucun conteneur ni mécanisme d'isolation de sécurité Windows n'est annoncé.

Le délai Python est de 30 secondes par défaut, configurable entre 1 et 120 secondes via l'API. Les sorties stdout/stderr sont drainées continuellement avec 64 Kio conservés par flux et par étape, puis une limite d'historique cumulée. Le code peut malgré cela produire beaucoup de fichiers ou consommer de la mémoire : aucune limite stricte mémoire/disque n'est fournie. Sous Windows, annulation/délai utilisent taskkill /T /F sur l'identifiant exact du processus, puis kill en repli. Cela vise l'arbre courant ; un descendant volontairement détaché peut échapper au mécanisme. Il n'y a pas de Job Object de confinement.

## Pipelines et persistance

Le moteur est local, séquentiel et déterministe pour une même configuration et les mêmes entrées. Les scripts personnels peuvent introduire leur propre non-déterminisme. Dépendances validées, cycles refusés, arrêt à la première erreur. Les étapes déjà terminées gardent leurs sorties dans l'espace de l'exécution échouée ; il n'y a pas de transaction globale sur les fichiers. Le résultat SQL affiché est limité ; un export tronqué est refusé pour éviter un fichier incomplet silencieux.

La publication de la base, du CSV et du JSON conserve des copies de secours et annule les remplacements déjà effectués si un remplacement suivant échoue. Si le retour arrière échoue lui aussi (verrou externe), une erreur indique les copies `.rollback-` laissées à côté des fichiers pour récupération. Ce mécanisme ne constitue pas une transaction atomique face à une coupure de courant entre deux remplacements. Fermez les outils externes avant de régénérer ou restaurer.

Une réinitialisation ou restauration ne supprime jamais `experiments/` ni les historiques. Les copies d'exécution sont indépendantes des réinitialisations ultérieures. Ne modifiez pas manuellement les fichiers du catalogue pendant que le serveur tourne. La sauvegarde porte sur les données d'un environnement et ses sources, pas sur l'ensemble du projet. Les espaces d'exécution ne sont pas purgés automatiquement : leur suppression manuelle dans le répertoire du laboratoire doit être un choix explicite.

## Hors périmètre initial

Pas de PostgreSQL, Parquet (pyarrow absent), ordonnanceur distribué, packaging Tauri, éditeur IDE complet, graphe de pipeline déplaçable à la souris, ni authentification multi-utilisateur. L'éditeur intégré reste simple. Les limites graphiques et tests effectivement exécutés figurent dans le rapport de livraison.

La reproduction par graine suppose la même version du générateur (champ generator_version). Une sauvegarde ou un espace de run conserve les données effectives et permet leur inspection après une mise à jour du générateur.
