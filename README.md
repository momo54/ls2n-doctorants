# Nouveaux doctorants LS2N

Page mise à jour chaque jour : **https://momo54.github.io/ls2n-doctorants/**

Elle liste les thèses en cours au LS2N d'après la page publique
[Amethis – thèses en cours](https://amethis.doctorat.org/amethis-client/doctorant/theses/E),
avec le directeur ou la directrice de thèse et le co-encadrement. Par défaut, la page affiche les
thèses commencées depuis le 1er septembre de l'année universitaire en cours ; on peut changer la date,
chercher un nom ou un sujet, et télécharger le CSV.

## Comment ça marche

- `nouveaux_doctorants_ls2n.py` ouvre la page publique Amethis dans un Chrome headless (Playwright),
  lit les données que la page reçoit et filtre sur le laboratoire.
- Le workflow `.github/workflows/mise-a-jour.yml` lance le script tous les jours à 5h17 UTC et
  publie le résultat sur GitHub Pages. Il peut aussi être lancé à la main depuis l'onglet *Actions*.

## En local

```bash
pip install playwright        # et Google Chrome, ou : python -m playwright install chromium
python3 nouveaux_doctorants_ls2n.py                     # depuis le 1er septembre
python3 nouveaux_doctorants_ls2n.py --depuis 2026-01-01
python3 nouveaux_doctorants_ls2n.py --tous --csv ls2n.csv
python3 nouveaux_doctorants_ls2n.py --labo LS2N --format markdown
python3 nouveaux_doctorants_ls2n.py --html site/index.html --csv site/ls2n.csv
```

Page non officielle ; les données viennent uniquement des thèses non confidentielles affichées
publiquement par Amethis.
