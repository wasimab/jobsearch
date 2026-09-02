#!/usr/bin/env python3
"""
job_sites.py -- the deep-link launcher catalogue.
=================================================

LinkedIn, Indeed and Glassdoor do not expose a public job-search API to
individual developers, so a script cannot legitimately pull their listings.
What a script CAN do -- and what this file does -- is build the exact
pre-filtered search URL for each site, for each of your search terms, in
each of your target regions. One click and you land on live results on
their own site.

Every entry is a URL template. Placeholders:
    {kw}       -- your search term, URL-encoded          ("SAP%20Concur")
    {kw_plus}  -- your search term, plus-encoded         ("SAP+Concur")
    {kw_slug}  -- your search term, hyphen-slugged       ("sap-concur")

`confidence` is honest bookkeeping, not decoration:
    "verified"  -- I loaded this exact URL shape in a browser and saw real
                   filtered results (done 2026-09-02).
    "standard"  -- the site's long-standing documented/observable search
                   form. Very likely correct, not re-checked today.
    "landing"   -- the site renders search client-side or via POST, so a
                   keyword URL isn't reliable. Links to the site's search
                   page; you type the term there.

Run `python3 verify_links.py` any time to re-check every link and catch
sites that have changed their URL format.
"""

# ---------------------------------------------------------------------------
# The terms the launcher offers as clickable chips. Keep this list short --
# these are terms you'd actually click, not the full crawl keyword list in
# job_search.py.
# ---------------------------------------------------------------------------

LAUNCHER_TERMS = [
    "SAP Concur",
    "Concur Consultant",
    "Application Support Manager",
    "IT Service Delivery Manager",
    "ITSM Manager",
    "IT Program Manager",
    "IT Manager",
    "Document Management Systems",
]

# ---------------------------------------------------------------------------
# SITE CATALOGUE
# ---------------------------------------------------------------------------
# Ordered to match a remote-first search: worldwide remote boards come
# before relocation markets.

