#!/usr/bin/env python3
"""
job_sites.py -- markets, roles, and the deep-link catalogue.
============================================================

The portal navigates on two axes:

    MARKET  (where the job is)   -- Remote, Contract, Gulf, SEA, ANZ, Pakistan, West
    ROLE    (what the job is)    -- Concur, App Support, Service Delivery, DMS, Programme

Pick a market, then a role, and the portal shows BOTH the live listings that
match AND the job sites to search for exactly that combination. One screen
instead of two separate worlds.

LinkedIn, Indeed and Glassdoor have no public job API for individual
developers, so a script cannot legitimately pull their listings. What it CAN
do -- and what this file does -- is build their exact pre-filtered search URL
for each market and role. One click, live results, on their own site.

URL template placeholders:
    {kw}             search term, URL-encoded        "SAP%20Concur"
    {kw_plus}        plus-encoded                    "SAP+Concur"
    {kw_slug}        hyphen-slugged                  "sap-concur"
    {kw_slug_space}  lowercased, %20 spaces          "sap%20concur"

`confidence`:
    "verified"  loaded in a browser and confirmed showing filtered results
    "standard"  the site's long-standing search form
    "landing"   search runs client-side; opens their search page, you type it

Run `python3 verify_links.py` monthly to catch sites that change format.
"""

# ---------------------------------------------------------------------------
# ROLES -- what you're looking for.
#
# `keywords` must stay in step with KEYWORD_GROUPS in job_search.py: that's
# how a fetched listing gets sorted into a role tab.
# `site_term` is what gets typed into LinkedIn/Indeed/Bayt for this role.
#
# NOTE: SAP ERP / S/4HANA / ABAP / FICO roles are deliberately absent. You
# have no SAP ERP experience, so searching for it only produces listings you
# can't honestly apply to. job_search.py also actively filters those out.
# ---------------------------------------------------------------------------

ROLES = [
    {
        "id": "concur",
        "label": "SAP Concur",
        "blurb": "Your most differentiated skill. Fewest competitors, highest day rates.",
        "site_term": "SAP Concur",
        "keywords": ["SAP Concur", "Concur consultant", "Concur implementation",
                     "travel and expense system", "freelance Concur consultant"],
        "alt_terms": ["Concur Consultant", "Travel and Expense"],
    },
    {
        "id": "appsupport",
        "label": "Application Support",
        "blurb": "30,000-user global estates. Your TEXLA and ACT experience maps directly.",
        "site_term": "Application Support Manager",
        "keywords": ["application support manager", "IT support manager"],
        "alt_terms": ["IT Support Manager"],
    },
    {
        "id": "servicedelivery",
        "label": "Service Delivery & ITSM",
        "blurb": "ITIL v4, ServiceNow, CAB, Major Incident. SLA +25%, MTTR -30%.",
        "site_term": "IT Service Delivery Manager",
        "keywords": ["IT service delivery manager", "ITSM manager",
                     "service desk manager", "IT operations manager"],
        "alt_terms": ["ITSM Manager", "Service Desk Manager", "IT Operations Manager"],
    },
    {
        "id": "dms",
        "label": "Document Management",
        "blurb": "DMS/EDMS support and implementation — your Jacobs engineering-lifecycle work.",
        "site_term": "Document Management System",
        "keywords": ["document management systems", "EDMS implementation"],
        "alt_terms": ["EDMS", "Document Controller Systems"],
    },
    {
        "id": "programme",
        "label": "Programme & Project",
        "blurb": "Global rollouts, M&A integration, multi-timezone project controls.",
        "site_term": "IT Program Manager",
        "keywords": ["IT program manager", "IT project manager"],
        "alt_terms": ["IT Project Manager", "IT Delivery Manager"],
    },
]

ROLE_IDS = [r["id"] for r in ROLES]


def role_of_keyword(keyword: str) -> str:
    for r in ROLES:
        if keyword in r["keywords"]:
            return r["id"]
    return "other"


# ---------------------------------------------------------------------------
# MARKETS -- where the job is. Each carries its own site list.
# A single listing can belong to several markets at once: a remote contract
# role in Dubai shows under Remote, Contract AND Gulf.
# ---------------------------------------------------------------------------

