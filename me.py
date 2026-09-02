#!/usr/bin/env python3
"""
me.py -- YOUR details, YOUR resumes, YOUR cover-note templates.
====================================================================

Fill this in ONCE. Every "Apply Kit" in the portal is then generated from
it: the right resume for the role, a tailored cover note, and every answer
you get asked on an application form, ready to copy.

Anything marked TODO is a field recruiters actually ask for. Leave one blank
and you'll be typing it by hand every single time.

Nothing here is secret -- no passwords, no keys. It's the same information
you'd put on a CV. Still, if your repo is public, consider whether you want
your phone number in it (the portal works fine with it removed).
"""

# ---------------------------------------------------------------------------
# 1. YOUR DETAILS -- these fill the "Application answers" panel
# ---------------------------------------------------------------------------

PROFILE = {
    "name":            "Muhammad Wasim Abbas",
    "email":           "wasim.ab@gmail.com",
    "phone":           "+92 300 1701809",
    "location":        "Lahore, Pakistan",
    "linkedin":        "https://linkedin.com/in/m-wasimabbas",
    "years":           "18+",

    # ---- TODO: fill these five in. They are the ones you get asked most. --
    "nationality":     "TODO — required on every Gulf application",
    "notice_period":   "TODO — e.g. 'Immediate' or '30 days'",
    "visa_status":     "TODO — e.g. 'Requires sponsorship' / 'Visit visa eligible'",
    "salary_expect":   "TODO — a range, e.g. 'USD 70–90k' or 'AED 30–38k/month'",
    "driving_licence": "TODO — matters more than you'd think in the GCC",
    # ----------------------------------------------------------------------

    "work_pref":       "Remote preferred; open to relocation for the right role",
    "relocation":      "Yes — GCC, Singapore / SE Asia, Australia, UK",
    "availability":    "Available for interview at short notice across GST, SGT, GMT",
}

# ---------------------------------------------------------------------------
# 2. YOUR RESUMES
#
# Put your PDFs in a `resumes/` folder in the repo and commit them. The Apply
# Kit then links straight to the right one. If a file isn't there, the link
# simply won't show -- nothing breaks.
# ---------------------------------------------------------------------------

RESUMES = {
    "concur":  {"file": "resumes/02-sap-concur-consultant.pdf",
                "label": "SAP Concur Consultant version"},
    "itsm":    {"file": "resumes/03-itsm-support-manager.pdf",
                "label": "ITSM / Support Manager version"},
    "gcc":     {"file": "resumes/04-gulf-gcc.pdf",
                "label": "Gulf / GCC version"},
    "master":  {"file": "resumes/01-master-ats.pdf",
                "label": "Master ATS version"},
}


def resume_for(role: str, markets: list) -> str:
    """Which resume to send. Gulf beats role; Concur beats everything else."""
    if "gcc" in markets:
        return "gcc"
    if role == "concur":
        return "concur"
    if role in ("appsupport", "servicedelivery"):
        return "itsm"
    return "master"


# ---------------------------------------------------------------------------
# 3. COVER NOTE
#
# {company} {title} {role_label} {opening} {proof} are filled per listing.
# Keep it SHORT. Three paragraphs beats one page, every time.
# ---------------------------------------------------------------------------

COVER_TEMPLATE = """Dear Hiring Team,

I'm applying for the {title} role at {company}. {opening}

{proof}

I'm {availability_short}, and my notice period is {notice_period}. {visa_line} I'd welcome the chance to talk through how this maps to what your team needs.

Kind regards,
{name}
{phone} · {email}
{linkedin}"""

