# Daily Job Search Portal

Searches for roles matching your background, flags remote + possible
visa-sponsorship mentions, shows the relevant bit of your resume next to
each match, and rebuilds a simple status page every day. Runs on GitHub's
free tier -- no Claude account, no server, nothing to keep open.

`index.html` in this folder is a **sample preview** built from fake data so
you can see the look before connecting anything real. Once you follow the
steps below, it'll rebuild itself daily with actual listings.

## What this does *not* do, on purpose

It does not create accounts on job sites or submit applications for you.
Every listing links straight to the real posting so you apply in one click
once you've glanced at it. Two reasons:

- The only legitimate way to search programmatically (used here) is a
  search-only API -- there's no "submit" endpoint to hook into.
- Most real applications have custom questions, and a handful of employers'
  systems actively flag/reject bot-submitted applications. A silent
  auto-submit bot is more likely to hurt an application with 18 years of
  real experience behind it than help it.

## Setup (about 5 minutes)

1. **Create a GitHub repo** (private is fine) and add these files, keeping
   the folder structure exactly as-is -- `.github/workflows/` must stay at
   the repo root for GitHub Actions to see it.

2. **Get a free Adzuna API key**: https://developer.adzuna.com/ -- sign up,
   no cost, takes about 2 minutes. You'll get an `App ID` and `App Key`.

3. **Add them as repo secrets** (not directly in the code):
   Repo -> Settings -> Secrets and variables -> Actions -> New repository
   secret
   - `ADZUNA_APP_ID`
   - `ADZUNA_APP_KEY`

4. **Enable GitHub Pages**: Settings -> Pages -> Source: "Deploy from a
   branch" -> Branch: `main`, folder `/ (root)`. You'll get a URL like
   `https://<yourusername>.github.io/<reponame>/` -- bookmark it, that's
   your portal.

5. **Trigger the first run**: Actions tab -> "Daily Job Search" -> "Run
   workflow". After it finishes (~1-2 min), refresh your Pages URL.

From then on it reruns automatically every day at 06:00 UTC (edit the cron
line in `.github/workflows/daily-job-search.yml` to change the time).

## Tuning it

Everything worth adjusting is in `job_search.py`, near the top:

- `KEYWORD_GROUPS` -- the search terms, now including `"Asta Powerproject"`.
  That tool isn't in your resume, so `EXPERIENCE_BANK["planning"]` points
  matches at your genuine critical-path / global-programme experience
  instead of claiming hands-on Asta experience you'd have to back up in an
  interview. If you *do* have real Asta Powerproject experience, add it to
  that bucket directly and it'll show up honestly from then on.
- `COUNTRIES` -- which Adzuna country indexes to search.
- `MAX_PAGES` -- results depth per search (raise once you've confirmed a
  clean first run; more pages = more API calls against your daily quota).
- `EXPERIENCE_BANK` -- the resume bullets shown under "Why you're a fit".
  Pulled from the resume you shared; edit freely, it's yours.
- `VISA_HINTS` / `REMOTE_HINTS` -- the keyword patterns used to flag
  listings. Best-effort text matching, not a guarantee -- always confirm
  sponsorship on the actual listing.

## If something looks off on the first real run

I wrote this against Adzuna's documented API shape but couldn't test a live
call from the environment I built it in (no outbound access to job-board
domains there). If a field comes back blank where you'd expect data (e.g.
company name, or every result has 0 listings), check the console output
from the Action's run log first -- it prints a warning line for anything
that failed, which usually points straight at the fix.
