"""
Modèles de données du jeu de gestion de club.
Couvre : ligues/divisions, clubs, joueurs, saisons, calendrier,
transferts, matchs (avec remplacements), et compositions.
"""
from datetime import datetime
from app.extensions import db


# ---------------------------------------------------------------------------
# LIGUES & DIVISIONS
# ---------------------------------------------------------------------------

class Confederation(db.Model):
    __tablename__ = "confederations"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False)  # UEFA, CAF...
    pays = db.relationship("Pays", backref="confederation", lazy=True)


class Pays(db.Model):
    __tablename__ = "pays"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False)
    code_iso = db.Column(db.String(3))
    confederation_id = db.Column(db.Integer, db.ForeignKey("confederations.id"))
    ligues = db.relationship("Ligue", backref="pays", lazy=True)


class Ligue(db.Model):
    """Une ligue = une pyramide nationale (ex: 'France'). Contient
    plusieurs Division (D1, D2...)."""
    __tablename__ = "ligues"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)  # ex: "Championnat de France"
    pays_id = db.Column(db.Integer, db.ForeignKey("pays.id"))
    divisions = db.relationship("Division", backref="ligue", lazy=True,
                                 order_by="Division.niveau")


class Division(db.Model):
    """Un niveau de la pyramide (D1, D2...) avec ses règles de
    montée/descente."""
    __tablename__ = "divisions"
    id = db.Column(db.Integer, primary_key=True)
    ligue_id = db.Column(db.Integer, db.ForeignKey("ligues.id"), nullable=False)
    nom = db.Column(db.String(120), nullable=False)  # ex: "Ligue 1", "MTN Elite One"
    niveau = db.Column(db.Integer, nullable=False)  # 1 = D1, 2 = D2...
    nb_clubs = db.Column(db.Integer, default=18)
    nb_montants = db.Column(db.Integer, default=0)   # places de montée vers niveau-1
    nb_relegues = db.Column(db.Integer, default=0)   # places de descente vers niveau+1
    autorise_creation_club = db.Column(db.Boolean, default=False)
    clubs = db.relationship("Club", backref="division", lazy=True)


# ---------------------------------------------------------------------------
# CLUBS
# ---------------------------------------------------------------------------

class Club(db.Model):
    __tablename__ = "clubs"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    ville = db.Column(db.String(120))
    division_id = db.Column(db.Integer, db.ForeignKey("divisions.id"), nullable=False)
    est_club_joueur = db.Column(db.Boolean, default=False)  # club créé/contrôlé par l'utilisateur
    budget = db.Column(db.Float, default=1_000_000.0)
    reputation = db.Column(db.Integer, default=50)  # 1-100, influe sur négociations
    couleur_1 = db.Column(db.String(7), default="#1a1a2e")
    couleur_2 = db.Column(db.String(7), default="#ffffff")
    formation_favorite = db.Column(db.String(10), default="4-4-2")
    consigne_mentalite_defaut = db.Column(db.String(20), default="equilibre")
    consigne_style_defaut = db.Column(db.String(20), default="possession")
    ligne_defensive_defaut = db.Column(db.Integer, default=50)
    pressing_defaut = db.Column(db.Integer, default=50)

    joueurs = db.relationship("Joueur", backref="club", lazy=True,
                               foreign_keys="Joueur.club_id")
    entraineurs = db.relationship("Entraineur", backref="club", lazy=True,
                                   foreign_keys="Entraineur.club_id")

    def effectif_actif(self):
        return [j for j in self.joueurs if j.statut == "actif"]

    def entraineur_actuel(self):
        return next((e for e in self.entraineurs if e.statut == "actif"), None)


# ---------------------------------------------------------------------------
# ENTRAÎNEURS
# ---------------------------------------------------------------------------

class Entraineur(db.Model):
    __tablename__ = "entraineurs"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    nationalite = db.Column(db.String(80))
    date_naissance = db.Column(db.Date)

    tactique_preferee = db.Column(db.String(10), default="4-4-2")
    niveau = db.Column(db.Integer, default=50)  # 0-99, influe les résultats et le vote The Best
    reputation = db.Column(db.Integer, default=50)

    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"))
    statut = db.Column(db.String(20), default="actif")  # actif / sans_club / licencie

    def age(self, date_reference=None):
        from datetime import datetime as _dt
        ref = date_reference or _dt.utcnow().date()
        if not self.date_naissance:
            return None
        return ref.year - self.date_naissance.year - (
            (ref.month, ref.day) < (self.date_naissance.month, self.date_naissance.day)
        )


# ---------------------------------------------------------------------------
# JOUEURS
# ---------------------------------------------------------------------------

