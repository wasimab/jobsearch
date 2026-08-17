#!/usr/bin/env python3
"""
Daily Job Search Agent
=======================
Searches for roles matching your background (SAP Concur / ITSM / Application
Support / IT Management), flags remote + possible visa-sponsorship mentions,
attaches the relevant bit of YOUR resume to each match, and builds a static
HTML "portal" (index.html) you can open in any browser -- no Claude account,
no server.

DATA SOURCE
-----------
Uses Adzuna (https://developer.adzuna.com) -- a free, legitimate job-search
API that aggregates listings across ~20 countries. It's per-country, not
"worldwide" in one call, so this loops over the COUNTRIES list below.

SETUP (takes ~2 minutes)
-------------------------
1. Get a free App ID + App Key: https://developer.adzuna.com/  (instant,
   no credit card).
2. Set them as environment variables before running:
       export ADZUNA_APP_ID="xxxx"
       export ADZUNA_APP_KEY="xxxx"
   (For the GitHub Actions version, add these as repo Secrets instead --
   see README.md. Never commit real keys into this file.)
3. Run:  python3 job_search.py
4. Open index.html.

HONEST CAVEATS
--------------
- I can't make live calls to Adzuna from the sandbox this was written in
  (no outbound network access to job-board domains there), so this is
  built carefully against Adzuna's documented API shape but NOT tested
  against a live response. First run: check the console output -- if any
  field comes back empty where you'd expect data, the API shape likely
  shifted and the field name needs a tweak.
- "Visa mention" is a best-effort keyword scan of the job description
  (looks for phrases like "visa sponsorship", "will sponsor", "work
  permit"). It is NOT a guarantee the employer will actually sponsor --
  always verify on the listing itself.
- This only *searches and links*. It does not create accounts or submit
  applications on any site -- see README.md for why.
"""

import os
import re
import json
import time
import urllib.request
import urllib.error
from urllib.parse import quote
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# CONFIG -- edit freely
# ---------------------------------------------------------------------------

APP_ID = os.environ.get("ADZUNA_APP_ID", "")
APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")

# Adzuna covers roughly 18-19 country indexes -- verified against their
# current docs (https://developer.adzuna.com/docs/countries) as of this
# edit. Notably, it does NOT include Pakistan, the Gulf states, or most of
# Southeast Asia -- Jooble below fills that specific gap.
COUNTRIES = [
    "us", "gb", "ca", "au", "de", "fr", "nl", "es", "it",
    "at", "in", "sg", "nz", "za", "ch",
]

# Second source, specifically to cover what Adzuna's country list can't:
# Pakistan, the Gulf, and Southeast Asia beyond Singapore. Free key at
# https://jooble.org/api/about. Unlike Adzuna, Jooble takes a free-text
# location per call instead of a fixed country-code list.
JOOBLE_APP_KEY = os.environ.get("JOOBLE_APP_KEY", "")
JOOBLE_LOCATIONS = [
    "Pakistan", "United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait",
    "Bahrain", "Malaysia", "Hong Kong", "Thailand", "Indonesia", "Taiwan",
]

# Each string is one search query. Kept as separate terms (rather than one
# giant OR) so results stay relevant per term instead of noisy.
KEYWORD_GROUPS = [
    "SAP Concur",
    "Concur consultant",
    "IT support manager",
    "IT service management manager",
    "application support manager",
    "document management systems",
    "IT program manager",
    "Asta Powerproject",  # planning/scheduling tool -- not in your resume,
                          # see EXPERIENCE_BANK["planning"] below for how
                          # matches on this term are handled honestly
]

# 15 countries x 8 keywords (Adzuna) + 11 locations x 8 keywords (Jooble)
# = a lot of calls per run -- around 200. Both services' free tiers have a
# daily cap that I don't have an exact current number for. If a run starts
# failing partway through with rate-limit warnings, trim COUNTRIES,
# JOOBLE_LOCATIONS, or KEYWORD_GROUPS rather than raising MAX_PAGES.

