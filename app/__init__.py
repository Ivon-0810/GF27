import os
import sys
from flask import Flask
from app.extensions import db


def _chemin_ressources():
    """Renvoie le dossier où trouver templates/ et static/, que
    l'appli tourne en Python normal ou packagée en .exe (PyInstaller
    extrait ses données dans sys._MEIPASS à l'exécution)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.abspath(os.path.dirname(__file__))


def _chemin_donnees_ecrivables():
    """Dossier où écrire la base SQLite : à côté de l'exécutable en
    .exe (jamais dans le dossier temporaire de PyInstaller, qui est
    effacé à la fermeture), à côté du code en développement."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def create_app():
    base_dir = _chemin_ressources()
    app = Flask(__name__,
                template_folder=os.path.join(base_dir, "templates"),
                static_folder=os.path.join(base_dir, "static"))

    dossier_donnees = os.path.join(_chemin_donnees_ecrivables(), "instance")
    os.makedirs(dossier_donnees, exist_ok=True)
    db_path = os.path.join(dossier_donnees, "gestion_club.db")

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "dev-secret-key-a-changer"

    db.init_app(app)

    from app.models import models  # noqa: F401  (enregistre les modèles)

    from app.routes.main import main_bp
    from app.routes.effectif import effectif_bp
    from app.routes.mercato import mercato_bp
    from app.routes.match_routes import match_bp
    from app.routes.palmares import palmares_bp
    from app.routes.recherche import recherche_bp
    from app.routes.saison import saison_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(effectif_bp)
    app.register_blueprint(mercato_bp)
    app.register_blueprint(match_bp)
    app.register_blueprint(palmares_bp)
    app.register_blueprint(recherche_bp)
    app.register_blueprint(saison_bp)

    return app
