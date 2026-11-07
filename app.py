"""Application web multijoueur ; les salons vivent en mémoire dans ce processus."""

from dataclasses import dataclass, field
import os
import secrets
import string
import threading
import time
from typing import Dict, List, Optional, Set

from flask import Flask, jsonify, render_template, request, send_file, session

from main import (
    CARTES,
    ChoixPouvoir,
    DirectionScore,
    Equipe,
    Jeu,
    ModeRevelation,
)


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
    MAX_CONTENT_LENGTH=16 * 1024,
)

_ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_ROOMS: Dict[str, "Salon"] = {}
_ROOMS_LOCK = threading.RLock()
_ROOM_EXPIRATION_SECONDS = 12 * 60 * 60
_PLAYER_TIMEOUT_SECONDS = 12


@dataclass
class JoueurSalon:
    nom: str
    jeton: str
    derniere_activite: float = field(default_factory=time.time)
    connecte: bool = True


@dataclass
class Salon:
    code: str
    nombre_joueurs: int
    joueurs: List[JoueurSalon]
    jeton_hote: str
    phase: str = "attente"
    jeu: Optional[Jeu] = None
    tirages: Dict[str, int] = field(default_factory=dict)
    cartes_absolues_disponibles: List[int] = field(default_factory=list)
    action_en_attente: Optional[dict] = None
    choix_13: Dict[str, int] = field(default_factory=dict)
    joueurs_qui_doivent_choisir_13: Set[str] = field(default_factory=set)
    messages_prives: Dict[str, str] = field(default_factory=dict)
    modifie_a: float = field(default_factory=time.time)


def _nettoyer_salons() -> None:
    maintenant = time.time()
    a_supprimer = [
        code
        for code, salon in _ROOMS.items()
        if maintenant - salon.modifie_a > _ROOM_EXPIRATION_SECONDS
    ]
    for code in a_supprimer:
        del _ROOMS[code]


def _generer_code_salon() -> str:
    while True:
        code = "".join(secrets.choice(_ROOM_CODE_ALPHABET) for _ in range(6))
        if code not in _ROOMS:
            return code


def _marquer_joueurs_inactifs(salon: Salon, maintenant: float) -> None:
    for joueur in salon.joueurs:
        if maintenant - joueur.derniere_activite > _PLAYER_TIMEOUT_SECONDS:
            joueur.connecte = False


def _jeton_csrf() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(24)
    return session["csrf"]


def _verifier_csrf() -> None:
    attendu = session.get("csrf")
    fourni = request.headers.get("X-CSRF-Token")
    if not fourni and request.is_json:
        contenu = request.get_json(silent=True)
        if isinstance(contenu, dict):
            fourni = contenu.get("csrf")
    if (
        not isinstance(attendu, str)
        or not isinstance(fourni, str)
        or not secrets.compare_digest(attendu, fourni)
    ):
        raise ValueError("La session du navigateur a expiré. Recharge la page et réessaie.")


def _salon_courant() -> Salon:
    code = session.get("room_code")
    jeton = session.get("player_token")
    if not isinstance(code, str) or not isinstance(jeton, str):
        raise PermissionError("Rejoins un salon avant de jouer.")
    salon = _ROOMS.get(code)
    if salon is None:
        session.pop("room_code", None)
        session.pop("player_token", None)
        raise PermissionError("Ce salon n'existe plus ou a expiré.")
    maintenant = time.time()
    _marquer_joueurs_inactifs(salon, maintenant)
    joueur_courant = next(
        (joueur for joueur in salon.joueurs if joueur.jeton == jeton),
        None,
    )
    if joueur_courant is None:
        session.pop("room_code", None)
        session.pop("player_token", None)
        raise PermissionError("Cette session n'est plus membre du salon.")
    joueur_courant.connecte = True
    joueur_courant.derniere_activite = maintenant
    salon.modifie_a = time.time()
    return salon


def _joueur_courant_salon(salon: Salon) -> JoueurSalon:
    jeton = session.get("player_token")
    for joueur in salon.joueurs:
        if joueur.jeton == jeton:
            return joueur
    raise PermissionError("Joueur inconnu dans ce salon.")


def _joueurs_deconnectes(salon: Salon) -> List[str]:
    return [joueur.nom for joueur in salon.joueurs if not joueur.connecte]