RESULTS_PER_QUERY = 20
MAX_PAGES = 1  # raise to 2-3 once a first run confirms everything works

VISA_HINTS = re.compile(
    r"visa spons|sponsor.{0,20}visa|work permit|relocation assist|"
    r"will sponsor|skilled worker visa|right to work",
    re.IGNORECASE,
)
REMOTE_HINTS = re.compile(r"\bremote\b|work from home|\bwfh\b|hybrid", re.IGNORECASE)

OUTPUT_JSON = "jobs.json"
OUTPUT_HTML = "index.html"

# ---------------------------------------------------------------------------
# YOUR EXPERIENCE, keyed for matching -- pulled straight from your resume so
# each listing can show *why* you're a fit. Edit the text freely; it's yours.
# ---------------------------------------------------------------------------

EXPERIENCE_BANK = {
    "concur": [
        "Directed the global deployment of SAP Concur (Travel & Expense) "
        "across 20+ regions, including SQL-based executive dashboards "
        "(Worley, 2018-2020).",
        "Primary point of contact for SAP Concur import/integration error "
        "resolution across 30,000+ enterprise users (TEXLA Technologies, "
        "2021-2024).",
        "Led localized SAP Concur implementation across multiple APAC "
        "countries -- expense types, policy groups, approval workflows "
        "(Jacobs, 2011-2018).",
    ],
    "itsm": [
        "ITIL v4 certified; chaired Change Advisory Boards and led Major "
        "Incident Management during critical outages.",
        "Optimized ServiceNow assignment rules, engineering a dynamic "
        "routing system across onshore/offshore units (ACT UK, "
        "2024-present).",
        "Lifted SLA compliance 25% and cut MTTR 30% via real-time KPI "
        "dashboards and a self-service knowledge base.",
    ],
    "application support": [
        "Directed global application support for 30,000+ enterprise users "
        "across US, APAC and EMEA (TEXLA Technologies).",
        "Maintained 99.9% uptime for enterprise SaaS applications while "
        "running global project controls across time zones (ACT UK).",
    ],
    "document management": [
        "Managed enterprise Document Management Systems and corporate "
        "finance systems at 99% reliability (Jacobs, 2007-2010).",
        "Led UAT, deployment scheduling and change governance for "
        "large-scale enterprise system upgrades.",
    ],
    "it manager": [
        "IT Program & Support Manager (ACT UK, 2024-present) and IT "
        "Application Lead / Global Project Manager (Worley, 2018-2020) -- "
        "global project controls, vendor negotiation, licensing strategy.",
    ],
    "integration": [
        "Built Concur-to-Oracle AP financial posting integration (GL, tax, "
        "cost-object mapping) and enterprise SSO/HRIS data feeds.",
        "Coordinated cross-team data-feed and file-transfer integrations, "
        "diagnosing import/export errors at the platform level.",
    ],
    # NOTE: Asta Powerproject itself doesn't appear anywhere in the resume,
    # so these bullets deliberately do NOT claim hands-on experience with
    # that specific tool -- that would be a claim you couldn't back up in
    # an interview. They point instead at the genuinely-held, adjacent
    # skill (critical-path/resource tracking, global programme delivery)
    # that IS in the resume. If you do have real Asta Powerproject
    # experience, add it here directly and it'll show up honestly.
    "planning": [
        "Single point of contact for global project controls, tracking "
        "critical-path milestones and resource availability across "
        "multiple time zones (ACT UK, 2024-present).",
        "IT Application Lead / Global Project Manager overseeing "
        "multi-region programme delivery and stakeholder coordination "
        "through a major M&A integration (Worley, 2018-2020).",
    ],
}


