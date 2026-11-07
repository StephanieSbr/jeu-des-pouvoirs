"""Moteur de base du jeu des pouvoirs : cartes, tours, équipes et parties."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import random
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


cartes = list(range(1, 36))

_CARTES_VERTES = {1, 2, 3, 4, 5, 6, 7, 8, 17}
_CARTES_JAUNES = {9, 10, 11, 12, 13, 14, 15, 16, 17}
_CARTES_ROUGES = {17, 18, 19, 20, 21, 22, 23, 24, 25}
_CARTES_BLEUES = {17, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35}
_CARTES_ABSOLUES = {30, 31, 32, 33, 34, 35}


def is_vert(n: int) -> bool:
    return n in _CARTES_VERTES


def is_jaune(n: int) -> bool:
    return n in _CARTES_JAUNES


def is_rouge(n: int) -> bool:
    return n in _CARTES_ROUGES


def is_bleu(n: int) -> bool:
    return n in _CARTES_BLEUES


def is_absolut(n: int) -> bool:
    return n in _CARTES_ABSOLUES


class TypePouvoir(Enum):
    """Catégories de pouvoirs utilisées pour décrire les 35 cartes."""

    DEFAUSSER_CARTE_EN_JEU = "défausser une carte en jeu"
    DEFAUSSER_SA_CARTE = "défausser sa carte"
    DEFAUSSER_SI_CARTE_PRESENTE = "se défausser si une carte est présente"
    ECHANGER_CARTE = "échanger une carte"
    ECHANGER_MAIN = "échanger une carte de sa main"
    IMPOSER_SCORE = "imposer un score minimal ou maximal"
    MODIFIER_GAGNANT = "modifier la carte qui remporte le tour"
    MONTRER_CARTE = "montrer une carte"
    POSER_CARTE_DEVANT_JOUEUR = "poser une carte devant un joueur"
    DEFAUSSER_CARTE_SUPPLEMENTAIRE = "défausser une carte supplémentaire de sa main"
    MODIFIER_ORDRE = "modifier l'ordre du prochain tour"
    PROTEGER_CARTE = "ne jamais défausser sauf exception"
    AUTRE = "autre pouvoir"


@dataclass
class PouvoirCarte:
    """Description éditable ; l'effet est implémenté par le moteur selon le score."""

    type: Optional[TypePouvoir] = None
    description: str = "À compléter"
    subtilites: str = ""


@dataclass(frozen=True)
class Carte:
    score: int
    couleurs: FrozenSet[str]
    absolut: bool
    image: Path
    pouvoir: PouvoirCarte


