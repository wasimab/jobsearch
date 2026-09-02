#!/usr/bin/env python3
"""
Daily Job Search Agent  --  v2
==============================
Searches for roles matching Muhammad Wasim Abbas's background (SAP Concur /
ITSM / Application Support / IT Program Management), flags remote, contract
and visa-sponsorship signals, scores each match remote-first, attaches the
relevant bit of the resume, and rebuilds a static HTML portal (index.html)
that also carries a one-click deep-link launcher for LinkedIn, Indeed,
Glassdoor, Bayt, Naukrigulf, Seek, JobStreet, Rozee and the major remote
boards.

WHAT CHANGED FROM v1
--------------------
1. Gulf/GCC + wider Middle East, wider SE Asia, and Australia/NZ coverage.
2. Remote-first scoring -- remote and contract roles float to the top,
   relocation roles sit below them, matching a "remote first, relocate if
   the role is worth it" search.
3. Contract / consultant / freelance keywords added.
4. A "Job Sites" tab in the portal: pre-filtered search links per site per
   region, built from job_sites.py. This is how LinkedIn/Indeed/Glassdoor
   get covered -- see the honest note below.
5. The portal now works even on a run that fetched zero listings, because
   the launcher tab is generated from static config, not from API results.

DATA SOURCES
------------
- Adzuna (https://developer.adzuna.com) -- free API, ~19 country indexes.
  Broad Western + India + Singapore coverage. No Gulf, no Pakistan.
- Jooble (https://jooble.org/api/about) -- free API, free-text location per
  call. This is what covers Pakistan, the whole GCC, and SE Asia.

WHY LINKEDIN / INDEED / GLASSDOOR AREN'T FETCHED
------------------------------------------------
None of the three offer a public job-search API to individual developers,
and scraping them violates their terms and gets IPs blocked fast. So this
agent does the legitimate thing: it builds the exact pre-filtered search URL
for each site and each region, and the portal renders them as one-click
buttons. You still see live results -- on their site, one click away.

SETUP
-----
See README.md. Short version: free Adzuna key + free Jooble key as GitHub
repo secrets, enable Pages, done.
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from urllib.parse import quote
from datetime import datetime, timezone

from job_sites import as_portal_data

# ---------------------------------------------------------------------------
# CONFIG -- edit freely
# ---------------------------------------------------------------------------

APP_ID = os.environ.get("ADZUNA_APP_ID", "")
APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
JOOBLE_APP_KEY = os.environ.get("JOOBLE_APP_KEY", "")

# Set DEMO=1 to build the portal without any API keys -- useful for checking
# the layout renders before you have keys.
DEMO_MODE = os.environ.get("DEMO", "") == "1"

# Adzuna country indexes. Unsupported codes just log a warning and skip, so
# it's safe to leave extras in here.
COUNTRIES = [
    "gb", "us", "ca", "au", "nz", "sg", "in",
    "de", "nl", "fr", "es", "it", "at", "ch", "be", "pl", "za",
]

# Jooble takes a free-text location, which is how the Gulf, Pakistan and the
# rest of SE Asia get covered -- Adzuna has no index for any of them.
JOOBLE_LOCATIONS = [
    # Gulf / GCC / wider Middle East
    "United Arab Emirates", "Dubai", "Abu Dhabi",
    "Saudi Arabia", "Riyadh", "Jeddah",
    "Qatar", "Kuwait", "Bahrain", "Oman", "Jordan", "Egypt",
    # Pakistan
    "Pakistan", "Lahore", "Karachi", "Islamabad",
    # SE Asia / APAC
    "Singapore", "Malaysia", "Hong Kong", "Thailand",
    "Indonesia", "Philippines", "Vietnam",
    # Australia / NZ (Jooble as a second pass over Adzuna)
    "Australia", "New Zealand",
    # Remote, as a pseudo-location -- Jooble indexes plenty of these
    "Remote",
]

# Each string is one search query, kept separate so results stay relevant
# per term rather than turning into noise.
KEYWORD_GROUPS = [
    # --- core Concur identity (highest-value, most differentiated) -------
    "SAP Concur",
    "Concur consultant",
    "Concur implementation",
    "travel and expense system",
    # --- support / ITSM management --------------------------------------
    "application support manager",
    "IT support manager",
    "IT service delivery manager",
    "ITSM manager",
    "service desk manager",
    # --- programme / project --------------------------------------------
    "IT program manager",
    "IT project manager",
    # --- adjacent / systems ---------------------------------------------
    "document management systems",
    "SAP functional consultant",
    # --- engagement type (catches contract + freelance framings) --------
    "IT contract consultant",
    "freelance SAP consultant",
]

RESULTS_PER_QUERY = 20
MAX_PAGES = 1  # raise to 2-3 once a first run confirms everything works

# Listings older than this are dropped. Applying to a 60-day-old posting is
# mostly wasted effort.
MAX_AGE_DAYS = 45

VISA_HINTS = re.compile(
    r"visa spons|sponsor.{0,20}visa|work permit|relocation assist|"
    r"will sponsor|skilled worker visa|right to work|employment pass|"
    r"iqama|relocation package|relocation support",
    re.IGNORECASE,
)
REMOTE_HINTS = re.compile(
    r"\bremote\b|work from home|\bwfh\b|hybrid|distributed team|"
    r"work from anywhere",
    re.IGNORECASE,
)
CONTRACT_HINTS = re.compile(
    r"\bcontract\b|\bcontractor\b|fixed term|\bfreelanc|day rate|"
    r"\bb2b\b|outside ir35|inside ir35|consultan|interim|temporary",
    re.IGNORECASE,
)

# Regions, for the portal's region tab. Maps a country label to a bucket.
REGION_MAP = {
    "GULF": {"United Arab Emirates", "Dubai", "Abu Dhabi", "Saudi Arabia",
             "Riyadh", "Jeddah", "Qatar", "Kuwait", "Bahrain", "Oman",
             "Jordan", "Egypt"},
    "SEA / APAC": {"SG", "Singapore", "Malaysia", "Hong Kong", "Thailand",
                   "Indonesia", "Philippines", "Vietnam", "IN"},
    "ANZ": {"AU", "NZ", "Australia", "New Zealand"},
    "PAKISTAN": {"Pakistan", "Lahore", "Karachi", "Islamabad"},
    "UK / EUROPE": {"GB", "DE", "NL", "FR", "ES", "IT", "AT", "CH", "BE",
                    "PL"},
    "AMERICAS": {"US", "CA"},
    "AFRICA": {"ZA"},
}


def region_of(country: str) -> str:
    for region, members in REGION_MAP.items():
        if country in members:
            return region
    return "OTHER"


OUTPUT_JSON = "jobs.json"
OUTPUT_HTML = "index.html"

# ---------------------------------------------------------------------------
# YOUR EXPERIENCE, keyed for matching -- pulled from the resume so each
# listing can show *why* you're a fit. Edit freely; it's yours.
# ---------------------------------------------------------------------------

EXPERIENCE_BANK = {
    "concur": [
        "Directed the end-to-end global deployment of SAP Concur (Travel & "
        "Expense) across 20+ regions, including SQL-based executive "
        "compliance dashboards (Worley, 2018-2020).",
        "Led localized SAP Concur implementations across multiple APAC "
        "countries -- Expense and Travel module configuration, policy "
        "groups, approval workflows, local regulatory alignment "
        "(Jacobs, 2011-2018).",
        "Primary point of contact for SAP Concur import/integration error "
        "resolution across 30,000+ enterprise users (TEXLA Technologies, "
        "2021-2024).",
    ],
    "itsm": [
        "ITIL v4 certified; established and chaired regional Change "
        "Advisory Boards and led Major Incident Management during "
        "critical outages.",
        "Optimized ServiceNow assignment rules into a dynamic routing "
        "system allocating incidents across onshore and offshore units "
        "(ACT UK, 2024-present).",
        "Lifted SLA compliance 25% and cut MTTR 30% via real-time KPI "
        "dashboards and a self-service knowledge base.",
    ],
    "application support": [
        "Directed global support operations for 30,000+ enterprise users "
        "across US, APAC and EMEA, adapting SaaS support frameworks to "
        "regional compliance requirements (TEXLA Technologies).",
        "Maintained 99.9% uptime for enterprise SaaS applications and "
        "managed zero-downtime release cycles for high-availability "
        "financial systems.",
    ],
    "document management": [
        "Managed enterprise Document Management Systems and corporate "
        "finance systems at 99% reliability across high-intensity "
        "engineering project lifecycles (Jacobs, 2007-2010).",
        "Led UAT, deployment scheduling and change governance for "
        "large-scale enterprise system upgrades.",
    ],
    "it manager": [
        "IT Program & Support Manager (ACT UK, 2024-present) and IT "
        "Application Lead / Global Project Manager (Worley, 2018-2020) -- "
        "global project controls, Tier-1 vendor negotiation, licensing "
        "strategy.",
        "Spearheaded enterprise application migration through the "
        "Jacobs-Worley M&A integration with zero loss of operational data.",
    ],
    "integration": [
        "Enterprise systems integration across SAP S/4HANA and SAP ERP, "
        "third-party financial platforms, and data mapping/validation "
        "between Concur and downstream finance systems.",
        "Coordinated cross-team data-feed and file-transfer integrations, "
        "diagnosing import/export errors at the platform level.",
    ],
    "consulting": [
        "Client-facing consultant across the full delivery lifecycle -- "
        "requirements workshops, solution design, configuration, UAT, "
        "cutover, go-live and hypercare.",
        "Directed training and knowledge transfer for 5,000+ end users "
        "during major system rollouts.",
    ],
    # Asta Powerproject does not appear in the resume. These bullets point
    # at the genuinely-held adjacent skill (critical path / global programme
    # delivery) rather than claiming hands-on tool experience that couldn't
    # be backed up in an interview. If you DO have real Asta experience,
    # add it here and it shows up honestly from then on.
    "planning": [
        "Single point of contact for global project controls, tracking "
        "critical-path milestones and resource availability across "
        "multiple time zones (ACT UK, 2024-present).",
        "Global Project Manager overseeing multi-region programme delivery "
        "and stakeholder coordination through a major M&A integration "
        "(Worley, 2018-2020).",
    ],
}


def relevant_experience(title: str, description: str) -> list[str]:
    """Return up to 3 resume bullets relevant to this listing."""
    text = f"{title} {description}".lower()
    hits: list[str] = []
    if "concur" in text or "travel and expense" in text or "t&e" in text:
        hits += EXPERIENCE_BANK["concur"]
    if any(k in text for k in ("itsm", "service management", "servicenow",
                               "itil", "service desk", "incident manage")):
        hits += EXPERIENCE_BANK["itsm"]
    if "application support" in text or "support manager" in text:
        hits += EXPERIENCE_BANK["application support"]
    if "document management" in text or re.search(r"\bdms\b", text):
        hits += EXPERIENCE_BANK["document management"]
    if any(k in text for k in ("it manager", "program manager",
                               "programme manager", "project manager",
                               "it support", "delivery manager")):
        hits += EXPERIENCE_BANK["it manager"]
    if any(k in text for k in ("integration", "interface", "sap erp",
                               "s/4hana", "s4hana")):
        hits += EXPERIENCE_BANK["integration"]
    if any(k in text for k in ("consultant", "consulting", "advisory",
                               "implementation partner")):
        hits += EXPERIENCE_BANK["consulting"]
    if any(k in text for k in ("asta", "powerproject", "primavera",
                               "planning engineer", "project planner",
                               "scheduler", "critical path")):
        hits += EXPERIENCE_BANK["planning"]

    seen, out = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out[:3]


# ---------------------------------------------------------------------------
# SCORING -- remote first, relocation as backup
# ---------------------------------------------------------------------------

# Terms that indicate the listing is squarely in your wheelhouse rather than
# a loose keyword collision.
STRONG_TITLE_TERMS = (
    "concur", "expense", "itsm", "service management", "application support",
    "support manager", "service delivery", "it manager", "program manager",
    "programme manager", "sap",
)


def score_job(job: dict) -> int:
    """
    Higher is better. Tuned for a remote-first search with relocation as a
    backup, so remote and contract signals outweigh geography.
    """
    score = 0
    title = (job.get("title") or "").lower()

    if job.get("remote_mention"):
        score += 40
    if job.get("contract_mention"):
        score += 15
    if job.get("visa_mention"):
        score += 12

    # Title relevance beats description relevance by a lot.
    if any(t in title for t in STRONG_TITLE_TERMS):
        score += 25
    if "concur" in title:
        score += 20          # your single most differentiated skill
    if "senior" in title or "lead" in title or "head of" in title:
        score += 6

    # How much of your resume actually matched.
    score += 5 * len(job.get("relevant_experience", []))

    # Region nudges -- small, so they never outrank a good remote role.
    region = region_of(job.get("country", ""))
    score += {"GULF": 8, "SEA / APAC": 8, "ANZ": 5,
              "UK / EUROPE": 4, "PAKISTAN": 3}.get(region, 0)

    # Freshness.
    days = days_old(job.get("posted", ""))
    if days is not None:
        if days <= 2:
            score += 12
        elif days <= 7:
            score += 6
        elif days > 30:
            score -= 8

    return score


def days_old(iso: str):
    if not iso:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(iso.replace("Z", "Z"), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt).days
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------------

def fetch_adzuna(country: str, query: str, page: int = 1) -> dict:
    url = (
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        f"?app_id={APP_ID}&app_key={APP_KEY}"
        f"&results_per_page={RESULTS_PER_QUERY}"
        f"&what={quote(query)}"
        f"&max_days_old={MAX_AGE_DAYS}"
        f"&sort_by=date"
        f"&content-type=application/json"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "job-search-agent/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read()[:160].decode("utf-8", "replace")
        print(f"  [warn] adzuna {country}/{query!r}: HTTP {e.code} -- {body}")
        return {"results": []}
    except Exception as e:  # noqa: BLE001 -- keep the run going
        print(f"  [warn] adzuna {country}/{query!r}: {e}")
        return {"results": []}


def fetch_jooble(keyword: str, location: str) -> list[dict]:
    url = f"https://jooble.org/api/{JOOBLE_APP_KEY}"
    payload = json.dumps({"keywords": keyword, "location": location}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json",
                 "User-Agent": "job-search-agent/2.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("jobs", []) or []
    except urllib.error.HTTPError as e:
        print(f"  [warn] jooble {location}/{keyword!r}: HTTP {e.code} -- "
              f"{e.read()[:160].decode('utf-8', 'replace')}")
        return []
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] jooble {location}/{keyword!r}: {e}")
        return []


def collect_jobs() -> list[dict]:
    all_jobs: dict[str, dict] = {}

    if APP_ID and APP_KEY:
        total = len(COUNTRIES) * len(KEYWORD_GROUPS) * MAX_PAGES
        print(f"Adzuna: {len(COUNTRIES)} countries x {len(KEYWORD_GROUPS)} "
              f"keywords x {MAX_PAGES} page(s) = up to {total} calls...")
        for country in COUNTRIES:
            for kw in KEYWORD_GROUPS:
                for page in range(1, MAX_PAGES + 1):
                    data = fetch_adzuna(country, kw, page)
                    results = data.get("results", [])
                    if results:
                        print(f"  {country}/{kw!r}: {len(results)}")
                    for r in results:
                        job_id = str(r.get("id") or r.get("redirect_url") or "")
                        if not job_id or job_id in all_jobs:
                            continue
                        title = (r.get("title") or "").strip()
                        desc = r.get("description", "") or ""
                        blob = f"{title} {desc}"
                        all_jobs[job_id] = {
                            "id": job_id,
                            "title": re.sub(r"<[^>]+>", "", title),
                            "company": (r.get("company") or {}).get("display_name", "Unknown"),
                            "location": (r.get("location") or {}).get("display_name", country.upper()),
                            "country": country.upper(),
                            "source": "Adzuna",
                            "link": r.get("redirect_url", ""),
                            "posted": r.get("created", ""),
                            "matched_keyword": kw,
                            "remote_mention": bool(REMOTE_HINTS.search(blob)),
                            "visa_mention": bool(VISA_HINTS.search(desc)),
                            "contract_mention": bool(CONTRACT_HINTS.search(blob)),
                            "relevant_experience": relevant_experience(title, desc),
                        }
                    time.sleep(0.25)
    else:
        print("Skipping Adzuna -- ADZUNA_APP_ID / ADZUNA_APP_KEY not set.")

    if JOOBLE_APP_KEY:
        print(f"Jooble: {len(JOOBLE_LOCATIONS)} locations x "
              f"{len(KEYWORD_GROUPS)} keywords (Gulf / Pakistan / SE Asia)...")
        for location in JOOBLE_LOCATIONS:
            for kw in KEYWORD_GROUPS:
                results = fetch_jooble(kw, location)
                if results:
                    print(f"  jooble {location}/{kw!r}: {len(results)}")
                for r in results:
                    job_id = "jooble-" + str(r.get("id") or r.get("link") or "")
                    if job_id == "jooble-" or job_id in all_jobs:
                        continue
                    title = (r.get("title") or "").strip()
                    desc = r.get("snippet", "") or ""
                    blob = f"{title} {desc}"
                    all_jobs[job_id] = {
                        "id": job_id,
                        "title": re.sub(r"<[^>]+>", "", title),
                        "company": r.get("company") or "Unknown",
                        "location": r.get("location") or location,
                        "country": location,
                        "source": "Jooble",
                        "link": r.get("link", ""),
                        "posted": r.get("updated", ""),
                        "matched_keyword": kw,
                        "remote_mention": bool(REMOTE_HINTS.search(blob)),
                        "visa_mention": bool(VISA_HINTS.search(desc)),
                        "contract_mention": bool(CONTRACT_HINTS.search(blob)),
                        "relevant_experience": relevant_experience(title, desc),
                    }
                time.sleep(0.25)
    else:
        print("Skipping Jooble -- JOOBLE_APP_KEY not set. Without it there "
              "is NO Gulf/GCC or Pakistan coverage; Adzuna has no index for "
              "either. Free key: https://jooble.org/api/about")

    jobs = []
    for j in all_jobs.values():
        age = days_old(j.get("posted", ""))
        if age is not None and age > MAX_AGE_DAYS:
            continue
        j["region"] = region_of(j["country"])
        j["score"] = score_job(j)
        jobs.append(j)
    return jobs


# ---------------------------------------------------------------------------
# PORTAL
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Search — Daily Status</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #12181F;
    --panel: #1B232D;
    --panel-hover: #212B36;
    --border: #2A343F;
    --text: #E8ECEF;
    --text-muted: #8B98A5;
    --amber: #F0A83D;
    --teal: #4FB8A8;
    --violet: #A78BC9;
    --rose: #D98E8E;
    --font-mono: 'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, monospace;
    --font-sans: 'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: var(--font-sans); line-height: 1.5;
  }
  a { color: inherit; }
  .wrap { max-width: 900px; margin: 0 auto; padding: 28px 20px 80px; }

  .status-bar {
    display: flex; flex-wrap: wrap; justify-content: space-between;
    align-items: center; gap: 12px; padding: 16px 20px;
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; margin-bottom: 18px;
  }
  .status-left { display: flex; align-items: center; gap: 10px; }
  .dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--teal); box-shadow: 0 0 0 4px rgba(79,184,168,0.15);
  }
  .status-label {
    font-family: var(--font-mono); font-size: 13px;
    letter-spacing: 0.06em; font-weight: 500;
  }
  .status-right {
    display: flex; flex-wrap: wrap; gap: 16px;
    font-family: var(--font-mono); font-size: 12px; color: var(--text-muted);
  }
  .status-right .hl { color: var(--amber); font-weight: 600; }

  .tabs { display: flex; gap: 8px; margin-bottom: 10px; overflow-x: auto;
          -webkit-overflow-scrolling: touch; scrollbar-width: none; }
  .tabs::-webkit-scrollbar { display: none; }
  .subtabs { display: flex; gap: 6px; margin-bottom: 20px; overflow-x: auto;
             -webkit-overflow-scrolling: touch; scrollbar-width: none;
             padding-left: 4px; border-left: 2px solid var(--border); }
  .subtabs::-webkit-scrollbar { display: none; }
  .chip {
    font-family: var(--font-mono); font-size: 12px; background: transparent;
    color: var(--text-muted); border: 1px solid var(--border);
    padding: 6px 12px; border-radius: 999px; cursor: pointer;
    white-space: nowrap; flex: 0 0 auto;
  }
  .chip.sub { font-size: 11px; padding: 4px 10px; opacity: 0.85; }
  .chip:hover { border-color: var(--teal); color: var(--text); }
  .chip.active { background: var(--teal); border-color: var(--teal);
                 color: #0B1319; font-weight: 600; }
  .chip:focus-visible, .ticket-apply:focus-visible, summary:focus-visible,
  .sitelink:focus-visible { outline: 2px solid var(--amber); outline-offset: 2px; }

  .ticket {
    display: flex; gap: 12px; background: var(--panel);
    border: 1px solid var(--border); border-radius: 10px;
    padding: 16px 18px; margin-bottom: 12px;
  }
  .ticket:hover { background: var(--panel-hover); }
  .ticket-status { flex: 0 0 auto; padding-top: 5px; }
  .ticket-status .dot { background: var(--amber); box-shadow: 0 0 0 4px rgba(240,168,61,0.15); }
  .ticket-body { flex: 1 1 auto; min-width: 0; }
  .ticket-head { display: flex; flex-wrap: wrap; justify-content: space-between;
                 align-items: baseline; gap: 8px 12px; }
  .ticket-title { font-size: 16px; font-weight: 600; margin: 0; }
  .badges { display: flex; gap: 6px; flex-wrap: wrap; }
  .badge {
    font-family: var(--font-mono); font-size: 10.5px; letter-spacing: 0.04em;
    padding: 3px 8px; border-radius: 5px; font-weight: 600; white-space: nowrap;
  }
  .badge-remote   { background: rgba(79,184,168,0.15);  color: var(--teal); }
  .badge-visa     { background: rgba(167,139,196,0.18); color: var(--violet); }
  .badge-contract { background: rgba(217,142,142,0.16); color: var(--rose); }

  .ticket-meta { font-family: var(--font-mono); font-size: 12px;
                 color: var(--text-muted); margin-top: 6px; }
  .country-tag { color: var(--amber); font-weight: 600; }

  .ticket-experience { margin-top: 10px; }
  .ticket-experience summary { cursor: pointer; font-size: 13px;
                               color: var(--amber); font-weight: 500; }
  .ticket-experience ul { margin: 8px 0 0; padding-left: 18px;
                          font-size: 13.5px; color: var(--text); }
  .ticket-experience li { margin-bottom: 6px; }

  .ticket-apply {
    display: inline-block; margin-top: 12px; font-family: var(--font-mono);
    font-size: 12.5px; font-weight: 600; text-decoration: none;
    color: var(--bg); background: var(--amber); padding: 7px 14px;
    border-radius: 6px;
  }
  .ticket-apply:hover { opacity: 0.9; }

  /* --- Job Sites launcher --- */
  .launcher-intro {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 18px; margin-bottom: 16px;
    font-size: 13.5px; color: var(--text-muted);
  }
  .launcher-intro strong { color: var(--text); }
  .term-row { margin-bottom: 20px; }
  .term-label {
    font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.08em;
    color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase;
  }
  .sitegroup {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 18px; margin-bottom: 12px;
  }
  .sitegroup h3 { margin: 0 0 4px; font-size: 15px; }
  .sitegroup .blurb { font-size: 12.5px; color: var(--text-muted); margin: 0 0 12px; }
  .sitelinks { display: flex; flex-wrap: wrap; gap: 8px; }
  .sitelink {
    font-family: var(--font-mono); font-size: 12px; text-decoration: none;
    border: 1px solid var(--border); border-radius: 6px;
    padding: 7px 11px; color: var(--text); background: rgba(255,255,255,0.02);
    display: inline-flex; align-items: center; gap: 7px;
  }
  .sitelink:hover { border-color: var(--teal); background: var(--panel-hover); }
  .conf { width: 6px; height: 6px; border-radius: 50%; flex: 0 0 auto;
          display: inline-block; }
  .conf-verified { background: var(--teal); }
  .conf-standard { background: var(--amber); }
  .conf-landing  { background: var(--text-muted); }
  .sitenote { font-size: 11.5px; color: var(--text-muted); margin-top: 10px;
              padding-left: 2px; border-left: 2px solid var(--border);
              padding: 4px 0 4px 8px; }
  .legend { font-family: var(--font-mono); font-size: 11px;
            color: var(--text-muted); margin: 14px 0 0;
            display: flex; gap: 16px; flex-wrap: wrap; }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }

  .empty { text-align: center; padding: 60px 20px; color: var(--text-muted);
           font-family: var(--font-mono); font-size: 13px; line-height: 1.8; }

  footer { margin-top: 28px; font-family: var(--font-mono); font-size: 11px;
           color: var(--text-muted); text-align: center; }

  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>
<div class="wrap">

  <div class="status-bar">
    <div class="status-left">
      <span class="dot"></span>
      <span class="status-label">JOB SEARCH — STATUS: ACTIVE</span>
    </div>
    <div class="status-right">
      <span>Last sync: __GENERATED_AT__</span>
      <span>Uptime: 18 yrs, 0 unplanned gaps</span>
      <span class="hl">__COUNT__ matches</span>
    </div>
  </div>

  <nav class="tabs" id="tabs">
    <button class="chip active" data-tab="all">All</button>
    <button class="chip" data-tab="remote">Remote</button>
    <button class="chip" data-tab="contract">Contract</button>
    <button class="chip" data-tab="visa">Visa Sponsor</button>
    <button class="chip" data-tab="region">Region</button>
    <button class="chip" data-tab="role">Role</button>
    <button class="chip" data-tab="latest">Latest</button>
    <button class="chip" data-tab="sites">⌕ Job Sites</button>
  </nav>
  <nav class="subtabs" id="subtabs" style="display:none;"></nav>

  <div id="list"></div>

  <footer>Generated __GENERATED_AT__ · searches and links, never auto-applies · edit job_search.py / job_sites.py to change scope</footer>
</div>

<script>
const JOBS = __JOBS_JSON__;
const SITES = __SITES_JSON__;

/* ------------------------------------------------------------------ */
/* helpers                                                             */
/* ------------------------------------------------------------------ */
function daysAgo(iso) {
  if (!iso) return Infinity;
  const d = new Date(iso);
  return isNaN(d) ? Infinity : (Date.now() - d.getTime()) / 86400000;
}
function fmtDate(iso) {
  const days = daysAgo(iso);
  if (!isFinite(days)) return "date unknown";
  const whole = Math.floor(days);
  if (whole <= 0) return "today";
  if (whole === 1) return "1 day ago";
  return whole + " days ago";
}
function countBy(arr) {
  const counts = {};
  arr.forEach(v => { if (v) counts[v] = (counts[v] || 0) + 1; });
  return counts;
}
function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
function slugify(term) {
  return term.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
function buildUrl(tpl, term) {
  return tpl
    .replace(/\{kw_slug_space\}/g, encodeURIComponent(term.toLowerCase()))
    .replace(/\{kw_slug\}/g, slugify(term))
    .replace(/\{kw_plus\}/g, encodeURIComponent(term).replace(/%20/g, "+"))
    .replace(/\{kw\}/g, encodeURIComponent(term));
}

/* Role groups consolidate raw search keywords into cleaner tabs.
   Keep in step with KEYWORD_GROUPS in job_search.py. */
const ROLE_GROUPS = {
  "SAP Concur": ["SAP Concur", "Concur consultant", "Concur implementation",
                 "travel and expense system"],
  "Support & ITSM": ["IT support manager", "ITSM manager",
                     "application support manager", "service desk manager",
                     "IT service delivery manager"],
  "Program & Project": ["IT program manager", "IT project manager"],
  "Document Management": ["document management systems"],
  "SAP / Integration": ["SAP functional consultant"],
  "Contract & Freelance": ["IT contract consultant", "freelance SAP consultant"],
};
function roleGroupOf(keyword) {
  for (const [name, kws] of Object.entries(ROLE_GROUPS)) {
    if (kws.includes(keyword)) return name;
  }
  return "Other";
}

const regionCounts = countBy(JOBS.map(j => j.region));
const REGIONS_PRESENT = Object.keys(regionCounts)
  .sort((a, b) => regionCounts[b] - regionCounts[a]);
const roleCounts = countBy(JOBS.map(j => roleGroupOf(j.matched_keyword)));
const ROLES_PRESENT = Object.keys(roleCounts)
  .sort((a, b) => roleCounts[b] - roleCounts[a]);

let state = { primary: 'all', secondary: null, term: SITES.terms[0] };

function matchesPrimary(job) {
  switch (state.primary) {
    case 'remote':   return job.remote_mention;
    case 'contract': return job.contract_mention;
    case 'visa':     return job.visa_mention;
    case 'latest':   return daysAgo(job.posted) <= 3;
    case 'region':   return state.secondary ? job.region === state.secondary : true;
    case 'role':     return state.secondary ? roleGroupOf(job.matched_keyword) === state.secondary : true;
    default:         return true;
  }
}

/* ------------------------------------------------------------------ */
/* rendering                                                           */
/* ------------------------------------------------------------------ */
function renderSubtabs() {
  const el = document.getElementById('subtabs');
  let items = null;
  if (state.primary === 'region')
    items = REGIONS_PRESENT.map(r => [r, `${r} (${regionCounts[r]})`]);
  if (state.primary === 'role')
    items = ROLES_PRESENT.map(r => [r, `${r} (${roleCounts[r]})`]);
  if (state.primary === 'sites')
    items = SITES.terms.map(t => [t, t]);
  if (!items || !items.length) {
    el.style.display = 'none'; el.innerHTML = ''; return;
  }
  const active = state.primary === 'sites' ? state.term : state.secondary;
  el.style.display = 'flex';
  el.innerHTML = items.map(([value, label]) =>
    `<button class="chip sub ${active === value ? 'active' : ''}" data-sub="${esc(value)}">${esc(label)}</button>`
  ).join('');
}

function card(job) {
  const badges = [
    job.remote_mention   ? '<span class="badge badge-remote">REMOTE</span>' : '',
    job.contract_mention ? '<span class="badge badge-contract">CONTRACT</span>' : '',
    job.visa_mention     ? '<span class="badge badge-visa">VISA MENTION</span>' : '',
  ].join('');
  const exp = (job.relevant_experience || []).map(e => `<li>${esc(e)}</li>`).join('');
  const expBlock = exp ? `
    <details class="ticket-experience">
      <summary>Why you're a fit</summary>
      <ul>${exp}</ul>
    </details>` : '';
  return `
    <article class="ticket">
      <div class="ticket-status"><span class="dot"></span></div>
      <div class="ticket-body">
        <div class="ticket-head">
          <h2 class="ticket-title">${esc(job.title) || 'Untitled listing'}</h2>
          <div class="badges">${badges}</div>
        </div>
        <div class="ticket-meta"><span class="country-tag">${esc(job.region || job.country || '—')}</span> · ${esc(job.company)} · ${esc(job.location)} · posted ${fmtDate(job.posted)} · via ${esc(job.source || '—')} · matched: ${esc(job.matched_keyword)}</div>
        ${expBlock}
        <a class="ticket-apply" href="${esc(job.link)}" target="_blank" rel="noopener">Open listing →</a>
      </div>
    </article>`;
}

function renderSites() {
  const term = state.term;
  const groups = SITES.groups.map(g => {
    const links = g.sites.map(s => `
      <a class="sitelink" href="${esc(buildUrl(s.url, term))}" target="_blank" rel="noopener"
         title="${esc(s.note || '')}">
        <span class="conf conf-${esc(s.confidence)}"></span>${esc(s.name)}
      </a>`).join('');
    const notes = g.sites.filter(s => s.note).map(s =>
      `<div class="sitenote"><strong>${esc(s.name)}</strong> — ${esc(s.note)}</div>`
    ).join('');
    return `
      <section class="sitegroup">
        <h3>${esc(g.group)}</h3>
        <p class="blurb">${esc(g.blurb)}</p>
        <div class="sitelinks">${links}</div>
        ${notes}
      </section>`;
  }).join('');

  return `
    <div class="launcher-intro">
      Every link below runs a live search for <strong>“${esc(term)}”</strong> on that
      site, pre-filtered where the site allows it (last 7 days, newest first, remote-only
      where relevant). Pick a different term from the row above.
      <div class="legend">
        <span><i class="conf conf-verified"></i> URL format checked live</span>
        <span><i class="conf conf-standard"></i> site's standard search form</span>
        <span><i class="conf conf-landing"></i> search page — type the term there</span>
      </div>
    </div>
    ${groups}`;
}

function render() {
  renderSubtabs();
  const list = document.getElementById('list');

  if (state.primary === 'sites') { list.innerHTML = renderSites(); return; }

  const filtered = JOBS.filter(matchesPrimary)
                       .sort((a, b) => (b.score || 0) - (a.score || 0));
  if (filtered.length === 0) {
    list.innerHTML = `<div class="empty">
      No listings in this view yet.<br>
      Try the <strong>⌕ Job Sites</strong> tab — those searches always work,<br>
      even on a day the APIs return nothing.
    </div>`;
    return;
  }
  list.innerHTML = filtered.map(card).join('');
}

document.getElementById('tabs').addEventListener('click', (e) => {
  const btn = e.target.closest('.chip');
  if (!btn) return;
  document.querySelectorAll('#tabs .chip').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  state.primary = btn.dataset.tab;
  state.secondary = state.primary === 'region' ? (REGIONS_PRESENT[0] || null)
                  : state.primary === 'role'   ? (ROLES_PRESENT[0] || null)
                  : null;
  render();
});

document.getElementById('subtabs').addEventListener('click', (e) => {
  const btn = e.target.closest('.chip');
  if (!btn) return;
  if (state.primary === 'sites') state.term = btn.dataset.sub;
  else state.secondary = btn.dataset.sub;
  render();
});

render();
</script>
</body>
</html>
"""