def relevant_experience(title: str, description: str) -> list[str]:
    """Return up to 3 resume bullets relevant to this listing."""
    text = f"{title} {description}".lower()
    hits: list[str] = []
    if "concur" in text:
        hits += EXPERIENCE_BANK["concur"]
    if "itsm" in text or "service management" in text or "servicenow" in text:
        hits += EXPERIENCE_BANK["itsm"]
    if "application support" in text or "support manager" in text:
        hits += EXPERIENCE_BANK["application support"]
    if "document management" in text or re.search(r"\bdms\b", text):
        hits += EXPERIENCE_BANK["document management"]
    if any(k in text for k in ("it manager", "program manager", "project manager", "it support")):
        hits += EXPERIENCE_BANK["it manager"]
    if "integration" in text or "interface" in text:
        hits += EXPERIENCE_BANK["integration"]
    if any(k in text for k in (
        "asta", "powerproject", "primavera", "planning engineer",
        "project planner", "scheduler", "critical path",
    )):
        hits += EXPERIENCE_BANK["planning"]

    seen, out = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out[:3]


# ---------------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------------

def fetch_adzuna(country: str, query: str, page: int = 1) -> dict:
    if not APP_ID or not APP_KEY:
        raise RuntimeError(
            "Missing ADZUNA_APP_ID / ADZUNA_APP_KEY. See the setup notes at "
            "the top of this file -- it's a free 2-minute signup."
        )
    url = (
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        f"?app_id={APP_ID}&app_key={APP_KEY}"
        f"&results_per_page={RESULTS_PER_QUERY}"
        f"&what={quote(query)}"
        f"&content-type=application/json"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "job-search-agent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read()[:200]
        print(f"  [warn] {country}/{query}: HTTP {e.code} -- {body}")
        return {"results": []}
    except Exception as e:  # noqa: BLE001 -- keep the run going on a bad call
        print(f"  [warn] {country}/{query}: {e}")
        return {"results": []}


def fetch_jooble(keyword: str, location: str) -> list[dict]:
    """
    Best-effort. Unlike Adzuna (which I've now confirmed works end to end
    against real traffic), I have only moderate confidence in this exact
    response shape -- I couldn't make a live call from the sandbox this was
    written in. If JOOBLE_APP_KEY is set but this consistently returns
    nothing, uncomment the debug print below, check one run's log output,
    and tell me what the real field names are so I can fix the mapping.
    """
    if not JOOBLE_APP_KEY:
        return []
    url = f"https://jooble.org/api/{JOOBLE_APP_KEY}"
    payload = json.dumps({"keywords": keyword, "location": location}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "job-search-agent/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # print(data)  # uncomment to inspect the raw shape on a first run
            return data.get("jobs", [])
    except urllib.error.HTTPError as e:
        print(f"  [warn] jooble {location}/{keyword}: HTTP {e.code} -- {e.read()[:200]}")
        return []
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] jooble {location}/{keyword}: {e}")
        return []


def collect_jobs() -> list[dict]:
    all_jobs: dict[str, dict] = {}
    total_calls = len(COUNTRIES) * len(KEYWORD_GROUPS) * MAX_PAGES
    print(f"Searching {len(COUNTRIES)} countries x {len(KEYWORD_GROUPS)} "
          f"keywords x {MAX_PAGES} page(s) = up to {total_calls} Adzuna calls...")

    for country in COUNTRIES:
        for kw in KEYWORD_GROUPS:
            for page in range(1, MAX_PAGES + 1):
                data = fetch_adzuna(country, kw, page)
                results = data.get("results", [])
                print(f"  {country}/{kw!r} page {page}: {len(results)} results")
                for r in results:
                    job_id = str(r.get("id") or r.get("redirect_url") or "")
                    if not job_id or job_id in all_jobs:
                        continue
                    title = r.get("title", "").strip()
                    desc = r.get("description", "")
                    company = (r.get("company") or {}).get("display_name", "Unknown")
                    location = (r.get("location") or {}).get("display_name", country.upper())
                    all_jobs[job_id] = {
                        "id": job_id,
                        "title": title,
                        "company": company,
                        "location": location,
                        "country": country.upper(),
                        "link": r.get("redirect_url", ""),
                        "posted": r.get("created", ""),
                        "matched_keyword": kw,
                        "remote_mention": bool(REMOTE_HINTS.search(f"{title} {desc}")),
                        "visa_mention": bool(VISA_HINTS.search(desc)),
                        "relevant_experience": relevant_experience(title, desc),
                    }
                time.sleep(0.3)  # be polite to the API

    if JOOBLE_APP_KEY:
        print(f"Searching {len(JOOBLE_LOCATIONS)} locations x "
              f"{len(KEYWORD_GROUPS)} keywords via Jooble "
              f"(Pakistan / Gulf / SE Asia)...")
        for location in JOOBLE_LOCATIONS:
            for kw in KEYWORD_GROUPS:
                results = fetch_jooble(kw, location)
                print(f"  jooble {location}/{kw!r}: {len(results)} results")
                for r in results:
                    job_id = "jooble-" + str(r.get("id") or r.get("link") or "")
                    if job_id == "jooble-" or job_id in all_jobs:
                        continue
                    title = (r.get("title") or "").strip()
                    desc = r.get("snippet", "")
                    all_jobs[job_id] = {
                        "id": job_id,
                        "title": title,
                        "company": r.get("company", "Unknown"),
                        "location": r.get("location", location),
                        "country": location,
                        "link": r.get("link", ""),
                        "posted": r.get("updated", ""),
                        "matched_keyword": kw,
                        "remote_mention": bool(REMOTE_HINTS.search(f"{title} {desc}")),
                        "visa_mention": bool(VISA_HINTS.search(desc)),
                        "relevant_experience": relevant_experience(title, desc),
                    }
                time.sleep(0.3)
    else:
        print("Skipping Jooble (no JOOBLE_APP_KEY) -- Pakistan/Gulf/SE Asia "
              "coverage relies on Adzuna's India + Singapore indexes only.")

    return list(all_jobs.values())


# ---------------------------------------------------------------------------
# BUILD PORTAL
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Search -- Daily Status</title>
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
    --font-mono: 'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, monospace;
    --font-sans: 'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--font-sans);
    line-height: 1.5;
  }
  a { color: inherit; }
  .wrap { max-width: 840px; margin: 0 auto; padding: 28px 20px 80px; }

  .status-bar {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 16px 20px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    margin-bottom: 18px;
  }
  .status-left { display: flex; align-items: center; gap: 10px; }
  .dot {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--teal);
    box-shadow: 0 0 0 4px rgba(79,184,168,0.15);
  }
  .status-label {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    font-weight: 500;
  }
  .status-right {
    display: flex; flex-wrap: wrap; gap: 16px;
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-muted);
  }
  .status-right .hl { color: var(--amber); font-weight: 600; }

  .tabs {
    display: flex; gap: 8px;
    margin-bottom: 10px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }
  .tabs::-webkit-scrollbar { display: none; }
  .subtabs {
    display: flex; gap: 6px;
    margin-bottom: 20px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding-left: 4px;
    border-left: 2px solid var(--border);
  }
  .subtabs::-webkit-scrollbar { display: none; }
  .chip {
    font-family: var(--font-mono);
    font-size: 12px;
    background: transparent;
    color: var(--text-muted);
    border: 1px solid var(--border);
    padding: 6px 12px;
    border-radius: 999px;
    cursor: pointer;
    white-space: nowrap;
    flex: 0 0 auto;
  }
  .chip.sub { font-size: 11px; padding: 4px 10px; opacity: 0.85; }
  .chip:hover { border-color: var(--teal); color: var(--text); }
  .chip.active {
    background: var(--teal);
    border-color: var(--teal);
    color: #0B1319;
    font-weight: 600;
  }
  .chip:focus-visible, .ticket-apply:focus-visible, summary:focus-visible {
    outline: 2px solid var(--amber);
    outline-offset: 2px;
  }

  .ticket {
    display: flex;
    gap: 12px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 12px;
  }
  .ticket:hover { background: var(--panel-hover); }
  .ticket-status { flex: 0 0 auto; padding-top: 5px; }
  .ticket-status .dot { background: var(--amber); box-shadow: 0 0 0 4px rgba(240,168,61,0.15); }
  .ticket-body { flex: 1 1 auto; min-width: 0; }
  .ticket-head {
    display: flex; flex-wrap: wrap; justify-content: space-between;
    align-items: baseline; gap: 8px 12px;
  }
  .ticket-title { font-size: 16px; font-weight: 600; margin: 0; }
  .badges { display: flex; gap: 6px; flex-wrap: wrap; }
  .badge {
    font-family: var(--font-mono);
    font-size: 10.5px;
    letter-spacing: 0.04em;
    padding: 3px 8px;
    border-radius: 5px;
    font-weight: 600;
    white-space: nowrap;
  }
  .badge-remote { background: rgba(79,184,168,0.15); color: var(--teal); }
  .badge-visa { background: rgba(167,139,196,0.18); color: var(--violet); }

  .ticket-meta {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 6px;
  }
  .country-tag {
    color: var(--amber);
    font-weight: 600;
  }

  .ticket-experience { margin-top: 10px; }
  .ticket-experience summary {
    cursor: pointer;
    font-size: 13px;
    color: var(--amber);
    font-weight: 500;
  }
  .ticket-experience ul {
    margin: 8px 0 0;
    padding-left: 18px;
    font-size: 13.5px;
    color: var(--text);
  }
  .ticket-experience li { margin-bottom: 6px; }

  .ticket-apply {
    display: inline-block;
    margin-top: 12px;
    font-family: var(--font-mono);
    font-size: 12.5px;
    font-weight: 600;
    text-decoration: none;
    color: var(--bg);
    background: var(--amber);
    padding: 7px 14px;
    border-radius: 6px;
  }
  .ticket-apply:hover { opacity: 0.9; }

  .empty {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
    font-family: var(--font-mono);
    font-size: 13px;
  }

  footer {
    margin-top: 28px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-muted);
    text-align: center;
  }

  @media (prefers-reduced-motion: reduce) {
    * { transition: none !important; }
  }
