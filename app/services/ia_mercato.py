"""
IA du mercato : à chaque déclenchement (bouton "Simuler le mercato"),
chaque club NON contrôlé par l'utilisateur regarde son groupe de
postes le plus faible, cherche un joueur mieux noté et abordable chez
un autre club, et fait une offre.

- Si le club vendeur est aussi une IA : la négociation se résout
  immédiatement (même règle que le mercato joueur : acceptée si
  l'offre >= 90% de la valeur marchande).
- Si le club vendeur est celui de l'utilisateur : l'offre reste
  "en_negociation" et attend une réponse humaine (voir
  app/routes/mercato.py -> offres_recues / repondre_offre).
"""
import random
from app.extensions import db
from app.models.models import Club, Joueur, Transfert

GROUPES_POSTES = {
    "gardien": ["GB"],
    "defense": ["DC", "DD", "DG"],
    "milieu": ["MDC", "MC", "MD", "MG", "MOC"],
    "attaque": ["AD", "AG", "BU"],
}

MAX_TRANSFERTS_PAR_SIMULATION = 15


def _note_moyenne_groupe(club, postes):
    joueurs = [j for j in club.effectif_actif() if j.poste_principal in postes]
    if not joueurs:
        return 0
    return sum(j.overall() for j in joueurs) / len(joueurs)


def _besoin_prioritaire(club):
    """Renvoie (nom_groupe, liste_postes) du groupe le plus faible."""
    notes = {nom: _note_moyenne_groupe(club, postes) for nom, postes in GROUPES_POSTES.items()}
    nom_faible = min(notes, key=notes.get)
    return nom_faible, GROUPES_POSTES[nom_faible]


def _chercher_candidat(club_acheteur, postes_cibles, budget_max):
    candidats = (Joueur.query
                 .filter(Joueur.club_id != club_acheteur.id)
                 .filter(Joueur.poste_principal.in_(postes_cibles))
                 .filter(Joueur.valeur_marchande <= budget_max)
                 .order_by(Joueur.valeur_marchande.desc())
                 .limit(20).all())
    # Parmi les abordables, on prend le mieux noté (l'IA vise le
    # meilleur renfort qu'elle peut se permettre, pas le moins cher)
    candidats = [c for c in candidats if c.club_id]
    if not candidats:
        return None
    return max(candidats, key=lambda j: j.overall())


def simuler_mercato_ia(club_utilisateur_id=None):
    """Fait tourner l'IA sur un sous-ensemble de clubs (pour rester
    rapide) et renvoie un résumé texte des mouvements."""
    clubs_ia = Club.query.filter(Club.id != club_utilisateur_id).all()
    random.shuffle(clubs_ia)

    resume = []
    nb_transferts = 0

    for club in clubs_ia:
        if nb_transferts >= MAX_TRANSFERTS_PAR_SIMULATION:
            break
        if club.budget < 20_000:
            continue

        nom_besoin, postes = _besoin_prioritaire(club)
        budget_max = club.budget * 0.7
        candidat = _chercher_candidat(club, postes, budget_max)
        if not candidat:
            continue

        note_actuelle = _note_moyenne_groupe(club, postes)
        if candidat.overall() <= note_actuelle:
            continue  # pas d'intérêt à recruter moins bon que l'existant

        montant_offre = round(candidat.valeur_marchande * random.uniform(0.95, 1.25), -2)
        if montant_offre > club.budget:
            continue

        club_vendeur_id = candidat.club_id

        if club_vendeur_id == club_utilisateur_id:
            # Laisse la décision à l'utilisateur
            db.session.add(Transfert(
                joueur_id=candidat.id, club_vendeur_id=club_vendeur_id,
                club_acheteur_id=club.id, montant=montant_offre,
                type_operation="transfert", statut="en_negociation",
            ))
            resume.append(f"{club.nom} propose {montant_offre:,.0f} € pour {candidat.nom} "
                          f"(à valider par toi)")
            continue

        club_vendeur = Club.query.get(club_vendeur_id)
        seuil_acceptation = candidat.valeur_marchande * 0.9
        acceptee = montant_offre >= seuil_acceptation

        db.session.add(Transfert(
            joueur_id=candidat.id, club_vendeur_id=club_vendeur_id,
            club_acheteur_id=club.id, montant=montant_offre,
            type_operation="transfert",
            statut="finalisee" if acceptee else "refusee",
        ))

        if acceptee:
            club.budget -= montant_offre
            if club_vendeur:
                club_vendeur.budget += montant_offre
            candidat.club_id = club.id
            resume.append(f"✅ {club.nom} recrute {candidat.nom} "
                          f"({nom_besoin}) pour {montant_offre:,.0f} €"
                          + (f", en provenance de {club_vendeur.nom}" if club_vendeur else ""))
            nb_transferts += 1

    db.session.commit()
    return resume