# One opening line per role -- the hook that says "I've actually done this".
OPENINGS = {
    "concur":
        "I've spent much of the last decade delivering SAP Concur: I directed "
        "the end-to-end global rollout of Concur Travel & Expense across 20+ "
        "regions at Worley, and led localised country-by-country "
        "implementations across APAC at Jacobs.",
    "appsupport":
        "I've run global application support at scale — most recently for "
        "30,000+ enterprise users across the US, APAC and EMEA, holding 99.9% "
        "uptime while adapting support frameworks to each region's compliance "
        "requirements.",
    "servicedelivery":
        "I'm an ITIL v4 certified service delivery lead who has chaired Change "
        "Advisory Boards and Major Incident Management, lifted SLA compliance "
        "by 25% and cut MTTR by 30% through real-time KPI dashboards and "
        "ServiceNow process redesign.",
    "dms":
        "I managed enterprise Document Management Systems at 99% reliability "
        "through high-intensity engineering project lifecycles at Jacobs, "
        "including UAT, deployment scheduling and change governance for "
        "large-scale system upgrades.",
    "programme":
        "I've led global IT programmes end to end — a 20+ region SAP Concur "
        "rollout, a full enterprise application migration through the "
        "Jacobs–Worley M&A integration, and a technical demerger delivered "
        "on-site in the USA.",
    "other":
        "I bring 18+ years of international enterprise IT experience across "
        "APAC, EMEA and North America, spanning SAP Concur delivery, global "
        "application support and IT programme management.",
}

# The second paragraph — evidence. Kept factual and defensible.
PROOFS = {
    "concur":
        "Across those programmes I configured Expense and Travel modules, "
        "policy groups and approval workflows to local regulatory "
        "requirements, built SQL-based executive compliance dashboards, and "
        "later owned Concur import and integration error resolution across a "
        "30,000-user estate. I've seen Concur from design through go-live and "
        "then lived with it in production — which tends to change the design "
        "decisions you make.",
    "appsupport":
        "I cut MTTR 30% by architecting an enterprise IT portal and "
        "self-service knowledge base, chaired Major Incident Management during "
        "critical outages as the primary client liaison to C-suite "
        "stakeholders, and managed zero-downtime release cycles for "
        "high-availability financial systems.",
    "servicedelivery":
        "Most recently I re-engineered ServiceNow assignment rules into a "
        "dynamic routing system allocating incidents across onshore and "
        "offshore units, and I hold accountability for global project controls "
        "across multiple time zones — critical-path milestones, resource "
        "availability and Tier-1 vendor licensing strategy.",
    "dms":
        "That work sat alongside corporate finance systems support and "
        "enterprise system integration, so I'm comfortable both with the "
        "document lifecycle itself and with the interfaces and data flows "
        "around it. I've also run training and knowledge transfer for 5,000+ "
        "end users during major rollouts.",
    "programme":
        "I act as the single point of contact for high-stakes go-lives and "
        "post-launch stabilisation, chair regional Change Advisory Boards, and "
        "author and test business continuity plans. My delivery record "
        "includes zero loss of critical operational data through a full M&A "
        "systems integration.",
    "other":
        "I'm ITIL v4 and ISTQB certified, have led onshore/offshore teams, "
        "negotiated with Tier-1 software vendors, and delivered training to "
        "5,000+ end users. I spent 13 years based in Singapore delivering "
        "enterprise SaaS for Tier-1 engineering and consulting firms.",
}

# Standard answers to the questions application forms ask over and over.
# Edit freely — these are yours.
STOCK_ANSWERS = [
    {"q": "Why are you interested in this role?",
     "a": "It's a direct match for what I've actually delivered — {role_label} "
          "work at enterprise scale across multiple regions — and {company} "
          "operates at the kind of scale where that experience compounds "
          "rather than sits idle."},
    {"q": "What is your greatest strength?",
     "a": "Being the single accountable point of contact on complex, "
          "multi-country delivery. I've held that role through a 20+ region "
          "Concur rollout, an M&A systems integration and a technical "
          "demerger, and the common thread is that nothing gets lost between "
          "teams or time zones."},
    {"q": "Why are you leaving / looking?",
     "a": "I'm looking for a role where SAP Concur and enterprise service "
          "delivery are the core of the job rather than one part of it, and "
          "where I can commit long-term. My track record is 18 years with "
          "long tenures, not short hops."},
    {"q": "Notice period / availability",
     "a": "{notice_period}. {availability}"},
    {"q": "Are you eligible to work in this location?",
     "a": "{visa_status} I'm actively seeking roles with sponsorship and can "
          "relocate at short notice."},
]


def as_portal_data() -> dict:
    return {
        "profile": PROFILE,
        "resumes": RESUMES,
        "coverTemplate": COVER_TEMPLATE,
        "openings": OPENINGS,
        "proofs": PROOFS,
        "stockAnswers": STOCK_ANSWERS,
    }