POSTES = [
    "GB",                                   # Gardien
    "DC", "DD", "DG",                       # Défenseurs
    "MDC", "MC", "MD", "MG", "MOC",         # Milieux
    "AD", "AG", "BU",                       # Attaquants
]


class Joueur(db.Model):
    __tablename__ = "joueurs"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    date_naissance = db.Column(db.Date)
    nationalite = db.Column(db.String(80))
    poste_principal = db.Column(db.String(5))
    postes_secondaires = db.Column(db.String(40))  # ex: "MC,MD"

    # Attributs détaillés façon FM (0-99)
    attaque = db.Column(db.Integer, default=50)     # puissance offensive globale
    finition = db.Column(db.Integer, default=50)    # précision devant le but
    defense = db.Column(db.Integer, default=50)
    tacle = db.Column(db.Integer, default=50)
    passe = db.Column(db.Integer, default=50)
    vision = db.Column(db.Integer, default=50)       # qualité de la dernière passe
    dribble = db.Column(db.Integer, default=50)
    physique = db.Column(db.Integer, default=50)
    vitesse = db.Column(db.Integer, default=50)
    technique = db.Column(db.Integer, default=50)
    mental = db.Column(db.Integer, default=50)

    # CA/PA façon FM : niveau_actuel = CA (visible), potentiel = PA (caché,
    # révélé progressivement par le scouting — voir RapportScouting)
    niveau_actuel = db.Column(db.Integer, default=50)   # CA
    potentiel = db.Column(db.Integer, default=50)        # PA, plafond de progression

    forme = db.Column(db.Integer, default=70)       # condition physique, 0-100%
    moral = db.Column(db.Integer, default=70)        # 0-100
    fatigue = db.Column(db.Integer, default=0)       # fatigue cumulée, 0-100
    blessure_jours_restants = db.Column(db.Integer, default=0)

    valeur_marchande = db.Column(db.Float, default=100_000.0)
    salaire_mensuel = db.Column(db.Float, default=1000.0)
    fin_contrat = db.Column(db.Date)

    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"))
    statut = db.Column(db.String(20), default="actif")  # actif / prêté / libre

    def age(self, date_reference=None):
        ref = date_reference or datetime.utcnow().date()
        if not self.date_naissance:
            return None
        return ref.year - self.date_naissance.year - (
            (ref.month, ref.day) < (self.date_naissance.month, self.date_naissance.day)
        )

    def overall(self):
        """Note globale (CA) : utilise niveau_actuel si déjà calculé,
        sinon une moyenne pondérée des attributs bruts."""
        if self.niveau_actuel:
            return self.niveau_actuel
        base = (self.attaque + self.finition + self.defense + self.tacle +
                self.passe + self.vision + self.dribble + self.physique +
                self.vitesse + self.technique + self.mental) / 11
        return round(base)


# ---------------------------------------------------------------------------
# SAISONS & CALENDRIER
# ---------------------------------------------------------------------------

class Saison(db.Model):
    __tablename__ = "saisons"
    id = db.Column(db.Integer, primary_key=True)
    annee_debut = db.Column(db.Integer, nullable=False)  # 2026 -> saison 2026-2027
    annee_fin = db.Column(db.Integer, nullable=False)
    est_courante = db.Column(db.Boolean, default=False)


class Match(db.Model):
    __tablename__ = "matchs"
    id = db.Column(db.Integer, primary_key=True)
    saison_id = db.Column(db.Integer, db.ForeignKey("saisons.id"))
    division_id = db.Column(db.Integer, db.ForeignKey("divisions.id"))
    journee = db.Column(db.Integer)
    date_match = db.Column(db.DateTime)

    club_domicile_id = db.Column(db.Integer, db.ForeignKey("clubs.id"))
    club_exterieur_id = db.Column(db.Integer, db.ForeignKey("clubs.id"))
    club_domicile = db.relationship("Club", foreign_keys=[club_domicile_id])
    club_exterieur = db.relationship("Club", foreign_keys=[club_exterieur_id])

    score_domicile = db.Column(db.Integer)
    score_exterieur = db.Column(db.Integer)
    statut = db.Column(db.String(20), default="a_jouer")
    # a_jouer / en_cours (mi-temps incluse) / termine / simule

    minute_courante = db.Column(db.Integer, default=0)

    # Statistiques live (mises à jour minute par minute)
    tirs_domicile = db.Column(db.Integer, default=0)
    tirs_cadres_domicile = db.Column(db.Integer, default=0)
    xg_domicile = db.Column(db.Float, default=0.0)
    possession_domicile = db.Column(db.Integer, default=50)  # %

    tirs_exterieur = db.Column(db.Integer, default=0)
    tirs_cadres_exterieur = db.Column(db.Integer, default=0)
    xg_exterieur = db.Column(db.Float, default=0.0)
    possession_exterieur = db.Column(db.Integer, default=50)

    evenements = db.relationship("EvenementMatch", backref="match", lazy=True,
                                  order_by="EvenementMatch.minute")


