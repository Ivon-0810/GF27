"""
Moteur de match v2 — simulation minute par minute basée sur des duels
d'attributs, modulée par la tactique choisie (mentalité, style de
jeu, ligne défensive, intensité du pressing).

Ce module reste un moteur STATISTIQUE (pas de moteur 3D/2D avec
déplacement de joueurs) : il calcule des probabilités d'évènements
et les distribue dans le temps, façon Football Manager.
"""
import random

MODIFICATEURS_STYLE = {
    # (bonus_attaque, bonus_defense, bonus_possession, risque_erreur)
    "gegenpressing":   {"attaque": 1.08, "defense": 0.95, "possession": 3,  "risque": 1.15},
    "possession":      {"attaque": 0.98, "defense": 1.05, "possession": 8,  "risque": 0.90},
    "contre_attaque":  {"attaque": 1.05, "defense": 1.00, "possession": -6, "risque": 0.95},
    "jeu_direct":      {"attaque": 1.02, "defense": 0.98, "possession": -3, "risque": 1.05},
}

MODIFICATEURS_MENTALITE = {
    "offensif":  {"attaque": 1.12, "defense": 0.88},
    "equilibre": {"attaque": 1.00, "defense": 1.00},
    "defensif":  {"attaque": 0.85, "defense": 1.15},
}


def _tactique_ou_defaut(composition):
    if composition is None:
        return {"style": "possession", "mentalite": "equilibre",
                "ligne_defensive": 50, "pressing": 50}
    return {
        "style": getattr(composition, "consigne_style", "possession") or "possession",
        "mentalite": getattr(composition, "consigne_mentalite", "equilibre") or "equilibre",
        "ligne_defensive": getattr(composition, "ligne_defensive", 50) or 50,
        "pressing": getattr(composition, "intensite_pressing", 50) or 50,
    }


def force_offensive(joueurs_titulaires, tactique=None):
    if not joueurs_titulaires:
        return 40
    tactique = tactique or {"style": "possession", "mentalite": "equilibre"}
    mod_style = MODIFICATEURS_STYLE[tactique["style"]]["attaque"]
    mod_ment = MODIFICATEURS_MENTALITE[tactique["mentalite"]]["attaque"]

    valeurs = [
        (j.attaque * 0.30 + j.finition * 0.25 + j.dribble * 0.20 +
         j.vitesse * 0.15 + j.vision * 0.10)
        * (j.forme / 100) * (1 - j.fatigue / 200) * (j.moral / 100 * 0.3 + 0.7)
        for j in joueurs_titulaires
    ]
    return (sum(valeurs) / len(valeurs)) * mod_style * mod_ment


def force_defensive(joueurs_titulaires, tactique=None):
    if not joueurs_titulaires:
        return 40
    tactique = tactique or {"style": "possession", "mentalite": "equilibre"}
    mod_style = MODIFICATEURS_STYLE[tactique["style"]]["defense"]
    mod_ment = MODIFICATEURS_MENTALITE[tactique["mentalite"]]["defense"]

    valeurs = [
        (j.defense * 0.40 + j.tacle * 0.30 + j.physique * 0.20 + j.mental * 0.10)
        * (j.forme / 100) * (1 - j.fatigue / 200)
        for j in joueurs_titulaires
    ]
    return (sum(valeurs) / len(valeurs)) * mod_style * mod_ment


def stats_equipe_depuis_composition(joueurs_titulaires, composition):
    tactique = _tactique_ou_defaut(composition)
    return {
        "attaque": force_offensive(joueurs_titulaires, tactique),
        "defense": force_defensive(joueurs_titulaires, tactique),
        "tactique": tactique,
        "joueurs": joueurs_titulaires,
    }


def _possession_du_moment(stats_dom, stats_ext):
    base = 50
    base += (stats_dom["attaque"] - stats_ext["attaque"]) * 0.3
    base += MODIFICATEURS_STYLE[stats_dom["tactique"]["style"]]["possession"]
    base -= MODIFICATEURS_STYLE[stats_ext["tactique"]["style"]]["possession"]
    return max(25, min(75, round(base)))


def _choisir_buteur(joueurs_titulaires):
    if not joueurs_titulaires:
        return None
    ponderations = []
    for j in joueurs_titulaires:
        poids = (j.finition * 0.6 + j.attaque * 0.4)
        if j.poste_principal in ("BU", "AD", "AG"):
            poids *= 2.2
        elif j.poste_principal in ("MOC", "MC", "MD", "MG"):
            poids *= 1.1
        elif j.poste_principal == "GB":
            poids *= 0.02
        ponderations.append(max(poids, 1))
    return random.choices(joueurs_titulaires, weights=ponderations, k=1)[0]