</style>
</head>
<body>
<div class="wrap">

  <div class="status-bar">
    <div class="status-left">
      <span class="dot"></span>
      <span class="status-label">JOB SEARCH -- STATUS: ACTIVE</span>
    </div>
    <div class="status-right">
      <span>Last sync: __GENERATED_AT__</span>
      <span>Uptime: 18 yrs, 0 unplanned gaps</span>
      <span class="hl">__COUNT__ matches</span>
    </div>
  </div>

  <nav class="tabs" id="tabs">
    <button class="chip active" data-tab="all">All</button>
    <button class="chip" data-tab="country">Country</button>
    <button class="chip" data-tab="remote">Remote</button>
    <button class="chip" data-tab="visa">Visa Sponsor</button>
    <button class="chip" data-tab="role">Role</button>
    <button class="chip" data-tab="latest">Latest</button>
  </nav>
  <nav class="subtabs" id="subtabs" style="display:none;"></nav>

  <div id="list"></div>

  <footer>Generated __GENERATED_AT__ &middot; searches, does not auto-apply &middot; edit job_search.py to change scope</footer>
</div>

<script>
const JOBS = __JOBS_JSON__;

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

// Role groups consolidate the raw search keywords into cleaner tabs.
// Matches KEYWORD_GROUPS in job_search.py -- update both together.
const ROLE_GROUPS = {
  "SAP Concur": ["SAP Concur", "Concur consultant"],
  "Support & ITSM": ["IT support manager", "IT service management manager", "application support manager"],
  "Document Management": ["document management systems"],
  "Asta Powerproject": ["Asta Powerproject"],
  "Program & Project Mgmt": ["IT program manager"],
};
function roleGroupOf(keyword) {
  for (const [name, kws] of Object.entries(ROLE_GROUPS)) {
    if (kws.includes(keyword)) return name;
  }
  return null;
}

