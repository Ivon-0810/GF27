"""
Peuple la base avec les données réelles de départ :
- Les 5 grands championnats européens (D1 uniquement)
- La pyramide camerounaise : MTN Elite One (D1) + MTN Elite Two (D2,
  où la création de club est autorisée, avec montée possible en D1)
- Saisons de 2026-2027 à 2085-2086 (60 saisons), la première étant
  active.

NB : les compositions de championnats européens évoluent chaque
année (montées/descentes). Cette liste correspond à la saison
2026-2027 telle que connue au moment de la création du jeu — à
ajuster/importer si besoin via un futur écran d'administration.
"""
from datetime import date
from app.extensions import db
from app.models.models import (Confederation, Pays, Ligue, Division, Club, Saison)

# ---------------------------------------------------------------------------
# Données réelles des championnats (saison 2026-2027)
# ---------------------------------------------------------------------------

PREMIER_LEAGUE = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton & Hove Albion",
    "Chelsea", "Coventry City", "Crystal Palace", "Everton", "Fulham",
    "Hull City", "Ipswich Town", "Leeds United", "Liverpool", "Manchester City",
    "Manchester United", "Newcastle United", "Nottingham Forest", "Sunderland",
    "Tottenham Hotspur",
]

LA_LIGA = [
    "Real Madrid", "FC Barcelone", "Atlético Madrid", "Athletic Bilbao",
    "Real Sociedad", "Real Betis", "Villarreal", "Valence", "Séville FC",
    "Girona", "Celta Vigo", "Osasuna", "Rayo Vallecano", "Getafe",
    "Alavés", "Mallorca", "Las Palmas", "Espanyol", "Levante", "Elche",
]

SERIE_A = [
    "Inter Milan", "AC Milan", "Juventus", "Naples", "AS Rome", "Atalanta",
    "Lazio Rome", "Fiorentina", "Bologne", "Torino", "Udinese", "Genoa",
    "Cagliari", "Hellas Vérone", "Côme", "Parme", "Lecce", "Sassuolo",
    "Pise", "Crémonèse",
]

BUNDESLIGA = [
    "Bayern Munich", "Bayer Leverkusen", "Borussia Dortmund",
    "RB Leipzig", "Eintracht Francfort", "VfB Stuttgart", "Fribourg",
    "Wolfsburg", "Borussia Mönchengladbach", "Mayence 05", "Union Berlin",
    "Werder Brême", "FC Augsbourg", "TSG Hoffenheim", "FC Heidenheim",
    "FC Cologne", "Hambourg SV", "St. Pauli",
]

LIGUE_1 = [
    "Paris Saint-Germain", "AS Monaco", "Olympique de Marseille",
    "Olympique Lyonnais", "LOSC Lille", "OGC Nice", "RC Lens",
    "Stade Rennais", "RC Strasbourg", "Stade Brestois", "Toulouse FC",
    "FC Nantes", "Montpellier HSC", "AJ Auxerre", "Angers SCO",
    "Le Havre AC", "FC Metz", "Paris FC",
]

# MTN Elite One 2026-2027 (14 clubs)
MTN_ELITE_ONE = [
    ("Colombe Sportive", "Sangmélima"),
    ("Unisport de Bafang", "Bafang"),
    ("Coton Sport", "Garoua"),
    ("Dynamo de Douala", "Douala"),
    ("Canon Sportif de Yaoundé", "Yaoundé"),
    ("Victoria United", "Limbe"),
    ("PWD Bamenda", "Bamenda"),
    ("Panthère Sportive du Ndé", "Bangangté"),
    ("Gazelle FA", "Garoua"),
    ("Aigle Royal de la Menoua", "Dschang"),
    ("Aigle Royal du Moungo", "Nkongsamba"),
    ("Stade Renard", "Melong"),
    ("Union Sportive d'Abong-Mbang", "Abong-Mbang"),
    ("Apejes de Mfou", "Mfou"),
]

