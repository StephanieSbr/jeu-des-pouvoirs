import unittest

import main


class ConfigurationMatchTests(unittest.TestCase):
    def test_four_players_keep_drawn_absolutes_and_get_five_cards(self):
        jeu = main.Jeu(["A", "B", "C", "D"])
        cartes_tirees = {"A": 30, "B": 31, "C": 34, "D": 35}
        partie = jeu.demarrer_match(cartes_tirees)

        self.assertEqual(len(partie.pioche), 15)
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

    def test_five_players_have_two_small_and_three_large_hands(self):
        jeu = main.Jeu(["A", "B", "C", "D", "E"])
        cartes_tirees = {"A": 30, "B": 31, "C": 32, "D": 34, "E": 35}
        partie = jeu.demarrer_match(cartes_tirees)
        taille_par_equipe = {}
        for joueur in jeu.joueurs:
            taille_par_equipe.setdefault(joueur.equipe, set()).add(len(joueur.main))

        self.assertEqual(len(partie.pioche), 12)
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


class WebSalonTests(unittest.TestCase):
    def setUp(self):
        from app import app, _ROOMS, _ROOMS_LOCK

        self.app = app
        self.app.config.update(TESTING=True)
        self.rooms = _ROOMS
        self.rooms_lock = _ROOMS_LOCK
        with self.rooms_lock:
            self.rooms.clear()

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
            {"nom": "Alice", "nombre_joueurs": 4},
        )
        self.assertEqual(response.status_code, 200)
        code = response.get_json()["code"]

        clients = [(host, host_csrf)]
        for name in ("Benoit", "Camille", "David"):
            client, csrf = self._client()
            joined = self._post(
                client,
                csrf,
                "/api/rejoindre",
                {"nom": name, "code": code},
            )
            self.assertEqual(joined.status_code, 200)
            clients.append((client, csrf))

        self.assertEqual(self._post(host, host_csrf, "/api/demarrer").status_code, 200)
        for client, csrf in clients:
            self.assertEqual(self._post(client, csrf, "/api/tirer").status_code, 200)

        states = [client.get("/api/etat").get_json() for client, _ in clients]
        self.assertTrue(all(state["phase"] == "active" for state in states))
        self.assertTrue(all(len(state["main"]) == 5 for state in states))
        for state in states:
            self.assertNotIn("main", state["joueurs"][0])
            self.assertEqual(
                sum(player["cartes_en_main"] for player in state["joueurs"])
                + state["pioche_restante"],
                35,
            )

    def test_csrf_is_required_for_mutating_routes(self):
        client, _csrf = self._client()
        response = client.post(
            "/api/salons",
            json={"nom": "Alice", "nombre_joueurs": 4},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("session", response.get_json()["error"].lower())

    def test_any_connected_player_can_start_a_full_room(self):
        clients = []
        code = None
        for index, name in enumerate(("Alice", "Benoit", "Camille", "David")):
            client, csrf = self._client()
            if index == 0:
                response = self._post(
                    client,
                    csrf,
                    "/api/salons",
                    {"nom": name, "nombre_joueurs": 4},
                )
                code = response.get_json()["code"]
            else:
                self._post(
                    client,
                    csrf,
                    "/api/rejoindre",
                    {"nom": name, "code": code},
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
            {"nom": "Alice", "nombre_joueurs": 4},
        )
        code = created.get_json()["code"]
        guest, guest_csrf = self._client()
        self._post(guest, guest_csrf, "/api/rejoindre", {"nom": "Benoit", "code": code})

        self.assertEqual(self._post(guest, guest_csrf, "/api/quitter").status_code, 200)
        newcomer, newcomer_csrf = self._client()
        joined = self._post(
            newcomer,
            newcomer_csrf,
            "/api/rejoindre",
            {"nom": "Camille", "code": code},
        )
        self.assertEqual(joined.status_code, 200)
        self.assertEqual(len(host.get("/api/etat").get_json()["joueurs"]), 2)

    def test_depart_during_match_pauses_until_same_player_rejoins(self):
        host, host_csrf = self._client()
        code = self._post(
            host,
            host_csrf,
            "/api/salons",
            {"nom": "Alice", "nombre_joueurs": 4},
        ).get_json()["code"]
        clients = [(host, host_csrf, "Alice")]
        for name in ("Benoit", "Camille", "David"):
            client, csrf = self._client()
            self._post(client, csrf, "/api/rejoindre", {"nom": name, "code": code})
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
            {"nom": name, "code": code},
        )
        self.assertEqual(joined.status_code, 200)
        resumed_state = host.get("/api/etat").get_json()
        self.assertEqual(resumed_state["joueurs_deconnectes"], [])
        self.assertEqual(resumed_state["phase"], "tirage")


if __name__ == "__main__":
    unittest.main()