# Fiches des pouvoirs fournies par le créateur du jeu.
POUVOIRS_CARTES: Dict[int, PouvoirCarte] = {
    1: PouvoirCarte(TypePouvoir.DEFAUSSER_CARTE_EN_JEU, "Défausse la carte verte de plus forte valeur."),
    2: PouvoirCarte(TypePouvoir.DEFAUSSER_SI_CARTE_PRESENTE, "Se défausse si une autre carte verte est en jeu."),
    3: PouvoirCarte(TypePouvoir.DEFAUSSER_SI_CARTE_PRESENTE, "Se défausse si une carte jaune est en jeu."),
    4: PouvoirCarte(TypePouvoir.DEFAUSSER_SI_CARTE_PRESENTE, "Se défausse si une carte rouge est en jeu."),
    5: PouvoirCarte(TypePouvoir.DEFAUSSER_SI_CARTE_PRESENTE, "Se défausse si une carte bleue est en jeu."),
    6: PouvoirCarte(TypePouvoir.DEFAUSSER_SA_CARTE, "Se défausse si c'est la carte la plus faible en jeu."),
    7: PouvoirCarte(TypePouvoir.DEFAUSSER_SI_CARTE_PRESENTE, "Se défausse si c'est la seule carte verte en jeu."),
    8: PouvoirCarte(TypePouvoir.DEFAUSSER_CARTE_EN_JEU, "Défausse la carte verte de plus faible valeur."),
    9: PouvoirCarte(TypePouvoir.DEFAUSSER_CARTE_EN_JEU, "Défausse la carte jaune de plus forte valeur."),
    10: PouvoirCarte(TypePouvoir.DEFAUSSER_SI_CARTE_PRESENTE, "Se défausse si une carte absolue est en jeu."),
    11: PouvoirCarte(TypePouvoir.DEFAUSSER_SI_CARTE_PRESENTE, "Se défausse si c'est la seule carte jaune en jeu."),
    12: PouvoirCarte(TypePouvoir.MODIFIER_GAGNANT, "La carte la plus faible remporte le tour."),
    13: PouvoirCarte(TypePouvoir.DEFAUSSER_CARTE_SUPPLEMENTAIRE, "Si elle est défaussée, son propriétaire choisit une autre carte de sa main à défausser, sauf la 14."),
    14: PouvoirCarte(TypePouvoir.PROTEGER_CARTE, "Ne peut jamais être défaussée, sauf si elle remporte le tour."),
    15: PouvoirCarte(TypePouvoir.IMPOSER_SCORE, "Les joueurs suivants jouent au-dessus ou au-dessous de 15 ; à défaut, ils jouent une carte au plus proche de 15."),
    16: PouvoirCarte(TypePouvoir.DEFAUSSER_CARTE_EN_JEU, "Défausse la carte jaune de plus faible valeur."),
    17: PouvoirCarte(None, "Possède les quatre couleurs et n'a pas d'autre pouvoir."),
    18: PouvoirCarte(TypePouvoir.DEFAUSSER_CARTE_EN_JEU, "Défausse la carte rouge de plus forte valeur."),
    19: PouvoirCarte(TypePouvoir.DEFAUSSER_SI_CARTE_PRESENTE, "Se défausse si c'est la seule carte rouge en jeu."),
    20: PouvoirCarte(TypePouvoir.DEFAUSSER_CARTE_EN_JEU, "Défausse la carte de plus faible valeur en jeu."),
    21: PouvoirCarte(TypePouvoir.POSER_CARTE_DEVANT_JOUEUR, "Peut être posée devant un joueur qui n'a pas encore joué ; celui-ci pose une carte devant son propriétaire."),
    22: PouvoirCarte(TypePouvoir.MODIFIER_ORDRE, "Le joueur à gauche du propriétaire de la 22 commence le prochain tour."),
    23: PouvoirCarte(TypePouvoir.ECHANGER_CARTE, "Échange sa place avec une carte déjà en jeu ; l'autre carte vient devant son propriétaire."),
    24: PouvoirCarte(TypePouvoir.MONTRER_CARTE, "Montre une carte choisie de sa main à un joueur, ou demande à un joueur de choisir une carte à montrer."),
    25: PouvoirCarte(TypePouvoir.DEFAUSSER_CARTE_EN_JEU, "Défausse la carte rouge de plus faible valeur."),
    26: PouvoirCarte(TypePouvoir.MODIFIER_GAGNANT, "La carte la plus forte est ignorée ; la deuxième plus forte remporte le tour, sauf si la 12 est en jeu."),
    27: PouvoirCarte(TypePouvoir.DEFAUSSER_CARTE_EN_JEU, "Défausse toutes les cartes jaunes en jeu, sauf la 14."),
    28: PouvoirCarte(TypePouvoir.POSER_CARTE_DEVANT_JOUEUR, "Renvoie une carte déjà jouée dans la main de son propriétaire, qui en pose une autre sans pouvoir direct."),
    29: PouvoirCarte(TypePouvoir.ECHANGER_CARTE, "Échange une carte déjà en jeu avec une carte de sa main."),
    30: PouvoirCarte(TypePouvoir.ECHANGER_MAIN, "Après la pose, échange une carte de sa main contre une carte choisie par un autre joueur."),
    31: PouvoirCarte(TypePouvoir.ECHANGER_MAIN, "Après la pose, échange une carte de sa main contre une carte choisie par un autre joueur."),
    32: PouvoirCarte(TypePouvoir.ECHANGER_MAIN, "Après la pose, échange une carte de sa main contre une carte choisie par un autre joueur."),
    33: PouvoirCarte(TypePouvoir.ECHANGER_MAIN, "Après la pose, échange une carte de sa main contre une carte choisie par un autre joueur."),
    34: PouvoirCarte(TypePouvoir.ECHANGER_MAIN, "Après la pose, échange une carte de sa main contre une carte choisie par un autre joueur."),
    35: PouvoirCarte(TypePouvoir.ECHANGER_MAIN, "Après la pose, échange une carte de sa main contre une carte choisie par un autre joueur."),
}


def _creer_cartes() -> Dict[int, Carte]:
    ensembles = {
        "vert": _CARTES_VERTES,
        "jaune": _CARTES_JAUNES,
        "rouge": _CARTES_ROUGES,
        "bleu": _CARTES_BLEUES,
    }
    dossier_images = Path(__file__).resolve().parent / "images jeu"
    return {
        score: Carte(
            score=score,
            couleurs=frozenset(
                couleur for couleur, scores in ensembles.items() if score in scores
            ),
            absolut=is_absolut(score),
            image=dossier_images / "{}.png".format(score),
            pouvoir=POUVOIRS_CARTES[score],
        )
        for score in cartes
    }


CARTES: Dict[int, Carte] = _creer_cartes()


class Equipe(Enum):
    A = "Équipe A"
    B = "Équipe B"


class DirectionScore(Enum):
    AU_DESSUS = "au-dessus de 15"
    EN_DESSOUS = "au-dessous de 15"


class ModeRevelation(Enum):
    MONTRER_MA_CARTE = "montrer une carte de ma main"
    DEMANDER_CARTE = "demander une carte choisie par l'autre joueur"


@dataclass
class Joueur:
    nom: str
    equipe: Optional[Equipe]
    main: List[Carte] = field(default_factory=list)


@dataclass(frozen=True)
class CartePosee:
    """Carte devant un joueur, avec le joueur qui la possède et celui qui l'a posée."""

    carte: Carte
    proprietaire: str
    poseur: str
    pouvoir_direct_actif: bool = True


@dataclass
class EtatPartie:
    numero: int
    pioche: List[Carte]
    # La clé est le joueur devant lequel la carte est posée.
    en_jeu: Dict[str, CartePosee] = field(default_factory=dict)
    defausse: List[Carte] = field(default_factory=list)
    dernieres_defausses: List[int] = field(default_factory=list)
    derniers_defausseurs: List[str] = field(default_factory=list)
    tour_index: int = 0
    joueurs_ayant_joue: Set[str] = field(default_factory=set)
    direction_15: Optional[DirectionScore] = None
    terminee: bool = False
    equipe_gagnante: Optional[Equipe] = None
    joueur_gagnant: Optional[str] = None
    dernier_joueur_a_remporter_tour: Optional[str] = None
    nombre_tours: int = 0
    journal: List[str] = field(default_factory=list)
    cartes_13_a_resoudre: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ChoixPouvoir:
    """Choix fournis par les joueurs pour les pouvoirs immédiats."""

    utiliser_21: Optional[bool] = None
    joueur_cible: Optional[str] = None
    direction_15: Optional[DirectionScore] = None
    mode_24: Optional[ModeRevelation] = None
    score_main: Optional[int] = None
    score_main_cible: Optional[int] = None
    score_en_jeu: Optional[int] = None
    score_forcee_21: Optional[int] = None
    score_remplacement_28: Optional[int] = None