def _commentaire(type_evt, minute, nom_equipe, nom_joueur=None, nom_entrant=None):
    if type_evt == "but":
        return f"⚽ BUT ! {minute}' — {nom_joueur} fait trembler les filets pour {nom_equipe} !"
    if type_evt == "occasion":
        return f"{minute}' — Belle occasion pour {nom_equipe}, ça sent le danger."
    if type_evt == "carton_jaune":
        return f"🟨 {minute}' — Carton jaune pour {nom_joueur} ({nom_equipe})."
    if type_evt == "changement":
        return f"🔄 {minute}' — Changement chez {nom_equipe} : {nom_entrant} remplace {nom_joueur}."
    if type_evt == "mi_temps":
        return "⏸️ Fin de la première période."
    if type_evt == "fin_match":
        return "🏁 Coup de sifflet final !"
    return f"{minute}' — {nom_equipe}"


def simuler_minute(minute, stats_dom, stats_ext, nom_dom="Domicile", nom_ext="Extérieur"):
    evenements = []

    def _p_but(att, deff):
        ratio = att / max(deff, 1)
        return max(0.0, min(0.013 * ratio, 0.08))

    def _p_tir(att, deff):
        ratio = att / max(deff, 1)
        return max(0.0, min(0.05 * ratio, 0.22))

    for cote, (att_stats, def_stats, nom_equipe) in (
        ("domicile", (stats_dom, stats_ext, nom_dom)),
        ("exterieur", (stats_ext, stats_dom, nom_ext)),
    ):
        if random.random() < _p_tir(att_stats["attaque"], def_stats["defense"]):
            cadre = random.random() < 0.42
            xg = round(random.uniform(0.03, 0.35), 2)
            but_marque = cadre and random.random() < _p_but(att_stats["attaque"],
                                                              def_stats["defense"]) * 6

            evt = {"minute": minute, "type": "tir", "equipe": cote,
                   "cadre": cadre, "xg": xg}

            if but_marque:
                buteur = _choisir_buteur(att_stats["joueurs"])
                evt["type"] = "but"
                evt["joueur_id"] = buteur.id if buteur else None
                evt["joueur_nom"] = buteur.nom if buteur else "?"
                evt["commentaire"] = _commentaire("but", minute, nom_equipe,
                                                   nom_joueur=evt["joueur_nom"])
            elif cadre:
                evt["commentaire"] = _commentaire("occasion", minute, nom_equipe)

            evenements.append(evt)

        if random.random() < 0.003:
            fautif = random.choice(att_stats["joueurs"]) if att_stats["joueurs"] else None
            evenements.append({
                "minute": minute, "type": "carton_jaune", "equipe": cote,
                "joueur_id": fautif.id if fautif else None,
                "joueur_nom": fautif.nom if fautif else "?",
                "commentaire": _commentaire("carton_jaune", minute, nom_equipe,
                                             nom_joueur=fautif.nom if fautif else "?"),
            })

    return evenements


def simuler_match_complet(stats_dom, stats_ext, nom_dom="Domicile", nom_ext="Extérieur"):
    score_dom, score_ext = 0, 0
    tous_evenements = []
    stats_finales = {"tirs_dom": 0, "cadres_dom": 0, "xg_dom": 0.0,
                      "tirs_ext": 0, "cadres_ext": 0, "xg_ext": 0.0}

    for minute in range(1, 91):
        evts = simuler_minute(minute, stats_dom, stats_ext, nom_dom, nom_ext)
        for e in evts:
            prefixe = "dom" if e["equipe"] == "domicile" else "ext"
            if e["type"] in ("but", "tir"):
                stats_finales[f"tirs_{prefixe}"] += 1
                if e.get("cadre") or e["type"] == "but":
                    stats_finales[f"cadres_{prefixe}"] += 1
                stats_finales[f"xg_{prefixe}"] += e.get("xg", 0.05)
            if e["type"] == "but":
                if e["equipe"] == "domicile":
                    score_dom += 1
                else:
                    score_ext += 1
        tous_evenements.extend(evts)

    possession_dom = _possession_du_moment(stats_dom, stats_ext)
    stats_finales["possession_dom"] = possession_dom
    stats_finales["possession_ext"] = 100 - possession_dom
    stats_finales["xg_dom"] = round(stats_finales["xg_dom"], 2)
    stats_finales["xg_ext"] = round(stats_finales["xg_ext"], 2)

    return score_dom, score_ext, tous_evenements, stats_finales
