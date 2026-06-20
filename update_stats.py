import os, requests
from datetime import datetime, timezone, timedelta

GITHUB_TOKEN = os.environ.get("GH_TOKEN", "")
GITHUB_USERNAME = "23abdul23"
LEETCODE_USERNAME = "abdulazeem23"

if not GITHUB_TOKEN:
    raise RuntimeError("GH_TOKEN environment variable is not set or is empty.")
print(f"Token loaded: {'*' * (len(GITHUB_TOKEN) - 4)}{GITHUB_TOKEN[-4:]}")

GH_HEADERS = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}

# ── 1. GitHub base stats (PRs, Issues, Languages) ────────────────────────────

BASE_QUERY = """
query($login: String!) {
  user(login: $login) {
    pullRequests(states: [MERGED, OPEN, CLOSED]) { totalCount }
    issues { totalCount }
    topRepositories(first: 20, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name }
          }
        }
      }
    }
  }
}
"""

# ── 2. Per-year contribution query ────────────────────────────────────────────
# contributionsCollection requires explicit from/to to cover all years

YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

def gql(query, variables):
    r = requests.post(
        "https://api.github.com/graphql",
        headers=GH_HEADERS,
        json={"query": query, "variables": variables},
    )
    if not r.ok:
        print(f"GitHub API error {r.status_code}: {r.text[:400]}")
        r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    return data["data"]

def fetch_github_base():
    data = gql(BASE_QUERY, {"login": GITHUB_USERNAME})
    return data["user"]

