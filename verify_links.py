#!/usr/bin/env python3
"""
verify_links.py -- re-check every deep link in job_sites.py.
============================================================

Job sites change their URL formats. This script builds every link the portal
would render (for the first launcher term) and reports the HTTP status of
each, so a format change shows up as a 404 instead of silently sending you
to a dead page.

    python3 verify_links.py

Read the output like this:
    200 / 30x  -- fine
    403        -- fine, almost certainly. Big job boards block automated
                  requests but serve the page normally in a real browser.
                  This script cannot tell a "correct URL that blocks bots"
                  apart from a wrong one, so 403s need a manual click.
    404        -- the URL format has changed. Fix that entry in job_sites.py.
    timeout    -- try again; the site may be slow or geo-gating.

Run it monthly, or after a site visibly stops working.
"""

import sys
import urllib.request
import urllib.error
from urllib.parse import quote

from job_sites import SITE_GROUPS, LAUNCHER_TERMS, slugify

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def build(tpl: str, term: str) -> str:
    return (tpl
            .replace("{kw_slug_space}", quote(term.lower()))
            .replace("{kw_slug}", slugify(term))
            .replace("{kw_plus}", quote(term).replace("%20", "+"))
            .replace("{kw}", quote(term)))


def check(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA},
                                 method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return str(resp.status)
    except urllib.error.HTTPError as e:
        return str(e.code)
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__}"


def main() -> int:
    term = sys.argv[1] if len(sys.argv) > 1 else LAUNCHER_TERMS[0]
    print(f"Checking every deep link with term: {term!r}\n")
    problems = 0
    for grp in SITE_GROUPS:
        print(f"── {grp['group']}")
        for site in grp["sites"]:
            url = build(site["url"], term)
            status = check(url)
            flag = ""
            if status == "404":
                flag = "  <-- BROKEN, fix job_sites.py"
                problems += 1
            elif status.startswith("ERR"):
                flag = "  <-- check manually"
            print(f"   {status:>10}  {site['name']}{flag}")
            if flag:
                print(f"               {url}")
        print()
    print(f"Done. {problems} link(s) returned 404 and need fixing.")
    print("403s are expected on the big boards and are not failures — "
          "click one in a browser to confirm.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