const countryCounts = countBy(JOBS.map(j => j.country));
const COUNTRIES_PRESENT = Object.keys(countryCounts).sort((a, b) => countryCounts[b] - countryCounts[a]);

const roleCounts = countBy(JOBS.map(j => roleGroupOf(j.matched_keyword)));
const ROLES_PRESENT = Object.keys(ROLE_GROUPS).filter(r => roleCounts[r]).sort((a, b) => (roleCounts[b] || 0) - (roleCounts[a] || 0));

let state = { primary: 'all', secondary: null };

function matchesPrimary(job) {
  switch (state.primary) {
    case 'remote': return job.remote_mention;
    case 'visa': return job.visa_mention;
    case 'latest': return daysAgo(job.posted) <= 3;
    case 'country': return state.secondary ? job.country === state.secondary : true;
    case 'role': return state.secondary ? roleGroupOf(job.matched_keyword) === state.secondary : true;
    default: return true;
  }
}

function renderSubtabs() {
  const el = document.getElementById('subtabs');
  let items = null;
  if (state.primary === 'country') items = COUNTRIES_PRESENT.map(c => [c, `${c} (${countryCounts[c]})`]);
  if (state.primary === 'role') items = ROLES_PRESENT.map(r => [r, `${r} (${roleCounts[r]})`]);
  if (!items || !items.length) {
    el.style.display = 'none';
    el.innerHTML = '';
    return;
  }
  el.style.display = 'flex';
  el.innerHTML = items.map(([value, label]) =>
    `<button class="chip sub ${state.secondary === value ? 'active' : ''}" data-sub="${value}">${label}</button>`
  ).join('');
}

