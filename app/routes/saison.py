from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from app.extensions import db
from app.models.models import Club, Saison, Match
from app.services.gestion_saison import (calculer_classement,
                                          matchs_de_la_prochaine_journee,
                                          saison_est_terminee, cloturer_saison)
from app.services import moteur_match
from app.routes.match_routes import _assurer_composition, _stats_equipe, _incrementer_but

saison_bp = Blueprint("saison", __name__)


def _club_et_saison():
    club = Club.query.get(session.get("club_id"))
    saison = Saison.query.filter_by(est_courante=True).first()
    return club, saison


@saison_bp.route("/classement")
def voir_classement():
    club, saison = _club_et_saison()
    if not club or not saison:
        return redirect(url_for("main.accueil"))
    classement = calculer_classement(club.division_id, saison.id)
    return render_template("classement.html", club=club, saison=saison,
                            division=club.division, classement=classement)


@saison_bp.route("/calendrier")
def voir_calendrier():
    club, saison = _club_et_saison()
    if not club or not saison:
        return redirect(url_for("main.accueil"))

    journee, matchs = matchs_de_la_prochaine_journee(club.division_id, saison.id)
    match_du_club = next((m for m in matchs
                          if m.club_domicile_id == club.id or m.club_exterieur_id == club.id),
                          None) if matchs else None
    saison_finie = saison_est_terminee(saison.id)

    return render_template("calendrier.html", club=club, saison=saison, journee=journee,
                            matchs=matchs, match_du_club=match_du_club,
                            saison_finie=saison_finie)


@saison_bp.route("/calendrier/simuler-journee", methods=["POST"])
def simuler_journee():
    """Simule instantanément tous les matchs de la prochaine journée
    SAUF celui du club de l'utilisateur, qu'il ira jouer/suivre lui-même
    depuis l'écran Jour de match."""
    club, saison = _club_et_saison()
    if not club or not saison:
        return jsonify({"ok": False}), 400

    journee, matchs = matchs_de_la_prochaine_journee(club.division_id, saison.id)
    if not matchs:
        return jsonify({"ok": True, "message": "Aucune journée à jouer."})

    for match in matchs:
        if match.club_domicile_id == club.id or match.club_exterieur_id == club.id:
            continue  # laissé à l'utilisateur
        club_dom = Club.query.get(match.club_domicile_id)
        club_ext = Club.query.get(match.club_exterieur_id)
        comp_dom = _assurer_composition(match, club_dom)
        comp_ext = _assurer_composition(match, club_ext)
        stats_dom = _stats_equipe(comp_dom)
        stats_ext = _stats_equipe(comp_ext)
        score_dom, score_ext, evenements, stats_f = moteur_match.simuler_match_complet(
            stats_dom, stats_ext, club_dom.nom, club_ext.nom)
        for e in evenements:
            if e["type"] == "but":
                _incrementer_but(e.get("joueur_id"), match.saison_id, match.division_id)
        match.score_domicile = score_dom
        match.score_exterieur = score_ext
        match.minute_courante = 90
        match.statut = "simule"

    db.session.commit()
    return jsonify({"ok": True, "message": f"Journée {journee} simulée."})


@saison_bp.route("/saison/cloturer", methods=["POST"])
def cloturer():
    _, saison = _club_et_saison()
    if not saison:
        return jsonify({"ok": False}), 400
    reussi = cloturer_saison(saison.id)
    return jsonify({"ok": reussi,
                     "message": "Nouvelle saison lancée !" if reussi
                     else "Il reste des matchs à jouer cette saison."})