def _exiger_joueurs_connectes(salon: Salon) -> None:
    absents = _joueurs_deconnectes(salon)
    if absents:
        raise ValueError(
            "La partie est en pause. En attente du retour de : {}.".format(
                ", ".join(absents)
            )
        )


def _api_erreur(message: str, statut: int):
    return jsonify({"error": message}), statut


def _lire_json() -> dict:
    contenu = request.get_json(silent=False)
    if not isinstance(contenu, dict):
        raise ValueError("La requête doit contenir un objet JSON.")
    return contenu


def _jouer_avec_choix(jeu: Jeu, score: int, donnees: dict) -> None:
    direction = donnees.get("direction_15")
    mode_24 = donnees.get("mode_24")
    choix = ChoixPouvoir(
        utiliser_21=donnees.get("utiliser_21"),
        joueur_cible=donnees.get("joueur_cible"),
        direction_15=(
            DirectionScore(direction) if direction is not None else None
        ),
        mode_24=ModeRevelation(mode_24) if mode_24 is not None else None,
        score_main=donnees.get("score_main"),
        score_main_cible=donnees.get("score_main_cible"),
        score_forcee_21=donnees.get("score_forcee_21"),
        score_remplacement_28=donnees.get("score_remplacement_28"),
    )
    jeu.poser_carte(score, choix)


def _lancer_partie_suivante(salon: Salon) -> None:
    if salon.jeu is None:
        raise RuntimeError("Le match n'a pas encore commencé.")
    salon.jeu.demarrer_partie()
    salon.phase = "active"
    salon.action_en_attente = None
    salon.choix_13.clear()
    salon.joueurs_qui_doivent_choisir_13.clear()


def _gagnants_13_requis(jeu: Jeu) -> Set[str]:
    """Liste les propriétaires de 13 défaussées qui ont encore un choix possible."""
    partie = jeu.partie
    if partie is None:
        return set()
    gagnante = jeu._determiner_gagnante(partie)
    defausses = jeu._determiner_defausses(partie, gagnante)
    proprietaires = set(partie.cartes_13_a_resoudre)
    if 13 in defausses:
        proprietaires.update(
            carte_posee.proprietaire
            for carte_posee in partie.en_jeu.values()
            if carte_posee.carte.score == 13
        )
    return {
        nom
        for nom in proprietaires
        if any(carte.score != 14 for carte in jeu._joueur_par_nom(nom).main)
    }


def _resoudre_tour(salon: Salon) -> None:
    if salon.jeu is None:
        raise RuntimeError("Le match n'a pas commencé.")
    salon.jeu.terminer_tour(salon.choix_13)
    salon.choix_13.clear()
    salon.joueurs_qui_doivent_choisir_13.clear()
    if salon.jeu.match_termine or salon.jeu.parties_jouees >= salon.jeu.NOMBRE_MAX_PARTIES:
        salon.phase = "match_termine"
    else:
        salon.phase = "entre_parties"


def _apres_pose(salon: Salon) -> None:
    jeu = salon.jeu
    if jeu is None or jeu.partie is None:
        return
    if len(jeu.partie.joueurs_ayant_joue) != len(jeu.joueurs):
        return
    salon.joueurs_qui_doivent_choisir_13 = _gagnants_13_requis(jeu)
    if salon.joueurs_qui_doivent_choisir_13:
        salon.phase = "choix_13"
    else:
        _resoudre_tour(salon)


