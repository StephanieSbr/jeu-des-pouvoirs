import unittest

import main


class ConfigurationMatchTests(unittest.TestCase):
    def test_last_turn_discards_are_kept_separately_for_the_next_turn(self):
        jeu = main.Jeu(["A", "B", "C", "D"])
        jeu.demarrer_match({"A": 30, "B": 31, "C": 34, "D": 35})
        partie = jeu.partie
        partie.en_jeu = {
            "A": main.CartePosee(main.CARTES[1], "A", "A"),
            "B": main.CartePosee(main.CARTES[4], "B", "B"),
            "C": main.CartePosee(main.CARTES[8], "C", "C"),
            "D": main.CartePosee(main.CARTES[18], "D", "D"),
        }
        partie.joueurs_ayant_joue = {"A", "B", "C", "D"}

        jeu.terminer_tour()

        self.assertEqual(set(partie.dernieres_defausses), {1, 4, 8, 18})
        self.assertEqual(set(partie.derniers_defausseurs), {"A", "B", "C", "D"})

    def test_four_players_keep_drawn_absolutes_and_get_five_cards(self):
        jeu = main.Jeu(["A", "B", "C", "D"])
        cartes_tirees = {"A": 30, "B": 31, "C": 34, "D": 35}
        partie = jeu.demarrer_match(cartes_tirees)

        self.assertEqual(len(partie.pioche), 13)
        self.assertEqual({joueur.nom: len(joueur.main) for joueur in jeu.joueurs}, {
            "A": 5,
            "B": 5,
            "C": 5,
            "D": 5,
        })
        self.assertIs(jeu.joueurs[0].equipe, main.Equipe.A)
        self.assertIs(jeu.joueurs[3].equipe, main.Equipe.A)
        self.assertEqual(
            {carte.score for joueur in jeu.joueurs for carte in joueur.main}
            & set(cartes_tirees.values()),
            set(cartes_tirees.values()),
        )
        self.assertEqual(
            len({carte.score for joueur in jeu.joueurs for carte in joueur.main}),
            20,
        )
        cartes_en_jeu = {
            carte.score for joueur in jeu.joueurs for carte in joueur.main
        } | {carte.score for carte in partie.pioche}
        absolues_tirees = set(cartes_tirees.values())
        self.assertTrue(absolues_tirees <= cartes_en_jeu)
        self.assertFalse(({30, 31, 32, 33, 34, 35} - absolues_tirees) & cartes_en_jeu)
        for joueur in jeu.joueurs:
            absolues_en_main = {
                carte.score for carte in joueur.main if carte.score in absolues_tirees
            }
            self.assertEqual(absolues_en_main, {cartes_tirees[joueur.nom]})

    def test_five_players_have_two_small_and_three_large_hands(self):
        jeu = main.Jeu(["A", "B", "C", "D", "E"])
        cartes_tirees = {"A": 30, "B": 31, "C": 32, "D": 34, "E": 35}
        partie = jeu.demarrer_match(cartes_tirees)
        taille_par_equipe = {}
        for joueur in jeu.joueurs:
            taille_par_equipe.setdefault(joueur.equipe, set()).add(len(joueur.main))

        self.assertEqual(len(partie.pioche), 11)
        self.assertEqual(
            sorted(len(joueurs) for joueurs in (
                [j for j in jeu.joueurs if j.equipe is equipe]
                for equipe in main.Equipe
            )),
            [2, 3],
        )
        self.assertEqual(taille_par_equipe[main.Equipe.A], {4})
        self.assertEqual(taille_par_equipe[main.Equipe.B], {5})

    def test_six_players_are_individual_and_get_five_cards(self):
        jeu = main.Jeu(["A", "B", "C", "D", "E", "F"])
        partie = jeu.demarrer_match()

        self.assertTrue(jeu.individuel)
        self.assertTrue(all(joueur.equipe is None for joueur in jeu.joueurs))
        self.assertTrue(all(len(joueur.main) == 5 for joueur in jeu.joueurs))
        self.assertEqual(len(partie.pioche), 5)
        self.assertEqual(set(jeu.victoires_joueurs), {"A", "B", "C", "D", "E", "F"})

    def test_next_party_uses_full_shuffled_deck_and_same_teams(self):
        jeu = main.Jeu(["A", "B", "C", "D", "E"])
        jeu.demarrer_match({"A": 30, "B": 31, "C": 32, "D": 34, "E": 35})
        teams = {joueur.nom: joueur.equipe for joueur in jeu.joueurs}
        jeu.terminer_partie(main.Equipe.A)
        partie = jeu.demarrer_partie()

        self.assertEqual(len(partie.pioche), 12)
        self.assertEqual(teams, {joueur.nom: joueur.equipe for joueur in jeu.joueurs})
        self.assertTrue(
            all(
                len(joueur.main) == (4 if joueur.equipe is main.Equipe.A else 5)
                for joueur in jeu.joueurs
            )
        )

    def test_six_players_can_continue_past_three_parties_until_a_player_wins_twice(self):
        jeu = main.Jeu(["A", "B", "C", "D", "E", "F"])
        jeu.demarrer_match()

        jeu.terminer_partie(joueur="A")
        jeu.demarrer_partie()
        jeu.terminer_partie(joueur="B")
        jeu.demarrer_partie()
        jeu.terminer_partie(joueur="C")
        fourth_partie = jeu.demarrer_partie()

        self.assertEqual(fourth_partie.numero, 4)
        self.assertFalse(jeu.match_termine)

        jeu.terminer_partie(joueur="A")

        self.assertEqual(jeu.joueur_gagnant_match, "A")
        self.assertTrue(jeu.match_termine)
        with self.assertRaises(RuntimeError):
            jeu.demarrer_partie()

    def test_team_matches_keep_the_three_party_limit(self):
        jeu = main.Jeu(["A", "B", "C", "D"])
        jeu.demarrer_match({"A": 30, "B": 31, "C": 34, "D": 35})

        jeu.terminer_partie(main.Equipe.A)
        jeu.demarrer_partie()
        jeu.terminer_partie(main.Equipe.B)
        jeu.demarrer_partie()
        jeu.terminer_partie(main.Equipe.A)

        with self.assertRaises(RuntimeError):
            jeu.demarrer_partie()