class EvenementMatch(db.Model):
    """Un évènement du direct : but, carton, changement, mi-temps..."""
    __tablename__ = "evenements_match"
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matchs.id"), nullable=False)
    minute = db.Column(db.Integer, nullable=False)
    type_evenement = db.Column(db.String(30))  # but, carton_jaune, carton_rouge,
    # changement, blessure, mi_temps, fin_match
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"))
    joueur_id = db.Column(db.Integer, db.ForeignKey("joueurs.id"))
    joueur_entrant_id = db.Column(db.Integer, db.ForeignKey("joueurs.id"))
    description = db.Column(db.String(255))


class Composition(db.Model):
    """La feuille de match d'un club pour un match donné : onze de
    départ, remplaçants, et tactique."""
    __tablename__ = "compositions"
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matchs.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    formation = db.Column(db.String(10), default="4-4-2")
    consigne_mentalite = db.Column(db.String(20), default="equilibre")
    # offensif / equilibre / defensif
    consigne_style = db.Column(db.String(20), default="possession")
    # gegenpressing / possession / contre_attaque / jeu_direct
    ligne_defensive = db.Column(db.Integer, default=50)  # 0=très basse, 100=très haute
    intensite_pressing = db.Column(db.Integer, default=50)  # 0-100

    titulaires = db.relationship("CompositionJoueur", backref="composition",
                                  lazy=True)


class CompositionJoueur(db.Model):
    __tablename__ = "composition_joueurs"
    id = db.Column(db.Integer, primary_key=True)
    composition_id = db.Column(db.Integer, db.ForeignKey("compositions.id"))
    joueur_id = db.Column(db.Integer, db.ForeignKey("joueurs.id"))
    poste_occupe = db.Column(db.String(5))
    est_titulaire = db.Column(db.Boolean, default=True)
    sorti_minute = db.Column(db.Integer, nullable=True)


# ---------------------------------------------------------------------------
# TRANSFERTS
# ---------------------------------------------------------------------------

class Transfert(db.Model):
    __tablename__ = "transferts"
    id = db.Column(db.Integer, primary_key=True)
    joueur_id = db.Column(db.Integer, db.ForeignKey("joueurs.id"), nullable=False)
    club_vendeur_id = db.Column(db.Integer, db.ForeignKey("clubs.id"))
    club_acheteur_id = db.Column(db.Integer, db.ForeignKey("clubs.id"))
    joueur = db.relationship("Joueur")
    club_vendeur = db.relationship("Club", foreign_keys=[club_vendeur_id])
    club_acheteur = db.relationship("Club", foreign_keys=[club_acheteur_id])
    montant = db.Column(db.Float, default=0.0)
    type_operation = db.Column(db.String(20), default="transfert")
    # transfert / pret / fin_contrat / clause_rachat
    date_operation = db.Column(db.DateTime, default=datetime.utcnow)
    saison_id = db.Column(db.Integer, db.ForeignKey("saisons.id"))
    statut = db.Column(db.String(20), default="en_negociation")
    # en_negociation / acceptee / refusee / finalisee


# ---------------------------------------------------------------------------
# STATISTIQUES DE SAISON (nécessaires pour calculer les distinctions
# et alimenter le scouting sur des bases factuelles)
# ---------------------------------------------------------------------------

class StatistiqueSaisonJoueur(db.Model):
    __tablename__ = "statistiques_saison_joueur"
    id = db.Column(db.Integer, primary_key=True)
    joueur_id = db.Column(db.Integer, db.ForeignKey("joueurs.id"), nullable=False)
    saison_id = db.Column(db.Integer, db.ForeignKey("saisons.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"))
    division_id = db.Column(db.Integer, db.ForeignKey("divisions.id"))

    matchs_joues = db.Column(db.Integer, default=0)
    buts = db.Column(db.Integer, default=0)
    passes_decisives = db.Column(db.Integer, default=0)
    cartons_jaunes = db.Column(db.Integer, default=0)
    cartons_rouges = db.Column(db.Integer, default=0)
    clean_sheets = db.Column(db.Integer, default=0)  # gardiens/défenseurs
    note_moyenne = db.Column(db.Float, default=6.0)  # note façon FM, 0-10