def _etat_public(salon: Salon, jeton: str) -> dict:
    moi = next(joueur for joueur in salon.joueurs if joueur.jeton == jeton)
    etat = {
        "code": salon.code,
        "phase": salon.phase,
        "vous": moi.nom,
        "hote": jeton == salon.jeton_hote,
        "nombre_joueurs": salon.nombre_joueurs,
        "joueurs": [
            {
                "nom": joueur.nom,
                "a_tire": joueur.nom in salon.tirages,
                "connecte": joueur.connecte,
            }
            for joueur in salon.joueurs
        ],
        "joueurs_deconnectes": _joueurs_deconnectes(salon),
        "messages_prives": salon.messages_prives.pop(moi.nom, None),
        "tirage_personnel": salon.tirages.get(moi.nom),
        "equipes_revelees": salon.phase != "tirage",
        "action_en_attente": None,
    }
    if salon.phase == "attente":
        etat["peut_commencer"] = (
            len(salon.joueurs) == salon.nombre_joueurs
            and not _joueurs_deconnectes(salon)
        )
        return etat
    if salon.jeu is None:
        return etat

    jeu = salon.jeu
    etat["individuel"] = jeu.individuel
    etat["scores_equipes"] = {
        equipe.value: jeu.victoires[equipe] for equipe in Equipe
    }
    etat["scores_joueurs"] = dict(jeu.victoires_joueurs)
    etat["parties_jouees"] = jeu.parties_jouees
    etat["equipe_gagnante_match"] = (
        jeu.equipe_gagnante.value if jeu.equipe_gagnante is not None else None
    )
    etat["joueur_gagnant_match"] = jeu.joueur_gagnant_match
    if jeu.partie is None:
        return etat

    partie = jeu.partie
    etat.update(
        {
            "numero_partie": partie.numero,
            "numero_tour": partie.nombre_tours + 1,
            "joueur_courant": None,
            "joueurs_ayant_joue": sorted(partie.joueurs_ayant_joue),
            "direction_15": (
                partie.direction_15.value if partie.direction_15 is not None else None
            ),
            "pioche_restante": len(partie.pioche),
            "defausse": [carte.score for carte in partie.defausse],
            "cartes_en_jeu": [
                {
                    "devant": emplacement,
                    "proprietaire": carte_posee.proprietaire,
                    "score": carte_posee.carte.score,
                    "image": "/cartes/{}.png".format(carte_posee.carte.score),
                }
                for emplacement, carte_posee in partie.en_jeu.items()
            ],
            "main": [
                {
                    "score": carte.score,
                    "image": "/cartes/{}.png".format(carte.score),
                    "pouvoir": carte.pouvoir.description,
                }
                for carte in next(
                    joueur for joueur in jeu.joueurs if joueur.nom == moi.nom
                ).main
            ],
            "joueurs": [
                {
                    "nom": joueur.nom,
                    "equipe": joueur.equipe.value if joueur.equipe else None,
                    "cartes_en_main": len(joueur.main),
                    "a_joue": joueur.nom in partie.joueurs_ayant_joue,
                    "carte_devant": (
                        partie.en_jeu[joueur.nom].carte.score
                        if joueur.nom in partie.en_jeu
                        else None
                    ),
                    "victoires": (
                        jeu.victoires_joueurs[joueur.nom]
                        if jeu.individuel
                        else jeu.victoires[joueur.equipe]
                    ),
                }
                for joueur in jeu.joueurs
            ],
        }
    )
    if salon.phase == "active":
        try:
            etat["joueur_courant"] = jeu.joueur_courant.nom
        except RuntimeError:
            pass

    action = salon.action_en_attente
    if action and jeton in (action["acteur_token"], action["cible_token"]):
        etat["action_en_attente"] = {
            "type": action["type"],
            "acteur": action["acteur"],
            "cible": action["cible"],
            "score": action["score"],
            "est_cible": jeton == action["cible_token"],
            "emplacement": action.get("emplacement"),
            "carte_a_remplacer": action.get("carte_a_remplacer"),
        }
    if salon.phase == "choix_13" and moi.nom in salon.joueurs_qui_doivent_choisir_13:
        etat["doit_choisir_13"] = True
        etat["cartes_choix_13"] = [
            carte.score for carte in jeu._joueur_par_nom(moi.nom).main if carte.score != 14
        ]
    else:
        etat["doit_choisir_13"] = False

    if salon.phase == "tirage":
        etat["tirages_valides"] = len(salon.tirages)
    if salon.phase == "entre_parties":
        etat["peut_commencer"] = not _joueurs_deconnectes(salon)
    if salon.phase == "match_termine":
        etat["peut_nouveau_match"] = not _joueurs_deconnectes(salon)
        partie = jeu.partie
        etat["vainqueur_partie"] = (
            partie.equipe_gagnante.value
            if partie and partie.equipe_gagnante is not None
            else partie.joueur_gagnant
            if partie
            else None
        )
    return etat


@app.get("/")
def accueil():
    return render_template(
        "index.html",
        csrf=_jeton_csrf(),
        has_room=bool(session.get("room_code") and session.get("player_token")),
    )


@app.get("/cartes/<int:score>.png")
def image_carte(score: int):
    carte = CARTES.get(score)
    if carte is None or not carte.image.is_file():
        return _api_erreur("Image de carte introuvable.", 404)
    return send_file(carte.image, mimetype="image/png", conditional=True)