class WebSalonTests(unittest.TestCase):
    def setUp(self):
        from app import app, _ROOMS, _ROOMS_LOCK

        self.app = app
        self.app.config.update(TESTING=True)
        self.rooms = _ROOMS
        self.rooms_lock = _ROOMS_LOCK
        with self.rooms_lock:
            self.rooms.clear()

    def test_turn_resolution_keeps_the_current_game_active_when_hands_remain(self):
        from app import JoueurSalon, Salon, _etat_public, _resoudre_tour

        jeu = main.Jeu(["A", "B", "C", "D"])
        jeu.demarrer_match({"A": 30, "B": 31, "C": 34, "D": 35})
        partie = jeu.partie
        partie.en_jeu = {
            nom: main.CartePosee(main.CARTES[score], nom, nom)
            for nom, score in zip(("A", "B", "C", "D"), (17, 18, 19, 20))
        }
        partie.joueurs_ayant_joue = {"A", "B", "C", "D"}
        salon = Salon(
            "ABC123",
            4,
            [JoueurSalon(nom, nom) for nom in ("A", "B", "C", "D")],
            "A",
            phase="active",
            jeu=jeu,
        )

        _resoudre_tour(salon)

        self.assertEqual(salon.phase, "active")
        self.assertFalse(partie.terminee)
        self.assertEqual(partie.nombre_tours, 1)
        self.assertTrue(all(joueur.main for joueur in jeu.joueurs))
        self.assertEqual(jeu.joueur_courant.nom, "D")
        resume = _etat_public(salon, "A")["resume_tour"]
        self.assertEqual(
            resume,
            {"gagnant": "D", "defausseurs": ["A", "D"], "commence": "D"},
        )

    def test_turn_resolution_offers_the_next_deal_when_a_player_runs_out(self):
        from app import JoueurSalon, Salon, _resoudre_tour

        jeu = main.Jeu(["A", "B", "C", "D"])
        jeu.demarrer_match({"A": 30, "B": 31, "C": 34, "D": 35})
        partie = jeu.partie
        partie.en_jeu = {}
        for joueur in jeu.joueurs:
            carte = joueur.main.pop()
            joueur.main.clear()
            partie.en_jeu[joueur.nom] = main.CartePosee(
                carte,
                joueur.nom,
                joueur.nom,
            )
        partie.joueurs_ayant_joue = {"A", "B", "C", "D"}
        salon = Salon(
            "ABC123",
            4,
            [JoueurSalon(nom, nom) for nom in ("A", "B", "C", "D")],
            "A",
            phase="active",
            jeu=jeu,
        )

        _resoudre_tour(salon)

        self.assertEqual(salon.phase, "entre_parties")
        self.assertTrue(partie.terminee)

    def test_six_player_room_offers_a_fourth_party(self):
        from app import JoueurSalon, Salon, _resoudre_tour

        names = ["A", "B", "C", "D", "E", "F"]
        jeu = main.Jeu(names)
        jeu.demarrer_match()
        jeu.terminer_partie(joueur="A")
        jeu.demarrer_partie()
        jeu.terminer_partie(joueur="B")
        partie = jeu.demarrer_partie()
        partie.en_jeu = {}
        for joueur, score in zip(jeu.joueurs, (17, 18, 19, 20, 25, 26)):
            joueur.main.clear()
            partie.en_jeu[joueur.nom] = main.CartePosee(
                main.CARTES[score],
                joueur.nom,
                joueur.nom,
            )
        partie.joueurs_ayant_joue = set(names)
        salon = Salon(
            "ABC123",
            6,
            [JoueurSalon(nom, nom) for nom in names],
            "A",
            phase="active",
            jeu=jeu,
        )

        _resoudre_tour(salon)

        self.assertEqual(salon.phase, "entre_parties")
        self.assertEqual(jeu.parties_jouees, 3)

    def _client(self):
        client = self.app.test_client()
        client.get("/")
        with client.session_transaction() as browser_session:
            csrf = browser_session["csrf"]
        return client, csrf

    def _post(self, client, csrf, route, payload=None):
        return client.post(
            route,
            json=payload or {},
            headers={"X-CSRF-Token": csrf},
        )

    def test_private_room_draw_and_hands_are_per_player(self):
        host, host_csrf = self._client()
        response = self._post(
            host,
            host_csrf,
            "/api/salons",
            {"nom": "Alice", "nom_salon": "Partie test", "nombre_joueurs": 4},
        )
        self.assertEqual(response.status_code, 200)
        nom_salon = response.get_json()["nom_salon"]

        clients = [(host, host_csrf)]
        for name in ("Benoit", "Camille", "David"):
            client, csrf = self._client()
            joined = self._post(
                client,
                csrf,
                "/api/rejoindre",
                {"nom": name, "nom_salon": nom_salon},
            )
            self.assertEqual(joined.status_code, 200)
            clients.append((client, csrf))

        self.assertEqual(self._post(host, host_csrf, "/api/demarrer").status_code, 200)
        waiting_to_draw = host.get("/api/etat").get_json()
        self.assertEqual(waiting_to_draw["phase"], "tirage")
        self.assertEqual(waiting_to_draw["tirages_publics"], [])
        self.assertEqual(waiting_to_draw["tirages_valides"], 0)
        for index, (client, csrf) in enumerate(clients):
            self.assertEqual(self._post(client, csrf, "/api/tirer").status_code, 200)
            states = [client.get("/api/etat").get_json() for client, _ in clients]
            phase = "revelation" if index == len(clients) - 1 else "tirage"
            self.assertTrue(all(state["phase"] == phase for state in states))
            self.assertTrue(
                all(len(state["tirages_publics"]) == index + 1 for state in states)
            )

        states = [client.get("/api/etat").get_json() for client, _ in clients]
        self.assertTrue(all(state["phase"] == "revelation" for state in states))
        for state in states:
            self.assertEqual(len(state["tirages_publics"]), 4)
            self.assertEqual(
                {tirage["nom"] for tirage in state["tirages_publics"]},
                {"Alice", "Benoit", "Camille", "David"},
            )
        for index, (client, csrf) in enumerate(clients):
            self.assertEqual(
                self._post(client, csrf, "/api/voir-absolues").status_code,
                200,
            )
            states = [client.get("/api/etat").get_json() for client, _ in clients]
            phase = "active" if index == len(clients) - 1 else "revelation"
            self.assertTrue(all(state["phase"] == phase for state in states))

        states = [client.get("/api/etat").get_json() for client, _ in clients]
        self.assertTrue(all(state["phase"] == "active" for state in states))
        self.assertTrue(all(state["tirages_publics"] == [] for state in states))
        self.assertTrue(all(len(state["main"]) == 5 for state in states))
        for state in states:
            self.assertNotIn("main", state["joueurs"][0])
            self.assertEqual(
                sum(player["cartes_en_main"] for player in state["joueurs"])
                + state["pioche_restante"],
                33,
            )

    def test_room_names_are_unique_case_insensitively(self):
        owner, csrf = self._client()
        created = self._post(
            owner,
            csrf,
            "/api/salons",
            {"nom": "Alice", "nom_salon": "Soirée", "nombre_joueurs": 4},
        )
        self.assertEqual(created.status_code, 200)

        duplicate_client, duplicate_csrf = self._client()
        duplicate = self._post(
            duplicate_client,
            duplicate_csrf,
            "/api/salons",
            {"nom": "Benoit", "nom_salon": "  SOIRÉE ", "nombre_joueurs": 5},
        )

        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("déjà utilisé", duplicate.get_json()["error"])
        listed = self._client()[0].get("/api/salons").get_json()["salons"]
        self.assertEqual([salon["nom"] for salon in listed], ["Soirée"])

    def test_only_room_creator_can_close_a_listed_room(self):
        host, host_csrf = self._client()
        nom_salon = self._post(
            host,
            host_csrf,
            "/api/salons",
            {"nom": "Alice", "nom_salon": "Partie publique", "nombre_joueurs": 4},
        ).get_json()["nom_salon"]
        clients = [(host, host_csrf)]
        for name in ("Benoit", "Camille", "David"):
            client, csrf = self._client()
            response = self._post(
                client,
                csrf,
                "/api/rejoindre",
                {"nom": name, "nom_salon": nom_salon},
            )
            self.assertEqual(response.status_code, 200)
            clients.append((client, csrf))

        self.assertEqual(self._post(host, host_csrf, "/api/demarrer").status_code, 200)
        listing = clients[1][0].get("/api/salons").get_json()["salons"]
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]["phase"], "tirage")
        self.assertEqual(listing[0]["nom"], nom_salon)
        self.assertFalse(listing[0]["peut_cloturer"])

        forbidden = self._post(
            clients[1][0],
            clients[1][1],
            "/api/cloturer",
            {"nom_salon": nom_salon},
        )
        self.assertEqual(forbidden.status_code, 403)

        closed = self._post(
            host,
            host_csrf,
            "/api/cloturer",
            {"nom_salon": nom_salon},
        )
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(host.get("/api/salons").get_json()["salons"], [])
        self.assertEqual(clients[1][0].get("/api/etat").status_code, 401)

    def test_every_card_image_is_served(self):
        client = self.app.test_client()
        for score in range(1, 36):
            with self.subTest(score=score):
                response = client.get("/cartes/{}.png".format(score))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, "image/png")

    def test_rules_image_is_served(self):
        response = self.app.test_client().get("/regles.png")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")

    def test_homepage_uses_versioned_frontend_assets(self):
        response = self.app.test_client().get("/")
        self.assertIn(b"game.js?v=20261107-12", response.data)
        self.assertIn(b"style.css?v=20261107-12", response.data)

    def test_display_colors_match_card_colors_and_black_for_17(self):
        from app import _couleur_affichage

        expected = {
            1: "vert",
            9: "jaune",
            18: "rouge",
            30: "bleu",
            17: "noir",
        }
        for score, color in expected.items():
            with self.subTest(score=score):
                self.assertEqual(_couleur_affichage(score), color)

    def test_private_card_revelation_uses_image_without_printing_its_number(self):
        from app import _message_revelation

        message = _message_revelation("Alice", 17)
        self.assertEqual(message["image"], "/cartes/17.png")
        self.assertNotIn("17", message["texte"])

    def test_csrf_is_required_for_mutating_routes(self):
        client, _ = self._client()
        response = client.post(
            "/api/salons",
            json={"nom": "Alice", "nombre_joueurs": 4},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("session", response.get_json()["error"].lower())

    def test_any_connected_player_can_start_a_full_room(self):
        clients = []
        for index, name in enumerate(("Alice", "Benoit", "Camille", "David")):
            client, csrf = self._client()
            if index == 0:
                response = self._post(
                    client,
                    csrf,
                    "/api/salons",
                    {
                        "nom": name,
                        "nom_salon": "Salon de test",
                        "nombre_joueurs": 4,
                    },
                )
                nom_salon = response.get_json()["nom_salon"]
            else:
                self._post(
                    client,
                    csrf,
                    "/api/rejoindre",
                    {"nom": name, "nom_salon": nom_salon},
                )
            clients.append((client, csrf))

        states = [client.get("/api/etat").get_json() for client, _ in clients]
        self.assertTrue(all(state["peut_commencer"] for state in states))
        self.assertEqual(self._post(clients[-1][0], clients[-1][1], "/api/demarrer").status_code, 200)

    def test_leaving_waiting_room_frees_the_seat(self):
        host, host_csrf = self._client()
        created = self._post(
            host,
            host_csrf,
            "/api/salons",
            {"nom": "Alice", "nom_salon": "Salon ouvert", "nombre_joueurs": 4},
        )
        nom_salon = created.get_json()["nom_salon"]
        guest, guest_csrf = self._client()
        self._post(
            guest,
            guest_csrf,
            "/api/rejoindre",
            {"nom": "Benoit", "nom_salon": nom_salon},
        )

        self.assertEqual(self._post(guest, guest_csrf, "/api/quitter").status_code, 200)
        newcomer, newcomer_csrf = self._client()
        joined = self._post(
            newcomer,
            newcomer_csrf,
            "/api/rejoindre",
            {"nom": "Camille", "nom_salon": nom_salon},
        )
        self.assertEqual(joined.status_code, 200)
        self.assertEqual(len(host.get("/api/etat").get_json()["joueurs"]), 2)

    def test_depart_during_match_pauses_until_same_player_rejoins(self):
        host, host_csrf = self._client()
        nom_salon = self._post(
            host,
            host_csrf,
            "/api/salons",
            {"nom": "Alice", "nom_salon": "Partie active", "nombre_joueurs": 4},
        ).get_json()["nom_salon"]
        clients = [(host, host_csrf, "Alice")]
        for name in ("Benoit", "Camille", "David"):
            client, csrf = self._client()
            self._post(
                client,
                csrf,
                "/api/rejoindre",
                {"nom": name, "nom_salon": nom_salon},
            )
            clients.append((client, csrf, name))
        self._post(host, host_csrf, "/api/demarrer")

        leaver, leaver_csrf, name = clients[-1]
        departure = leaver.post(
            "/api/quitter",
            json={"csrf": leaver_csrf},
        )
        self.assertEqual(departure.status_code, 200)
        paused_state = host.get("/api/etat").get_json()
        self.assertEqual(paused_state["joueurs_deconnectes"], [name])
        blocked_action = self._post(clients[0][0], clients[0][1], "/api/tirer")
        self.assertEqual(blocked_action.status_code, 400)
        self.assertIn("pause", blocked_action.get_json()["error"].lower())

        returned, returned_csrf = self._client()
        joined = self._post(
            returned,
            returned_csrf,
            "/api/rejoindre",
            {"nom": name, "nom_salon": nom_salon},
        )
        self.assertEqual(joined.status_code, 200)
        resumed_state = host.get("/api/etat").get_json()
        self.assertEqual(resumed_state["joueurs_deconnectes"], [])
        self.assertEqual(resumed_state["phase"], "tirage")


if __name__ == "__main__":
    unittest.main()
