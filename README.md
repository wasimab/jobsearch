# Job Search Portal — v4

A daily-refreshing job portal that runs on GitHub's free tier. No server, no
subscription, nothing to keep open. It searches for roles matching your
background, ranks them remote-first, shows the relevant part of your resume
next to each one, and gives you a one-click launcher into live searches on
LinkedIn, Indeed, Glassdoor, Bayt, Naukrigulf, Seek, JobStreet, Rozee and
the major remote boards.

---

## Setup from scratch — about 15 minutes, once

### 1. Create the repo

1. Go to <https://github.com/new>.
2. Name it something like `job-search`. **Private is fine** — GitHub Pages
   works on private repos on the free tier for personal accounts, but if you
   hit a Pages restriction, make it public. Nothing sensitive lives in the
   code; the API keys go in Secrets, never in a file.
3. Tick "Add a README file" so the repo isn't empty, then **Create
   repository**.

### 2. Upload these files

Keep the folder structure exactly as it is — `.github/workflows/` must sit
at the repo root or GitHub Actions won't find the schedule.

```
job-search/
├── job_search.py
├── job_sites.py
├── me.py              <- YOUR details. Fill in the TODOs.
├── verify_links.py
├── README.md
├── resumes/           <- put your 4 PDFs here
└── .github/
    └── workflows/
        └── daily-job-search.yml
```

Easiest way: on the repo page click **Add file → Upload files**, drag the
whole `job-search-agent` folder's contents in, and commit. GitHub preserves
the folder structure from a drag-and-drop.

### 3. Get the two free API keys

**Adzuna** — <https://developer.adzuna.com/>
Sign up, no card needed, takes about two minutes. You get an **App ID** and
an **App Key**. Covers UK, US, Canada, Australia, NZ, Singapore, India,
South Africa and most of Western Europe.

**Jooble** — <https://jooble.org/api/about>
Request a free API key. **Do not skip this one.** Adzuna has no index for
the Gulf, no index for Pakistan, and nothing for SE Asia beyond Singapore.
Jooble is the only thing covering UAE, Saudi, Qatar, Kuwait, Bahrain, Oman,
Pakistan, Malaysia, Hong Kong, Thailand, Indonesia, the Philippines and
Vietnam. Without it, the regions you specifically asked for are empty.

### 4. Add the keys as repo secrets

Repo → **Settings** → **Secrets and variables** → **Actions** → **New
repository secret**. Add three:

| Name | Value |
|---|---|
| `ADZUNA_APP_ID` | your Adzuna App ID |
| `ADZUNA_APP_KEY` | your Adzuna App Key |
| `JOOBLE_APP_KEY` | your Jooble key |

Secrets are encrypted and never appear in logs or in the committed files.

### 5. Turn on GitHub Pages

Repo → **Settings** → **Pages** → Source: **Deploy from a branch** →
Branch: `main`, folder `/ (root)` → **Save**.

You'll get a URL like `https://<your-username>.github.io/job-search/`.
**Bookmark it on your phone and your laptop.** That's your portal.

### 6. Run it for the first time

Repo → **Actions** tab → **Daily Job Search** → **Run workflow**.

It takes two to four minutes. When it goes green, refresh your Pages URL.
If you still see an old version, hard-refresh (Ctrl+Shift+R / Cmd+Shift+R)
or open it in a private window — GitHub Pages caches aggressively.

From then on it reruns itself every day at **03:00 UTC (08:00 Pakistan
time)**, so a fresh portal is waiting when you start your day. Change the
`cron:` line in `.github/workflows/daily-job-search.yml` to move it.

---

## Using the portal

The portal navigates on **two axes**. Pick where, then pick what — and the
page shows both the live listings for that combination *and* the sites to
search for it. One screen, not two separate tabs.

**Row 1 — WHERE (market).** Every chip carries a live count.

| Market | What it holds |
|---|---|
| **Remote** | Remote and hybrid roles from anywhere. Your first preference — start here daily. |
| **Contract & Freelance** | Day-rate, interim, freelance, outside-IR35. Fastest route to income. |
| **Gulf / GCC** | UAE, Saudi, Qatar, Kuwait, Bahrain, Oman. |
| **Singapore & SE Asia** | SG, Malaysia, HK, Thailand, Indonesia, Philippines, Vietnam. |
| **Australia & NZ** | Skilled-visa friendly for IT management. |
| **Pakistan** | Local, plus Pakistan-based roles serving overseas clients. |
| **UK, Europe & Americas** | UK sponsorship is well-trodden for IT management. |

A listing can sit in several markets at once — a remote contract role in
Dubai appears under **Remote**, **Contract** and **Gulf**.

**Row 2 — WHAT (role).**

| Role | Covers |
|---|---|
| **SAP Concur** | Concur, Concur consultant/implementation, Travel & Expense |
| **Application Support** | Application support manager, IT support manager |
| **Service Delivery & ITSM** | Service delivery, ITSM, service desk, IT operations manager |
| **Document Management** | DMS and EDMS, support and implementation |
| **Programme & Project** | IT programme manager, IT project manager |

**Row 3 — toggles.** Remote only · Contract only · Visa mention · Last 3 days.
These stack on top of whatever market and role you've chosen.

### The sites panel

Under the heading you get every job site for that market, each link already
built for the selected role's search term. The **term** chips let you vary
the phrasing — "SAP Concur" vs "Concur Consultant" vs "Travel and Expense" —
because boards match differently.

The coloured dot is honest bookkeeping:

- 🟢 **checked live** — that exact URL was loaded in a browser and showed
  real filtered results. Bayt (all six GCC countries plus Pakistan),
  Naukrigulf, Rozee.pk.
