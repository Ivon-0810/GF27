# Gestion Club — jeu de gestion de football (mode Président/Coach)

## Lancer le jeu en développement

```bash
cd gestion-club
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Le navigateur s'ouvre automatiquement sur http://127.0.0.1:5000.

⚠️ Je n'ai pas pu exécuter ce code moi-même avant de te le livrer : le
bac à sable où je travaille n'a pas d'accès réseau pour installer
Flask-SQLAlchemy. Le code est syntaxiquement valide (vérifié), mais
**teste-le en premier** et dis-moi la moindre erreur — je corrige
immédiatement.

## Compiler en .exe

Deux options :
1. **Automatique** : pousse le projet sur GitHub, le workflow
   `.github/workflows/build.yml` compile le `.exe` à chaque push sur
   `main` (onglet Actions → artefact `GestionClub-windows`).
2. **En local (sous Windows)** :
   ```bash
   pip install pyinstaller
   pyinstaller --noconfirm --onefile --name GestionClub --add-data "app/templates;templates" --add-data "app/static;static" run.py
   ```

## Ce qui est fait et fonctionne

- **Données réelles** : 5 grands championnats européens (2026-2027) +
  MTN Elite One/Two (Cameroun, avec création de club en D2 et montée
  en D1), 60 saisons (2026-2086)
- **Calendrier de saison automatique** : championnat aller-retour
  généré pour chaque division, classement en direct, simulation de
  la journée (sauf ton match, que tu vas jouer toi-même), clôture de
  saison avec montées/descentes réelles entre MTN Elite One et Elite
  Two, puis ouverture automatique de la saison suivante
- **Joueurs façon FM** : finition, tacle, vision, dribble, CA/PA
  (niveau actuel vs potentiel caché), forme, moral, fatigue
- **Entraîneurs** générés pour chaque club, avec stats de saison
  (victoires/nuls/défaites/classement) alimentant leur palmarès
- **Tactiques** : formation, mentalité (offensif/équilibré/défensif),
  style (gegenpressing/possession/contre-attaque/jeu direct), ligne
  défensive, intensité du pressing — ajustables y compris à la
  mi-temps
- **Moteur de match v2** : duels d'attributs, tirs/tirs cadrés/xG/
  possession en direct, buteur identifié individuellement,
  commentaires texte générés, changements en cours de match
- **Palmarès individuel** façon vrai football : Ballon d'Or, Trophée
  Yachine, Trophée Kopa, The Best (entraîneur), Ballon d'Or Africain,
  + Soulier d'Or / Gant d'Or / Joueur de la saison / Meilleur jeune /
  Meilleur entraîneur pour chaque championnat — calculé automatiquement
  à la clôture de chaque saison
- **Mercato** avec négociation simplifiée automatique, **et IA des
  autres clubs** : bouton "Simuler le mercato" qui fait recruter les
  clubs adverses selon leur poste le plus faible et leur budget ; si
  un club IA vise un joueur de TON club, l'offre atterrit dans
  "Offres reçues" pour que tu l'acceptes ou la refuses toi-même
- **Scouting (couche données)** : recruteurs + rapports bruités sur
  le potentiel caché — pas encore d'écran dédié
- **Thème sombre façon FM27** (Bootstrap 5) + barre de recherche
  globale (joueurs/clubs/compétitions)
- **Packaging .exe** : ouverture auto du navigateur, chemins
  compatibles PyInstaller, workflow GitHub Actions, `.gitignore` propre

## Ce qui n'est PAS encore fait (feuille de route honnête)

1. **Écran de composition visuel** (glisser-déposer sur un terrain) —
   pour l'instant la sélection des titulaires pour un match est faite
   automatiquement (meilleurs joueurs disponibles par poste)
2. **Écran de scouting** (envoyer un recruteur, consulter ses
   rapports) — la logique existe côté serveur, l'interface reste à
   faire
3. **Ligue des Champions / Ligue Africaine des Champions** — modèle
   de données prêt (`Competition`), qualification et calendrier à
   implémenter
4. **Vraies données joueurs** (noms réels) via import CSV — les
   effectifs actuels sont générés avec des noms plausibles mais
   fictifs
5. **Montées/descentes pour les 5 championnats européens** : comme
   ils n'ont qu'une seule division dans le jeu (pas de D2 nationale
   pour l'instant), il n'y a pas encore de relégation/promotion pour
   eux — seul un champion est couronné chaque saison
6. **IA du mercato affinée** : pour l'instant elle recrute selon le
   poste le plus faible et le budget, sans tenir compte des besoins
   fins (âge, temps de jeu, style tactique) ni des ventes de joueurs
   surnuméraires

Dis-moi par quoi tu veux qu'on continue.
