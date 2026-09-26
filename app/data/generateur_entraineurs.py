import random
from datetime import date, timedelta
from app.extensions import db
from app.models.models import Entraineur, Club

PRENOMS_COACH = ["Jürgen", "Pep", "Carlo", "Didier", "Antonio", "Jose", "Marco",
                 "Thomas", "Julian", "Xavi", "Roberto", "Massimiliano", "Zinedine",
                 "Samuel", "Joseph", "Rigobert", "Patrice"]
NOMS_COACH = ["Klopp", "Guardiola", "Ancelotti", "Deschamps", "Conte", "Mourinho",
              "Rossi", "Tuchel", "Nagelsmann", "Hernandez", "Martinez", "Allegri",
              "Zidane", "Eto'o", "Mbami", "Song", "Lauren"]


def _nom_coach_aleatoire():
    return f"{random.choice(PRENOMS_COACH)} {random.choice(NOMS_COACH)}"


def _date_naissance_coach():
    age = random.randint(38, 64)
    return date(2026, 1, 1) - timedelta(days=age * 365)


def generer_entraineurs():
    """Crée un entraîneur pour chaque club qui n'en a pas encore."""
    clubs = Club.query.all()
    for club in clubs:
        if club.entraineur_actuel():
            continue
        niveau = max(25, min(95, 40 + int(club.reputation * 0.55) + random.randint(-8, 8)))
        db.session.add(Entraineur(
            nom=_nom_coach_aleatoire(),
            nationalite="Inconnue",
            date_naissance=_date_naissance_coach(),
            tactique_preferee=random.choice(["4-4-2", "4-3-3", "3-5-2", "4-2-3-1"]),
            niveau=niveau,
            reputation=club.reputation,
            club_id=club.id,
            statut="actif",
        ))
    db.session.commit()