- 🟡 **standard search form** — the site's long-standing search URL.
- ⚪ **type the term there** — search runs client-side and can't be linked.
  GulfTalent and Toptal.

Run `python3 verify_links.py` monthly. `404` means a site changed format and
needs fixing in `job_sites.py`. `403` is expected and fine — big boards block
scripted requests but serve the page normally in a browser.

### The Apply Kit

Every listing has an **⚡ Apply kit** button. It opens a panel with everything
one application needs:

- **The right resume**, chosen automatically — Gulf listing gets the GCC
  version, Concur role gets the Concur version, support/ITSM gets the ITSM
  version, everything else gets the master. Links to a `resumes/` folder in
  the repo, so commit your four PDFs there.
- **A cover note**, already written for that company and that role, in an
  editable box. Edit it, hit Copy.
- **Application answers** — the five questions every form asks, answered.
- **Form fields** — click any to copy. Amber ones are still TODO in `me.py`.

**Mark applied** tracks what you've sent. The count sits in the header, and
**Hide applied** clears them out of the list. It's stored in your browser
only, so it doesn't survive clearing site data or move between devices —
keep a spreadsheet too if you want a permanent record.

For the truly repetitive fields, save them once in **Chrome → Settings →
Autofill → Addresses**. Most application forms then fill themselves, and the
Apply Kit covers what autofill can't.

### Fill in me.py first

`me.py` has five TODOs: nationality, notice period, visa status, salary
expectation, driving licence. Every Apply Kit uses them, and they're the
fields recruiters filter on. Ten minutes once, saved on every application
after.

### SAP ERP is deliberately excluded

You have no SAP ERP experience, so those listings are noise. There are no
generic SAP keywords in the crawl, and `is_sap_erp_noise()` in
`job_search.py` actively drops anything mentioning S/4HANA, ABAP, FICO,
SAP MM/SD/PP/HCM/BW/Basis, SuccessFactors, Ariba or Fiori — *unless* the
listing also mentions Concur or Travel & Expense, in which case it's a
genuine Concur role and is kept. Each run prints how many were dropped.

---

## Why LinkedIn / Indeed / Glassdoor aren't fetched into the portal

None of the three offer a public job-search API to individual developers
any more, and scraping them breaches their terms and gets IPs blocked
quickly. So the agent does the legitimate thing instead: it builds the exact
pre-filtered search URL and hands it to you as a button. You still see live
results — on their site, one click away, always current.

In practice this loses less than it sounds. Adzuna and Jooble are both
aggregators that already pull from thousands of company career pages and
smaller boards, and Google Jobs (in the launcher) indexes LinkedIn and
Indeed postings anyway.

## What this deliberately does not do

It does not create accounts and it does not submit applications. Two
reasons, and the second is the important one:

1. There is no legitimate "submit" endpoint to hook into — the APIs are
   search-only.
2. Bulk bot-submitted applications get filtered by most ATS platforms, and
   LinkedIn and Indeed suspend accounts for automated activity. Losing your
   LinkedIn during a job search is a serious setback. With your profile,
   twelve well-targeted applications a week will outperform three hundred
   sprayed ones.

---

## Tuning it

Everything worth changing sits near the top of `job_search.py`:

- **`KEYWORD_GROUPS`** — the 16 search terms. Add or remove freely. Adding
  a term multiplies API calls, so trim as well as add.
- **`COUNTRIES`** — Adzuna country indexes. An unsupported code just logs a
  warning and skips, so it's safe to experiment.
- **`JOOBLE_LOCATIONS`** — free-text locations. This is where you add
  another Gulf or SEA city.
- **`MAX_AGE_DAYS`** — currently 45. Listings older than this are dropped.
- **`MAX_PAGES`** — depth per search. Raise to 2 once you've had a clean
  run; it doubles your API usage.
- **`score_job()`** — the ranking. Remote is worth +40, a Concur title +45
  total, region nudges are small on purpose so geography never outranks a
  good remote role. If you decide you'd rather prioritise the Gulf, raise
  its number there.
- **`EXPERIENCE_BANK`** — the resume bullets shown under "Why you're a
  fit". Edit freely, it's yours.

And in `job_sites.py`:

- **`LAUNCHER_TERMS`** — the chips in the Job Sites tab.
- **`SITE_GROUPS`** — add a site, or a country you want covered.

---

## If a run looks wrong

Check the Actions run log first — the script prints a warning line for
every failed call, and that usually points straight at the problem.

| Symptom | Cause |
|---|---|
| "Skipping Adzuna" | `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` secrets not set, or misspelled |
| "Skipping Jooble" | `JOOBLE_APP_KEY` not set — **this is why the Gulf and Pakistan are empty** |
| `HTTP 401` from Adzuna | Wrong key, or the App ID and App Key are swapped |
| `HTTP 429` | Free-tier daily quota hit. Trim `COUNTRIES` or `KEYWORD_GROUPS`, or leave `MAX_PAGES` at 1 |
| Zero results everywhere but no warnings | Keywords too narrow — try one broad term like `IT manager` to confirm the pipe works |
| Portal shows old data | GitHub Pages cache. Hard-refresh, or check `jobs.json` in the repo for the real state |

To test locally without touching GitHub:

```bash
export ADZUNA_APP_ID="..." ADZUNA_APP_KEY="..." JOOBLE_APP_KEY="..."
python3 job_search.py && open index.html
```

Or build just the portal shell, no keys and no API calls, to check the
layout:

```bash
DEMO=1 python3 job_search.py && open index.html
```
