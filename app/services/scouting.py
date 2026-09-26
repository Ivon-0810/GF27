"""
Réseau de recruteurs : chaque club-joueur peut employer des
recruteurs qui envoient des rapports sur des jeunes joueurs, avec une
estimation BRUITÉE du potentiel caché (PA) — plus la note du
recruteur est haute, plus la marge d'erreur est faible. C'est ce qui
rend le scouting utile : sans lui, le PA reste une donnée cachée.
"""
import random
from app.extensions import db
from app.models.models import Recruteur, RapportScouting, Joueur

NOMS_RECRUTEUR = ["Paul Le Guen", "Marc Ndoumbe", "Igor Petrov", "Hans Bauer",
                   "Luis Fernandez", "Samir Haddad", "Jean-Pierre Ateba"]


def creer_recruteur_pour_club(club, zone="Monde"):
    recruteur = Recruteur(
        nom=random.choice(NOMS_RECRUTEUR),
        club_id=club.id,
        note_evaluation=random.randint(35, 85),
        zone_couverte=zone,
        salaire_mensuel=random.randint(500, 3000),
    )
    db.session.add(recruteur)
    db.session.commit()
    return recruteur


def generer_rapport(recruteur, joueur):
    """Le PA réel du joueur reste dans la base (potentiel) ; le
    rapport donne une ESTIMATION bruitée, comme si le recruteur ne
    connaissait pas la vraie valeur — c'est ta responsabilité de ne
    pas 'tricher' en la consultant directement dans un vrai mode
    carrière si tu veux garder la tension du scouting."""
    marge = max(2, 25 - recruteur.note_evaluation // 4)
    bruit = random.randint(-marge, marge)
    estimation = max(30, min(99, joueur.potentiel + bruit))

    if estimation >= 85:
        recommandation = "Pépite à suivre de très près."
    elif estimation >= 70:
        recommandation = "Bon potentiel, rapport qualité/prix intéressant."
    elif estimation <= joueur.niveau_actuel + 3:
        recommandation = "Déjà proche de son plafond."
    else:
        recommandation = "Joueur correct, sans plus."

    rapport = RapportScouting(
        recruteur_id=recruteur.id, joueur_id=joueur.id,
        potentiel_estime=estimation, marge_erreur=marge,
        recommandation=recommandation,
    )
    db.session.add(rapport)
    db.session.commit()
    return rapport
