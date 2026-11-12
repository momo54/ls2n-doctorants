#!/usr/bin/env python3
"""Liste les nouveaux doctorants d'un laboratoire (LS2N par défaut) à partir d'Amethis.

Le script ouvre la page publique des thèses en cours
  https://amethis.doctorat.org/amethis-client/doctorant/theses/E
dans un Chrome headless (Playwright) et lit les données que la page reçoit,
puis filtre par laboratoire et par date de début de thèse.

Prérequis :  pip install playwright   (+ Google Chrome installé, ou `playwright install chromium`)

Exemples :
  python3 nouveaux_doctorants_ls2n.py                      # depuis le 1er septembre de l'année universitaire
  python3 nouveaux_doctorants_ls2n.py --depuis 2026-01-01
  python3 nouveaux_doctorants_ls2n.py --tous --csv ls2n.csv
  python3 nouveaux_doctorants_ls2n.py --labo LS2N --format markdown
  python3 nouveaux_doctorants_ls2n.py --html site/index.html --quiet   # page web (toutes les thèses du labo)
"""

import argparse
import csv
import datetime as dt
import html
import json
import os
import sys
import textwrap
import time
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

PAGE_URL = "https://amethis.doctorat.org/amethis-client/doctorant/theses/E"
THESE_URL = PAGE_URL + "/{}"


def debut_annee_universitaire(today=None):
    today = today or dt.date.today()
    year = today.year if today.month >= 9 else today.year - 1
    return dt.date(year, 9, 1)


def charger_theses(timeout_s=120):
    """Ouvre la page publique et récupère la liste des thèses qu'elle charge."""
    captured = {}

    def handle(route):
        resp = route.fetch(timeout=timeout_s * 1000)
        captured["body"] = resp.body()
        route.fulfill(response=resp)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        # La page est une PWA : sans bloquer le service worker, les requêtes
        # ne sont pas interceptables (et peuvent être servies depuis un cache périmé).
        context = browser.new_context(locale="fr-FR", service_workers="block")
        page = context.new_page()
        page.route("**/getAllThesesAnonymous", handle)
        page.goto(PAGE_URL)
        t0 = time.time()
        while "body" not in captured and time.time() - t0 < timeout_s:
            page.wait_for_timeout(500)
        browser.close()

    if "body" not in captured:
        sys.exit("Erreur : la liste des thèses n'a pas été reçue (timeout).")
    data = json.loads(captured["body"])
    if not data.get("success"):
        sys.exit(f"Erreur Amethis : {data.get('message')}")
    return data["data"]


def nom_doctorant(r):
    nom = r.get("indNomUsuLib") or r.get("indNomPatLib") or ""
    return f"{nom} {r.get('indPrnLib1', '')}".strip()


def ligne(r):
    return {
        "debut": r.get("thsDebDat", ""),
        "debut_iso": r.get("thsDebDatIso", ""),
        "doctorant": nom_doctorant(r),
        "directeur": r.get("directeur", ""),
        "co_directeur": r.get("coDirecteur", ""),
        "etablissement": r.get("etbSigle") or r.get("etbLib", ""),
        "ecole_doctorale": r.get("edoNatSigle", ""),
        "specialite": r.get("thsSpecialiteLib", ""),
        "titre": (r.get("thsLanguePrincLib") or "").strip(),
        "financement": r.get("finConditionFinanciereLib", ""),
        "lien": THESE_URL.format(r.get("thsId")),
    }


# --------------------------------------------------------------------------- page HTML

