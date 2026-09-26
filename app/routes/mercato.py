from flask import Blueprint, render_template, session, request, jsonify
from app.extensions import db
from app.models.models import Club, Joueur, Transfert
from app.services.ia_mercato import simuler_mercato_ia
from datetime import datetime

mercato_bp = Blueprint("mercato", __name__)


@mercato_bp.route("/mercato")
def marche_transferts():
    club = Club.query.get(session.get("club_id"))
    q = request.args.get("q", "")
    poste = request.args.get("poste", "")

    query = Joueur.query.filter(Joueur.club_id != club.id)
    if q:
        query = query.filter(Joueur.nom.ilike(f"%{q}%"))
    if poste:
        query = query.filter(Joueur.poste_principal == poste)

    joueurs = query.order_by(Joueur.valeur_marchande.desc()).limit(50).all()
    return render_template("mercato.html", club=club, joueurs=joueurs, q=q, poste=poste)


@mercato_bp.route("/mercato/offre", methods=["POST"])
def faire_offre():
    club = Club.query.get(session.get("club_id"))
    data = request.get_json()
    joueur = Joueur.query.get(data["joueur_id"])
    montant = float(data["montant"])
    type_operation = data.get("type_operation", "transfert")

    if montant > club.budget:
        return jsonify({"ok": False, "message": "Budget insuffisant"}), 400

    # Logique de négociation simplifiée : acceptation probable si
    # l'offre est proche ou supérieure à la valeur marchande.
    seuil_acceptation = joueur.valeur_marchande * 0.9
    acceptee = montant >= seuil_acceptation

    transfert = Transfert(
        joueur_id=joueur.id,
        club_vendeur_id=joueur.club_id,
        club_acheteur_id=club.id,
        montant=montant,
        type_operation=type_operation,
        date_operation=datetime.utcnow(),
        statut="finalisee" if acceptee else "refusee",
    )
    db.session.add(transfert)

    if acceptee:
        club.budget -= montant
        joueur.club_id = club.id

    db.session.commit()
    return jsonify({
        "ok": True,
        "acceptee": acceptee,
        "message": "Transfert finalisé !" if acceptee else "Offre refusée par le club vendeur.",
    })


@mercato_bp.route("/mercato/historique")
def historique():
    club = Club.query.get(session.get("club_id"))
    transferts = Transfert.query.filter(
        (Transfert.club_acheteur_id == club.id) | (Transfert.club_vendeur_id == club.id)
    ).order_by(Transfert.date_operation.desc()).all()
    return render_template("historique_transferts.html", club=club, transferts=transferts)


@mercato_bp.route("/mercato/simuler-ia", methods=["POST"])
def simuler_ia():
    """Fait bouger les autres clubs sur le marché (recrutements
    autonomes selon leurs besoins de poste et leur budget)."""
    club = Club.query.get(session.get("club_id"))
    resume = simuler_mercato_ia(club_utilisateur_id=club.id if club else None)
    return jsonify({"ok": True, "mouvements": resume,
                     "message": f"{len(resume)} mouvement(s) sur le marché."})


@mercato_bp.route("/mercato/offres-recues")
def offres_recues():
    club = Club.query.get(session.get("club_id"))
    offres = Transfert.query.filter_by(
        club_vendeur_id=club.id, statut="en_negociation").order_by(
        Transfert.date_operation.desc()).all()
    return render_template("offres_recues.html", club=club, offres=offres)


@mercato_bp.route("/mercato/offre/<int:transfert_id>/repondre", methods=["POST"])
def repondre_offre(transfert_id):
    club = Club.query.get(session.get("club_id"))
    transfert = Transfert.query.get_or_404(transfert_id)
    if transfert.club_vendeur_id != club.id or transfert.statut != "en_negociation":
        return jsonify({"ok": False, "message": "Offre introuvable ou déjà traitée."}), 400

    data = request.get_json()
    accepter = bool(data.get("accepter"))

    if accepter:
        joueur = Joueur.query.get(transfert.joueur_id)
        club_acheteur = Club.query.get(transfert.club_acheteur_id)
        joueur.club_id = club_acheteur.id
        club.budget += transfert.montant
        club_acheteur.budget -= transfert.montant
        transfert.statut = "finalisee"
        message = f"Transfert accepté : {joueur.nom} rejoint {club_acheteur.nom}."
    else:
        transfert.statut = "refusee"
        message = "Offre refusée."

    db.session.commit()
    return jsonify({"ok": True, "message": message})
