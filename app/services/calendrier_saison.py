"""
Génère le calendrier d'une saison : pour chaque division, un
championnat classique en aller-retour (round-robin), où chaque club
affronte tous les autres deux fois (une fois à domicile, une fois à
l'extérieur).

Algorithme du "cercle" (round-robin standard) : on fixe un club et on
fait tourner les autres autour de lui, journée après journée.
"""
import random
from datetime import datetime, timedelta
from app.extensions import db
from app.models.models import Division, Club, Match


def _generer_journees_aller(clubs):
    """Renvoie une liste de journées (aller simple) : chaque journée
    est une liste de tuples (domicile, exterieur)."""
    equipes = clubs[:]
    if len(equipes) % 2 == 1:
        equipes.append(None)  # équipe fictive = journée de repos ("bye")

    n = len(equipes)
    journees = []
    for _ in range(n - 1):
        paires = []
        for i in range(n // 2):
            a, b = equipes[i], equipes[n - 1 - i]
            if a is not None and b is not None:
                paires.append((a, b))
        journees.append(paires)
        # rotation : on garde le premier fixe, on tourne les autres
        equipes = [equipes[0]] + [equipes[-1]] + equipes[1:-1]
    return journees


def generer_calendrier_division(division, saison, date_debut=None):
    """Crée les matchs (aller + retour) pour une division sur une
    saison donnée. Idempotent : ne fait rien si des matchs existent
    déjà pour ce couple division/saison."""
    if Match.query.filter_by(division_id=division.id, saison_id=saison.id).first():
        return 0

    clubs = list(division.clubs)
    if len(clubs) < 2:
        return 0

    random.shuffle(clubs)  # évite un calendrier identique chaque saison
    journees_aller = _generer_journees_aller(clubs)

    date_courante = date_debut or datetime(saison.annee_debut, 8, 15)
    numero_journee = 1
    nb_crees = 0

    # Aller
    for paires in journees_aller:
        for dom, ext in paires:
            db.session.add(Match(
                saison_id=saison.id, division_id=division.id,
                journee=numero_journee, date_match=date_courante,
                club_domicile_id=dom.id, club_exterieur_id=ext.id,
                statut="a_jouer",
            ))
            nb_crees += 1
        numero_journee += 1
        date_courante += timedelta(days=7)

    # Retour : mêmes paires, domicile/extérieur inversés
    for paires in journees_aller:
        for dom, ext in paires:
            db.session.add(Match(
                saison_id=saison.id, division_id=division.id,
                journee=numero_journee, date_match=date_courante,
                club_domicile_id=ext.id, club_exterieur_id=dom.id,
                statut="a_jouer",
            ))
            nb_crees += 1
        numero_journee += 1
        date_courante += timedelta(days=7)

    db.session.commit()
    return nb_crees


def generer_calendrier_saison_complete(saison):
    """Génère le calendrier de toutes les divisions pour une saison
    donnée (appelé une fois au début de chaque saison)."""
    total = 0
    for division in Division.query.all():
        total += generer_calendrier_division(division, saison)
    return total
