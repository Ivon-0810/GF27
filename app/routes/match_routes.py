from flask import Blueprint, render_template, session, request, jsonify
from app.extensions import db
from app.models.models import (Club, Joueur, Match, Composition,
                                CompositionJoueur, EvenementMatch,
                                StatistiqueSaisonJoueur)
from app.services import moteur_match

match_bp = Blueprint("match", __name__)


FORMATIONS_POSTES = {
    "4-4-2":    ["GB", "DD", "DC", "DC", "DG", "MD", "MC", "MC", "MG", "BU", "BU"],
    "4-3-3":    ["GB", "DD", "DC", "DC", "DG", "MDC", "MC", "MC", "AD", "BU", "AG"],
    "3-5-2":    ["GB", "DC", "DC", "DC", "MD", "MDC", "MC", "MC", "MG", "BU", "BU"],
    "4-2-3-1":  ["GB", "DD", "DC", "DC", "DG", "MDC", "MDC", "MOC", "AD", "AG", "BU"],
    "5-3-2":    ["GB", "DD", "DC", "DC", "DC", "DG", "MC", "MC", "MC", "BU", "BU"],
}


def _assurer_composition(match, club):
    """Si aucune composition n'existe encore pour ce club sur ce
    match, en génère une automatiquement : les meilleurs joueurs
    disponibles au poste le plus proche, selon la formation et les
    consignes par défaut du club. Le reste de l'effectif part sur le
    banc (utilisable pour les changements)."""
    composition = Composition.query.filter_by(match_id=match.id, club_id=club.id).first()
    if composition:
        return composition

    formation = club.formation_favorite if club.formation_favorite in FORMATIONS_POSTES else "4-4-2"
    composition = Composition(
        match_id=match.id, club_id=club.id, formation=formation,
        consigne_mentalite=club.consigne_mentalite_defaut,
        consigne_style=club.consigne_style_defaut,
        ligne_defensive=club.ligne_defensive_defaut,
        intensite_pressing=club.pressing_defaut,
    )
    db.session.add(composition)
    db.session.flush()

    disponibles = sorted(club.effectif_actif(), key=lambda j: -j.overall())
    deja_pris = set()
    postes_recherches = FORMATIONS_POSTES[formation]

    for poste in postes_recherches:
        candidat = next((j for j in disponibles
                          if j.id not in deja_pris and j.poste_principal == poste), None)
        if not candidat:
            candidat = next((j for j in disponibles if j.id not in deja_pris), None)
        if candidat:
            deja_pris.add(candidat.id)
            db.session.add(CompositionJoueur(composition_id=composition.id,
                                              joueur_id=candidat.id,
                                              poste_occupe=poste, est_titulaire=True))

    for joueur in disponibles:
        if joueur.id not in deja_pris:
            db.session.add(CompositionJoueur(composition_id=composition.id,
                                              joueur_id=joueur.id,
                                              poste_occupe=joueur.poste_principal,
                                              est_titulaire=False))
    db.session.commit()
    return composition


def _stats_equipe(composition):
    if composition is None:
        return moteur_match.stats_equipe_depuis_composition([], None)
    titulaires_ids = [cj.joueur_id for cj in composition.titulaires if cj.est_titulaire]
    joueurs = Joueur.query.filter(Joueur.id.in_(titulaires_ids)).all() if titulaires_ids else []
    return moteur_match.stats_equipe_depuis_composition(joueurs, composition)


def _incrementer_but(joueur_id, saison_id, division_id=None):
    if not joueur_id or not saison_id:
        return
    stat = StatistiqueSaisonJoueur.query.filter_by(
        joueur_id=joueur_id, saison_id=saison_id).first()
    if not stat:
        joueur = Joueur.query.get(joueur_id)
        stat = StatistiqueSaisonJoueur(joueur_id=joueur_id, saison_id=saison_id,
                                        club_id=joueur.club_id if joueur else None,
                                        division_id=division_id)
        db.session.add(stat)
    elif division_id and not stat.division_id:
        stat.division_id = division_id
    stat.buts = (stat.buts or 0) + 1


def _finaliser_participations(match, composition):
    """Incrémente matchs_joues pour tous les joueurs ayant terminé le
    match dans le onze (titulaires restants + entrants), afin
    d'alimenter le calcul du palmarès de fin de saison."""
    if not composition or not match.saison_id:
        return
    joueur = None
    for cj in composition.titulaires:
        if not cj.est_titulaire:
            continue
        stat = StatistiqueSaisonJoueur.query.filter_by(
            joueur_id=cj.joueur_id, saison_id=match.saison_id).first()
        if not stat:
            joueur = Joueur.query.get(cj.joueur_id)
            stat = StatistiqueSaisonJoueur(joueur_id=cj.joueur_id, saison_id=match.saison_id,
                                            club_id=joueur.club_id if joueur else None,
                                            division_id=match.division_id)
            db.session.add(stat)
        stat.matchs_joues = (stat.matchs_joues or 0) + 1
        if not stat.division_id:
            stat.division_id = match.division_id