@app.post("/api/salons")
def creer_salon():
    try:
        _verifier_csrf()
        donnees = _lire_json()
        nom = str(donnees.get("nom", "")).strip()
        nombre = donnees.get("nombre_joueurs")
        if len(nom) > 24 or not nom:
            raise ValueError("Choisis un nom de joueur de 1 à 24 caractères.")
        if nombre not in (4, 5, 6):
            raise ValueError("Choisis 4, 5 ou 6 joueurs.")
        with _ROOMS_LOCK:
            _nettoyer_salons()
            code = _generer_code_salon()
            jeton = secrets.token_urlsafe(32)
            salon = Salon(
                code=code,
                nombre_joueurs=nombre,
                joueurs=[JoueurSalon(nom=nom, jeton=jeton)],
                jeton_hote=jeton,
            )
            _ROOMS[code] = salon
            session["room_code"] = code
            session["player_token"] = jeton
        return jsonify({"ok": True, "code": code})
    except ValueError as erreur:
        return _api_erreur(str(erreur), 400)


@app.post("/api/rejoindre")
def rejoindre_salon():
    try:
        _verifier_csrf()
        donnees = _lire_json()
        code = str(donnees.get("code", "")).strip().upper()
        nom = str(donnees.get("nom", "")).strip()
        if len(nom) > 24 or not nom:
            raise ValueError("Choisis un nom de joueur de 1 à 24 caractères.")
        with _ROOMS_LOCK:
            _nettoyer_salons()
            salon = _ROOMS.get(code)
            if salon is None:
                raise ValueError("Code de salon invalide ou expiré.")
            _marquer_joueurs_inactifs(salon, time.time())
            joueur_existant = next(
                (
                    joueur
                    for joueur in salon.joueurs
                    if joueur.nom.casefold() == nom.casefold()
                ),
                None,
            )
            if joueur_existant is not None:
                if joueur_existant.connecte:
                    raise ValueError("Ce nom est déjà utilisé dans le salon.")
                joueur_existant.jeton = secrets.token_urlsafe(32)
                joueur_existant.connecte = True
                joueur_existant.derniere_activite = time.time()
                jeton = joueur_existant.jeton
            else:
                if salon.phase != "attente":
                    raise ValueError("La partie a déjà commencé.")
                if len(salon.joueurs) >= salon.nombre_joueurs:
                    raise ValueError("Ce salon est complet.")
                jeton = secrets.token_urlsafe(32)
                salon.joueurs.append(JoueurSalon(nom=nom, jeton=jeton))
            salon.modifie_a = time.time()
            session["room_code"] = code
            session["player_token"] = jeton
        return jsonify({"ok": True, "code": code})
    except ValueError as erreur:
        return _api_erreur(str(erreur), 400)


@app.get("/api/etat")
def obtenir_etat():
    try:
        with _ROOMS_LOCK:
            salon = _salon_courant()
            jeton = session["player_token"]
            return jsonify(_etat_public(salon, jeton))
    except PermissionError as erreur:
        return _api_erreur(str(erreur), 401)


@app.post("/api/quitter")
def quitter_salon():
    try:
        _verifier_csrf()
        with _ROOMS_LOCK:
            salon = _salon_courant()
            joueur = _joueur_courant_salon(salon)
            if salon.phase == "attente":
                salon.joueurs.remove(joueur)
                if salon.jeton_hote == joueur.jeton:
                    salon.jeton_hote = (
                        salon.joueurs[0].jeton if salon.joueurs else ""
                    )
                if not salon.joueurs:
                    del _ROOMS[salon.code]
                else:
                    salon.modifie_a = time.time()
            else:
                joueur.connecte = False
                joueur.derniere_activite = time.time()
                salon.modifie_a = time.time()
            session.pop("room_code", None)
            session.pop("player_token", None)
        return jsonify({"ok": True})
    except PermissionError as erreur:
        return _api_erreur(str(erreur), 403)
    except ValueError as erreur:
        return _api_erreur(str(erreur), 400)


@app.post("/api/demarrer")
def demarrer_match():
    try:
        _verifier_csrf()
        with _ROOMS_LOCK:
            salon = _salon_courant()
            if salon.phase != "attente" or len(salon.joueurs) != salon.nombre_joueurs:
                raise ValueError("Le salon doit être complet avant de démarrer.")
            _exiger_joueurs_connectes(salon)
            noms = [joueur.nom for joueur in salon.joueurs]
            salon.jeu = Jeu(noms)
            if len(noms) == 6:
                salon.jeu.demarrer_match()
                salon.phase = "active"
            else:
                salon.phase = "tirage"
                salon.cartes_absolues_disponibles = sorted(
                    main_score for main_score in range(30, 36)
                )
            salon.modifie_a = time.time()
            return jsonify({"ok": True})
    except PermissionError as erreur:
        return _api_erreur(str(erreur), 403)
    except (ValueError, RuntimeError) as erreur:
        return _api_erreur(str(erreur), 400)


