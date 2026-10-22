import json
import os
import requests
from datetime import datetime, timezone, timedelta

import cards

GITHUB_TOKEN = os.environ.get("GH_TOKEN", "")
GITHUB_USERNAME = "23abdul23"
LEETCODE_USERNAME = "abdulazeem23"

if not GITHUB_TOKEN:
    raise RuntimeError("GH_TOKEN environment variable is not set or is empty.")

GH_HEADERS = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}

# ── GitHub queries ────────────────────────────────────────────────────────────

# Languages come from repos the user owns and did not fork; forks and
# collaborator repos used to skew the percentages (e.g. HTML at 58%).
BASE_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    pullRequests { totalCount }
    issues { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

YEAR_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
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
        timeout=30,
    )
    if not r.ok:
        print(f"GitHub API error {r.status_code}: {r.text[:400]}")
        r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    return data["data"]


def fetch_all_years(created_at):
    """Walk every year from account creation (not a hardcoded year) to today."""
    now = datetime.now(timezone.utc)
    start_year = int(created_at[:4])
    all_days, total_commits = {}, 0
    for year in range(start_year, now.year + 1):
        from_dt = f"{year}-01-01T00:00:00Z"
        to_dt = f"{year}-12-31T23:59:59Z" if year < now.year else now.strftime("%Y-%m-%dT%H:%M:%SZ")
        data = gql(YEAR_QUERY, {"login": GITHUB_USERNAME, "from": from_dt, "to": to_dt})
        cc = data["user"]["contributionsCollection"]
        total_commits += cc["totalCommitContributions"]
        for week in cc["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                all_days[day["date"]] = day["contributionCount"]
    return total_commits, sorted(all_days.items())


def calc_streak(days):
    day_map = dict(days)
    today = datetime.now(timezone.utc).date()
    check = today if day_map.get(today.isoformat(), 0) > 0 else today - timedelta(days=1)
    current = 0
    while day_map.get(check.isoformat(), 0) > 0:
        current += 1
        check -= timedelta(days=1)
    longest = run = 0
    for _, count in days:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)
    return current, longest


def calc_languages(user):
    sizes = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            sizes[edge["node"]["name"]] = sizes.get(edge["node"]["name"], 0) + edge["size"]
    total = sum(sizes.values()) or 1
    top = sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:5]
    return [(n, round(s * 100 / total, 1)) for n, s in top]


# ── LeetCode ──────────────────────────────────────────────────────────────────

LC_CACHE = "assets/leetcode.json"
# Last known good values, used until the first successful live fetch
LC_DEFAULT = {"total": 390, "easy": 0, "medium": 0, "hard": 0, "rating": 1585, "top": None}

LC_STATS_Q = """
query($username: String!) {
  matchedUser(username: $username) {
    submitStatsGlobal { acSubmissionNum { difficulty count } }
  }
}
"""
LC_CONTEST_Q = """
query($username: String!) {
  userContestRanking(username: $username) { rating topPercentage }
  userContestRankingHistory(username: $username) { attended rating }
}
"""


