import sys
import threading
import webbrowser

from app import create_app
from app.extensions import db
from app.data.seed_data import peupler_base
from app.data.generateur_joueurs import generer_effectifs
from app.data.generateur_entraineurs import generer_entraineurs
from app.services.calendrier_saison import generer_calendrier_saison_complete
from app.models.models import Saison

app = create_app()

with app.app_context():
    db.create_all()
    peupler_base()
    generer_effectifs()
    generer_entraineurs()
    saison_courante = Saison.query.filter_by(est_courante=True).first()
    if saison_courante:
        generer_calendrier_saison_complete(saison_courante)


def _ouvrir_navigateur():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    # En .exe (PyInstaller), pas de rechargeur automatique : on ouvre
    # directement le navigateur sur l'appli.
    est_fige = getattr(sys, "frozen", False)
    threading.Timer(1.2, _ouvrir_navigateur).start()
    app.run(debug=not est_fige, port=5000, use_reloader=False)
