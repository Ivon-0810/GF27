from flask import Blueprint, render_template, redirect, url_for, session, request
from app.extensions import db
from app.models.models import Club, Division, Ligue, Pays, Saison

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def accueil():
    club_id = session.get("club_id")
    if club_id:
        return redirect(url_for("effectif.voir_effectif"))
    ligues = Ligue.query.all()
    return render_template("choix_club.html", ligues=ligues)


@main_bp.route("/choisir-club/<int:club_id>")
def choisir_club(club_id):
    session["club_id"] = club_id
    return redirect(url_for("effectif.voir_effectif"))


@main_bp.route("/tableau-de-bord")
def tableau_de_bord():
    club = Club.query.get(session.get("club_id"))
    saison = Saison.query.filter_by(est_courante=True).first()
    return render_template("dashboard.html", club=club, saison=saison)