SITE_GROUPS = [
    # -----------------------------------------------------------------
    {
        "group": "Remote — worldwide",
        "blurb": "Fully-remote roles, no relocation. Start here.",
        "sites": [
            {
                "name": "LinkedIn — Remote, past week",
                "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&f_WT=2&f_TPR=r604800&sortBy=DD",
                "confidence": "standard",
                "note": "f_WT=2 = remote only. f_TPR=r604800 = posted in last 7 days.",
            },
            {
                "name": "LinkedIn — Remote contract only",
                "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&f_WT=2&f_JT=C&f_TPR=r604800&sortBy=DD",
                "confidence": "standard",
                "note": "f_JT=C restricts to contract roles.",
            },
            {
                "name": "Indeed — Remote (global site)",
                "url": "https://www.indeed.com/jobs?q={kw_plus}&l=Remote&fromage=7&sort=date",
                "confidence": "standard",
            },
            {
                "name": "Glassdoor — Remote",
                "url": "https://www.glassdoor.com/Job/jobs.htm?sc.keyword={kw_plus}&remoteWorkType=1",
                "confidence": "standard",
                "note": "Glassdoor's pretty URLs embed character offsets and can't be templated; this keyword form is the stable one.",
            },
            {
                "name": "Google Jobs — aggregates almost everything",
                "url": "https://www.google.com/search?q={kw_plus}+remote+jobs&ibp=htl;jobs",
                "confidence": "standard",
                "note": "Pulls from LinkedIn, Indeed, company career pages and hundreds of boards at once.",
            },
            {
                "name": "We Work Remotely",
                "url": "https://weworkremotely.com/remote-jobs/search?term={kw_plus}",
                "confidence": "standard",
            },
            {
                "name": "Remote OK",
                "url": "https://remoteok.com/remote-{kw_slug}-jobs",
                "confidence": "standard",
            },
            {
                "name": "Remotive",
                "url": "https://remotive.com/remote-jobs?search={kw_plus}",
                "confidence": "standard",
            },
            {
                "name": "Working Nomads",
                "url": "https://www.workingnomads.com/jobs?search={kw_plus}",
                "confidence": "standard",
            },
            {
                "name": "Himalayas",
                "url": "https://himalayas.app/jobs?search={kw_plus}",
                "confidence": "standard",
            },
            {
                "name": "FlexJobs (paid, strong on contract)",
                "url": "https://www.flexjobs.com/search?search={kw_plus}",
                "confidence": "standard",
            },
        ],
    },
    # -----------------------------------------------------------------
    {
        "group": "Contract / freelance / consulting",
        "blurb": "Day-rate and project work — the fastest route to income while permanent roles are in flight.",
        "sites": [
            {
                "name": "Upwork",
                "url": "https://www.upwork.com/nx/search/jobs/?q={kw_plus}&sort=recency",
                "confidence": "standard",
            },
            {
                "name": "Toptal (apply once, get matched)",
                "url": "https://www.toptal.com/talent/apply",
                "confidence": "landing",
                "note": "Screening-based network — one application, then they route projects to you.",
            },
            {
                "name": "Freelancer.com",
                "url": "https://www.freelancer.com/jobs/?keyword={kw_plus}",
                "confidence": "standard",
            },
            {
                "name": "Fiverr Pro (SAP / ERP consulting)",
                "url": "https://www.fiverr.com/search/gigs?query={kw_plus}",
                "confidence": "standard",
            },
            {
                "name": "Dice (US contract / corp-to-corp)",
                "url": "https://www.dice.com/jobs?q={kw_plus}&workplaceTypes=Remote&filters.postedDate=SEVEN",
                "confidence": "standard",
            },
            {
                "name": "SAP Concur partner directory (approach partners directly)",
                "url": "https://www.concur.com/en-us/app-center",
                "confidence": "landing",
                "note": "Concur implementation partners hire Concur consultants constantly and rarely advertise. Cold outreach here converts well.",
            },
        ],
    },
    # -----------------------------------------------------------------
    {
        "group": "Gulf / GCC / Middle East",
        "blurb": "UAE, Saudi, Qatar, Kuwait, Bahrain, Oman. Tax-free, and employers here sponsor visas as a matter of routine.",
        "sites": [
            {
                "name": "Bayt — UAE",
                "url": "https://www.bayt.com/en/uae/jobs/{kw_slug}-jobs/",
                "confidence": "verified",
            },
            {
                "name": "Bayt — Saudi Arabia",
                "url": "https://www.bayt.com/en/saudi-arabia/jobs/{kw_slug}-jobs/",
                "confidence": "verified",
            },
            {
                "name": "Bayt — Qatar",
                "url": "https://www.bayt.com/en/qatar/jobs/{kw_slug}-jobs/",
                "confidence": "verified",
            },
            {
                "name": "Bayt — Kuwait",
                "url": "https://www.bayt.com/en/kuwait/jobs/{kw_slug}-jobs/",
                "confidence": "verified",
            },
            {
                "name": "Bayt — Bahrain",
                "url": "https://www.bayt.com/en/bahrain/jobs/{kw_slug}-jobs/",
                "confidence": "verified",
            },
            {
                "name": "Bayt — Oman",
                "url": "https://www.bayt.com/en/oman/jobs/{kw_slug}-jobs/",
                "confidence": "verified",
            },
            {
                "name": "Naukrigulf — UAE",
                "url": "https://www.naukrigulf.com/{kw_slug}-jobs-in-uae",
                "confidence": "verified",
            },
            {
                "name": "Naukrigulf — Saudi Arabia",
                "url": "https://www.naukrigulf.com/{kw_slug}-jobs-in-saudi-arabia",
                "confidence": "verified",
            },
            {
                "name": "Naukrigulf — Qatar",
                "url": "https://www.naukrigulf.com/{kw_slug}-jobs-in-qatar",
                "confidence": "verified",
            },
            {
                "name": "GulfTalent (senior / management skew)",
                "url": "https://www.gulftalent.com/jobs/search",
                "confidence": "landing",
                "note": "Search runs client-side, so a keyword URL doesn't stick. Type the term in their search box — worth it, this board skews senior.",
            },
            {
                "name": "LinkedIn — Dubai, UAE",
                "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Dubai%2C%20United%20Arab%20Emirates&f_TPR=r604800&sortBy=DD",
                "confidence": "standard",
            },
            {
                "name": "LinkedIn — Riyadh, Saudi Arabia",
                "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Riyadh%2C%20Saudi%20Arabia&f_TPR=r604800&sortBy=DD",
                "confidence": "standard",
            },
            {
                "name": "LinkedIn — Doha, Qatar",
                "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Doha%2C%20Qatar&f_TPR=r604800&sortBy=DD",
                "confidence": "standard",
            },
            {
                "name": "Indeed — UAE",
                "url": "https://ae.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date",
                "confidence": "standard",
            },
            {
                "name": "Indeed — Saudi Arabia",
                "url": "https://sa.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date",
                "confidence": "standard",
            },
            {
                "name": "Indeed — Qatar",
                "url": "https://qa.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date",
                "confidence": "standard",
            },
            {
                "name": "Monster Gulf",
                "url": "https://www.monstergulf.com/srp/results?query={kw_plus}",
                "confidence": "standard",
            },
        ],
    },
    # -----------------------------------------------------------------
    {
        "group": "Singapore & SE Asia",
        "blurb": "Your 13-year Singapore tenure is a genuine advantage here — say so in the first line of every application.",
        "sites": [
            {
                "name": "MyCareersFuture (Singapore government portal)",
                "url": "https://www.mycareersfuture.gov.sg/search?search={kw_plus}&sortBy=new_posting_date",
                "confidence": "standard",
                "note": "Every SG role advertised to locals must appear here first. Best single SG source.",
            },
            {
                "name": "JobStreet — Singapore",
                "url": "https://sg.jobstreet.com/jobs?keywords={kw_plus}&sortmode=ListedDate",
                "confidence": "standard",
            },
            {
                "name": "JobStreet — Malaysia",
                "url": "https://my.jobstreet.com/jobs?keywords={kw_plus}&sortmode=ListedDate",
                "confidence": "standard",
            },
            {
                "name": "JobsDB — Hong Kong",
                "url": "https://hk.jobsdb.com/jobs?keywords={kw_plus}&sortmode=ListedDate",
                "confidence": "standard",
            },
            {
                "name": "JobsDB — Thailand",
                "url": "https://th.jobsdb.com/jobs?keywords={kw_plus}&sortmode=ListedDate",
                "confidence": "standard",
            },
            {
                "name": "LinkedIn — Singapore",
                "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Singapore&f_TPR=r604800&sortBy=DD",
                "confidence": "standard",
            },
            {
                "name": "Indeed — Singapore",
                "url": "https://sg.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date",
                "confidence": "standard",
            },
            {
                "name": "Indeed — Malaysia",
                "url": "https://malaysia.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date",
                "confidence": "standard",
            },
            {
                "name": "Glassdoor — Singapore",
                "url": "https://www.glassdoor.sg/Job/jobs.htm?sc.keyword={kw_plus}",
                "confidence": "standard",
            },
        ],
    },
    # -----------------------------------------------------------------
    {
        "group": "Australia & New Zealand",
        "blurb": "Skilled-visa friendly for IT management roles; Seek is the market, everything else is secondary.",
        "sites": [
            {
                "name": "Seek — Australia",
                "url": "https://www.seek.com.au/jobs?keywords={kw_plus}&sortmode=ListedDate",
                "confidence": "standard",
            },
            {
                "name": "Seek — Australia, remote only",
                "url": "https://www.seek.com.au/jobs?keywords={kw_plus}&workarrangement=2&sortmode=ListedDate",
                "confidence": "standard",
            },
            {
                "name": "Seek — New Zealand",
                "url": "https://www.seek.co.nz/jobs?keywords={kw_plus}&sortmode=ListedDate",
                "confidence": "standard",
            },
            {
                "name": "LinkedIn — Australia",
                "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Australia&f_TPR=r604800&sortBy=DD",
                "confidence": "standard",
            },
            {
                "name": "Indeed — Australia",
                "url": "https://au.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date",
                "confidence": "standard",
            },
        ],
    },
    # -----------------------------------------------------------------
    {
        "group": "Pakistan",
        "blurb": "Local market plus the growing set of Pakistan-based roles serving overseas clients.",
        "sites": [
            {
                "name": "Rozee.pk",
                "url": "https://www.rozee.pk/job/jsearch/q/{kw_slug_space}",
                "confidence": "verified",
            },
            {
                "name": "Mustakbil",
                "url": "https://www.mustakbil.com/jobs/search?q={kw_plus}",
                "confidence": "standard",
            },
            {
                "name": "LinkedIn — Pakistan",
                "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Pakistan&f_TPR=r604800&sortBy=DD",
                "confidence": "standard",
            },
            {
                "name": "Indeed — Pakistan",
                "url": "https://pk.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date",
                "confidence": "standard",
            },
            {
                "name": "Bayt — Pakistan",
                "url": "https://www.bayt.com/en/pakistan/jobs/{kw_slug}-jobs/",
                "confidence": "verified",
            },
        ],
    },
    # -----------------------------------------------------------------
    {
        "group": "UK, Europe & North America",
        "blurb": "Your existing UK employer and Portsmouth degree help here; UK Skilled Worker sponsorship is well-trodden for IT management.",
        "sites": [
            {
                "name": "LinkedIn — United Kingdom",
                "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=United%20Kingdom&f_TPR=r604800&sortBy=DD",
                "confidence": "standard",
            },
            {
                "name": "Indeed — UK",
                "url": "https://uk.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date",
                "confidence": "standard",
            },
            {
                "name": "Glassdoor — UK",
                "url": "https://www.glassdoor.co.uk/Job/jobs.htm?sc.keyword={kw_plus}",
                "confidence": "standard",
            },
            {
                "name": "UK licensed visa-sponsor register (check before applying)",
                "url": "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers",
                "confidence": "landing",
                "note": "Official Home Office list. Search the employer's name here before spending time on a UK application.",
            },
            {
                "name": "Totaljobs / CV-Library (UK)",
                "url": "https://www.totaljobs.com/jobs/{kw_slug}",
                "confidence": "standard",
            },
            {
                "name": "LinkedIn — Netherlands / Germany (English-language IT)",
                "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=European%20Union&f_TPR=r604800&sortBy=DD",
                "confidence": "standard",
            },
            {
                "name": "Indeed — Canada",
                "url": "https://ca.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date",
                "confidence": "standard",
            },
            {
                "name": "Indeed — United States",
                "url": "https://www.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date",
                "confidence": "standard",
            },
        ],
    },
]


def slugify(term: str) -> str:
    """'SAP Concur' -> 'sap-concur'"""
    out = []
    for ch in term.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def all_templates() -> list[str]:
    """Every URL template in the catalogue -- used by verify_links.py."""
    urls = []
    for grp in SITE_GROUPS:
        for site in grp["sites"]:
            urls.append(site["url"])
            if site.get("fallback"):
                urls.append(site["fallback"])
    return urls


def as_portal_data() -> dict:
    """The catalogue, shaped for injection into the portal HTML."""
    groups = []
    for grp in SITE_GROUPS:
        sites = []
        for s in grp["sites"]:
            sites.append({
                "name": s["name"],
                "url": s.get("fallback") or s["url"],
                "confidence": s["confidence"],
                "note": s.get("note", ""),
            })
        groups.append({
            "group": grp["group"],
            "blurb": grp["blurb"],
            "sites": sites,
        })
    return {"terms": LAUNCHER_TERMS, "groups": groups}


if __name__ == "__main__":
    import json
    print(json.dumps(as_portal_data(), indent=2))