def fetch_all_years():
    """Fetch contribution data year by year from account creation (2024) to now."""
    now = datetime.now(timezone.utc)
    # Abdul joined July 2024, so collect 2024, 2025, 2026
    start_year = 2024
    current_year = now.year

    all_days = []
    total_commits = 0

    for year in range(start_year, current_year + 1):
        from_dt = f"{year}-01-01T00:00:00Z"
        to_dt   = f"{year}-12-31T23:59:59Z" if year < current_year else now.strftime("%Y-%m-%dT%H:%M:%SZ")

        print(f"  Fetching contributions for {year}...")
        data = gql(YEAR_QUERY, {"login": GITHUB_USERNAME, "from": from_dt, "to": to_dt})
        cc = data["user"]["contributionsCollection"]
        total_commits += cc["totalCommitContributions"]

        for week in cc["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                all_days.append((day["date"], day["contributionCount"]))

    return total_commits, all_days

def calc_streak(all_days):
    days = sorted(set(all_days), key=lambda x: x[0])  # dedupe + sort by date
    today     = datetime.now(timezone.utc).date()
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()

    day_map = {d: c for d, c in days}

    # Current streak: walk back from today (allow today to be 0 if not yet contributed)
    current = 0
    check = today
    # if today has 0 contributions, start checking from yesterday
    if day_map.get(today_str, 0) == 0:
        check = today - timedelta(days=1)
    while True:
        s = check.isoformat()
        if day_map.get(s, 0) > 0:
            current += 1
            check -= timedelta(days=1)
        else:
            break

    # Longest streak across all days
    longest = 0
    run = 0
    for _, count in days:
        if count > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    return current, longest

def calc_languages(user):
    lang_sizes = {}
    for repo in user["topRepositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            lang_sizes[name] = lang_sizes.get(name, 0) + edge["size"]
    total = sum(lang_sizes.values()) or 1
    sorted_langs = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
    return [(name, round(size * 100 / total, 1)) for name, size in sorted_langs]

# ── 3. LeetCode stats ─────────────────────────────────────────────────────────

def fetch_leetcode():
    query = """
    query($username: String!) {
      matchedUser(username: $username) {
        submitStatsGlobal {
          acSubmissionNum { difficulty count }
        }
      }
    }
    """
    r = requests.post(
        "https://leetcode.com/graphql",
        json={"query": query, "variables": {"username": LEETCODE_USERNAME}},
        headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    stats = data["data"]["matchedUser"]["submitStatsGlobal"]["acSubmissionNum"]
    counts = {s["difficulty"]: s["count"] for s in stats}
    return (
        counts.get("All", 0),
        counts.get("Easy", 0),
        counts.get("Medium", 0),
        counts.get("Hard", 0),
    )

# ── 4. Build language bar (HTML table for visual progress bars) ───────────────

LANG_COLORS = {
    "TypeScript":       "#3178c6",
    "JavaScript":       "#f1e05a",
    "Python":           "#3572A5",
    "HTML":             "#e34c26",
    "CSS":              "#563d7c",
    "Java":             "#b07219",
    "C++":              "#f34b7d",
    "Shell":            "#89e051",
    "Jupyter Notebook": "#DA5B0B",
    "Go":               "#00ADD8",
    "Rust":             "#dea584",
}

def lang_table(langs):
    rows = ""
    for name, pct in langs:
        color = LANG_COLORS.get(name, "#888888")
        bar_fill = int(pct * 2)   # max ~200px wide bar
        rows += (
            f'<tr>'
            f'<td align="right" width="130"><b>{name}</b></td>'
            f'<td width="220">'
            f'<img src="https://progress-bar.xyz/{int(pct)}/?width=200&color={color[1:]}&bg=e0e0e0" height="12"/>'
            f'</td>'
            f'<td><code>{pct}%</code></td>'
            f'</tr>\n'
        )
    return f'<table>\n{rows}</table>'

# ── 5. Build README ───────────────────────────────────────────────────────────

def build_readme(gh_base, total_commits, current_streak, longest_streak,
                 lc_total, lc_easy, lc_med, lc_hard, langs):

    total_prs    = gh_base["pullRequests"]["totalCount"]
    total_issues = gh_base["issues"]["totalCount"]
    updated      = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    # LeetCode breakdown — only show if non-zero
    lc_breakdown = ""
    if lc_easy + lc_med + lc_hard > 0:
        lc_breakdown = f"""&nbsp;&nbsp;✅ Easy **{lc_easy}** &nbsp;·&nbsp; 🟡 Medium **{lc_med}** &nbsp;·&nbsp; 🔴 Hard **{lc_hard}**"""

    lang_html = lang_table(langs)

    readme = f"""<h1 align="center">Abdul Azeem Ansari</h1>
<h3 align="center">Backend & AI Systems Engineer · B.Tech IT @ IIIT Allahabad</h3>

<p align="center">
  <a href="https://linkedin.com/in/abdulazeemansari"><img src="https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white"/></a>
  <a href="https://www.leetcode.com/abdulazeem23"><img src="https://img.shields.io/badge/LeetCode-FFA116?style=flat&logo=leetcode&logoColor=white"/></a>
  <a href="https://codeforces.com/profile/abdulazeem23"><img src="https://img.shields.io/badge/Codeforces-1F8ACB?style=flat&logo=codeforces&logoColor=white"/></a>
  <img src="https://komarev.com/ghpvc/?username=23abdul23&style=flat&color=0e75b6"/>
</p>

---

### 🔧 What I'm Building

- **@ Crecientech (SDE Intern)** — Scalable backend services, LLM agents, RAG pipelines, and graph-aware reasoning systems for AI-powered biomedical research (FastAPI · Neo4j · PostgreSQL)
- **Aegis ID** — Campus management platform for 2,000+ users: identity, access control, movement tracking, and emergency response (Node.js · Redis · BullMQ · AWS)

---

### 🚀 Featured Projects

| Project | What it does | Stack |
|---|---|---|
| [**TBEP V2**](https://github.com/23abdul23) | AI platform for biomedical researchers to explore multi-omics datasets and knowledge graphs via natural language | FastAPI · Neo4j · LLM Agents · RAG |
| [**Aegis ID**](https://github.com/23abdul23/Aegis) | Mobile-first campus management: identity, access control, geofenced authorization, async notifications | Node.js · PostgreSQL · Redis · Docker · AWS |

---

### 📊 Live Stats
<sub>🔄 Auto-updated daily via GitHub Actions &nbsp;·&nbsp; Last updated: <b>{updated}</b></sub>

<br/>

| 🔥 Current Streak | ⚡ Longest Streak | 💻 Total Commits | 🔀 Pull Requests | 🐛 Issues |
|:-:|:-:|:-:|:-:|:-:|
| **{current_streak} days** | **{longest_streak} days** | **{total_commits:,}** | **{total_prs:,}** | **{total_issues:,}** |

<br/>

**🧩 LeetCode &nbsp;·&nbsp; {lc_total} problems solved**{"  " + lc_breakdown if lc_breakdown else ""}

<br/>

**📝 Top Languages**

{lang_html}

---

### 🛠 Skills

```
Languages      C++  Python  TypeScript  JavaScript  Java  Bash
Backend        Node.js  Express.js  FastAPI  REST APIs  JWT  Prisma
Databases      PostgreSQL  MongoDB  Neo4j  MySQL
AI Systems     LLM Agents  Tool Calling  RAG  Knowledge Graphs
Cloud/DevOps   AWS  GCP  Docker  Nginx  GitHub Actions  CI/CD
Distributed    Redis  BullMQ  Async Processing  Concurrency
Core CS        DSA  OOP  OS  DBMS  System Design  Microservices
```

---

### 🏆 Achievements

- 🥇 **AIR 5555** in JEE Main 2024 — Top 0.341% nationally
- 💻 **{lc_total}+ LeetCode** problems solved · Max Rating: 1585
- 🏅 **Top 20 Finalist** at Educathon 2.0 (National Hackathon) among 300+ teams
- 🔀 **3 PRs merged** into [drawpyo](https://github.com/MrYsLab/drawpyo) open-source Python library
- 🤝 Mentored **110+ students** in open-source contribution via FOSS Wing, Geekhaven
"""
    return readme

# ── 6. Main ───────────────────────────────────────────────────────────────────

def main():
    print("Fetching GitHub base stats...")
    gh_base = fetch_github_base()

    print("Fetching all-time contributions (year by year)...")
    total_commits, all_days = fetch_all_years()

    print("Calculating streak from full history...")
    current_streak, longest_streak = calc_streak(all_days)

    print("Calculating top languages...")
    langs = calc_languages(gh_base)

    print("Fetching LeetCode stats...")
    try:
        lc_total, lc_easy, lc_med, lc_hard = fetch_leetcode()
    except Exception as e:
        print(f"LeetCode fetch failed ({e}), using last known values")
        lc_total, lc_easy, lc_med, lc_hard = 390, 0, 0, 0

    print(f"\n✓ Total commits (all time): {total_commits:,}")
    print(f"✓ Current streak: {current_streak} days")
    print(f"✓ Longest streak: {longest_streak} days")
    print(f"✓ PRs: {gh_base['pullRequests']['totalCount']}  Issues: {gh_base['issues']['totalCount']}")
    print(f"✓ LeetCode: {lc_total} solved (E:{lc_easy} M:{lc_med} H:{lc_hard})")
    print(f"✓ Top langs: {[l[0] for l in langs]}")

    readme = build_readme(
        gh_base, total_commits, current_streak, longest_streak,
        lc_total, lc_easy, lc_med, lc_hard, langs
    )

    with open("README.md", "w") as f:
        f.write(readme)

    print("\n✅ README.md updated successfully!")

if __name__ == "__main__":
    main()