@match_bp.route("/match/<int:match_id>")
def jour_de_match(match_id):
    match = Match.query.get_or_404(match_id)
    club_dom = Club.query.get(match.club_domicile_id)
    club_ext = Club.query.get(match.club_exterieur_id)
    comp_dom = _assurer_composition(match, club_dom)
    comp_ext = _assurer_composition(match, club_ext)
    club_utilisateur_id = session.get("club_id")
    return render_template("match.html", match=match, club_dom=club_dom,
                            club_ext=club_ext, comp_dom=comp_dom, comp_ext=comp_ext,
                            club_utilisateur_id=club_utilisateur_id)


@match_bp.route("/match/<int:match_id>/avancer", methods=["POST"])
def avancer_match(match_id):
    """Avance le match de plusieurs minutes ; s'arrête à la 45e
    (mi-temps, pour permettre changements + retouches tactiques) puis
    à la 90e. Renvoie les évènements enrichis (buteur identifié,
    commentaires) et les stats live (tirs/cadrés/xG/possession)."""
    match = Match.query.get_or_404(match_id)
    comp_dom = Composition.query.filter_by(match_id=match.id,
                                            club_id=match.club_domicile_id).first()
    comp_ext = Composition.query.filter_by(match_id=match.id,
                                            club_id=match.club_exterieur_id).first()
    club_dom = Club.query.get(match.club_domicile_id)
    club_ext = Club.query.get(match.club_exterieur_id)
    stats_dom = _stats_equipe(comp_dom)
    stats_ext = _stats_equipe(comp_ext)

    minutes_cibles = [45, 90]
    prochaine_pause = next((m for m in minutes_cibles if m > match.minute_courante), 90)

    nouveaux_evenements = []
    while match.minute_courante < prochaine_pause:
        match.minute_courante += 1
        evts = moteur_match.simuler_minute(match.minute_courante, stats_dom, stats_ext,
                                            club_dom.nom if club_dom else "Domicile",
                                            club_ext.nom if club_ext else "Extérieur")
        for e in evts:
            club_id = match.club_domicile_id if e["equipe"] == "domicile" else match.club_exterieur_id
            prefixe = "domicile" if e["equipe"] == "domicile" else "exterieur"

            if e["type"] in ("but", "tir"):
                setattr(match, f"tirs_{prefixe}", (getattr(match, f"tirs_{prefixe}") or 0) + 1)
                if e.get("cadre") or e["type"] == "but":
                    setattr(match, f"tirs_cadres_{prefixe}",
                            (getattr(match, f"tirs_cadres_{prefixe}") or 0) + 1)
                setattr(match, f"xg_{prefixe}",
                        round((getattr(match, f"xg_{prefixe}") or 0) + e.get("xg", 0.05), 2))

            if e["type"] == "but":
                if e["equipe"] == "domicile":
                    match.score_domicile = (match.score_domicile or 0) + 1
                else:
                    match.score_exterieur = (match.score_exterieur or 0) + 1
                _incrementer_but(e.get("joueur_id"), match.saison_id, match.division_id)

            ev = EvenementMatch(match_id=match.id, minute=e["minute"],
                                 type_evenement=e["type"], club_id=club_id,
                                 joueur_id=e.get("joueur_id"),
                                 description=e.get("commentaire", ""))
            db.session.add(ev)
            nouveaux_evenements.append({
                "minute": e["minute"], "type": e["type"], "equipe": e["equipe"],
                "joueur_nom": e.get("joueur_nom"), "commentaire": e.get("commentaire", ""),
            })

    possession_dom = moteur_match._possession_du_moment(stats_dom, stats_ext)
    match.possession_domicile = possession_dom
    match.possession_exterieur = 100 - possession_dom

    if match.minute_courante >= 90:
        match.statut = "termine"
        _finaliser_participations(match, comp_dom)
        _finaliser_participations(match, comp_ext)
    elif match.minute_courante >= 45:
        match.statut = "mi_temps"
    else:
        match.statut = "en_cours"

    db.session.commit()
    return jsonify({
        "minute": match.minute_courante,
        "score_domicile": match.score_domicile,
        "score_exterieur": match.score_exterieur,
        "statut": match.statut,
        "evenements": nouveaux_evenements,
        "stats": {
            "tirs_dom": match.tirs_domicile, "cadres_dom": match.tirs_cadres_domicile,
            "xg_dom": match.xg_domicile, "possession_dom": match.possession_domicile,
            "tirs_ext": match.tirs_exterieur, "cadres_ext": match.tirs_cadres_exterieur,
            "xg_ext": match.xg_exterieur, "possession_ext": match.possession_exterieur,
        },
    })


