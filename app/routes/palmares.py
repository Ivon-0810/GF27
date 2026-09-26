from flask import Blueprint, render_template, request
from app.models.models import Saison, DistinctionSaison, TypeDistinction
from app.services.attribution_distinctions import attribuer_distinctions_saison

palmares_bp = Blueprint("palmares", __name__)


@palmares_bp.route("/palmares")
def voir_palmares():
    saisons = Saison.query.order_by(Saison.annee_debut.desc()).all()
    saison_id = request.args.get("saison_id", type=int)
    saison = (Saison.query.get(saison_id) if saison_id else
              Saison.query.filter_by(est_courante=True).first())

    distinctions_mondiales = []
    distinctions_continentales = []
    distinctions_par_division = {}

    if saison:
        rows = (DistinctionSaison.query
                .filter_by(saison_id=saison.id)
                .join(TypeDistinction)
                .order_by(TypeDistinction.nom, DistinctionSaison.rang)
                .all())
        for d in rows:
            if d.type_distinction.portee == "mondial":
                distinctions_mondiales.append(d)
            elif d.type_distinction.portee == "continental":
                distinctions_continentales.append(d)
            else:
                nom_div = d.type_distinction.division_id
                distinctions_par_division.setdefault(nom_div, []).append(d)

    return render_template("palmares.html", saisons=saisons, saison=saison,
                            distinctions_mondiales=distinctions_mondiales,
                            distinctions_continentales=distinctions_continentales,
                            distinctions_par_division=distinctions_par_division)


@palmares_bp.route("/palmares/calculer/<int:saison_id>", methods=["POST"])
def calculer(saison_id):
    """Déclenche manuellement le calcul du palmarès pour une saison
    (utile tant que la fin de saison automatique n'existe pas)."""
    a_reussi = attribuer_distinctions_saison(saison_id)
    from flask import redirect, url_for, flash
    return redirect(url_for("palmares.voir_palmares", saison_id=saison_id))
