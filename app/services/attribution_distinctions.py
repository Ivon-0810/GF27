"""
Calcule et enregistre le palmarès individuel d'une saison, à partir
des statistiques cumulées (StatistiqueSaisonJoueur / Entraineur).

IMPORTANT : ce calcul ne peut produire un palmarès réaliste QUE si
des matchs ont été joués/simulés pendant la saison (ce sont eux qui
alimentent StatistiqueSaisonJoueur via app/routes/match_routes.py).
Tant que le calendrier de saison automatique n'existe pas encore,
lance cette fonction après avoir simulé manuellement quelques
matchs pour voir un palmarès non vide.
"""
from app.extensions import db
from app.models.models import (TypeDistinction, DistinctionSaison,
                                StatistiqueSaisonJoueur, StatistiqueSaisonEntraineur,
                                Joueur, Division, Ligue)

CATALOGUE_MONDIAL = [
    ("BALLON_OR", "Ballon d'Or", "joueur"),
    ("YACHINE", "Trophée Yachine (meilleur gardien)", "gardien"),
    ("KOPA", "Trophée Kopa (meilleur jeune, -21 ans)", "jeune"),
    ("THE_BEST_COACH", "The Best — Entraîneur de l'année", "entraineur"),
]

CATALOGUE_CONTINENTAL_AFRICAIN = [
    ("BALLON_OR_AFRICAIN", "Ballon d'Or Africain", "joueur"),
]

CATALOGUE_PAR_DIVISION = [
    ("SOULIER_OR", "Soulier d'Or — {division}", "buteur"),
    ("GANT_OR", "Gant d'Or — {division}", "gardien"),
    ("JOUEUR_SAISON", "Joueur de la saison — {division}", "joueur"),
    ("MEILLEUR_JEUNE", "Meilleur jeune — {division}", "jeune"),
    ("MEILLEUR_ENTRAINEUR", "Meilleur entraîneur — {division}", "entraineur"),
]


def initialiser_catalogue():
    """Crée les TypeDistinction s'ils n'existent pas déjà (idempotent)."""
    if TypeDistinction.query.first():
        return

    for code, nom, categorie in CATALOGUE_MONDIAL:
        db.session.add(TypeDistinction(code=code, nom=nom, portee="mondial",
                                        categorie=categorie))
    for code, nom, categorie in CATALOGUE_CONTINENTAL_AFRICAIN:
        db.session.add(TypeDistinction(code=code, nom=nom, portee="continental",
                                        categorie=categorie))

    for division in Division.query.all():
        for code_base, nom_template, categorie in CATALOGUE_PAR_DIVISION:
            code = f"{code_base}_{division.id}"
            db.session.add(TypeDistinction(
                code=code, nom=nom_template.format(division=division.nom),
                portee="national", categorie=categorie, division_id=division.id))

    db.session.commit()


def _top_n(liste, cle, n=3):
    return sorted(liste, key=cle, reverse=True)[:n]


def _enregistrer(type_code, saison_id, gagnants):
    """gagnants : liste de tuples (joueur_id|None, entraineur_id|None,
    club_id, valeur_cle) déjà triée du 1er au 3e."""
    type_dist = TypeDistinction.query.filter_by(code=type_code).first()
    if not type_dist:
        return
    # Retire une éventuelle attribution précédente pour cette saison (idempotent)
    DistinctionSaison.query.filter_by(type_distinction_id=type_dist.id,
                                       saison_id=saison_id).delete()
    for rang, (joueur_id, entraineur_id, club_id, valeur) in enumerate(gagnants, start=1):
        db.session.add(DistinctionSaison(
            type_distinction_id=type_dist.id, saison_id=saison_id, rang=rang,
            joueur_id=joueur_id, entraineur_id=entraineur_id, club_id=club_id,
            valeur_cle=valeur))


