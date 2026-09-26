from flask import Blueprint, render_template, request
from app.models.models import Joueur, Club, Ligue

recherche_bp = Blueprint("recherche", __name__)


@recherche_bp.route("/recherche")
def rechercher():
    q = request.args.get("q", "").strip()
    joueurs, clubs, ligues = [], [], []
    if q:
        joueurs = Joueur.query.filter(Joueur.nom.ilike(f"%{q}%")).limit(25).all()
        clubs = Club.query.filter(Club.nom.ilike(f"%{q}%")).limit(25).all()
        ligues = Ligue.query.filter(Ligue.nom.ilike(f"%{q}%")).limit(10).all()
    return render_template("recherche.html", q=q, joueurs=joueurs, clubs=clubs, ligues=ligues)