MARKETS = [
    {
        "id": "remote",
        "label": "Remote",
        "icon": "◉",
        "blurb": "Fully-remote and hybrid roles, no relocation. Your stated first preference — start every day here.",
        "sites": [
            {"name": "LinkedIn — remote, past week", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&f_WT=2&f_TPR=r604800&sortBy=DD",
             "note": "f_WT=2 restricts to remote; f_TPR=r604800 to the last 7 days."},
            {"name": "Google Jobs", "confidence": "standard",
             "url": "https://www.google.com/search?q={kw_plus}+remote+jobs&ibp=htl;jobs",
             "note": "Aggregates LinkedIn, Indeed, company career pages and hundreds of boards in one search."},
            {"name": "Indeed — remote", "confidence": "standard",
             "url": "https://www.indeed.com/jobs?q={kw_plus}&l=Remote&fromage=7&sort=date"},
            {"name": "Glassdoor — remote", "confidence": "standard",
             "url": "https://www.glassdoor.com/Job/jobs.htm?sc.keyword={kw_plus}&remoteWorkType=1"},
            {"name": "We Work Remotely", "confidence": "standard",
             "url": "https://weworkremotely.com/remote-jobs/search?term={kw_plus}"},
            {"name": "Remote OK", "confidence": "standard",
             "url": "https://remoteok.com/remote-{kw_slug}-jobs"},
            {"name": "Remotive", "confidence": "standard",
             "url": "https://remotive.com/remote-jobs?search={kw_plus}"},
            {"name": "Working Nomads", "confidence": "standard",
             "url": "https://www.workingnomads.com/jobs?search={kw_plus}"},
            {"name": "Himalayas", "confidence": "standard",
             "url": "https://himalayas.app/jobs?search={kw_plus}"},
            {"name": "FlexJobs", "confidence": "standard",
             "url": "https://www.flexjobs.com/search?search={kw_plus}",
             "note": "Paid, but unusually strong on remote contract and part-time senior roles."},
        ],
    },
    {
        "id": "contract",
        "label": "Contract & Freelance",
        "icon": "◐",
        "blurb": "Day-rate, interim and project work — the fastest route to income while permanent roles are in flight.",
        "sites": [
            {"name": "LinkedIn — contract only", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&f_JT=C&f_TPR=r604800&sortBy=DD",
             "note": "f_JT=C restricts to contract postings."},
            {"name": "LinkedIn — remote contract", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&f_WT=2&f_JT=C&f_TPR=r604800&sortBy=DD"},
            {"name": "SAP Concur partner directory", "confidence": "landing",
             "url": "https://www.concur.com/en-us/app-center",
             "note": "Concur implementation partners hire Concur consultants constantly and advertise almost none of it. Message their delivery leads on LinkedIn — this converts better than any board."},
            {"name": "Upwork", "confidence": "standard",
             "url": "https://www.upwork.com/nx/search/jobs/?q={kw_plus}&sort=recency"},
            {"name": "Toptal", "confidence": "landing",
             "url": "https://www.toptal.com/talent/apply",
             "note": "Screening-based network: one application, then they route projects to you."},
            {"name": "Freelancer.com", "confidence": "standard",
             "url": "https://www.freelancer.com/jobs/?keyword={kw_plus}"},
            {"name": "Fiverr Pro", "confidence": "standard",
             "url": "https://www.fiverr.com/search/gigs?query={kw_plus}"},
            {"name": "Dice — US contract / C2C", "confidence": "standard",
             "url": "https://www.dice.com/jobs?q={kw_plus}&workplaceTypes=Remote&filters.postedDate=SEVEN"},
        ],
    },
    {
        "id": "gcc",
        "label": "Gulf / GCC",
        "icon": "▲",
        "blurb": "UAE, Saudi, Qatar, Kuwait, Bahrain, Oman. Tax-free, and employers here sponsor visas as a matter of routine.",
        "sites": [
            {"name": "Bayt — UAE", "confidence": "verified",
             "url": "https://www.bayt.com/en/uae/jobs/{kw_slug}-jobs/"},
            {"name": "Bayt — Saudi Arabia", "confidence": "verified",
             "url": "https://www.bayt.com/en/saudi-arabia/jobs/{kw_slug}-jobs/"},
            {"name": "Bayt — Qatar", "confidence": "verified",
             "url": "https://www.bayt.com/en/qatar/jobs/{kw_slug}-jobs/"},
            {"name": "Bayt — Kuwait", "confidence": "verified",
             "url": "https://www.bayt.com/en/kuwait/jobs/{kw_slug}-jobs/"},
            {"name": "Bayt — Bahrain", "confidence": "verified",
             "url": "https://www.bayt.com/en/bahrain/jobs/{kw_slug}-jobs/"},
            {"name": "Bayt — Oman", "confidence": "verified",
             "url": "https://www.bayt.com/en/oman/jobs/{kw_slug}-jobs/"},
            {"name": "Naukrigulf — UAE", "confidence": "verified",
             "url": "https://www.naukrigulf.com/{kw_slug}-jobs-in-uae"},
            {"name": "Naukrigulf — Saudi Arabia", "confidence": "verified",
             "url": "https://www.naukrigulf.com/{kw_slug}-jobs-in-saudi-arabia"},
            {"name": "Naukrigulf — Qatar", "confidence": "verified",
             "url": "https://www.naukrigulf.com/{kw_slug}-jobs-in-qatar"},
            {"name": "LinkedIn — Dubai", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Dubai%2C%20United%20Arab%20Emirates&f_TPR=r604800&sortBy=DD"},
            {"name": "LinkedIn — Riyadh", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Riyadh%2C%20Saudi%20Arabia&f_TPR=r604800&sortBy=DD"},
            {"name": "LinkedIn — Doha", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Doha%2C%20Qatar&f_TPR=r604800&sortBy=DD"},
            {"name": "Indeed — UAE", "confidence": "standard",
             "url": "https://ae.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date"},
            {"name": "Indeed — Saudi Arabia", "confidence": "standard",
             "url": "https://sa.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date"},
            {"name": "Indeed — Qatar", "confidence": "standard",
             "url": "https://qa.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date"},
            {"name": "Monster Gulf", "confidence": "standard",
             "url": "https://www.monstergulf.com/srp/results?query={kw_plus}"},
            {"name": "GulfTalent", "confidence": "landing",
             "url": "https://www.gulftalent.com/jobs/search",
             "note": "Search runs client-side so a keyword URL won't stick — type the term in their box. Worth the extra ten seconds: this board skews senior."},
        ],
    },
    {
        "id": "sea",
        "label": "Singapore & SE Asia",
        "icon": "◆",
        "blurb": "Thirteen years in Singapore is a real advantage here. Say it in the first line of every application.",
        "sites": [
            {"name": "MyCareersFuture — Singapore", "confidence": "standard",
             "url": "https://www.mycareersfuture.gov.sg/search?search={kw_plus}&sortBy=new_posting_date",
             "note": "Every Singapore role advertised to locals must be posted here first. Best single SG source."},
            {"name": "JobStreet — Singapore", "confidence": "standard",
             "url": "https://sg.jobstreet.com/jobs?keywords={kw_plus}&sortmode=ListedDate"},
            {"name": "JobStreet — Malaysia", "confidence": "standard",
             "url": "https://my.jobstreet.com/jobs?keywords={kw_plus}&sortmode=ListedDate"},
            {"name": "JobsDB — Hong Kong", "confidence": "standard",
             "url": "https://hk.jobsdb.com/jobs?keywords={kw_plus}&sortmode=ListedDate"},
            {"name": "JobsDB — Thailand", "confidence": "standard",
             "url": "https://th.jobsdb.com/jobs?keywords={kw_plus}&sortmode=ListedDate"},
            {"name": "LinkedIn — Singapore", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Singapore&f_TPR=r604800&sortBy=DD"},
            {"name": "Indeed — Singapore", "confidence": "standard",
             "url": "https://sg.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date"},
            {"name": "Indeed — Malaysia", "confidence": "standard",
             "url": "https://malaysia.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date"},
            {"name": "Glassdoor — Singapore", "confidence": "standard",
             "url": "https://www.glassdoor.sg/Job/jobs.htm?sc.keyword={kw_plus}"},
        ],
    },
    {
        "id": "anz",
        "label": "Australia & NZ",
        "icon": "■",
        "blurb": "Skilled-visa friendly for IT management. Seek is the market; everything else is secondary.",
        "sites": [
            {"name": "Seek — Australia", "confidence": "standard",
             "url": "https://www.seek.com.au/jobs?keywords={kw_plus}&sortmode=ListedDate"},
            {"name": "Seek — Australia, remote", "confidence": "standard",
             "url": "https://www.seek.com.au/jobs?keywords={kw_plus}&workarrangement=2&sortmode=ListedDate"},
            {"name": "Seek — New Zealand", "confidence": "standard",
             "url": "https://www.seek.co.nz/jobs?keywords={kw_plus}&sortmode=ListedDate"},
            {"name": "LinkedIn — Australia", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Australia&f_TPR=r604800&sortBy=DD"},
            {"name": "Indeed — Australia", "confidence": "standard",
             "url": "https://au.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date"},
        ],
    },
    {
        "id": "pk",
        "label": "Pakistan",
        "icon": "●",
        "blurb": "Local market, plus the growing set of Pakistan-based roles serving overseas clients.",
        "sites": [
            {"name": "Rozee.pk", "confidence": "verified",
             "url": "https://www.rozee.pk/job/jsearch/q/{kw_slug_space}"},
            {"name": "Mustakbil", "confidence": "standard",
             "url": "https://www.mustakbil.com/jobs/search?q={kw_plus}"},
            {"name": "Bayt — Pakistan", "confidence": "verified",
             "url": "https://www.bayt.com/en/pakistan/jobs/{kw_slug}-jobs/"},
            {"name": "LinkedIn — Pakistan", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=Pakistan&f_TPR=r604800&sortBy=DD"},
            {"name": "Indeed — Pakistan", "confidence": "standard",
             "url": "https://pk.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date"},
        ],
    },
    {
        "id": "west",
        "label": "UK, Europe & Americas",
        "icon": "▼",
        "blurb": "Your current UK employer and Portsmouth degree help here. UK Skilled Worker sponsorship is well-trodden for IT management.",
        "sites": [
            {"name": "LinkedIn — United Kingdom", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=United%20Kingdom&f_TPR=r604800&sortBy=DD"},
            {"name": "Indeed — UK", "confidence": "standard",
             "url": "https://uk.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date"},
            {"name": "Glassdoor — UK", "confidence": "standard",
             "url": "https://www.glassdoor.co.uk/Job/jobs.htm?sc.keyword={kw_plus}"},
            {"name": "Totaljobs — UK", "confidence": "standard",
             "url": "https://www.totaljobs.com/jobs/{kw_slug}"},
            {"name": "UK licensed visa-sponsor register", "confidence": "landing",
             "url": "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers",
             "note": "Official Home Office list. Search the employer's name here before spending time on a UK application."},
            {"name": "LinkedIn — European Union", "confidence": "standard",
             "url": "https://www.linkedin.com/jobs/search/?keywords={kw}&location=European%20Union&f_TPR=r604800&sortBy=DD"},
            {"name": "Indeed — Canada", "confidence": "standard",
             "url": "https://ca.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date"},
            {"name": "Indeed — United States", "confidence": "standard",
             "url": "https://www.indeed.com/jobs?q={kw_plus}&fromage=7&sort=date"},
        ],
    },
]

MARKET_IDS = [m["id"] for m in MARKETS]


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


def all_keywords() -> list[str]:
    """Every crawl keyword, derived from ROLES so the two can't drift apart."""
    kws = []
    for r in ROLES:
        for k in r["keywords"]:
            if k not in kws:
                kws.append(k)
    return kws


def as_portal_data() -> dict:
    return {
        "roles": [
            {"id": r["id"], "label": r["label"], "blurb": r["blurb"],
             "term": r["site_term"], "altTerms": r.get("alt_terms", []),
             "keywords": r["keywords"]}
            for r in ROLES
        ],
        "markets": [
            {"id": m["id"], "label": m["label"], "icon": m["icon"],
             "blurb": m["blurb"],
             "sites": [{"name": s["name"], "url": s["url"],
                        "confidence": s["confidence"], "note": s.get("note", "")}
                       for s in m["sites"]]}
            for m in MARKETS
        ],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(as_portal_data(), indent=2))