class Jeu:
    """Rencontre entre deux équipes ; chaque tour se termine après une pose par joueur."""

    CARTES_PAR_MAIN_PAR_DEFAUT = 5
    PARTIES_A_GAGNER = 2
    NOMBRE_MAX_PARTIES = 3

    def __init__(
        self,
        noms_joueurs: List[str],
        equipes: Optional[Dict[str, Equipe]] = None,
    ) -> None:
        noms = [nom.strip() for nom in noms_joueurs]
        if not 4 <= len(noms) <= 6:
            raise ValueError("Il faut entre 4 et 6 joueurs.")
        if any(not nom for nom in noms):
            raise ValueError("Le nom d'un joueur ne peut pas être vide.")
        if len({nom.casefold() for nom in noms}) != len(noms):
            raise ValueError("Chaque joueur doit avoir un nom différent.")

        equipes = equipes or {}
        joueurs_inconnus = set(equipes) - set(noms)
        if joueurs_inconnus:
            raise ValueError(
                "Aucune équipe ne peut être attribuée à ces joueurs : {}.".format(
                    ", ".join(sorted(joueurs_inconnus))
                )
            )

        self.joueurs: List[Joueur] = []
        for index, nom in enumerate(noms):
            equipe = (
                None
                if len(noms) == 6
                else equipes.get(nom, Equipe.A if index % 2 == 0 else Equipe.B)
            )
            if equipe is not None and not isinstance(equipe, Equipe):
                raise ValueError("L'équipe de {} doit être Equipe.A ou Equipe.B.".format(nom))
            self.joueurs.append(Joueur(nom=nom, equipe=equipe))

        if len(noms) != 6 and {joueur.equipe for joueur in self.joueurs} != set(Equipe):
            raise ValueError("Les deux équipes doivent avoir au moins un joueur.")

        self.individuel = len(noms) == 6
        self.victoires = {equipe: 0 for equipe in Equipe}
        self.victoires_joueurs = {joueur.nom: 0 for joueur in self.joueurs}
        self.partie: Optional[EtatPartie] = None
        self.parties_jouees = 0

    def demarrer_match(
        self, cartes_absolues: Optional[Dict[str, int]] = None
    ) -> EtatPartie:
        """Attribue les équipes par tirage d'absolues et distribue la première partie."""
        if self.parties_jouees or self.partie is not None:
            raise RuntimeError("Le match a déjà commencé.")

        if self.individuel:
            if cartes_absolues:
                raise ValueError("À six joueurs, il n'y a pas de tirage d'équipe.")
            for joueur in self.joueurs:
                joueur.equipe = None
            return self._distribuer_partie(
                list(CARTES.values()),
                {joueur.nom: 5 for joueur in self.joueurs},
            )

        if cartes_absolues is None or set(cartes_absolues) != {
            joueur.nom for joueur in self.joueurs
        }:
            raise ValueError("Chaque joueur doit avoir tiré une carte absolue.")
        valeurs = list(cartes_absolues.values())
        if any(valeur not in _CARTES_ABSOLUES for valeur in valeurs):
            raise ValueError("Le tirage ne peut contenir que des cartes absolues.")
        if len(set(valeurs)) != len(valeurs):
            raise ValueError("Une carte absolue ne peut être tirée qu'une fois.")

        classement = sorted(self.joueurs, key=lambda joueur: cartes_absolues[joueur.nom])
        indices_equipe_a = {0, len(classement) - 1}
        for index, joueur in enumerate(classement):
            joueur.equipe = Equipe.A if index in indices_equipe_a else Equipe.B

        nombres_cartes = {
            joueur.nom: (
                5 if len(self.joueurs) == 4 or joueur.equipe is Equipe.B else 4
            )
            for joueur in self.joueurs
        }
        # Les absolues non tirées restent hors de la première partie.
        pioche = [
            carte
            for score, carte in CARTES.items()
            if score not in _CARTES_ABSOLUES
        ]
        random.shuffle(pioche)
        for joueur in self.joueurs:
            joueur.main = [CARTES[cartes_absolues[joueur.nom]]]
            for _ in range(nombres_cartes[joueur.nom] - 1):
                joueur.main.append(pioche.pop())

        self.parties_jouees = 1
        self.partie = EtatPartie(numero=1, pioche=pioche)
        return self.partie

    @property
    def equipe_gagnante(self) -> Optional[Equipe]:
        if self.individuel:
            return None
        for equipe, victoires in self.victoires.items():
            if victoires >= self.PARTIES_A_GAGNER:
                return equipe
        return None

    @property
    def joueur_gagnant_match(self) -> Optional[str]:
        if not self.individuel:
            return None
        return next(
            (
                nom
                for nom, victoires in self.victoires_joueurs.items()
                if victoires >= self.PARTIES_A_GAGNER
            ),
            None,
        )

    @property
    def match_termine(self) -> bool:
        return self.equipe_gagnante is not None or self.joueur_gagnant_match is not None

    @property
    def joueur_courant(self) -> Joueur:
        """Renvoie le prochain joueur qui doit poser une carte."""
        partie = self._partie_active()
        for decalage in range(len(self.joueurs)):
            index = (partie.tour_index + decalage) % len(self.joueurs)
            joueur = self.joueurs[index]
            if joueur.nom not in partie.joueurs_ayant_joue:
                return joueur
        raise RuntimeError("Tous les joueurs ont joué ; il faut terminer le tour.")

    def demarrer_partie(
        self, cartes_par_joueur: Optional[int] = None
    ) -> EtatPartie:
        if self.match_termine:
            raise RuntimeError("La rencontre est déjà terminée.")
        if self.partie is not None and not self.partie.terminee:
            raise RuntimeError("La partie précédente n'est pas terminée.")
        if self.parties_jouees >= self.NOMBRE_MAX_PARTIES:
            raise RuntimeError("La rencontre ne peut pas dépasser trois parties.")
        if self.individuel and cartes_par_joueur != 5:
            if cartes_par_joueur is not None:
                raise ValueError("À six joueurs, chaque joueur reçoit cinq cartes.")
        if not self.individuel and self.parties_jouees == 0:
            raise RuntimeError("Il faut tirer les équipes avec demarrer_match() avant la partie.")

        if cartes_par_joueur is None:
            cartes_joueur = {
                joueur.nom: (
                    4
                    if len(self.joueurs) == 5 and joueur.equipe is Equipe.A
                    else self.CARTES_PAR_MAIN_PAR_DEFAUT
                )
                for joueur in self.joueurs
            }
        else:
            if not isinstance(cartes_par_joueur, int) or cartes_par_joueur < 1:
                raise ValueError("Chaque joueur doit recevoir au moins une carte.")
            cartes_joueur = {
                joueur.nom: cartes_par_joueur for joueur in self.joueurs
            }
        if sum(cartes_joueur.values()) > len(CARTES):
            raise ValueError("Il n'y a pas assez de cartes pour cette distribution.")

        return self._distribuer_partie(list(CARTES.values()), cartes_joueur)

    def _distribuer_partie(
        self, pioche: List[Carte], cartes_joueur: Dict[str, int]
    ) -> EtatPartie:
        """Mélange et distribue sans remise un paquet complet."""
        random.shuffle(pioche)
        for joueur in self.joueurs:
            joueur.main.clear()
        for joueur in self.joueurs:
            for _ in range(cartes_joueur[joueur.nom]):
                joueur.main.append(pioche.pop())

        self.parties_jouees += 1
        self.partie = EtatPartie(numero=self.parties_jouees, pioche=pioche)
        return self.partie

    def poser_carte(self, score: int, choix: Optional[ChoixPouvoir] = None) -> None:
        """Pose la carte du joueur courant et résout seulement son pouvoir immédiat."""
        partie = self._partie_active()
        joueur = self.joueur_courant
        choix = choix or ChoixPouvoir()
        carte = self._trouver_dans_main(joueur, score)

        if joueur.nom in partie.en_jeu:
            raise RuntimeError("Une carte est déjà posée devant {}.".format(joueur.nom))
        if partie.direction_15 is not None and score != 15:
            self._verifier_contrainte_15(joueur, score)

        cartes_deja_posees = dict(partie.en_jeu)
        if score == 21:
            self._jouer_21(joueur, carte, choix)
        elif score == 15:
            if choix.direction_15 is None:
                raise ValueError("Il faut choisir au-dessus ou au-dessous de 15.")
            if not isinstance(choix.direction_15, DirectionScore):
                raise ValueError("La direction de la carte 15 est invalide.")
            self._poser(joueur, carte)
            partie.direction_15 = choix.direction_15
        elif score == 23 and cartes_deja_posees:
            cible = self._joueur_cible(choix.joueur_cible, joueur)
            if cible.nom not in cartes_deja_posees:
                raise ValueError("La cible de la carte 23 n'a pas encore de carte en jeu.")
            self._poser(joueur, carte)
            # La carte échangée prend la place du 23 ; le 23 va devant l'autre joueur.
            partie.en_jeu[joueur.nom], partie.en_jeu[cible.nom] = (
                partie.en_jeu[cible.nom],
                partie.en_jeu[joueur.nom],
            )
        elif score == 24:
            self._jouer_24(joueur, carte, choix)
        elif score == 28 and cartes_deja_posees:
            self._jouer_28(joueur, carte, choix, cartes_deja_posees)
        elif score == 29 and cartes_deja_posees and len(joueur.main) > 1:
            self._jouer_29(joueur, carte, choix, cartes_deja_posees)
        elif 30 <= score <= 35 and self._echange_30_35_possible(
            joueur, score, choix
        ):
            self._jouer_30_35(joueur, carte, choix)
        else:
            # Les pouvoirs de défausse et les pouvoirs passifs sont évalués en fin de tour.
            self._poser(joueur, carte)
            if score in (23, 28, 29) and not cartes_deja_posees:
                partie.journal.append(
                    "La carte {} est posée sans pouvoir : aucune autre carte n'était en jeu.".format(
                        score
                    )
                )

        partie.joueurs_ayant_joue.add(joueur.nom)
        partie.tour_index = (self.joueurs.index(joueur) + 1) % len(self.joueurs)

    def terminer_tour(self, choix_13: Optional[Dict[str, int]] = None) -> str:
        """Résout les défausses, remet les autres cartes en main et choisit le gagnant."""
        partie = self._partie_active()
        if len(partie.joueurs_ayant_joue) != len(self.joueurs):
            raise RuntimeError("Chaque joueur doit poser une carte avant la fin du tour.")
        if len(partie.en_jeu) != len(self.joueurs):
            raise RuntimeError("Il doit y avoir exactement une carte devant chaque joueur.")

        choix_13 = choix_13 or {}
        defausse_avant_tour = len(partie.defausse)
        gagnante = self._determiner_gagnante(partie)
        scores_posees = {
            carte_posee.proprietaire: carte_posee.carte.score
            for carte_posee in partie.en_jeu.values()
        }
        scores_a_defausser = self._determiner_defausses(partie, gagnante)
        joueur_22 = next(
            (
                carte_posee.poseur
                for carte_posee in partie.en_jeu.values()
                if carte_posee.carte.score == 22
            ),
            None,
        )
        proprietaires_13 = list(partie.cartes_13_a_resoudre)
        proprietaires_13.extend(
            carte_posee.proprietaire
            for carte_posee in partie.en_jeu.values()
            if carte_posee.carte.score == 13 and 13 in scores_a_defausser
        )
        proprietaires_13 = list(dict.fromkeys(proprietaires_13))

        proprietaires_avec_choix = [
            nom
            for nom in proprietaires_13
            if self._cartes_autres_que_14(self._joueur_par_nom(nom))
        ]
        if set(choix_13) - set(proprietaires_avec_choix):
            raise ValueError("Un choix de défausse 13 a été fourni sans être nécessaire.")

        # On valide tous les choix avant de modifier les mains ou la table.
        for nom in proprietaires_avec_choix:
            if nom not in choix_13:
                raise ValueError(
                    "Le propriétaire de la carte 13 doit choisir une carte supplémentaire."
                )
            score_extra = choix_13[nom]
            if score_extra == 14:
                raise ValueError("La carte supplémentaire choisie ne peut pas être la 14.")
            self._trouver_dans_main(self._joueur_par_nom(nom), score_extra)

        # La 13 impose une défausse depuis la main avant le retour des cartes non défaussées.
        defausseurs = list(proprietaires_avec_choix)
        for nom in proprietaires_avec_choix:
            joueur = self._joueur_par_nom(nom)
            extra = self._retirer_de_la_main(joueur, choix_13[nom])
            partie.defausse.append(extra)
            partie.journal.append(
                "{} défausse aussi la carte {} grâce à la carte 13.".format(nom, extra.score)
            )

        for joueur_devant, carte_posee in list(partie.en_jeu.items()):
            del partie.en_jeu[joueur_devant]
            score_carte = carte_posee.carte.score
            if score_carte in scores_a_defausser:
                partie.defausse.append(carte_posee.carte)
                defausseurs.append(carte_posee.proprietaire)
                partie.journal.append("La carte {} est défaussée.".format(score_carte))
            else:
                self._joueur_par_nom(carte_posee.proprietaire).main.append(carte_posee.carte)

        # Conserve le résultat de ce tour pour l'afficher pendant le tour suivant.
        partie.dernieres_defausses = [
            carte.score for carte in partie.defausse[defausse_avant_tour:]
        ]
        partie.derniers_defausseurs = list(dict.fromkeys(defausseurs))
        if 13 in scores_a_defausser:
            partie.cartes_13_a_resoudre.clear()

        gagnant = self._joueur_par_nom(gagnante.proprietaire)
        partie.dernier_joueur_a_remporter_tour = gagnant.nom
        partie.nombre_tours += 1
        partie.journal.append("{} remporte le tour.".format(gagnant.nom))

        joueurs_sans_cartes = [joueur for joueur in self.joueurs if not joueur.main]
        if joueurs_sans_cartes:
            if self.individuel:
                # Si le vainqueur n'est pas à court de cartes, le plus haut score parmi les
                # joueurs à court de cartes départage la victoire individuelle.
                joueur_vainqueur = next(
                    (
                        joueur
                        for joueur in joueurs_sans_cartes
                        if joueur.nom == gagnant.nom
                    ),
                    None,
                )
                if joueur_vainqueur is None:
                    joueur_vainqueur = max(
                        joueurs_sans_cartes,
                        key=lambda joueur: scores_posees.get(joueur.nom, 0),
                    )
                self.terminer_partie(joueur=joueur_vainqueur.nom)
                nom_vainqueur = joueur_vainqueur.nom
            else:
                equipes_sans_cartes = {
                    joueur.equipe for joueur in joueurs_sans_cartes
                }
                # Si plusieurs équipes sont à court de cartes, la victoire du tour départage.
                if len(equipes_sans_cartes) > 1:
                    equipe_vainqueur = gagnant.equipe
                else:
                    equipe_vainqueur = next(iter(equipes_sans_cartes))
                self.terminer_partie(equipe=equipe_vainqueur)
                nom_vainqueur = equipe_vainqueur.value
            partie.cartes_13_a_resoudre.clear()
            partie.journal.append(
                "{} remporte la partie.".format(nom_vainqueur)
            )
            return gagnant.nom

        if joueur_22 is not None:
            index_depart = (self._index_joueur(joueur_22) + 1) % len(self.joueurs)
        else:
            index_depart = self._index_joueur(gagnant.nom)

        partie.tour_index = index_depart
        partie.joueurs_ayant_joue.clear()
        partie.direction_15 = None
        partie.cartes_13_a_resoudre.clear()
        return gagnant.nom

    def terminer_partie(
        self, equipe: Optional[Equipe] = None, joueur: Optional[str] = None
    ) -> None:
        """Termine la partie, notamment après la défausse d'une dernière main."""
        if self.partie is None or self.partie.terminee:
            raise RuntimeError("Aucune partie active à terminer.")
        if self.individuel:
            if equipe is not None or joueur not in self.victoires_joueurs:
                raise ValueError("Il faut désigner un joueur gagnant valide.")
            self.victoires_joueurs[joueur] += 1
            self.partie.joueur_gagnant = joueur
        else:
            if equipe not in self.victoires or joueur is not None:
                raise ValueError("Il faut désigner une équipe gagnante valide.")
            self.victoires[equipe] += 1
            self.partie.equipe_gagnante = equipe
        self.partie.terminee = True

    def defausser_de_la_main(self, joueur: Joueur, score: int) -> Carte:
        """Défausse une carte de main ; une 13 ainsi défaussée garde son effet."""
        carte = self._retirer_de_la_main(joueur, score)
        partie = self._partie_active()
        partie.defausse.append(carte)
        if score == 13:
            partie.cartes_13_a_resoudre.append(joueur.nom)
        return carte

    def defausser_en_jeu(self, score: int) -> Carte:
        """Défausse une carte déjà posée ; une 13 ainsi défaussée garde son effet."""
        partie = self._partie_active()
        joueur_devant, carte_posee = self._trouver_en_jeu(score)
        del partie.en_jeu[joueur_devant]
        partie.defausse.append(carte_posee.carte)
        if score == 13:
            partie.cartes_13_a_resoudre.append(carte_posee.proprietaire)
        return carte_posee.carte

    def echanger_deux_mains(
        self, joueur_a: Joueur, score_a: int, joueur_b: Joueur, score_b: int
    ) -> None:
        """Opération bas niveau : échange deux cartes de main sans activer leur pouvoir."""
        carte_a = self._trouver_dans_main(joueur_a, score_a)
        carte_b = self._trouver_dans_main(joueur_b, score_b)
        joueur_a.main.remove(carte_a)
        joueur_b.main.remove(carte_b)
        joueur_a.main.append(carte_b)
        joueur_b.main.append(carte_a)

    def _jouer_21(
        self, joueur: Joueur, carte: Carte, choix: ChoixPouvoir
    ) -> None:
        partie = self._partie_active()
        if choix.utiliser_21 is None:
            raise ValueError("Il faut choisir si le pouvoir optionnel de la carte 21 est utilisé.")
        if not choix.utiliser_21:
            self._poser(joueur, carte)
            return

        cible = self._joueur_cible(choix.joueur_cible, joueur)
        if cible.nom in partie.joueurs_ayant_joue or cible.nom in partie.en_jeu:
            raise ValueError("La carte 21 doit viser un joueur qui n'a pas encore joué.")
        carte_forcee = self._trouver_dans_main(cible, choix.score_forcee_21)
        self._verifier_contrainte_15(cible, carte_forcee.score)

        # La 21 occupe la place de la cible ; celle-ci joue immédiatement devant le propriétaire.
        self._poser(joueur, carte, devant=cible.nom)
        self._poser(
            cible,
            carte_forcee,
            devant=joueur.nom,
            pouvoir_direct_actif=False,
        )
        partie.joueurs_ayant_joue.add(cible.nom)
        partie.journal.append(
            "{} joue la carte 21 devant {} ; {} pose la carte {} devant {}.".format(
                joueur.nom, cible.nom, cible.nom, carte_forcee.score, joueur.nom
            )
        )

    def _jouer_24(
        self, joueur: Joueur, carte: Carte, choix: ChoixPouvoir
    ) -> None:
        if choix.mode_24 is None:
            raise ValueError("Il faut choisir l'un des deux modes de la carte 24.")
        if not isinstance(choix.mode_24, ModeRevelation):
            raise ValueError("Le mode de révélation de la carte 24 est invalide.")
        cible = self._joueur_cible(choix.joueur_cible, joueur)
        if choix.mode_24 is ModeRevelation.MONTRER_MA_CARTE:
            revelee = self._trouver_main_sauf_score(
                joueur, carte.score, choix.score_main
            )
            message = "{} montre la carte {} à {}.".format(
                joueur.nom, revelee.score, cible.nom
            )
        else:
            revelee = self._trouver_dans_main(cible, choix.score_main_cible)
            message = "{} montre la carte {} à {}.".format(
                cible.nom, revelee.score, joueur.nom
            )
        self._poser(joueur, carte)
        self._partie_active().journal.append(message)

    def _jouer_28(
        self,
        joueur: Joueur,
        carte: Carte,
        choix: ChoixPouvoir,
        cartes_deja_posees: Dict[str, CartePosee],
    ) -> None:
        partie = self._partie_active()
        if choix.joueur_cible not in cartes_deja_posees:
            raise ValueError("La carte 28 doit cibler une carte déjà posée.")
        ancienne_carte = partie.en_jeu[choix.joueur_cible]
        proprietaire = self._joueur_par_nom(ancienne_carte.proprietaire)
        remplacements = [
            carte
            for carte in proprietaire.main
            if carte.score != ancienne_carte.carte.score
        ]
        if not remplacements:
            # Sans autre carte en main, il est impossible de remplacer la carte renvoyée.
            self._poser(joueur, carte)
            partie.journal.append(
                "La carte 28 est posée sans effet : {} n'a pas d'autre carte en main.".format(
                    proprietaire.nom
                )
            )
            return
        if choix.score_remplacement_28 == ancienne_carte.carte.score:
            raise ValueError("La carte remplacée ne peut pas être reposée par la carte 28.")
        if choix.score_remplacement_28 not in {c.score for c in remplacements}:
            raise ValueError(
                "Il faut choisir une autre carte de la main du propriétaire de la carte ciblée."
            )
        self._poser(joueur, carte)

        cible = choix.joueur_cible
        proprietaire.main.append(ancienne_carte.carte)
        remplacement = self._retirer_de_la_main(
            proprietaire, choix.score_remplacement_28
        )
        partie.en_jeu[cible] = CartePosee(
            carte=remplacement,
            proprietaire=proprietaire.nom,
            poseur=proprietaire.nom,
            pouvoir_direct_actif=False,
        )
        partie.journal.append(
            "{} renvoie la carte {} dans la main de {} ; la carte {} la remplace sans pouvoir direct.".format(
                joueur.nom, ancienne_carte.carte.score, proprietaire.nom, remplacement.score
            )
        )

    def _jouer_29(
        self,
        joueur: Joueur,
        carte: Carte,
        choix: ChoixPouvoir,
        cartes_deja_posees: Dict[str, CartePosee],
    ) -> None:
        partie = self._partie_active()
        if choix.joueur_cible not in cartes_deja_posees:
            raise ValueError("La carte 29 doit cibler une carte déjà posée.")
        self._trouver_main_sauf_score(joueur, carte.score, choix.score_main)
        self._poser(joueur, carte)

        cible = choix.joueur_cible
        ancienne_carte = partie.en_jeu[cible]
        self._joueur_par_nom(ancienne_carte.proprietaire).main.append(ancienne_carte.carte)
        nouvelle = self._retirer_de_la_main(joueur, choix.score_main)
        partie.en_jeu[cible] = CartePosee(
            carte=nouvelle,
            proprietaire=joueur.nom,
            poseur=joueur.nom,
            pouvoir_direct_actif=False,
        )

    def _jouer_30_35(
        self, joueur: Joueur, carte: Carte, choix: ChoixPouvoir
    ) -> None:
        cible = self._joueur_cible(choix.joueur_cible, joueur)
        carte_derniere = len(joueur.main) == 1
        if choix.score_main is not None and not carte_derniere:
            self._trouver_main_sauf_score(joueur, carte.score, choix.score_main)
        if choix.score_main_cible is None:
            raise ValueError("Le joueur ciblé doit choisir une carte de sa main.")
        self._trouver_dans_main(cible, choix.score_main_cible)
        self._poser(joueur, carte)

        if carte_derniere:
            if not self._partie_active().pioche:
                raise ValueError("La pioche est vide : l'échange de dernière carte est impossible.")
            carte_piochee = self._partie_active().pioche.pop()
            carte_donnee = carte_piochee
            self._partie_active().journal.append(
                "{} pioche la carte {} pour l'échange de sa carte absolue.".format(
                    joueur.nom, carte_piochee.score
                )
            )
        elif joueur.main:
            if choix.score_main is None:
                raise ValueError("Il faut choisir une carte de sa main à échanger.")
            carte_donnee = self._retirer_de_la_main(joueur, choix.score_main)
        else:
            raise RuntimeError("La main du joueur est incohérente après la pose.")
        carte_recue = self._retirer_de_la_main(cible, choix.score_main_cible)
        joueur.main.append(carte_recue)
        cible.main.append(carte_donnee)

    def _echange_30_35_possible(
        self, joueur: Joueur, score_joue: int, choix: ChoixPouvoir
    ) -> bool:
        """Sans deux cartes à échanger, la carte 30–35 est simplement posée."""
        a_carte_a_echanger = any(
            carte.score != score_joue for carte in joueur.main
        ) or (len(joueur.main) == 1 and bool(self._partie_active().pioche))
        if choix.joueur_cible is None:
            if any(autre is not joueur and autre.main for autre in self.joueurs):
                raise ValueError("Il faut désigner un joueur pour l'échange.")
            return False
        cible = self._joueur_cible(choix.joueur_cible, joueur)
        return a_carte_a_echanger and bool(cible.main)

    def _poser(
        self,
        joueur: Joueur,
        carte: Carte,
        devant: Optional[str] = None,
        pouvoir_direct_actif: bool = True,
    ) -> None:
        partie = self._partie_active()
        joueur_devant = devant or joueur.nom
        if joueur_devant in partie.en_jeu:
            raise RuntimeError("Une carte est déjà posée devant {}.".format(joueur_devant))
        self._retirer_de_la_main(joueur, carte.score)
        partie.en_jeu[joueur_devant] = CartePosee(
            carte=carte,
            proprietaire=joueur.nom,
            poseur=joueur.nom,
            pouvoir_direct_actif=pouvoir_direct_actif,
        )

    def _determiner_gagnante(
        self, partie: EtatPartie
    ) -> CartePosee:
        cartes_posees = list(partie.en_jeu.values())
        scores = [carte_posee.carte.score for carte_posee in cartes_posees]
        if 12 in scores:
            score_gagnant = min(scores)
        elif 26 in scores:
            score_gagnant = sorted(scores, reverse=True)[1]
        else:
            score_gagnant = max(scores)
        return next(
            carte_posee
            for carte_posee in cartes_posees
            if carte_posee.carte.score == score_gagnant
        )

    def _determiner_defausses(
        self, partie: EtatPartie, gagnante: CartePosee
    ) -> Set[int]:
        """Calcule tous les effets sur la table avant d'en déplacer les cartes."""
        scores = {carte_posee.carte.score for carte_posee in partie.en_jeu.values()}
        a_defausser = {gagnante.carte.score}
        couleurs = {
            score: CARTES[score].couleurs
            for score in scores
        }

        # Les cartes 1, 8, 9, 16, 18, 20 et 25 ciblent les cartes de ce tour comprises.
        cibles = (
            (1, "vert", True),
            (8, "vert", False),
            (9, "jaune", True),
            (16, "jaune", False),
            (18, "rouge", True),
            (20, None, False),
            (25, "rouge", False),
        )
        for pouvoir, couleur, prendre_max in cibles:
            if pouvoir not in scores:
                continue
            possibles = [
                score
                for score in scores
                if couleur is None or couleur in couleurs[score]
            ]
            if possibles:
                a_defausser.add(max(possibles) if prendre_max else min(possibles))

        # Ces pouvoirs conditionnels ne se déclenchent qu'à la fin du tour.
        for score in scores:
            couleurs_autres = {
                couleur
                for autre in scores
                if autre != score
                for couleur in couleurs[autre]
            }
            if score == 2 and "vert" in couleurs_autres:
                a_defausser.add(score)
            elif score == 3 and "jaune" in couleurs_autres:
                a_defausser.add(score)
            elif score == 4 and "rouge" in couleurs_autres:
                a_defausser.add(score)
            elif score == 5 and "bleu" in couleurs_autres:
                a_defausser.add(score)
            elif score == 6 and score == min(scores):
                a_defausser.add(score)
            elif score == 7 and sum("vert" in couleurs[s] for s in scores) == 1:
                a_defausser.add(score)
            elif score == 10 and any(CARTES[s].absolut for s in scores):
                a_defausser.add(score)
            elif score == 11 and sum("jaune" in couleurs[s] for s in scores) == 1:
                a_defausser.add(score)
            elif score == 19 and sum("rouge" in couleurs[s] for s in scores) == 1:
                a_defausser.add(score)

        # La 27 épargne toujours la 14 ; les autres effets respectent aussi sa protection.
        if 27 in scores:
            a_defausser.update(
                score
                for score in scores
                if score != 14 and "jaune" in couleurs[score]
            )
        if gagnante.carte.score != 14:
            a_defausser.discard(14)
        return a_defausser

    def _verifier_contrainte_15(self, joueur: Joueur, score: int) -> None:
        """Vérifie la direction choisie ; si elle est impossible, impose le plus proche."""
        partie = self._partie_active()
        direction = partie.direction_15
        if direction is None:
            return
        scores_en_main = [carte.score for carte in joueur.main]
        if direction is DirectionScore.AU_DESSUS:
            possibles = [valeur for valeur in scores_en_main if valeur > 15]
        else:
            possibles = [valeur for valeur in scores_en_main if valeur < 15]
        if not possibles:
            distance_min = min(abs(valeur - 15) for valeur in scores_en_main)
            possibles = [
                valeur
                for valeur in scores_en_main
                if abs(valeur - 15) == distance_min
            ]
        if score not in possibles:
            raise ValueError(
                "La carte doit respecter la contrainte de 15 (ou être au plus proche si impossible)."
            )

    def _joueur_cible(
        self, nom: Optional[str], joueur_actuel: Joueur
    ) -> Joueur:
        if nom is None:
            raise ValueError("Il faut désigner un joueur cible.")
        cible = self._joueur_par_nom(nom)
        if cible is joueur_actuel:
            raise ValueError("Un pouvoir ciblant un autre joueur ne peut pas se cibler soi-même.")
        return cible

    def _joueur_par_nom(self, nom: str) -> Joueur:
        for joueur in self.joueurs:
            if joueur.nom == nom:
                return joueur
        raise ValueError("Joueur inconnu : {}.".format(nom))

    def _index_joueur(self, nom: str) -> int:
        for index, joueur in enumerate(self.joueurs):
            if joueur.nom == nom:
                return index
        raise ValueError("Joueur inconnu : {}.".format(nom))

    def _trouver_dans_main(self, joueur: Joueur, score: Optional[int]) -> Carte:
        if score is None:
            raise ValueError("Il faut choisir une carte de la main.")
        for carte in joueur.main:
            if carte.score == score:
                return carte
        raise ValueError("{} n'a pas la carte {} en main.".format(joueur.nom, score))

    def _trouver_main_sauf_score(
        self, joueur: Joueur, score_exclu: int, score: Optional[int]
    ) -> Carte:
        carte = self._trouver_dans_main(joueur, score)
        if carte.score == score_exclu:
            raise ValueError("Il faut choisir une autre carte que celle qui vient d'être posée.")
        return carte

    @staticmethod
    def _retirer_de_la_main(joueur: Joueur, score: int) -> Carte:
        for carte in joueur.main:
            if carte.score == score:
                joueur.main.remove(carte)
                return carte
        raise ValueError("{} n'a pas la carte {} en main.".format(joueur.nom, score))

    def _trouver_en_jeu(self, score: int) -> Tuple[str, CartePosee]:
        for joueur_devant, carte_posee in self._partie_active().en_jeu.items():
            if carte_posee.carte.score == score:
                return joueur_devant, carte_posee
        raise ValueError("La carte {} n'est pas en jeu.".format(score))

    @staticmethod
    def _cartes_autres_que_14(joueur: Joueur) -> List[Carte]:
        return [carte for carte in joueur.main if carte.score != 14]

    def _partie_active(self) -> EtatPartie:
        if self.partie is None or self.partie.terminee:
            raise RuntimeError("Cette action nécessite une partie en cours.")
        return self.partie