HTML_TEMPLATE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nouveaux doctorants __LABO__</title>
<style>
:root {
  --bg: #f7f7f5; --card: #ffffff; --text: #1d2125; --muted: #5f6770; --border: #e2e4e7;
  --accent: #1b5e8c; --accent-soft: #e7f0f7; --row-hover: #f2f5f8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15181b; --card: #1d2125; --text: #e6e8ea; --muted: #9aa3ab; --border: #30363c;
    --accent: #7db8e3; --accent-soft: #1f3343; --row-hover: #242a30;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
main { max-width: 1200px; margin: 0 auto; padding: 32px 16px 48px; }
h1 { font-size: 1.7rem; margin: 0 0 4px; letter-spacing: -0.01em; }
.sub { color: var(--muted); margin: 0 0 24px; }
.controls { display: flex; flex-wrap: wrap; gap: 12px 20px; align-items: end;
  background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; margin-bottom: 16px; }
.controls label { display: flex; flex-direction: column; gap: 4px; font-size: .8rem; color: var(--muted); }
.controls input { font: inherit; color: var(--text); background: var(--bg); border: 1px solid var(--border);
  border-radius: 6px; padding: 6px 8px; }
.controls input[type=search] { min-width: 260px; }
.presets { display: flex; gap: 6px; flex-wrap: wrap; }
.presets button { font: inherit; font-size: .85rem; color: var(--accent); background: var(--accent-soft);
  border: 0; border-radius: 999px; padding: 6px 12px; cursor: pointer; }
.presets button:hover { filter: brightness(.95); }
.count { margin-left: auto; font-weight: 600; font-size: 1.05rem; }
.table-wrap { background: var(--card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 10px 12px; vertical-align: top; border-bottom: 1px solid var(--border); }
th { font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); background: var(--card); }
tr:last-child td { border-bottom: 0; }
tbody tr:hover { background: var(--row-hover); }
td.date { white-space: nowrap; font-variant-numeric: tabular-nums; }
td.name a { color: var(--accent); font-weight: 600; text-decoration: none; }
td.name a:hover { text-decoration: underline; }
.meta { color: var(--muted); font-size: .85rem; }
.empty { padding: 32px; text-align: center; color: var(--muted); }
footer { margin-top: 20px; color: var(--muted); font-size: .85rem; }
footer a { color: var(--accent); }
@media (max-width: 760px) {
  thead { display: none; }
  table, tbody, tr, td { display: block; width: 100%; }
  tr { padding: 10px 4px; border-bottom: 1px solid var(--border); }
  td { border: 0; padding: 2px 12px; }
  td.date { color: var(--muted); font-size: .85rem; }
  .controls input[type=search] { min-width: 0; width: 100%; }
  .count { margin-left: 0; }
}
</style>
</head>
<body>
<main>
  <h1>Nouveaux doctorants __LABO__</h1>
  <p class="sub">__LABO_LIB__ — thèses en cours d'après Amethis · mis à jour le __MAJ__</p>

  <div class="controls">
    <label>Thèse commencée depuis le
      <input type="date" id="depuis">
    </label>
    <div class="presets">
      <button type="button" data-preset="annee">Cette année universitaire</button>
      <button type="button" data-preset="30">30 derniers jours</button>
      <button type="button" data-preset="365">12 derniers mois</button>
      <button type="button" data-preset="tous">Toutes</button>
    </div>
    <label>Rechercher (nom, direction, sujet…)
      <input type="search" id="q" placeholder="ex. TABAREAU, robotique…">
    </label>
    <div class="count" id="count"></div>
  </div>

  <div class="table-wrap">
    <table>
      <thead><tr>
        <th>Début</th><th>Doctorant·e</th><th>Direction</th><th>Établ. / spécialité</th><th>Sujet</th>
      </tr></thead>
      <tbody id="rows">
__ROWS__
      </tbody>
    </table>
    <div class="empty" id="empty" hidden>Aucune thèse ne correspond à ces critères.</div>
  </div>

  <footer>
    __TOTAL__ thèses __LABO__ en cours au total ·
    <a href="__CSV__">Télécharger le CSV</a> ·
    Source : <a href="__SOURCE__">Amethis – thèses en cours</a> ·
    Page générée automatiquement chaque jour, non officielle.
  </footer>
</main>
<script>
(function () {
  var rows = Array.prototype.slice.call(document.querySelectorAll('#rows tr'));
  var depuis = document.getElementById('depuis');
  var q = document.getElementById('q');
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');

  function iso(d) { return d.toISOString().slice(0, 10); }
  function anneeUniv() {
    var now = new Date();
    var y = now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1;
    return y + '-09-01';
  }
  function norm(s) { return s.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase(); }

  function apply() {
    var d = depuis.value, terms = norm(q.value).split(/\\s+/).filter(Boolean), n = 0;
    rows.forEach(function (tr) {
      var ok = (!d || tr.dataset.date >= d);
      if (ok && terms.length) {
        var txt = tr.dataset.txt || (tr.dataset.txt = norm(tr.textContent));
        ok = terms.every(function (t) { return txt.indexOf(t) !== -1; });
      }
      tr.hidden = !ok; if (ok) n++;
    });
    count.textContent = n + (n > 1 ? ' doctorant·e·s' : ' doctorant·e');
    empty.hidden = n !== 0;
    var p = new URLSearchParams();
    if (d) p.set('depuis', d); else p.set('depuis', 'tous');
    if (q.value) p.set('q', q.value);
    history.replaceState(null, '', '?' + p.toString());
  }

  function preset(name) {
    if (name === 'tous') depuis.value = '';
    else if (name === 'annee') depuis.value = anneeUniv();
    else { var d = new Date(); d.setDate(d.getDate() - parseInt(name, 10)); depuis.value = iso(d); }
    apply();
  }

  var params = new URLSearchParams(location.search);
  var pd = params.get('depuis');
  depuis.value = pd === 'tous' ? '' : (pd || anneeUniv());
  q.value = params.get('q') || '';
  depuis.addEventListener('input', apply);
  q.addEventListener('input', apply);
  document.querySelectorAll('[data-preset]').forEach(function (b) {
    b.addEventListener('click', function () { preset(b.dataset.preset); });
  });
  apply();
})();
</script>
</body>
</html>
"""


def ecrire_html(path, lignes, labo, labo_lib, csv_name):
    e = html.escape
    rows = []
    for l in lignes:
        direction = e(l["directeur"])
        if l["co_directeur"]:
            direction += f'<div class="meta">co-dir. {e(l["co_directeur"])}</div>'
        rows.append(
            f'        <tr data-date="{e(l["debut_iso"])}">'
            f'<td class="date">{e(l["debut"])}</td>'
            f'<td class="name"><a href="{e(l["lien"])}">{e(l["doctorant"])}</a></td>'
            f'<td>{direction}</td>'
            f'<td>{e(l["etablissement"])}<div class="meta">{e(l["specialite"])}</div></td>'
            f'<td>{e(l["titre"])}</td></tr>'
        )
    maj = dt.datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y à %Hh%M")
    page = (HTML_TEMPLATE
            .replace("__ROWS__", "\n".join(rows))
            .replace("__LABO_LIB__", e(labo_lib))
            .replace("__LABO__", e(labo))
            .replace("__MAJ__", maj)
            .replace("__TOTAL__", str(len(lignes)))
            .replace("__CSV__", e(csv_name or "#"))
            .replace("__SOURCE__", PAGE_URL))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def ecrire_csv(path, lignes):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    champs = [k for k in (lignes[0].keys() if lignes else ["debut"]) if k != "debut_iso"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=champs, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Nouveaux doctorants d'un labo dans Amethis")
    ap.add_argument("--labo", default="LS2N", help="sigle ou code de l'unité de recherche (défaut : LS2N)")
    ap.add_argument("--depuis", type=dt.date.fromisoformat,
                    help="date de début minimale AAAA-MM-JJ (défaut : 1er septembre de l'année universitaire)")
    ap.add_argument("--tous", action="store_true", help="toutes les thèses en cours, sans filtre de date")
    ap.add_argument("--csv", metavar="FICHIER", help="exporte aussi le résultat en CSV")
    ap.add_argument("--html", metavar="FICHIER",
                    help="génère une page web avec toutes les thèses du labo (filtre de date dans la page)")
    ap.add_argument("--format", choices=["texte", "markdown"], default="texte")
    ap.add_argument("--quiet", action="store_true", help="n'affiche pas la liste dans le terminal")
    args = ap.parse_args()

    depuis = None if args.tous else (args.depuis or debut_annee_universitaire())
    labo = args.labo.upper()

    theses = charger_theses()
    du_labo = [r for r in theses
               if labo in ((r.get("urSigle") or "").upper(), (r.get("urCod") or "").upper())]
    if not du_labo:
        sys.exit(f"Aucune thèse trouvée pour le laboratoire {labo} ({len(theses)} thèses lues).")
    du_labo.sort(key=lambda r: (r.get("thsDebDatIso") or "", nom_doctorant(r)), reverse=True)
    toutes = [ligne(r) for r in du_labo]
    lignes = [l for l in toutes if not depuis or (l["debut_iso"] and l["debut_iso"] >= depuis.isoformat())]

    periode = f"depuis le {depuis.strftime('%d/%m/%Y')}" if depuis else "toutes dates"
    print(f"{len(lignes)} doctorant(s) {labo} {periode} "
          f"(sur {len(toutes)} thèses {labo} en cours dans Amethis)")

    if not args.quiet:
        print()
        if args.format == "markdown":
            print("| Début | Doctorant·e | Direction | Co-direction | Étab. | Spécialité | Sujet |")
            print("|---|---|---|---|---|---|---|")
            for l in lignes:
                print(f"| {l['debut']} | [{l['doctorant']}]({l['lien']}) | {l['directeur']} | "
                      f"{l['co_directeur']} | {l['etablissement']} | {l['specialite']} | {l['titre']} |")
        else:
            for l in lignes:
                dir_ = l["directeur"] + (f" (co-dir. {l['co_directeur']})" if l["co_directeur"] else "")
                print(f"{l['debut']}  {l['doctorant']}")
                print(f"            Direction : {dir_}")
                print(f"            {l['etablissement']} / ED {l['ecole_doctorale']} / {l['specialite']}")
                print(textwrap.fill(l["titre"], width=100, initial_indent="            Sujet : ",
                                    subsequent_indent="                    "))
                print(f"            {l['lien']}\n")

    if args.csv:
        # Avec --html, le CSV contient toutes les thèses du labo (comme la page) ; sinon la sélection.
        ecrire_csv(args.csv, toutes if args.html else lignes)
        print(f"CSV écrit : {args.csv}")
    if args.html:
        labo_lib = du_labo[0].get("urLib") or labo
        csv_rel = os.path.relpath(args.csv, os.path.dirname(os.path.abspath(args.html))) if args.csv else None
        ecrire_html(args.html, toutes, labo, labo_lib, csv_rel)
        print(f"Page écrite : {args.html}")


if __name__ == "__main__":
    main()