class StatistiqueSaisonEntraineur(db.Model):
    __tablename__ = "statistiques_saison_entraineur"
    id = db.Column(db.Integer, primary_key=True)
    entraineur_id = db.Column(db.Integer, db.ForeignKey("entraineurs.id"), nullable=False)
    saison_id = db.Column(db.Integer, db.ForeignKey("saisons.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"))

    victoires = db.Column(db.Integer, default=0)
    nuls = db.Column(db.Integer, default=0)
    defaites = db.Column(db.Integer, default=0)
    classement_final = db.Column(db.Integer, nullable=True)
    titre_remporte = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------------------------
# PALMARÈS & DISTINCTIONS INDIVIDUELLES
# ---------------------------------------------------------------------------

class TypeDistinction(db.Model):
    """Le catalogue des prix existants (inspirés du vrai football)."""
    __tablename__ = "types_distinction"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    nom = db.Column(db.String(120), nullable=False)
    portee = db.Column(db.String(20), nullable=False)
    # mondial / continental / national (=championnat)
    categorie = db.Column(db.String(20), nullable=False)
    # joueur / gardien / jeune / entraineur / buteur
    division_id = db.Column(db.Integer, db.ForeignKey("divisions.id"), nullable=True)
    # non-null uniquement pour les prix propres à un championnat


class DistinctionSaison(db.Model):
    """Un prix effectivement remis, saison après saison — l'historique
    du palmarès."""
    __tablename__ = "distinctions_saison"
    id = db.Column(db.Integer, primary_key=True)
    type_distinction_id = db.Column(db.Integer, db.ForeignKey("types_distinction.id"),
                                     nullable=False)
    saison_id = db.Column(db.Integer, db.ForeignKey("saisons.id"), nullable=False)
    rang = db.Column(db.Integer, default=1)  # 1er, 2e, 3e (podium façon Ballon d'Or)

    joueur_id = db.Column(db.Integer, db.ForeignKey("joueurs.id"), nullable=True)
    entraineur_id = db.Column(db.Integer, db.ForeignKey("entraineurs.id"), nullable=True)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=True)

    valeur_cle = db.Column(db.String(80), nullable=True)
    # ex: "27 buts" pour un Soulier d'Or, "18V 6N 2D" pour un coach

    type_distinction = db.relationship("TypeDistinction")
    joueur = db.relationship("Joueur")
    entraineur = db.relationship("Entraineur")
    club = db.relationship("Club")


# ---------------------------------------------------------------------------
# SCOUTING
# ---------------------------------------------------------------------------

class Recruteur(db.Model):
    """Un recruteur employé par le club-joueur : plus sa note est
    haute, plus l'estimation du potentiel caché (PA) qu'il ramène est
    fiable."""
    __tablename__ = "recruteurs"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    note_evaluation = db.Column(db.Integer, default=50)  # 0-99, fiabilité du rapport
    zone_couverte = db.Column(db.String(120), default="Monde")
    salaire_mensuel = db.Column(db.Float, default=800.0)


class RapportScouting(db.Model):
    __tablename__ = "rapports_scouting"
    id = db.Column(db.Integer, primary_key=True)
    recruteur_id = db.Column(db.Integer, db.ForeignKey("recruteurs.id"), nullable=False)
    joueur_id = db.Column(db.Integer, db.ForeignKey("joueurs.id"), nullable=False)
    date_rapport = db.Column(db.DateTime, default=datetime.utcnow)

    potentiel_estime = db.Column(db.Integer)  # estimation du PA, bruitée selon note_evaluation
    marge_erreur = db.Column(db.Integer, default=10)
    recommandation = db.Column(db.String(255))
    # ex: "Pépite à suivre", "Déjà à son plafond", "Bon rapport qualité/prix"


# ---------------------------------------------------------------------------
# COMPÉTITIONS CONTINENTALES (Ligue des Champions...)
# ---------------------------------------------------------------------------

class Competition(db.Model):
    """Compétition transversale aux ligues nationales (coupes
    continentales : Ligue des Champions, Ligue Africaine des
    Champions...)."""
    __tablename__ = "competitions"
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    confederation_id = db.Column(db.Integer, db.ForeignKey("confederations.id"))
    nb_qualifies_par_championnat = db.Column(db.Integer, default=4)


class ParticipationCompetition(db.Model):
    """Qualification d'un club à une compétition pour une saison
    donnée (calculée à partir de son classement en championnat)."""
    __tablename__ = "participations_competition"
    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    saison_id = db.Column(db.Integer, db.ForeignKey("saisons.id"), nullable=False)
    phase_atteinte = db.Column(db.String(40), default="phase_de_groupes")