# MTN Elite Two 2026-2027 (12 clubs, poule unique) — division où la
# création d'un club par l'utilisateur est autorisée
MTN_ELITE_TWO = [
    ("Tonnerre Kalara Club", "Yaoundé"),
    ("AS Fap", "Yaoundé"),
    ("Sable FC", "Batié"),
    ("Bamboutos de Mbouda", "Mbouda"),
    ("Atlantic Sportive", "Kribi"),
    ("Avion Academy", "Yaoundé"),
    ("Kumba FC", "Kumba"),
    ("Les Astres", "Douala"),
    ("AS Fortuna", "Mfou"),
    ("Fauve Azur Elite", "Douala"),
    ("Bafmeng United", "Bafmeng"),
    ("Union Sportive de Douala", "Douala"),
]


def _creer_pyramide_europeenne(nom_pays, code_iso, nom_ligue, clubs, nom_division):
    pays = Pays(nom=nom_pays, code_iso=code_iso)
    db.session.add(pays)
    db.session.flush()

    ligue = Ligue(nom=nom_ligue, pays_id=pays.id)
    db.session.add(ligue)
    db.session.flush()

    division = Division(ligue_id=ligue.id, nom=nom_division, niveau=1,
                         nb_clubs=len(clubs), nb_montants=0,
                         nb_relegues=3, autorise_creation_club=False)
    db.session.add(division)
    db.session.flush()

    for nom_club in clubs:
        db.session.add(Club(nom=nom_club, division_id=division.id,
                             budget=50_000_000.0, reputation=70))


def _creer_pyramide_camerounaise():
    pays = Pays(nom="Cameroun", code_iso="CMR")
    db.session.add(pays)
    db.session.flush()

    ligue = Ligue(nom="Football Camerounais", pays_id=pays.id)
    db.session.add(ligue)
    db.session.flush()

    d1 = Division(ligue_id=ligue.id, nom="MTN Elite One", niveau=1,
                   nb_clubs=len(MTN_ELITE_ONE), nb_montants=2,
                   nb_relegues=2, autorise_creation_club=False)
    d2 = Division(ligue_id=ligue.id, nom="MTN Elite Two", niveau=2,
                   nb_clubs=len(MTN_ELITE_TWO) + 1, nb_montants=2,
                   nb_relegues=0, autorise_creation_club=True)
    db.session.add_all([d1, d2])
    db.session.flush()

    for nom_club, ville in MTN_ELITE_ONE:
        db.session.add(Club(nom=nom_club, ville=ville, division_id=d1.id,
                             budget=800_000.0, reputation=55))
    for nom_club, ville in MTN_ELITE_TWO:
        db.session.add(Club(nom=nom_club, ville=ville, division_id=d2.id,
                             budget=150_000.0, reputation=35))


def peupler_base():
    if Ligue.query.first():
        return  # déjà peuplée

    conf_uefa = Confederation(nom="UEFA")
    conf_caf = Confederation(nom="CAF")
    db.session.add_all([conf_uefa, conf_caf])
    db.session.flush()

    _creer_pyramide_europeenne("Angleterre", "ENG", "Premier League",
                                PREMIER_LEAGUE, "Premier League")
    _creer_pyramide_europeenne("Espagne", "ESP", "LaLiga", LA_LIGA, "LaLiga")
    _creer_pyramide_europeenne("Italie", "ITA", "Serie A", SERIE_A, "Serie A")
    _creer_pyramide_europeenne("Allemagne", "GER", "Bundesliga", BUNDESLIGA,
                                "Bundesliga")
    _creer_pyramide_europeenne("France", "FRA", "Ligue 1", LIGUE_1, "Ligue 1")
    _creer_pyramide_camerounaise()

    # 60 saisons : 2026-2027 à 2085-2086
    for i, annee in enumerate(range(2026, 2086)):
        db.session.add(Saison(annee_debut=annee, annee_fin=annee + 1,
                               est_courante=(i == 0)))

    db.session.commit()
    print("Base peuplée avec succès : 6 pyramides nationales, "
          f"{len(PREMIER_LEAGUE) + len(LA_LIGA) + len(SERIE_A) + len(BUNDESLIGA) + len(LIGUE_1) + len(MTN_ELITE_ONE) + len(MTN_ELITE_TWO)} clubs, 60 saisons.")