@app.post("/api/tirer")
def tirer_absolue():
    try:
        _verifier_csrf()
        with _ROOMS_LOCK:
            salon = _salon_courant()
            _exiger_joueurs_connectes(salon)
            joueur = _joueur_courant_salon(salon)
            if salon.phase != "tirage":
                raise ValueError("Le tirage des équipes n'est pas en cours.")
            if joueur.nom in salon.tirages:
                raise ValueError("Tu as déjà tiré ta carte absolue.")
            if not salon.cartes_absolues_disponibles:
                raise RuntimeError("Il ne reste plus de carte absolue à tirer.")
            index = secrets.randbelow(len(salon.cartes_absolues_disponibles))
            score = salon.cartes_absolues_disponibles.pop(index)
            salon.tirages[joueur.nom] = score
            if len(salon.tirages) == salon.nombre_joueurs:
                if salon.jeu is None:
                    raise RuntimeError("Le moteur du jeu n'a pas été créé.")
                salon.jeu.demarrer_match(salon.tirages)
                salon.phase = "active"
            salon.modifie_a = time.time()
            return jsonify({"ok": True})
    except PermissionError as erreur:
        return _api_erreur(str(erreur), 403)
    except (ValueError, RuntimeError) as erreur:
        return _api_erreur(str(erreur), 400)


def _trouver_joueur(salon: Salon, nom: str) -> JoueurSalon:
    for joueur in salon.joueurs:
        if joueur.nom == nom:
            return joueur
    raise ValueError("Joueur cible inconnu.")