def attribuer_distinctions_saison(saison_id):
    initialiser_catalogue()

    stats_joueurs = StatistiqueSaisonJoueur.query.filter_by(saison_id=saison_id).all()
    stats_coachs = StatistiqueSaisonEntraineur.query.filter_by(saison_id=saison_id).all()

    if not stats_joueurs and not stats_coachs:
        return False  # rien à attribuer pour l'instant

    joueurs_par_id = {j.id: j for j in Joueur.query.all()}

    def score_global(s):
        return (s.buts or 0) * 2 + (s.passes_decisives or 0) + (s.note_moyenne or 6) * 3

    # --- Par division ---
    for division in Division.query.all():
        stats_div = [s for s in stats_joueurs if s.division_id == division.id]

        buteurs = _top_n(stats_div, lambda s: s.buts or 0)
        _enregistrer(f"SOULIER_OR_{division.id}", saison_id, [
            (s.joueur_id, None, s.club_id, f"{s.buts or 0} buts") for s in buteurs])

        gardiens = [s for s in stats_div
                    if joueurs_par_id.get(s.joueur_id) and
                    joueurs_par_id[s.joueur_id].poste_principal == "GB"]
        top_gardiens = _top_n(gardiens, lambda s: s.clean_sheets or 0)
        _enregistrer(f"GANT_OR_{division.id}", saison_id, [
            (s.joueur_id, None, s.club_id, f"{s.clean_sheets or 0} clean sheets")
            for s in top_gardiens])

        top_joueurs = _top_n(stats_div, score_global)
        _enregistrer(f"JOUEUR_SAISON_{division.id}", saison_id, [
            (s.joueur_id, None, s.club_id, f"Note {round(s.note_moyenne or 6, 1)}/10")
            for s in top_joueurs])

        jeunes = [s for s in stats_div
                  if joueurs_par_id.get(s.joueur_id) and
                  (joueurs_par_id[s.joueur_id].age() or 99) <= 21]
        top_jeunes = _top_n(jeunes, score_global)
        _enregistrer(f"MEILLEUR_JEUNE_{division.id}", saison_id, [
            (s.joueur_id, None, s.club_id, f"{s.buts or 0} buts") for s in top_jeunes])

        coachs_div = [s for s in stats_coachs
                      if s.club_id in [c.id for c in division.clubs]]
        top_coachs = _top_n(coachs_div, lambda s: s.victoires or 0)
        _enregistrer(f"MEILLEUR_ENTRAINEUR_{division.id}", saison_id, [
            (None, s.entraineur_id, s.club_id, f"{s.victoires or 0} victoires")
            for s in top_coachs])

    # --- Mondial ---
    top_monde = _top_n(stats_joueurs, score_global)
    _enregistrer("BALLON_OR", saison_id, [
        (s.joueur_id, None, s.club_id, f"Note {round(s.note_moyenne or 6, 1)}/10")
        for s in top_monde])

    gardiens_monde = [s for s in stats_joueurs
                       if joueurs_par_id.get(s.joueur_id) and
                       joueurs_par_id[s.joueur_id].poste_principal == "GB"]
    top_gardiens_monde = _top_n(gardiens_monde, lambda s: s.clean_sheets or 0)
    _enregistrer("YACHINE", saison_id, [
        (s.joueur_id, None, s.club_id, f"{s.clean_sheets or 0} clean sheets")
        for s in top_gardiens_monde])

    jeunes_monde = [s for s in stats_joueurs
                    if joueurs_par_id.get(s.joueur_id) and
                    (joueurs_par_id[s.joueur_id].age() or 99) <= 21]
    top_jeunes_monde = _top_n(jeunes_monde, score_global)
    _enregistrer("KOPA", saison_id, [
        (s.joueur_id, None, s.club_id, f"{s.buts or 0} buts") for s in top_jeunes_monde])

    top_coachs_monde = _top_n(stats_coachs, lambda s: s.victoires or 0)
    _enregistrer("THE_BEST_COACH", saison_id, [
        (None, s.entraineur_id, s.club_id, f"{s.victoires or 0} victoires")
        for s in top_coachs_monde])

    # --- Continental africain (proxy : divisions de la ligue camerounaise) ---
    ligue_cmr = Ligue.query.filter_by(nom="Football Camerounais").first()
    if ligue_cmr:
        divisions_cmr_ids = [d.id for d in ligue_cmr.divisions]
        stats_afrique = [s for s in stats_joueurs if s.division_id in divisions_cmr_ids]
        top_afrique = _top_n(stats_afrique, score_global)
        _enregistrer("BALLON_OR_AFRICAIN", saison_id, [
            (s.joueur_id, None, s.club_id, f"{s.buts or 0} buts") for s in top_afrique])

    db.session.commit()
    return True
