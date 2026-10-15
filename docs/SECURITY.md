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

## Entraînement et opérations structurées

Le nom « Bac à sable » désigne un espace d’expérimentation : il ne fournit pas de confinement système. La validation Python requiert le même consentement que l’atelier et conserve les droits du compte. Les contraintes pédagogiques interdisant réseau/fichiers ne sont pas des barrières de sécurité. Les tests locaux ne sont pas un système anti-triche : le propriétaire du poste contrôle son code, les validateurs et les fichiers. Les solutions de référence restent réservées aux tests et ne sont pas servies par l’API.

Chaque validation possède trois cas, un délai Python de trois secondes par cas et un budget vérifié de vingt secondes entre les cas ; une opération déjà engagée reste soumise à son propre délai. La sortie structurée Python est limitée à 1 Mo ; le code à 200 000 caractères et les notes à 5 000. Une réponse incorrecte, une annulation et une erreur technique ont des états distincts. Une réussite ne certifie pas la maîtrise d’une compétence.

Les nouveaux endpoints conservent les vérifications Host/Origin et le plafond HTTP de 1 Mo. Les imports acceptent du texte CSV/JSON de 750 Kio maximum et 10 000 lignes, sans chemin de fichier fourni au serveur. Ils refusent les objets imbriqués et valeurs non finies. Les identifiants SQL sont cités et les valeurs liées. Les éditions/suppressions de lignes exigent une clé primaire complète et une seule ligne correspondante ; l’interface refuse les entiers dont JavaScript perdrait la précision. L’export limite à 10 000 lignes et 5 Mo sans troncature silencieuse ; les BLOB ne sont pas exportés par ce premier lot.

Les snapshots automatiques protègent les opérations destructrices des formulaires. Le SQL libre et Python conservent les comportements et limites des ateliers : créer un snapshot manuel avant une expérimentation risquée reste possible. Les fichiers personnels ne sont jamais utilisés comme fixtures d’évaluation.
