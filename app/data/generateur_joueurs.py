"""
Génère un effectif de ~23 joueurs par club avec des attributs
plausibles (le nom des joueurs n'est pas réel — remplacer plus tard
par un import de vraies données si souhaité, ex. via CSV).
"""
import random
from datetime import date, timedelta
from app.extensions import db
from app.models.models import Joueur, Club

PRENOMS = ["Jean", "Paul", "André", "Samuel", "Eric", "Junior", "Franck",
           "Carlos", "Diego", "Luca", "Marco", "Hugo", "Lucas", "Thomas",
           "Karim", "Yannick", "Bertrand", "Steve", "Mohamed", "Ahmed",
           "Kevin", "Bryan", "Anthony", "Cédric", "Fabrice"]
NOMS = ["Mbappe", "Nguema", "Fouda", "Essomba", "Njoya", "Tchoua", "Kamga",
        "Rossi", "Bianchi", "Garcia", "Fernandez", "Muller", "Weber",
        "Dupont", "Lefevre", "Smith", "Johnson", "Brown", "Ateba",
        "Onana", "Eto", "Biya", "Mvondo", "Talla", "Sanogo"]

POSTES_PAR_FORMATION = (
    ["GB"] * 3 + ["DC"] * 5 + ["DD"] * 2 + ["DG"] * 2 +
    ["MDC"] * 2 + ["MC"] * 3 + ["MD"] * 1 + ["MG"] * 1 + ["MOC"] * 2 +
    ["AD"] * 1 + ["AG"] * 1 + ["BU"] * 3
)


def _nom_aleatoire():
    return f"{random.choice(PRENOMS)} {random.choice(NOMS)}"


def _date_naissance_aleatoire():
    age = random.randint(17, 35)
    jours = random.randint(0, 364)
    return date(2026, 1, 1) - timedelta(days=age * 365 + jours)


def _generer_joueur(club, niveau_base):
    poste = random.choice(POSTES_PAR_FORMATION)
    variation = random.randint(-8, 8)
    niveau = max(30, min(95, niveau_base + variation))

    def _attr():
        return max(20, min(99, niveau + random.randint(-10, 10)))

    ca = max(20, min(99, niveau + random.randint(-5, 5)))
    pa = min(99, ca + random.randint(0, 20))  # potentiel toujours >= niveau actuel

    return Joueur(
        nom=_nom_aleatoire(),
        date_naissance=_date_naissance_aleatoire(),
        nationalite="Inconnue",
        poste_principal=poste,
        attaque=_attr(), finition=_attr(), defense=_attr(), tacle=_attr(),
        passe=_attr(), vision=_attr(), dribble=_attr(), physique=_attr(),
        vitesse=_attr(), technique=_attr(), mental=_attr(),
        niveau_actuel=ca, potentiel=pa,
        forme=random.randint(60, 90),
        moral=random.randint(55, 90),
        valeur_marchande=max(5_000, ca * ca * random.uniform(80, 200)),
        salaire_mensuel=max(500, ca * random.uniform(20, 60)),
        fin_contrat=date(2027, 6, 30) + timedelta(days=365 * random.randint(0, 4)),
        club_id=club.id,
        statut="actif",
    )


def generer_effectifs():
    """Génère un effectif pour chaque club qui n'en a pas encore."""
    clubs = Club.query.all()
    for club in clubs:
        if club.joueurs:
            continue
        # Niveau moyen du club dérivé de sa réputation
        niveau_base = 35 + int(club.reputation * 0.5)
        for _ in range(23):
            db.session.add(_generer_joueur(club, niveau_base))
    db.session.commit()