def _commencer_pose(salon: Salon, donnees: dict) -> None:
    jeu = salon.jeu
    if jeu is None:
        raise RuntimeError("Le match n'a pas commencé.")
    joueur = _joueur_courant_salon(salon)
    if jeu.joueur_courant.nom != joueur.nom:
        raise PermissionError("Ce n'est pas encore ton tour.")
    if salon.action_en_attente is not None:
        raise ValueError("Un autre joueur doit d'abord répondre à un pouvoir.")
    score = donnees.get("score")
    if not isinstance(score, int):
        raise ValueError("Choisis une carte valide.")
    carte = jeu._trouver_dans_main(jeu._joueur_par_nom(joueur.nom), score)

    # Certains pouvoirs attendent la décision d'un autre joueur avant d'être résolus.
    if score == 21 and donnees.get("utiliser_21") is True:
        cible = _trouver_joueur(salon, donnees.get("joueur_cible", ""))
        if cible.nom == joueur.nom:
            raise ValueError("La carte 21 doit viser un autre joueur.")
        if cible.nom in jeu.partie.joueurs_ayant_joue or cible.nom in jeu.partie.en_jeu:
            raise ValueError("La carte 21 doit viser quelqu'un qui n'a pas encore joué.")
        salon.action_en_attente = {
            "type": "21",
            "acteur": joueur.nom,
            "acteur_token": joueur.jeton,
            "cible": cible.nom,
            "cible_token": cible.jeton,
            "score": score,
        }
        return

    if score == 24 and donnees.get("mode_24") == ModeRevelation.DEMANDER_CARTE.value:
        cible = _trouver_joueur(salon, donnees.get("joueur_cible", ""))
        if cible.nom == joueur.nom:
            raise ValueError("La carte 24 doit viser un autre joueur.")
        salon.action_en_attente = {
            "type": "24",
            "acteur": joueur.nom,
            "acteur_token": joueur.jeton,
            "cible": cible.nom,
            "cible_token": cible.jeton,
            "score": score,
        }
        return

    if score == 28 and jeu.partie.en_jeu:
        emplacement = donnees.get("joueur_cible")
        carte_posee = jeu.partie.en_jeu.get(emplacement)
        if carte_posee is None:
            raise ValueError("Choisis un joueur devant lequel une carte est posée.")
        proprietaire = _trouver_joueur(salon, carte_posee.proprietaire)
        cartes_de_remplacement = [
            c
            for c in jeu._joueur_par_nom(proprietaire.nom).main
            if c.score != carte_posee.carte.score
        ]
        if cartes_de_remplacement:
            salon.action_en_attente = {
                "type": "28",
                "acteur": joueur.nom,
                "acteur_token": joueur.jeton,
                "cible": proprietaire.nom,
                "cible_token": proprietaire.jeton,
                "score": score,
                "emplacement": emplacement,
                "carte_a_remplacer": carte_posee.carte.score,
            }
            return

    if 30 <= score <= 35:
        cible_nom = donnees.get("joueur_cible")
        cible = _trouver_joueur(salon, cible_nom) if cible_nom else None
        possede_une_carte_pour_echange = (
            len(jeu._joueur_par_nom(joueur.nom).main) > 1
            or bool(jeu.partie.pioche)
        )
        if cible is not None and cible.nom == joueur.nom:
            raise ValueError("Choisis un autre joueur pour l'échange.")
        adversaire_avec_cartes = [
            autre
            for autre in salon.joueurs
            if autre.nom != joueur.nom and jeu._joueur_par_nom(autre.nom).main
        ]
        if not possede_une_carte_pour_echange or not adversaire_avec_cartes:
            cible = None
        if cible is not None and possede_une_carte_pour_echange:
            if not jeu._joueur_par_nom(cible.nom).main:
                raise ValueError("Ce joueur n'a plus de carte à échanger.")
            carte_a_donner = donnees.get("score_main")
            if len(jeu._joueur_par_nom(joueur.nom).main) > 1:
                jeu._trouver_main_sauf_score(
                    jeu._joueur_par_nom(joueur.nom), score, carte_a_donner
                )
            elif carte_a_donner is not None:
                raise ValueError("La carte piochée sera échangée automatiquement.")
            salon.action_en_attente = {
                "type": "30-35",
                "acteur": joueur.nom,
                "acteur_token": joueur.jeton,
                "cible": cible.nom,
                "cible_token": cible.jeton,
                "score": score,
                "score_main": carte_a_donner,
            }
            return

    choix = dict(donnees)
    if score == 30 or 31 <= score <= 35:
        # Sans échange possible, la carte absolue est simplement posée.
        choix.pop("joueur_cible", None)
    _jouer_avec_choix(jeu, score, choix)
    if score == 24:
        cible_nom = donnees.get("joueur_cible")
        mode = donnees.get("mode_24")
        if mode == ModeRevelation.MONTRER_MA_CARTE.value:
            message = "{} te montre sa carte {}.".format(joueur.nom, donnees.get("score_main"))
            salon.messages_prives[cible_nom] = message
        elif mode == ModeRevelation.DEMANDER_CARTE.value:
            salon.messages_prives[joueur.nom] = "{} te montre sa carte {}.".format(
                cible_nom, donnees.get("score_main_cible")
            )
    _apres_pose(salon)


def _repondre_action(salon: Salon, score: int) -> None:
    action = salon.action_en_attente
    jeu = salon.jeu
    if action is None or jeu is None:
        raise ValueError("Aucune réponse n'est attendue.")
    joueur = _joueur_courant_salon(salon)
    if joueur.jeton != action["cible_token"]:
        raise PermissionError("Cette réponse est réservée au joueur visé.")

    choix = ChoixPouvoir()
    if action["type"] == "21":
        choix = ChoixPouvoir(
            utiliser_21=True,
            joueur_cible=action["cible"],
            score_forcee_21=score,
        )
    elif action["type"] == "24":
        choix = ChoixPouvoir(
            joueur_cible=action["cible"],
            mode_24=ModeRevelation.DEMANDER_CARTE,
            score_main_cible=score,
        )
    elif action["type"] == "28":
        choix = ChoixPouvoir(
            joueur_cible=action["emplacement"],
            score_remplacement_28=score,
        )
    elif action["type"] == "30-35":
        choix = ChoixPouvoir(
            joueur_cible=action["cible"],
            score_main=action["score_main"],
            score_main_cible=score,
        )
    else:
        raise RuntimeError("Type de réponse inconnu.")

    jeu.poser_carte(action["score"], choix)
    if action["type"] == "24":
        salon.messages_prives[action["acteur"]] = "{} te montre sa carte {}.".format(
            action["cible"], score
        )
    salon.action_en_attente = None
    _apres_pose(salon)


