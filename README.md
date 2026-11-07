# Jeu des pouvoirs

Application web multijoueur pour 4 à 6 personnes. Le serveur applique les pouvoirs des cartes ; chaque joueur rejoint un salon par son nom, et ne reçoit que les cartes de sa propre main.

## Règles de distribution implémentées

- **4 joueurs :** chaque joueur tire une carte absolue. La carte la plus forte et la plus faible déterminent une équipe ; les deux autres joueurs forment l'autre équipe. Chaque main commence avec la carte tirée et est complétée à cinq cartes.
- **5 joueurs :** même tirage ; la carte la plus forte et la    plus faible sont dans l'équipe de deux (quatre cartes par main), les trois autres dans l'équipe de trois (cinq cartes par main).
- **6 joueurs :** jeu individuel, cinq cartes par joueur, sans tirage d'équipe.
- Un paquet ne contient qu'un exemplaire de chaque carte. Les cartes sont distribuées sans remise ; les mains et la pioche ne partagent pas de doublons.
- Les équipes définies par tirage restent les mêmes pendant les parties du match. Une nouvelle distribution complète est faite entre les parties. Un nouveau match recommence le tirage d'équipe à 4 ou 5 joueurs.

Un match se gagne après deux parties remportées.
Les pouvoirs sont détaillés dans `main.py` et les choix de jeu sont validés par le serveur.


## Héberger avec GitHub et Render

GitHub stocke le code ; le serveur Render exécute le jeu et sert le site.

Le site est accessible avec le lien suivant : **https://jeu-des-pouvoirs.onrender.com/**

Le fichier `render.yaml` configure un seul processus web. C'est nécessaire pour ce prototype car les salons actifs sont conservés en mémoire.


## Parcours d'une partie

1. Un joueur crée un salon avec un nom unique et attend que les autres le rejoignent depuis la liste des salons ouverts.
2. Dès que le groupe est complet et connecté, le bouton de démarrage est disponible pour tous les joueurs.
3. À 4 ou 5 joueurs, chacun tire une carte absolue dans le salon. Une fois le tirage complet, les équipes sont révélées et la première distribution commence.
4. À 6 joueurs, le match individuel commence immédiatement.
5. Le joueur dont c'est le tour choisit une carte. Quand un pouvoir demande la décision d'un autre joueur, celui-ci reçoit son propre choix à l'écran.
6. Une fois que chaque joueur a posé une carte, les défausses sont résolues.
7. Si personne n'a épuisé sa main, le tour suivant commence automatiquement avec les cartes restantes. Quand une partie est gagnée, n'importe quel joueur peut lancer la distribution suivante. Après le match, n'importe quel joueur peut créer un nouveau match dans le même salon.