def lc_post(query):
    r = requests.post(
        "https://leetcode.com/graphql",
        json={"query": query, "variables": {"username": LEETCODE_USERNAME}},
        headers={
            "Content-Type": "application/json",
            "Referer": f"https://leetcode.com/u/{LEETCODE_USERNAME}/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json().get("data") or {}


def load_lc_cache():
    try:
        with open(LC_CACHE, encoding="utf-8") as f:
            return {**LC_DEFAULT, **json.load(f)}
    except Exception:
        return dict(LC_DEFAULT)


def fetch_leetcode():
    """Each part is fetched on its own; anything that fails keeps its cached value."""
    lc = load_lc_cache()
    try:
        m = lc_post(LC_STATS_Q).get("matchedUser")
        counts = {x["difficulty"]: x["count"] for x in m["submitStatsGlobal"]["acSubmissionNum"]}
        lc.update(total=counts.get("All", lc["total"]), easy=counts.get("Easy", 0),
                  medium=counts.get("Medium", 0), hard=counts.get("Hard", 0))
    except Exception as e:
        print(f"LeetCode solved-count fetch failed ({e}); using cached values")
    try:
        d = lc_post(LC_CONTEST_Q)
        hist = [h["rating"] for h in (d.get("userContestRankingHistory") or []) if h.get("attended")]
        rk = d.get("userContestRanking") or {}
        if hist:
            lc["rating"] = int(max(hist))
        elif rk.get("rating"):
            lc["rating"] = int(rk["rating"])
        if rk.get("topPercentage"):
            lc["top"] = round(rk["topPercentage"])
    except Exception as e:
        print(f"LeetCode contest fetch failed ({e}); using cached values")
    with open(LC_CACHE, "w", encoding="utf-8") as f:
        json.dump(lc, f)
    return lc


# ── Static profile content (from the Figma design) ────────────────────────────

INTERN = dict(
    badge="ENTERPRISE PRODUCTION", meta="Crecientech", title="Software Engineer Intern ",
    title2="@ Crecientech",
    desc="Architecting low-latency backend microservices and deterministic AI inference engines. "
         "Orchestrating multi-hop LLM agent workflows, vector embeddings and graph-aware RAG pipelines "
         "using knowledge graph reasoning.",
    style="grid",
    metrics=[("Query Latency", "~42ms", cards.GREEN), ("Tool Calling Accuracy", "99.4%", cards.CYAN),
             ("Data Throughput", "1.4M+", cards.TEXT)],
    sub=["p95 Neo4j traversal", "Structured schemas", "Records indexed"],
    chips=["FastAPI", "Neo4j (Cypher)", "PostgreSQL", "LangChain", "Qdrant Vector DB"],
)
AEGIS = dict(
    badge="FLAGSHIP DEPLOYMENT", meta="IIIT-A Ecosystem", title="Aegis ID ", title2="· Campus OS",
    desc="Institutional-grade attendance and identity platform handling concurrent peak loads. "
         "Powers geofencing and batch verification across 2,000+ campus users.",
    style="rows",
    metrics=[("Active Userbase", "2,000+ Students & Faculty", cards.TEXT),
             ("Async Job Queue (BullMQ)", "Zero Dropped Signals", cards.GREEN)],
    chips=["Node.js", "Redis", "BullMQ", "AWS EC2 / S3"],
)
ARCH = [
    dict(sys="SYSTEM // 001", tag="v2.1-prod", accent=cards.CYAN,
         title=["TBEP V2: Knowledge Graph", "Agent Platform"],
         desc="Biomedical literature extraction and reasoning engine using deterministic tool-calling LLM "
              "agents with Neo4j entity graphs. Bridges vector semantic search with graph traversals for "
              "hallucination-resistant querying.",
         flow_label="// TOPOLOGICAL EXECUTION PIPELINE",
         flow=[("1. Query Parsing", "Pydantic Schema", cards.CYAN), ("2. Graph Agent", "Neo4j Cypher Path", cards.GREEN),
               ("3. Synthesis", "Deterministic Stream", "#d0bcff")],
         bullets=["Autonomous multi-step tool execution with strict JSON parameter validation.",
                  "Sub-50ms relation lookup across 400,000+ biological node clusters."],
         chips=["FastAPI", "Neo4j", "LangChain", "Docker Compose"]),
    dict(sys="SYSTEM // 002", tag="Live Production", accent=cards.GREEN,
         title=["Aegis ID: High-Concurrency", "Identity Bus"],
         desc="Decoupled event-driven identity verification system built for unreliable campus networks. "
              "Uses Redis-backed BullMQ job pipelines and geofenced, time-based dynamic tokens.",
         flow_label="// HIGH-LOAD INGESTION MESH",
         flow=[("1. Geofence", "Haversine Sync", cards.GREEN), ("2. BullMQ", "Redis FIFO Bus", cards.CYAN),
               ("3. Persistence", "PostgreSQL Pool", cards.TEXT)],
         bullets=["Absorbs 500+ requests/second during synchronous 9 AM class roll calls.",
                  "Fault-tolerant retry queue prevents dropped packets during unstable mobile network transitions."],
         chips=["Redis", "BullMQ", "Node.js", "AWS S3"]),
]
SKILLS = [
    ("Languages", cards.CYAN, ["C++ (STL)", "Python", "TypeScript", "Java", "SQL"]),
    ("Backend", cards.GREEN, ["FastAPI", "Node.js", "Express", "RESTful API", "JWT / OAuth"]),
    ("Databases", cards.PURPLE, ["PostgreSQL", "Neo4j", "Redis", "MongoDB", "Qdrant"]),
    ("AI & Reasoning", cards.CYAN, ["LLM Agents", "Tool Calling", "Advanced RAG", "Knowledge Graph", "LangChain"]),
    ("Cloud & DevOps", cards.GREEN, ["Docker", "AWS (EC2/S3)", "GCP", "GitHub Actions", "Linux CLI"]),
]


def achievements(lc_total):
    return [
        ("JEE Main 2024", "AIR 5555", "Top 0.341% among 1.4M+ candidates nationally.", cards.CYAN),
        ("Educathon 2.0", "Top 20 Finalist", "Selected among 300+ national teams for automated educational tooling.", cards.GREEN),
        ("drawpyo (Python FOSS)", "3 PRs Merged", "Diagram object inheritance and schema generation work merged upstream.", cards.PURPLE),
        ("GeekHaven IIIT-A", "110+ Mentored", "Open-source workshops on Git workflows and Linux systems.", cards.CYAN),
    ]


def build_readme(prs, issues, updated):
    return f"""<div align="center">

![Hero](assets/hero.svg)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0e1420?style=flat&logo=linkedin&logoColor=4cd7f6)](https://linkedin.com/in/abdulazeemansari)
[![LeetCode](https://img.shields.io/badge/LeetCode-0e1420?style=flat&logo=leetcode&logoColor=4cd7f6)](https://www.leetcode.com/abdulazeem23)
[![Codeforces](https://img.shields.io/badge/Codeforces-0e1420?style=flat&logo=codeforces&logoColor=4cd7f6)](https://codeforces.com/profile/abdulazeem23)
![Views](https://komarev.com/ghpvc/?username=23abdul23&style=flat&color=4cd7f6&label=profile+views)

</div>

![Focus](assets/focus.svg)

![Telemetry](assets/telemetry.svg)

<sub>Auto-updated daily via GitHub Actions · Last updated: <b>{updated}</b> · {prs:,} pull requests · {issues:,} issues</sub>

![Architecture](assets/arch.svg)

![Skills](assets/skills.svg)

![Achievements](assets/achievements.svg)
"""


def main():
    os.makedirs("assets", exist_ok=True)
    base = gql(BASE_QUERY, {"login": GITHUB_USERNAME})["user"]
    commits, days = fetch_all_years(base["createdAt"])
    cur, longest = calc_streak(days)
    langs = calc_languages(base)
    lc = fetch_leetcode()

    now = datetime.now(timezone.utc)
    updated = now.strftime("%d %b %Y, %H:%M UTC")
    out = {
        "hero.svg": cards.hero("@23abdul23", "Abdul Azeem Ansari", "Backend & AI Systems Engineer",
                               "B.Tech IT @ IIIT Allahabad", "Shit happens, Keep pushing",
                               "Prayagraj, IN (UTC +05:30)", "Available for Backend & AI Infrastructure Roles"),
        "focus.svg": cards.focus(f"ACTIVE · {now.strftime('%b %Y').upper()}", INTERN, AEGIS),
        "arch.svg": cards.arch(ARCH),
        "skills.svg": cards.skills(SKILLS),
        "achievements.svg": cards.achievements(achievements(lc["total"])),
        "telemetry.svg": cards.telemetry(days, commits, cur, longest, langs,
                                         (lc["total"], lc["easy"], lc["medium"], lc["hard"]),
                                         lc["rating"], lc["top"], "Live sync: GitHub & LeetCode"),
    }
    for name, content in out.items():
        with open(os.path.join("assets", name), "w", encoding="utf-8") as f:
            f.write(content)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(build_readme(base["pullRequests"]["totalCount"], base["issues"]["totalCount"], updated))
    print(f"commits={commits} streak={cur}/{longest} langs={langs} lc={lc}")


if __name__ == "__main__":
    main()