@app.post("/api/jouer")
def jouer_carte():
    try:
        _verifier_csrf()
        donnees = _lire_json()
        with _ROOMS_LOCK:
            salon = _salon_courant()
            _exiger_joueurs_connectes(salon)
            if salon.phase != "active":
                raise ValueError("Aucune partie n'est en cours.")
            _commencer_pose(salon, donnees)
            salon.modifie_a = time.time()
            return jsonify({"ok": True})
    except PermissionError as erreur:
        return _api_erreur(str(erreur), 403)
    except (ValueError, RuntimeError) as erreur:
        return _api_erreur(str(erreur), 400)


@app.post("/api/repondre")
def repondre_pouvoir():
    try:
        _verifier_csrf()
        donnees = _lire_json()
        score = donnees.get("score")
        if not isinstance(score, int):
            raise ValueError("Choisis une carte valide.")
        with _ROOMS_LOCK:
            salon = _salon_courant()
            _exiger_joueurs_connectes(salon)
            _repondre_action(salon, score)
            salon.modifie_a = time.time()
            return jsonify({"ok": True})
    except PermissionError as erreur:
        return _api_erreur(str(erreur), 403)
    except (ValueError, RuntimeError) as erreur:
        return _api_erreur(str(erreur), 400)


@app.post("/api/choisir-13")
def choisir_carte_supplementaire():
    try:
        _verifier_csrf()
        donnees = _lire_json()
        score = donnees.get("score")
        if not isinstance(score, int):
            raise ValueError("Choisis une carte valide.")
        with _ROOMS_LOCK:
            salon = _salon_courant()
            _exiger_joueurs_connectes(salon)
            if salon.phase != "choix_13" or salon.jeu is None:
                raise ValueError("Aucun choix lié à la carte 13 n'est attendu.")
            joueur = _joueur_courant_salon(salon)
            if joueur.nom not in salon.joueurs_qui_doivent_choisir_13:
                raise PermissionError("Ce choix appartient à un autre joueur.")
            if score not in {
                carte.score
                for carte in salon.jeu._joueur_par_nom(joueur.nom).main
                if carte.score != 14
            }:
                raise ValueError("Choisis une carte de ta main, autre que la 14.")
            salon.choix_13[joueur.nom] = score
            if set(salon.choix_13) == salon.joueurs_qui_doivent_choisir_13:
                _resoudre_tour(salon)
            salon.modifie_a = time.time()
            return jsonify({"ok": True})
    except PermissionError as erreur:
        return _api_erreur(str(erreur), 403)
    except (ValueError, RuntimeError) as erreur:
        return _api_erreur(str(erreur), 400)


@app.post("/api/prochaine-partie")
def prochaine_partie():
    try:
        _verifier_csrf()
        with _ROOMS_LOCK:
            salon = _salon_courant()
            _exiger_joueurs_connectes(salon)
            if salon.phase != "entre_parties":
                raise ValueError("Le match n'attend pas une nouvelle partie.")
            _lancer_partie_suivante(salon)
            salon.modifie_a = time.time()
            return jsonify({"ok": True})
    except PermissionError as erreur:
        return _api_erreur(str(erreur), 403)
    except (ValueError, RuntimeError) as erreur:
        return _api_erreur(str(erreur), 400)


@app.post("/api/nouveau-match")
def nouveau_match():
    try:
        _verifier_csrf()
        with _ROOMS_LOCK:
            salon = _salon_courant()
            _exiger_joueurs_connectes(salon)
            if salon.phase != "match_termine":
                raise ValueError("Le match en cours n'est pas terminé.")
            salon.jeu = Jeu([joueur.nom for joueur in salon.joueurs])
            salon.tirages.clear()
            salon.action_en_attente = None
            salon.choix_13.clear()
            salon.joueurs_qui_doivent_choisir_13.clear()
            salon.messages_prives.clear()
            if len(salon.joueurs) == 6:
                salon.jeu.demarrer_match()
                salon.phase = "active"
            else:
                salon.cartes_absolues_disponibles = list(range(30, 36))
                salon.phase = "tirage"
            salon.modifie_a = time.time()
            return jsonify({"ok": True})
    except PermissionError as erreur:
        return _api_erreur(str(erreur), 403)
    except (ValueError, RuntimeError) as erreur:
        return _api_erreur(str(erreur), 400)


@app.errorhandler(413)
def contenu_trop_volumineux(_erreur):
    return _api_erreur("La requête est trop volumineuse.", 413)


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
