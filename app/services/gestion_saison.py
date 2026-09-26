"""
Classement en direct (calculé à la volée à partir des matchs joués)
et bascule de fin de saison : montées/descentes, entraîneurs (stats
de saison), attribution du palmarès, puis ouverture de la saison
suivante (calendrier généré automatiquement).
"""
from app.extensions import db
from app.models.models import (Match, Club, Division, Saison, Entraineur,
                                StatistiqueSaisonEntraineur)
from app.services.calendrier_saison import generer_calendrier_saison_complete
from app.services.attribution_distinctions import attribuer_distinctions_saison


def calculer_classement(division_id, saison_id):
    """Renvoie une liste de dicts triés du 1er au dernier :
    club, points, victoires, nuls, defaites, bp, bc, diff, joues."""
    clubs = Club.query.filter_by(division_id=division_id).all()
    stats = {c.id: {"club": c, "points": 0, "v": 0, "n": 0, "d": 0,
                     "bp": 0, "bc": 0, "joues": 0} for c in clubs}

    matchs = Match.query.filter_by(division_id=division_id, saison_id=saison_id).filter(
        Match.statut.in_(["termine", "simule"])).all()

    for m in matchs:
        if m.club_domicile_id not in stats or m.club_exterieur_id not in stats:
            continue
        dom, ext = stats[m.club_domicile_id], stats[m.club_exterieur_id]
        sd, se = m.score_domicile or 0, m.score_exterieur or 0
        dom["bp"] += sd; dom["bc"] += se; dom["joues"] += 1
        ext["bp"] += se; ext["bc"] += sd; ext["joues"] += 1
        if sd > se:
            dom["points"] += 3; dom["v"] += 1; ext["d"] += 1
        elif sd < se:
            ext["points"] += 3; ext["v"] += 1; dom["d"] += 1
        else:
            dom["points"] += 1; ext["points"] += 1; dom["n"] += 1; ext["n"] += 1

    classement = list(stats.values())
    for c in classement:
        c["diff"] = c["bp"] - c["bc"]
    classement.sort(key=lambda c: (c["points"], c["diff"], c["bp"]), reverse=True)
    return classement


def matchs_de_la_prochaine_journee(division_id, saison_id):
    """La plus petite journée qui contient encore un match 'a_jouer'."""
    match_suivant = (Match.query
                     .filter_by(division_id=division_id, saison_id=saison_id, statut="a_jouer")
                     .order_by(Match.journee.asc()).first())
    if not match_suivant:
        return None, []
    matchs = Match.query.filter_by(division_id=division_id, saison_id=saison_id,
                                    journee=match_suivant.journee).all()
    return match_suivant.journee, matchs


def saison_est_terminee(saison_id):
    return Match.query.filter_by(saison_id=saison_id, statut="a_jouer").first() is None


def appliquer_montees_descentes(ligue):
    """Pour une ligue à plusieurs divisions (ex: pyramide
    camerounaise), échange les clubs entre D1 et D2 selon le
    classement final et les places définies sur chaque Division."""
    divisions = sorted(ligue.divisions, key=lambda d: d.niveau)
    for i in range(len(divisions) - 1):
        d1, d2 = divisions[i], divisions[i + 1]  # d1 = niveau supérieur
        saison = Saison.query.filter_by(est_courante=True).first()

        classement_d1 = calculer_classement(d1.id, saison.id)
        classement_d2 = calculer_classement(d2.id, saison.id)

        nb = min(d1.nb_relegues, d2.nb_montants)
        if nb <= 0:
            continue

        a_descendre = classement_d1[-nb:] if nb <= len(classement_d1) else []
        a_monter = classement_d2[:nb] if nb <= len(classement_d2) else []

        for entree in a_descendre:
            entree["club"].division_id = d2.id
        for entree in a_monter:
            entree["club"].division_id = d1.id

    db.session.commit()


def _enregistrer_stats_entraineurs(saison):
    """Calcule victoires/nuls/défaites/classement final par
    entraîneur pour la saison, avant de basculer sur la suivante
    (nécessaire pour The Best / Meilleur entraîneur)."""
    for division in Division.query.all():
        classement = calculer_classement(division.id, saison.id)
        for rang, entree in enumerate(classement, start=1):
            club = entree["club"]
            coach = club.entraineur_actuel()
            if not coach:
                continue
            stat = StatistiqueSaisonEntraineur.query.filter_by(
                entraineur_id=coach.id, saison_id=saison.id).first()
            if not stat:
                stat = StatistiqueSaisonEntraineur(entraineur_id=coach.id,
                                                    saison_id=saison.id, club_id=club.id)
                db.session.add(stat)
            stat.victoires = entree["v"]
            stat.nuls = entree["n"]
            stat.defaites = entree["d"]
            stat.classement_final = rang
            stat.titre_remporte = (rang == 1)
    db.session.commit()


def cloturer_saison(saison_id):
    """Bascule de fin de saison : stats entraîneurs -> palmarès ->
    montées/descentes -> activation de la saison suivante -> génération
    de son calendrier."""
    saison = Saison.query.get(saison_id)
    if not saison or not saison_est_terminee(saison_id):
        return False

    _enregistrer_stats_entraineurs(saison)
    attribuer_distinctions_saison(saison_id)

    from app.models.models import Ligue
    for ligue in Ligue.query.all():
        if len(ligue.divisions) > 1:
            appliquer_montees_descentes(ligue)

    saison.est_courante = False
    saison_suivante = (Saison.query
                       .filter(Saison.annee_debut > saison.annee_debut)
                       .order_by(Saison.annee_debut.asc()).first())
    if saison_suivante:
        saison_suivante.est_courante = True
        db.session.commit()
        generer_calendrier_saison_complete(saison_suivante)
    else:
        db.session.commit()

    return True