function card(job) {
  const badges = [
    job.remote_mention ? '<span class="badge badge-remote">REMOTE</span>' : '',
    job.visa_mention ? '<span class="badge badge-visa">VISA MENTION</span>' : '',
  ].join('');

  const exp = (job.relevant_experience || []).map(e => `<li>${e}</li>`).join('');
  const expBlock = exp ? `
    <details class="ticket-experience">
      <summary>Why you're a fit</summary>
      <ul>${exp}</ul>
    </details>` : '';

  return `
    <article class="ticket" data-remote="${job.remote_mention}" data-visa="${job.visa_mention}">
      <div class="ticket-status"><span class="dot"></span></div>
      <div class="ticket-body">
        <div class="ticket-head">
          <h2 class="ticket-title">${job.title || 'Untitled listing'}</h2>
          <div class="badges">${badges}</div>
        </div>
        <div class="ticket-meta"><span class="country-tag">${job.country || '--'}</span> &middot; ${job.company} &middot; ${job.location} &middot; posted ${fmtDate(job.posted)} &middot; matched: ${job.matched_keyword}</div>
        ${expBlock}
        <a class="ticket-apply" href="${job.link}" target="_blank" rel="noopener">Open listing &rarr;</a>
      </div>
    </article>`;
}

function render() {
  renderSubtabs();
  const list = document.getElementById('list');
  const filtered = JOBS.filter(matchesPrimary);
  if (filtered.length === 0) {
    list.innerHTML = '<div class="empty">No listings in this view yet. Check back after the next sync, or widen KEYWORD_GROUPS / COUNTRIES in job_search.py.</div>';
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
  state.secondary = state.primary === 'country' ? (COUNTRIES_PRESENT[0] || null)
                   : state.primary === 'role' ? (ROLES_PRESENT[0] || null)
                   : null;
  render();
});

document.getElementById('subtabs').addEventListener('click', (e) => {
  const btn = e.target.closest('.chip');
  if (!btn) return;
  state.secondary = btn.dataset.sub;
  render();
});

render();
</script>
</body>
</html>
"""


def build_html(jobs: list[dict]) -> str:
    jobs_sorted = sorted(jobs, key=lambda j: j.get("posted", ""), reverse=True)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = HTML_TEMPLATE
    html = html.replace("__JOBS_JSON__", json.dumps(jobs_sorted))
    html = html.replace("__GENERATED_AT__", generated_at)
    html = html.replace("__COUNT__", str(len(jobs_sorted)))
    return html


def main() -> None:
    jobs = collect_jobs()
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)
    html = build_html(jobs)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nDone -- {len(jobs)} unique listing(s). Open {OUTPUT_HTML}.")


if __name__ == "__main__":
    main()
