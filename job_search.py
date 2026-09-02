#!/usr/bin/env python3
"""
Daily Job Search Agent  --  v3
==============================
Searches for roles matching Muhammad Wasim Abbas's background, scores them
remote-first, attaches the relevant part of the resume to each, and rebuilds
a static portal (index.html) navigated on two axes: MARKET and ROLE.

WHAT CHANGED IN v3
------------------
1. NAVIGATION REBUILT. Market is the primary axis (Remote / Contract /
   Gulf / SEA / ANZ / Pakistan / West), role is the secondary axis
   (Concur / App Support / Service Delivery / DMS / Programme). Pick both
   and the page shows the live listings AND the sites to search for that
   exact combination -- previously those were two unrelated tabs.
2. SAP ERP REMOVED. Keywords for generic SAP work are gone, and
   `is_sap_erp_noise()` actively drops SAP ERP / S/4HANA / ABAP / FICO /
   MM / SD / BASIS listings that have nothing to do with Concur.
3. A listing can belong to several markets at once -- a remote contract
   role in Dubai appears under Remote, Contract and Gulf.
4. Keywords now derive from ROLES in job_sites.py, so the crawl and the
   role tabs cannot drift apart.
5. Document Management widened to cover EDMS implementation as well as
   support.

DATA SOURCES
------------
- Adzuna  (https://developer.adzuna.com)  free key, ~19 country indexes.
- Jooble  (https://jooble.org/api/about)  free key, free-text location.
  Jooble is the ONLY source covering the Gulf and Pakistan -- Adzuna has
  no index for either.

LinkedIn / Indeed / Glassdoor have no public job API for individuals, so
they are covered by the deep-link launcher rather than fetched. See
job_sites.py.
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from urllib.parse import quote
from datetime import datetime, timezone

from job_sites import as_portal_data, all_keywords, ROLES, role_of_keyword

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

APP_ID = os.environ.get("ADZUNA_APP_ID", "")
APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
JOOBLE_APP_KEY = os.environ.get("JOOBLE_APP_KEY", "")

DEMO_MODE = os.environ.get("DEMO", "") == "1"

COUNTRIES = [
    "gb", "us", "ca", "au", "nz", "sg", "in",
    "de", "nl", "fr", "es", "it", "at", "ch", "be", "pl", "za",
]

JOOBLE_LOCATIONS = [
    "United Arab Emirates", "Dubai", "Abu Dhabi",
    "Saudi Arabia", "Riyadh", "Jeddah",
    "Qatar", "Kuwait", "Bahrain", "Oman", "Jordan", "Egypt",
    "Pakistan", "Lahore", "Karachi", "Islamabad",
    "Singapore", "Malaysia", "Hong Kong", "Thailand",
    "Indonesia", "Philippines", "Vietnam",
    "Australia", "New Zealand",
    "Remote",
]

# Derived from ROLES in job_sites.py -- edit roles there, not here.
KEYWORD_GROUPS = all_keywords()

RESULTS_PER_QUERY = 20
MAX_PAGES = 1
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

# --- SAP ERP exclusion ------------------------------------------------------
# You have no SAP ERP experience, so ERP listings are noise. A listing is
# dropped if it looks like core SAP ERP work AND never mentions Concur.
SAP_ERP_NOISE = re.compile(
    r"\bs/?4\s*hana\b|\babap\b|\bfico?\b|\bsap\s+(mm|sd|pp|hcm|hr|bw|basis|crm|ewm|le|pm|qm)\b|"
    r"\bsap\s+erp\b|\bsap\s+business\s+one\b|\becc\s*6\b|\bsap\s+successfactors\b|"
    r"\bsap\s+ariba\b|\bsap\s+fiori\b",
    re.IGNORECASE,
)
CONCUR_MENTION = re.compile(r"concur|travel\s*(&|and)\s*expense|\bt&e\b", re.IGNORECASE)


def is_sap_erp_noise(title: str, description: str) -> bool:
    blob = f"{title} {description}"
    if CONCUR_MENTION.search(blob):
        return False
    return bool(SAP_ERP_NOISE.search(blob))


# --- markets ----------------------------------------------------------------

GEO_MARKETS = {
    "gcc": {"United Arab Emirates", "Dubai", "Abu Dhabi", "Saudi Arabia",
            "Riyadh", "Jeddah", "Qatar", "Kuwait", "Bahrain", "Oman",
            "Jordan", "Egypt"},
    "sea": {"SG", "Singapore", "Malaysia", "Hong Kong", "Thailand",
            "Indonesia", "Philippines", "Vietnam", "IN"},
    "anz": {"AU", "NZ", "Australia", "New Zealand"},
    "pk":  {"Pakistan", "Lahore", "Karachi", "Islamabad"},
    "west": {"GB", "DE", "NL", "FR", "ES", "IT", "AT", "CH", "BE", "PL",
             "US", "CA", "ZA"},
}


def geo_market_of(country: str) -> str:
    for market, members in GEO_MARKETS.items():
        if country in members:
            return market
    return ""


def markets_of(job: dict) -> list[str]:
    """A listing can sit in several markets at once."""
    out = []
    if job.get("remote_mention"):
        out.append("remote")
    if job.get("contract_mention"):
        out.append("contract")
    geo = geo_market_of(job.get("country", ""))
    if geo:
        out.append(geo)
    return out


OUTPUT_JSON = "jobs.json"
OUTPUT_HTML = "index.html"

# ---------------------------------------------------------------------------
# YOUR EXPERIENCE, keyed for matching. Edit freely; it's yours.
# NOTE: no SAP ERP / S/4HANA claims anywhere -- you don't have that
# experience and shouldn't be shown as claiming it.
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
        "Primary point of contact for SAP Concur import and integration "
        "error resolution across 30,000+ enterprise users "
        "(TEXLA Technologies, 2021-2024).",
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
        "Built Concur-to-finance posting integrations (GL, tax and "
        "cost-object mapping) plus enterprise SSO and HRIS data feeds.",
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
}


def relevant_experience(title: str, description: str) -> list[str]:
    text = f"{title} {description}".lower()
    hits: list[str] = []
    if "concur" in text or "travel and expense" in text or "t&e" in text:
        hits += EXPERIENCE_BANK["concur"]
    if any(k in text for k in ("itsm", "service management", "servicenow",
                               "itil", "service desk", "incident manage")):
        hits += EXPERIENCE_BANK["itsm"]
    if "application support" in text or "support manager" in text:
        hits += EXPERIENCE_BANK["application support"]
    if "document management" in text or re.search(r"\b(dms|edms)\b", text):
        hits += EXPERIENCE_BANK["document management"]
    if any(k in text for k in ("it manager", "program manager",
                               "programme manager", "project manager",
                               "it support", "delivery manager",
                               "operations manager")):
        hits += EXPERIENCE_BANK["it manager"]
    if "integration" in text or "interface" in text:
        hits += EXPERIENCE_BANK["integration"]
    if any(k in text for k in ("consultant", "consulting", "advisory",
                               "implementation partner")):
        hits += EXPERIENCE_BANK["consulting"]

    seen, out = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out[:3]


# ---------------------------------------------------------------------------
# SCORING -- remote first, relocation as backup
# ---------------------------------------------------------------------------

STRONG_TITLE_TERMS = (
    "concur", "expense", "itsm", "service management", "application support",
    "support manager", "service delivery", "it manager", "program manager",
    "programme manager", "document management", "operations manager",
)


def days_old(iso: str):
    if not iso:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(iso, fmt)
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


def score_job(job: dict) -> int:
    score = 0
    title = (job.get("title") or "").lower()

    if job.get("remote_mention"):
        score += 40
    if job.get("contract_mention"):
        score += 15
    if job.get("visa_mention"):
        score += 12

    if any(t in title for t in STRONG_TITLE_TERMS):
        score += 25
    if "concur" in title:
        score += 20          # your single most differentiated skill
    if any(t in title for t in ("senior", "lead", "head of", "manager")):
        score += 6

    score += 5 * len(job.get("relevant_experience", []))

    for m in job.get("markets", []):
        score += {"gcc": 8, "sea": 8, "anz": 5, "west": 4, "pk": 3}.get(m, 0)

    d = days_old(job.get("posted", ""))
    if d is not None:
        if d <= 2:
            score += 12
        elif d <= 7:
            score += 6
        elif d > 30:
            score -= 8

    return score


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
    req = urllib.request.Request(url, headers={"User-Agent": "job-search-agent/3.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read()[:160].decode("utf-8", "replace")
        print(f"  [warn] adzuna {country}/{query!r}: HTTP {e.code} -- {body}")
        return {"results": []}
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] adzuna {country}/{query!r}: {e}")
        return {"results": []}


def fetch_jooble(keyword: str, location: str) -> list[dict]:
    url = f"https://jooble.org/api/{JOOBLE_APP_KEY}"
    payload = json.dumps({"keywords": keyword, "location": location}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json",
                 "User-Agent": "job-search-agent/3.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8")).get("jobs", []) or []
    except urllib.error.HTTPError as e:
        print(f"  [warn] jooble {location}/{keyword!r}: HTTP {e.code} -- "
              f"{e.read()[:160].decode('utf-8', 'replace')}")
        return []
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] jooble {location}/{keyword!r}: {e}")
        return []


def collect_jobs() -> list[dict]:
    all_jobs: dict[str, dict] = {}
    erp_dropped = 0

    if APP_ID and APP_KEY:
        total = len(COUNTRIES) * len(KEYWORD_GROUPS) * MAX_PAGES
        print(f"Adzuna: {len(COUNTRIES)} countries x {len(KEYWORD_GROUPS)} "
              f"keywords = up to {total} calls...")
        for country in COUNTRIES:
            for kw in KEYWORD_GROUPS:
                for page in range(1, MAX_PAGES + 1):
                    for r in fetch_adzuna(country, kw, page).get("results", []):
                        job_id = str(r.get("id") or r.get("redirect_url") or "")
                        if not job_id or job_id in all_jobs:
                            continue
                        title = re.sub(r"<[^>]+>", "", (r.get("title") or "").strip())
                        desc = r.get("description", "") or ""
                        if is_sap_erp_noise(title, desc):
                            erp_dropped += 1
                            continue
                        blob = f"{title} {desc}"
                        all_jobs[job_id] = {
                            "id": job_id,
                            "title": title,
                            "company": (r.get("company") or {}).get("display_name", "Unknown"),
                            "location": (r.get("location") or {}).get("display_name", country.upper()),
                            "country": country.upper(),
                            "source": "Adzuna",
                            "link": r.get("redirect_url", ""),
                            "posted": r.get("created", ""),
                            "matched_keyword": kw,
                            "role": role_of_keyword(kw),
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
                for r in fetch_jooble(kw, location):
                    job_id = "jooble-" + str(r.get("id") or r.get("link") or "")
                    if job_id == "jooble-" or job_id in all_jobs:
                        continue
                    title = re.sub(r"<[^>]+>", "", (r.get("title") or "").strip())
                    desc = r.get("snippet", "") or ""
                    if is_sap_erp_noise(title, desc):
                        erp_dropped += 1
                        continue
                    blob = f"{title} {desc}"
                    all_jobs[job_id] = {
                        "id": job_id,
                        "title": title,
                        "company": r.get("company") or "Unknown",
                        "location": r.get("location") or location,
                        "country": location,
                        "source": "Jooble",
                        "link": r.get("link", ""),
                        "posted": r.get("updated", ""),
                        "matched_keyword": kw,
                        "role": role_of_keyword(kw),
                        "remote_mention": bool(REMOTE_HINTS.search(blob)),
                        "visa_mention": bool(VISA_HINTS.search(desc)),
                        "contract_mention": bool(CONTRACT_HINTS.search(blob)),
                        "relevant_experience": relevant_experience(title, desc),
                    }
                time.sleep(0.25)
    else:
        print("Skipping Jooble -- JOOBLE_APP_KEY not set. Without it there is "
              "NO Gulf/GCC or Pakistan coverage. Free key: "
              "https://jooble.org/api/about")

    jobs = []
    for j in all_jobs.values():
        age = days_old(j.get("posted", ""))
        if age is not None and age > MAX_AGE_DAYS:
            continue
        j["markets"] = markets_of(j)
        j["score"] = score_job(j)
        jobs.append(j)

    print(f"\nDropped {erp_dropped} SAP ERP / S4HANA listing(s) as out of scope.")
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
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #12181F; --panel: #1B232D; --panel-2: #212B36; --panel-3: #26313D;
    --border: #2A343F; --border-2: #35414E;
    --text: #E8ECEF; --muted: #8B98A5;
    --amber: #F0A83D; --teal: #4FB8A8; --violet: #A78BC9; --rose: #D98E8E;
    --mono: 'IBM Plex Mono', ui-monospace, Menlo, monospace;
    --sans: 'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif;
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
         font-family:var(--sans); line-height:1.5; }
  a { color: inherit; }
  .wrap { max-width: 960px; margin: 0 auto; padding: 22px 18px 80px; }

  /* ---------- status ---------- */
  .status {
    display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center;
    gap:12px; padding:14px 18px; background:var(--panel);
    border:1px solid var(--border); border-radius:10px; margin-bottom:16px;
  }
  .status-l { display:flex; align-items:center; gap:10px; }
  .dot { width:9px; height:9px; border-radius:50%; background:var(--teal);
         box-shadow:0 0 0 4px rgba(79,184,168,.15); flex:0 0 auto; }
  .status-label { font-family:var(--mono); font-size:12.5px; letter-spacing:.06em; font-weight:500; }
  .status-r { display:flex; flex-wrap:wrap; gap:14px; font-family:var(--mono);
              font-size:11.5px; color:var(--muted); }
  .status-r .hl { color:var(--amber); font-weight:600; }

  /* ---------- nav ---------- */
  .navbar { background:var(--panel); border:1px solid var(--border);
            border-radius:10px; padding:12px 14px; margin-bottom:16px; }
  .navrow { display:flex; gap:7px; overflow-x:auto; scrollbar-width:none;
            -webkit-overflow-scrolling:touch; padding-bottom:2px; }
  .navrow::-webkit-scrollbar { display:none; }
  .navrow + .navrow { margin-top:10px; padding-top:10px; border-top:1px solid var(--border); }
  .navlabel { font-family:var(--mono); font-size:9.5px; letter-spacing:.13em;
              text-transform:uppercase; color:var(--muted); margin-bottom:6px; }

  .chip {
    font-family:var(--mono); font-size:12px; background:transparent; color:var(--muted);
    border:1px solid var(--border-2); padding:7px 12px; border-radius:7px;
    cursor:pointer; white-space:nowrap; flex:0 0 auto;
    display:inline-flex; align-items:center; gap:7px;
  }
  .chip:hover { border-color:var(--teal); color:var(--text); }
  .chip.active { background:var(--teal); border-color:var(--teal); color:#0B1319; font-weight:600; }
  .chip .n { font-size:10.5px; opacity:.75; font-variant-numeric:tabular-nums; }
  .chip.active .n { opacity:.8; }
  .chip.role.active { background:var(--amber); border-color:var(--amber); color:#1A1206; }
  .chip.tog { font-size:11.5px; padding:5px 10px; border-radius:99px; }
  .chip.tog.active { background:var(--violet); border-color:var(--violet); color:#161020; }
  .chip.term { font-size:11px; padding:4px 9px; border-radius:99px; }
  .chip.term.active { background:var(--panel-3); border-color:var(--teal); color:var(--text); font-weight:600; }
  .chip:focus-visible, .sitelink:focus-visible, .apply:focus-visible, summary:focus-visible {
    outline:2px solid var(--amber); outline-offset:2px; }

  /* ---------- context header ---------- */
  .context { margin: 4px 0 16px; }
  .context h1 { font-size:20px; margin:0 0 5px; font-weight:600; letter-spacing:-.01em; }
  .context p { margin:0; color:var(--muted); font-size:13.5px; max-width:70ch; }

  /* ---------- sites panel ---------- */
  .sites { background:var(--panel); border:1px solid var(--border);
           border-radius:10px; padding:15px 17px; margin-bottom:18px; }
  .sites-head { display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 12px; margin-bottom:11px; }
  .sites-head h2 { font-size:14px; margin:0; font-weight:600; }
  .sites-head .sub { font-family:var(--mono); font-size:11px; color:var(--muted); }
  .termrow { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; align-items:center; }
  .termrow .lbl { font-family:var(--mono); font-size:10px; letter-spacing:.1em;
                  text-transform:uppercase; color:var(--muted); margin-right:2px; }
  .sitelinks { display:flex; flex-wrap:wrap; gap:7px; }
  .sitelink {
    font-family:var(--mono); font-size:11.5px; text-decoration:none;
    border:1px solid var(--border-2); border-radius:6px; padding:7px 11px;
    color:var(--text); background:rgba(255,255,255,.02);
    display:inline-flex; align-items:center; gap:7px;
  }
  .sitelink:hover { border-color:var(--teal); background:var(--panel-2); }
  .conf { width:6px; height:6px; border-radius:50%; flex:0 0 auto; display:inline-block; }
  .conf-verified { background:var(--teal); }
  .conf-standard { background:var(--amber); }
  .conf-landing  { background:var(--muted); }
  .notes { margin-top:11px; display:flex; flex-direction:column; gap:6px; }
  .note { font-size:12px; color:var(--muted); border-left:2px solid var(--border-2);
          padding:2px 0 2px 9px; }
  .note b { color:var(--text); font-weight:600; }
  .legend { font-family:var(--mono); font-size:10.5px; color:var(--muted);
            margin-top:11px; display:flex; gap:14px; flex-wrap:wrap; }
  .legend span { display:inline-flex; align-items:center; gap:6px; }

  /* ---------- listings ---------- */
  .listhead { display:flex; flex-wrap:wrap; align-items:baseline; gap:10px;
              margin:0 0 11px; }
  .listhead h2 { font-size:14px; margin:0; font-weight:600; }
  .listhead .sub { font-family:var(--mono); font-size:11px; color:var(--muted); }

  .ticket { display:flex; gap:12px; background:var(--panel);
            border:1px solid var(--border); border-radius:10px;
            padding:15px 17px; margin-bottom:10px; }
  .ticket:hover { background:var(--panel-2); }
  .tstatus { flex:0 0 auto; padding-top:5px; }
  .tstatus .dot { background:var(--amber); box-shadow:0 0 0 4px rgba(240,168,61,.15); }
  .tbody { flex:1 1 auto; min-width:0; }
  .thead { display:flex; flex-wrap:wrap; justify-content:space-between;
           align-items:baseline; gap:7px 12px; }
  .ttitle { font-size:15.5px; font-weight:600; margin:0; }
  .badges { display:flex; gap:5px; flex-wrap:wrap; }
  .badge { font-family:var(--mono); font-size:10px; letter-spacing:.04em;
           padding:3px 7px; border-radius:5px; font-weight:600; white-space:nowrap; }
  .b-remote   { background:rgba(79,184,168,.15);  color:var(--teal); }
  .b-visa     { background:rgba(167,139,196,.18); color:var(--violet); }
  .b-contract { background:rgba(217,142,142,.16); color:var(--rose); }
  .tmeta { font-family:var(--mono); font-size:11.5px; color:var(--muted); margin-top:6px; }
  .tmeta .tag { color:var(--amber); font-weight:600; }
  details.why { margin-top:9px; }
  details.why summary { cursor:pointer; font-size:12.5px; color:var(--amber); font-weight:500; }
  details.why ul { margin:7px 0 0; padding-left:18px; font-size:13px; }
  details.why li { margin-bottom:5px; }
  .apply { display:inline-block; margin-top:11px; font-family:var(--mono);
           font-size:12px; font-weight:600; text-decoration:none; color:var(--bg);
           background:var(--amber); padding:7px 13px; border-radius:6px; }
  .apply:hover { opacity:.9; }

  .empty { text-align:center; padding:44px 20px; color:var(--muted);
           font-family:var(--mono); font-size:12.5px; line-height:1.9;
           background:var(--panel); border:1px dashed var(--border-2); border-radius:10px; }
  .more { display:block; width:100%; margin-top:6px; font-family:var(--mono);
          font-size:12px; background:var(--panel); color:var(--muted);
          border:1px solid var(--border-2); border-radius:8px; padding:11px;
          cursor:pointer; }
  .more:hover { border-color:var(--teal); color:var(--text); }

  footer { margin-top:26px; font-family:var(--mono); font-size:10.5px;
           color:var(--muted); text-align:center; }
  @media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
  @media (max-width: 560px) { .wrap { padding:16px 12px 60px; } .ttitle { font-size:15px; } }
</style>
</head>
<body>
<div class="wrap">

  <div class="status">
    <div class="status-l">
      <span class="dot"></span>
      <span class="status-label">JOB SEARCH — STATUS: ACTIVE</span>
    </div>
    <div class="status-r">
      <span>Last sync: __GENERATED_AT__</span>
      <span>Uptime: 18 yrs, 0 unplanned gaps</span>
      <span class="hl" id="totalcount">__COUNT__ matches</span>
    </div>
  </div>

  <div class="navbar">
    <div class="navlabel">Where — pick a market</div>
    <div class="navrow" id="marketrow"></div>
    <div class="navlabel" style="margin-top:12px;">What — pick a role</div>
    <div class="navrow" id="rolerow"></div>
    <div class="navrow" id="togglerow"></div>
  </div>

  <div class="context">
    <h1 id="ctxTitle"></h1>
    <p id="ctxBlurb"></p>
  </div>

  <section class="sites" id="sitesPanel"></section>

  <div class="listhead">
    <h2>Listings the agent found</h2>
    <span class="sub" id="listSub"></span>
  </div>
  <div id="list"></div>

  <footer>Generated __GENERATED_AT__ · searches and links, never auto-applies · SAP ERP roles excluded · edit job_search.py / job_sites.py to change scope</footer>
</div>

<script>
const JOBS  = __JOBS_JSON__;
const DATA  = __SITES_JSON__;
const MARKETS = DATA.markets;
const ROLES   = DATA.roles;

/* ---------------- helpers ---------------- */
function daysAgo(iso){ if(!iso) return Infinity; const d=new Date(iso);
  return isNaN(d)?Infinity:(Date.now()-d.getTime())/86400000; }
function fmtDate(iso){ const d=daysAgo(iso); if(!isFinite(d)) return "date unknown";
  const w=Math.floor(d); return w<=0?"today":w===1?"1 day ago":w+" days ago"; }
function esc(s){ return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;")
  .replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function slugify(t){ return t.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,""); }
function buildUrl(tpl, term){
  return tpl.replace(/\{kw_slug_space\}/g, encodeURIComponent(term.toLowerCase()))
            .replace(/\{kw_slug\}/g, slugify(term))
            .replace(/\{kw_plus\}/g, encodeURIComponent(term).replace(/%20/g,"+"))
            .replace(/\{kw\}/g, encodeURIComponent(term));
}

/* ---------------- state ---------------- */
let state = {
  market: "remote",
  role: "all",
  term: null,          // null = use the role's default site term
  remote: false, contract: false, visa: false, fresh: false,
  shown: 25
};

function marketOf(id){ return MARKETS.find(m => m.id === id); }
function roleOf(id){ return ROLES.find(r => r.id === id); }

function inMarket(j, id){ return (j.markets || []).indexOf(id) !== -1; }

function matches(j, opts){
  opts = opts || {};
  if (!opts.ignoreMarket && !inMarket(j, state.market)) return false;
  if (!opts.ignoreRole && state.role !== "all" && j.role !== state.role) return false;
  if (state.remote   && !j.remote_mention)   return false;
  if (state.contract && !j.contract_mention) return false;
  if (state.visa     && !j.visa_mention)     return false;
  if (state.fresh    && daysAgo(j.posted) > 3) return false;
  return true;
}

/* ---------------- nav ---------------- */
function renderNav(){
  document.getElementById("marketrow").innerHTML = MARKETS.map(m => {
    const n = JOBS.filter(j => inMarket(j, m.id) &&
      (state.role === "all" || j.role === state.role)).length;
    return `<button class="chip market ${state.market===m.id?"active":""}" data-market="${m.id}">
      <span>${esc(m.icon)}</span>${esc(m.label)}<span class="n">${n}</span></button>`;
  }).join("");

  const roleChips = [{id:"all", label:"All roles"}].concat(ROLES);
  document.getElementById("rolerow").innerHTML = roleChips.map(r => {
    const n = r.id === "all"
      ? JOBS.filter(j => inMarket(j, state.market)).length
      : JOBS.filter(j => inMarket(j, state.market) && j.role === r.id).length;
    return `<button class="chip role ${state.role===r.id?"active":""}" data-role="${r.id}">
      ${esc(r.label)}<span class="n">${n}</span></button>`;
  }).join("");

  const togs = [["remote","Remote only"],["contract","Contract only"],
                ["visa","Visa mention"],["fresh","Last 3 days"]];
  document.getElementById("togglerow").innerHTML = togs.map(([k,label]) =>
    `<button class="chip tog ${state[k]?"active":""}" data-tog="${k}">${esc(label)}</button>`
  ).join("");
}

/* ---------------- sites ---------------- */
function currentTerms(){
  if (state.role === "all") {
    return ROLES.map(r => r.term);
  }
  const r = roleOf(state.role);
  return [r.term].concat(r.altTerms || []);
}
function activeTerm(){
  const terms = currentTerms();
  return (state.term && terms.indexOf(state.term) !== -1) ? state.term : terms[0];
}

function renderSites(){
  const m = marketOf(state.market);
  const term = activeTerm();
  const terms = currentTerms();

  const termChips = terms.map(t =>
    `<button class="chip term ${t===term?"active":""}" data-term="${esc(t)}">${esc(t)}</button>`
  ).join("");

  const links = m.sites.map(s => `
    <a class="sitelink" href="${esc(buildUrl(s.url, term))}" target="_blank" rel="noopener"
       title="${esc(s.note||"")}"><span class="conf conf-${esc(s.confidence)}"></span>${esc(s.name)}</a>`
  ).join("");

  const notes = m.sites.filter(s => s.note).map(s =>
    `<div class="note"><b>${esc(s.name)}</b> — ${esc(s.note)}</div>`).join("");

  document.getElementById("sitesPanel").innerHTML = `
    <div class="sites-head">
      <h2>Search these sites — ${esc(m.label)}</h2>
      <span class="sub">${m.sites.length} sites · live results, one click</span>
    </div>
    <div class="termrow"><span class="lbl">term</span>${termChips}</div>
    <div class="sitelinks">${links}</div>
    <div class="notes">${notes}</div>
    <div class="legend">
      <span><i class="conf conf-verified"></i> checked live</span>
      <span><i class="conf conf-standard"></i> standard search form</span>
      <span><i class="conf conf-landing"></i> type the term there</span>
    </div>`;
}

/* ---------------- listings ---------------- */
function card(j){
  const badges = [
    j.remote_mention   ? '<span class="badge b-remote">REMOTE</span>' : '',
    j.contract_mention ? '<span class="badge b-contract">CONTRACT</span>' : '',
    j.visa_mention     ? '<span class="badge b-visa">VISA MENTION</span>' : '',
  ].join('');
  const exp = (j.relevant_experience||[]).map(e => `<li>${esc(e)}</li>`).join('');
  const why = exp ? `<details class="why"><summary>Why you're a fit — use this in your cover note</summary><ul>${exp}</ul></details>` : '';
  const r = roleOf(j.role);
  return `
    <article class="ticket">
      <div class="tstatus"><span class="dot"></span></div>
      <div class="tbody">
        <div class="thead">
          <h3 class="ttitle">${esc(j.title)||"Untitled listing"}</h3>
          <div class="badges">${badges}</div>
        </div>
        <div class="tmeta"><span class="tag">${esc(r?r.label:"Other")}</span> · ${esc(j.company)} · ${esc(j.location)} · posted ${fmtDate(j.posted)} · via ${esc(j.source||"—")}</div>
        ${why}
        <a class="apply" href="${esc(j.link)}" target="_blank" rel="noopener">Open listing →</a>
      </div>
    </article>`;
}

function renderList(){
  const list = document.getElementById("list");
  const all = JOBS.filter(j => matches(j)).sort((a,b) => (b.score||0)-(a.score||0));
  document.getElementById("listSub").textContent =
    all.length + (all.length === 1 ? " match" : " matches") + ", best fit first";

  if (!all.length){
    list.innerHTML = `<div class="empty">
      Nothing here right now.<br>
      The site links above still work — they search live, every time.<br>
      Or clear a filter, or try another market.
    </div>`;
    return;
  }
  const slice = all.slice(0, state.shown);
  list.innerHTML = slice.map(card).join("") +
    (all.length > state.shown
      ? `<button class="more" id="more">Show ${Math.min(25, all.length-state.shown)} more — ${all.length-state.shown} still hidden</button>`
      : "");
  const more = document.getElementById("more");
  if (more) more.addEventListener("click", () => { state.shown += 25; renderList(); });
}

/* ---------------- context ---------------- */
function renderContext(){
  const m = marketOf(state.market);
  const r = state.role === "all" ? null : roleOf(state.role);
  document.getElementById("ctxTitle").textContent =
    r ? `${r.label} — ${m.label}` : m.label;
  document.getElementById("ctxBlurb").textContent = r ? r.blurb : m.blurb;
}

function render(){ renderNav(); renderContext(); renderSites(); renderList(); }

/* ---------------- events ---------------- */
document.getElementById("marketrow").addEventListener("click", e => {
  const b = e.target.closest("[data-market]"); if(!b) return;
  state.market = b.dataset.market; state.shown = 25; render();
});
document.getElementById("rolerow").addEventListener("click", e => {
  const b = e.target.closest("[data-role]"); if(!b) return;
  state.role = b.dataset.role; state.term = null; state.shown = 25; render();
});
document.getElementById("togglerow").addEventListener("click", e => {
  const b = e.target.closest("[data-tog]"); if(!b) return;
  state[b.dataset.tog] = !state[b.dataset.tog]; state.shown = 25; render();
});
document.getElementById("sitesPanel").addEventListener("click", e => {
  const b = e.target.closest("[data-term]"); if(!b) return;
  state.term = b.dataset.term; renderSites();
});

render();
</script>
</body>
</html>
"""


def build_html(jobs: list[dict]) -> str:
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
        print("DEMO=1 -- no API calls, building the portal shell only.")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(build_html(jobs))

    if jobs:
        print("\nBy market:")
        for m in ("remote", "contract", "gcc", "sea", "anz", "pk", "west"):
            print(f"  {m:>9}: {sum(1 for j in jobs if m in j['markets'])}")
        print("By role:")
        for r in ROLES:
            print(f"  {r['id']:>16}: {sum(1 for j in jobs if j['role'] == r['id'])}")
    print(f"\nDone — {len(jobs)} listing(s). Wrote {OUTPUT_HTML} and {OUTPUT_JSON}.")


if __name__ == "__main__":
    main()