@match_bp.route("/match/<int:match_id>/changement", methods=["POST"])
def faire_changement(match_id):
    match = Match.query.get_or_404(match_id)
    data = request.get_json()
    composition_id = data["composition_id"]
    joueur_sortant_id = data["joueur_sortant_id"]
    joueur_entrant_id = data["joueur_entrant_id"]

    cj_sortant = CompositionJoueur.query.filter_by(
        composition_id=composition_id, joueur_id=joueur_sortant_id).first()
    cj_entrant = CompositionJoueur.query.filter_by(
        composition_id=composition_id, joueur_id=joueur_entrant_id).first()

    if not cj_sortant or not cj_entrant:
        return jsonify({"ok": False, "message": "Joueur introuvable dans la composition"}), 400

    cj_sortant.est_titulaire = False
    cj_sortant.sorti_minute = match.minute_courante
    cj_entrant.est_titulaire = True
    cj_entrant.poste_occupe = cj_sortant.poste_occupe

    sortant = Joueur.query.get(joueur_sortant_id)
    entrant = Joueur.query.get(joueur_entrant_id)
    commentaire = moteur_match._commentaire(
        "changement", match.minute_courante, "",
        nom_joueur=sortant.nom if sortant else "?",
        nom_entrant=entrant.nom if entrant else "?")

    ev = EvenementMatch(match_id=match.id, minute=match.minute_courante,
                         type_evenement="changement", joueur_id=joueur_sortant_id,
                         joueur_entrant_id=joueur_entrant_id, description=commentaire)
    db.session.add(ev)
    db.session.commit()
    return jsonify({"ok": True, "commentaire": commentaire})


@match_bp.route("/match/<int:match_id>/tactique", methods=["POST"])
def ajuster_tactique(match_id):
    """Ajustement tactique en cours de match (mentalité, style,
    ligne défensive, pressing) — typiquement utilisé à la mi-temps."""
    data = request.get_json()
    composition_id = data["composition_id"]
    composition = Composition.query.get_or_404(composition_id)

    for champ in ("consigne_mentalite", "consigne_style", "ligne_defensive",
                  "intensite_pressing", "formation"):
        if champ in data:
            setattr(composition, champ, data[champ])

    db.session.commit()
    return jsonify({"ok": True, "message": "Consignes mises à jour"})


@match_bp.route("/match/<int:match_id>/simuler", methods=["POST"])
def simuler_instantanement(match_id):
    match = Match.query.get_or_404(match_id)
    club_dom = Club.query.get(match.club_domicile_id)
    club_ext = Club.query.get(match.club_exterieur_id)
    comp_dom = _assurer_composition(match, club_dom)
    comp_ext = _assurer_composition(match, club_ext)
    stats_dom = _stats_equipe(comp_dom)
    stats_ext = _stats_equipe(comp_ext)

    score_dom, score_ext, evenements, stats_finales = moteur_match.simuler_match_complet(
        stats_dom, stats_ext, club_dom.nom if club_dom else "Domicile",
        club_ext.nom if club_ext else "Extérieur")

    for e in evenements:
        if e["type"] == "but":
            _incrementer_but(e.get("joueur_id"), match.saison_id, match.division_id)

    match.score_domicile = score_dom
    match.score_exterieur = score_ext
    match.minute_courante = 90
    match.statut = "simule"
    match.tirs_domicile = stats_finales["tirs_dom"]
    match.tirs_cadres_domicile = stats_finales["cadres_dom"]
    match.xg_domicile = stats_finales["xg_dom"]
    match.possession_domicile = stats_finales["possession_dom"]
    match.tirs_exterieur = stats_finales["tirs_ext"]
    match.tirs_cadres_exterieur = stats_finales["cadres_ext"]
    match.xg_exterieur = stats_finales["xg_ext"]
    match.possession_exterieur = stats_finales["possession_ext"]
    _finaliser_participations(match, comp_dom)
    _finaliser_participations(match, comp_ext)
    db.session.commit()

    return jsonify({"score_domicile": score_dom, "score_exterieur": score_ext,
                     "evenements": [e for e in evenements if e["type"] == "but"],
                     "stats": stats_finales})