def build_html(jobs: list[dict]) -> str:
    # Stable two-pass sort: newest first, then highest score first.
    jobs_sorted = sorted(jobs, key=lambda j: j.get("posted", ""), reverse=True)
    jobs_sorted = sorted(jobs_sorted, key=lambda j: j.get("score", 0), reverse=True)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = HTML_TEMPLATE
    html = html.replace("__JOBS_JSON__", json.dumps(jobs_sorted))
    html = html.replace("__SITES_JSON__", json.dumps(as_portal_data()))
    html = html.replace("__GENERATED_AT__", generated_at)
    html = html.replace("__COUNT__", str(len(jobs_sorted)))
    return html


def main() -> None:
    jobs = [] if DEMO_MODE else collect_jobs()
    if DEMO_MODE:
        print("DEMO=1 -- skipping all API calls, building portal shell only.")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(build_html(jobs))

    remote = sum(1 for j in jobs if j.get("remote_mention"))
    contract = sum(1 for j in jobs if j.get("contract_mention"))
    visa = sum(1 for j in jobs if j.get("visa_mention"))
    print(f"\nDone — {len(jobs)} listing(s): {remote} remote, "
          f"{contract} contract, {visa} with a visa/sponsorship mention.")
    print(f"Wrote {OUTPUT_HTML} and {OUTPUT_JSON}.")


if __name__ == "__main__":
    main()
