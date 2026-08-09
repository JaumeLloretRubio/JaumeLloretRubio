#!/usr/bin/env python3
"""
JAYORU__ / stats renderer
Genera assets/stats-{light,dark}.svg y assets/langs-{light,dark}.svg
con los datos reales de la API de GitHub, en el estilo brutalista del perfil.

Uso:
    GH_TOKEN=... GH_LOGIN=JaumeLloretRubio python3 scripts/gen_stats.py

Sin GH_TOKEN genera las tarjetas con ceros (placeholders), para poder
commitear los assets antes de la primera ejecucion del workflow.

Solo stdlib.
"""

import json
import os
import urllib.request
from pathlib import Path

LOGIN = os.environ.get("GH_LOGIN", "JaumeLloretRubio")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

FONT = "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
THEMES = [("light", "#ffffff", "#000000", "#8a8a8a"),
          ("dark", "#0a0a0a", "#ffffff", "#7d7d7d")]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
    }
  }
}
"""

# Lenguajes que no aportan informacion sobre lo que uno hace.
SKIP_LANGS = {"HTML", "CSS", "SCSS", "Shell", "Batchfile", "Makefile",
              "Dockerfile", "Roff", "TeX"}


def fetch():
    """Devuelve (stats_dict, [(lang, bytes), ...]) o placeholders si no hay token."""
    if not TOKEN:
        return ({"COMMITS": 0, "PULL REQUESTS": 0, "CODE REVIEWS": 0,
                 "ISSUES": 0, "STARS": 0, "REPOS": 0, "FOLLOWERS": 0}, [])

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}",
                 "Content-Type": "application/json",
                 "User-Agent": "jayoru-profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)

    if "errors" in payload:
        raise SystemExit(f"GitHub API error: {payload['errors']}")

    u = payload["data"]["user"]
    c = u["contributionsCollection"]
    repos = u["repositories"]["nodes"]

    langs = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name in SKIP_LANGS:
                continue
            langs[name] = langs.get(name, 0) + edge["size"]

    stats = {
        "COMMITS": c["totalCommitContributions"] + c["restrictedContributionsCount"],
        "PULL REQUESTS": c["totalPullRequestContributions"],
        "CODE REVIEWS": c["totalPullRequestReviewContributions"],
        "ISSUES": c["totalIssueContributions"],
        "STARS": sum(r["stargazerCount"] for r in repos),
        "REPOS": u["repositories"]["totalCount"],
        "FOLLOWERS": u["followers"]["totalCount"],
    }
    return stats, sorted(langs.items(), key=lambda kv: -kv[1])[:8]


def frame(w, h, title, right, bg, fg, mu, body, footer):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{title}">
<style>
 .m{{font-family:{FONT}}}
 @keyframes bl{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
 .cur{{animation:bl 1s steps(1,end) infinite}}
</style>
<rect width="{w}" height="{h}" fill="{bg}"/>
<rect x="5" y="5" width="{w - 10}" height="{h - 10}" fill="none" stroke="{fg}" stroke-width="3"/>
<line x1="5" y1="46" x2="{w - 5}" y2="46" stroke="{fg}" stroke-width="2"/>
<text class="m" x="22" y="31" font-size="13" fill="{fg}" letter-spacing="2.5">{title}</text>
<text class="m" x="{w - 22}" y="31" font-size="11" fill="{mu}" letter-spacing="1.5" text-anchor="end">{right}</text>
{body}
<line x1="5" y1="{h - 42}" x2="{w - 5}" y2="{h - 42}" stroke="{fg}" stroke-width="2"/>
<text class="m" x="22" y="{h - 17}" font-size="11.5" fill="{mu}">{footer}<tspan class="cur" fill="{fg}">&#9608;</tspan></text>
</svg>'''


def render_stats(stats, bg, fg, mu):
    w, rows = 500, list(stats.items())
    h = 46 + len(rows) * 34 + 60
    body, y = "", 84
    for label, value in rows:
        body += (f'<text class="m" x="22" y="{y}" font-size="12.5" fill="{mu}" letter-spacing="1.5">{label}</text>'
                 f'<text class="m" x="{w - 22}" y="{y}" font-size="16" font-weight="700" fill="{fg}" text-anchor="end">{value:,}</text>'
                 f'<line x1="22" y1="{y + 11}" x2="{w - 22}" y2="{y + 11}" stroke="{mu}" stroke-width="1" stroke-dasharray="2 4"/>')
        y += 34
    return frame(w, h, "STATS // 12 MESES", "AUTO &#183; DAILY", bg, fg, mu, body,
                 "&gt; git log --author=jayoru")


def render_langs(langs, bg, fg, mu):
    w = 500
    rows = langs or [("&#8212;", 1)]
    h = 46 + len(rows) * 34 + 60
    total = sum(v for _, v in rows) or 1
    top = max(v for _, v in rows) or 1
    x0, bw = 176, 232
    body, y = "", 84
    for name, size in rows:
        pct = 100.0 * size / total
        fill = max(3, round(bw * size / top))
        body += (f'<text class="m" x="22" y="{y}" font-size="12.5" fill="{fg}">{name[:14]}</text>'
                 f'<rect x="{x0}" y="{y - 12}" width="{bw}" height="15" fill="none" stroke="{mu}" stroke-width="1.5"/>'
                 f'<rect x="{x0}" y="{y - 12}" width="{fill}" height="15" fill="{fg}"/>'
                 f'<text class="m" x="{w - 22}" y="{y}" font-size="12.5" fill="{mu}" text-anchor="end">{pct:4.1f}%</text>')
        y += 34
    return frame(w, h, "TOP LANGS // BYTES", "OWNER REPOS", bg, fg, mu, body,
                 "&gt; wc -l ~/**/*")


def main():
    stats, langs = fetch()
    ASSETS.mkdir(exist_ok=True)
    for mode, bg, fg, mu in THEMES:
        (ASSETS / f"stats-{mode}.svg").write_text(render_stats(stats, bg, fg, mu), encoding="utf-8")
        (ASSETS / f"langs-{mode}.svg").write_text(render_langs(langs, bg, fg, mu), encoding="utf-8")
    print(f"ok · stats={stats} · langs={[l for l, _ in langs]}")


if __name__ == "__main__":
    main()
