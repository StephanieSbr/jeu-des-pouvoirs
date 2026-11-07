# Jeu des pouvoirs

Application web multijoueur pour 4 à 6 personnes. Le serveur applique les
pouvoirs des cartes ; chaque joueur rejoint le même salon depuis son ordinateur
avec un code, et ne reçoit que les cartes de sa propre main.

## Règles de distribution implémentées

- **4 joueurs :** chaque joueur tire une carte absolue. La carte la plus forte
  et la plus faible déterminent une équipe ; les deux autres joueurs forment
  l'autre équipe. Chaque main commence avec la carte tirée et est complétée à
  cinq cartes.
- **5 joueurs :** même tirage ; la carte la plus forte et la plus faible sont
  dans l'équipe de deux (quatre cartes par main), les trois autres dans l'équipe
  de trois (cinq cartes par main).
- **6 joueurs :** jeu individuel, cinq cartes par joueur, sans tirage d'équipe.
- Un paquet ne contient qu'un exemplaire de chaque carte. Les cartes sont
  distribuées sans remise ; les mains et la pioche ne partagent pas de doublons.
- Les équipes définies par tirage restent les mêmes pendant les parties du
  match. Une nouvelle distribution complète est faite entre les parties. Un
  nouveau match recommence le tirage d'équipe à 4 ou 5 joueurs.
- Une carte 30–35 jouée comme dernière carte fait piocher une carte ; cette
  carte est échangée contre une carte choisie par le joueur ciblé.

Un match se gagne après deux parties remportées, avec au plus trois parties.
Les pouvoirs sont détaillés dans `main.py` et les choix de jeu sont validés par
le serveur.

## Tester sur son ordinateur

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Ouvre ensuite <http://127.0.0.1:5000>. Cela rend le site accessible seulement
sur l'ordinateur qui exécute le serveur. Pour jouer depuis d'autres réseaux,
déploie l'application (étapes ci-dessous).

## Héberger avec GitHub et Render

GitHub stocke le code ; le serveur Render exécute le jeu et sert le site.

1. Enregistre ces fichiers dans ton dépôt GitHub.
2. Crée un compte Render et autorise Render à accéder au dépôt GitHub.
3. Dans Render, choisis **New → Blueprint**, sélectionne le dépôt et confirme
   la configuration lue dans `render.yaml`. Le service est configuré sur
   l'offre gratuite (`plan: free`).
4. Attends la fin du déploiement, puis ouvre l'adresse HTTPS fournie par Render.
5. Crée un salon, choisis 4, 5 ou 6 joueurs et partage le code aux autres.
   Chacun ouvre la même adresse, saisit son nom et rejoint le salon.

Le fichier `render.yaml` configure un seul processus web. C'est nécessaire
pour ce prototype car les salons actifs sont conservés en mémoire. Un
redémarrage ou une mise en veille qui relance le processus efface les salons et
les parties en cours. Les scores ne sont pas sauvegardés durablement ; ajoute
une base de données avant de considérer le site comme un service permanent.
L'offre gratuite peut mettre le service en veille après 15 minutes sans visite ;
le premier chargement suivant peut prendre environ une minute.

Pour héberger ailleurs, installe `requirements.txt` et démarre le serveur avec
`gunicorn --workers 1 --threads 8 --bind 0.0.0.0:$PORT app:app`. Configure une
variable d'environnement `SECRET_KEY` privée et stable ; ne la publie jamais
dans GitHub. Si le navigateur est servi en HTTPS, active aussi
`COOKIE_SECURE=1`.

## Parcours d'une partie

1. Un joueur crée un salon et attend que tous les joueurs le rejoignent.
2. Dès que le groupe est complet et connecté, le bouton de démarrage est
   disponible pour tous les joueurs.
3. À 4 ou 5 joueurs, chacun tire une carte absolue dans le salon. Une fois le
   tirage complet, les équipes sont révélées et la première distribution commence.
4. À 6 joueurs, le match individuel commence immédiatement.
5. Le joueur dont c'est le tour choisit une carte. Quand un pouvoir demande la
   décision d'un autre joueur, celui-ci reçoit son propre choix à l'écran.
6. Une fois que chaque joueur a posé une carte, les défausses sont résolues.
   Si une 13 demande une défausse supplémentaire, son propriétaire choisit sa
   carte lui-même.
7. Si personne n'a épuisé sa main, le tour suivant commence automatiquement
   avec les cartes restantes. Quand une partie est gagnée, n'importe quel joueur
   peut lancer la distribution suivante. Après le match, n'importe quel joueur
   peut créer un nouveau match dans le même salon.

Chaque joueur peut quitter avec le bouton **Quitter le jeu**. Fermer l'onglet
signale aussi son départ ; si le navigateur n'envoie pas ce signal, le serveur
le détecte après environ 12 secondes sans activité. Dans le salon d'attente, le
joueur est retiré. En cours de match, la partie est mise en pause et ce joueur
peut revenir avec le même nom et le code du salon ; les actions reprennent après
son retour.

Les pouvoirs de révélation restent privés dans l'interface : les mains des
adversaires ne sont jamais renvoyées au navigateur d'un autre joueur.

Pendant une partie, la table est disposée en cercle : ton siège est en bas,
les autres suivent dans le sens horaire. Les cartes sont affichées par image ;
les noms des coéquipiers partagent une couleur, les noms en jeu individuel
restent noirs, et les défausses du tour précédent apparaissent en haut à droite.
