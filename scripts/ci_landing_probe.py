# -*- coding: utf-8 -*-
"""Did the landing page have anything real to show? Run under `odoo shell`.

    odoo shell ${ARGS} -d <db> --no-http < scripts/ci_landing_probe.py

WHY THIS EXISTS AS WELL AS THE TESTS
------------------------------------
`test_every_amount_equals_its_source_report` compares every figure with its
source. On a database where every figure is unavailable — a company that has
posted nothing — that comparison is 0.0 == 0.0 five times and passes by having
nothing to do. The test is still correct: it must pass on an empty tenant,
because rule 4 says the page has to be right there too.

So the question "was the comparison meaningful" is a fact about the DATABASE,
not about the code, and it belongs in the job rather than in the test. This
prints it:

    SAPIAN-LANDING lines=<n> available=<n> nonzero=<n> unavailable_with_reason=<n>

and the job requires `nonzero` to be at least 3 on the demo database. A run
where the demo data stopped loading then fails here instead of reporting a
green comparison over five zeros.

The window is the month the PAGE reads — the one that has finished — and the
demo tenant is built to trade in the three months before the build for exactly
that reason. It is not "whichever month happens to have data": that would make
the probe a proxy for the thing it is supposed to prove.
"""

import datetime

# THE MONTH THE PAGE ITSELF READS, not a pinned one and not "whichever month
# has data". The landing page shows the month that has FINISHED, because that
# is the month with a filing deadline attached, and the demo tenant now trades
# in the three months before the build for the same reason. Asking the probe
# about any other month would make it a proxy for the thing it is supposed to
# prove.
_TODAY = datetime.date.today()
_FIRST_OF_THIS = _TODAY.replace(day=1)
_LAST_OF_PREV = _FIRST_OF_THIS - datetime.timedelta(days=1)
WINDOW = (_LAST_OF_PREV.replace(day=1), _LAST_OF_PREV)

# THE COMPANY THAT HAS DATA, and not `search([], limit=1)`.
#
# The first version took the first company and got Odoo's stock "My Company",
# which has no Ethiopian chart and no entries — so the page it built was
# correctly all-unavailable, and the job correctly failed on `nonzero=0`. The
# demo trader provisions its OWN company through the onboarding wizard, and that
# is the tenant this step is named after.
#
# Chosen by counting posted lines in the window rather than by name: a probe
# that greps for "Selam General Trading PLC" breaks the day the demo tenant is
# renamed, and would then report zero figures as a landing-page defect.
# Counted per company with `search_count` rather than grouped: `read_group` is
# gone from the public API in Odoo 19 and `_read_group`'s return shape has moved
# between versions, and a probe that breaks on an ORM rename would read as a
# landing-page defect. There are a handful of companies; the loop is free.
candidates = []
for candidate in env["res.company"].search([]):  # noqa: F821
    posted = env["account.move.line"].search_count(  # noqa: F821
        [
            ("company_id", "=", candidate.id),
            ("parent_state", "=", "posted"),
            ("date", ">=", WINDOW[0]),
            ("date", "<=", WINDOW[1]),
        ]
    )
    if posted:
        candidates.append((posted, candidate))
candidates.sort(key=lambda row: -row[0])

if not candidates:
    print("SAPIAN-LANDING lines=0 available=0 nonzero=0 unavailable_with_reason=0")
    print("SAPIAN-LANDING blank_without_reason=0")
    print(
        "SAPIAN-LANDING ABORTED no company posted anything between %s and %s, so "
        "there is no tenant with data to measure" % WINDOW
    )
    raise SystemExit(0)

posted_lines, company = candidates[0]
print(
    "SAPIAN-LANDING chose company=%s posted_lines=%d"
    % (company.name, posted_lines)
)
landing = env["sapian.landing"].with_company(company).create(  # noqa: F821
    {"company_id": company.id, "date_from": WINDOW[0], "date_to": WINDOW[1]}
)
landing._build_lines()

amounts = landing.line_ids.filtered(lambda ln: ln.kind == "amount")
available = amounts.filtered("available")
nonzero = available.filtered(lambda ln: abs(ln.value) > 0.005)
missing = amounts.filtered(lambda ln: not ln.available)

print(
    "SAPIAN-LANDING lines=%d available=%d nonzero=%d unavailable_with_reason=%d"
    % (
        len(landing.line_ids),
        len(available),
        len(nonzero),
        len(missing.filtered("unavailable_reason")),
    )
)
print("SAPIAN-LANDING company=%s period=%s" % (company.name, landing.period_label))
for line in amounts:
    # THE PERIOD IS PRINTED BESIDE THE FIGURE, because the four filings are no
    # longer all counted in the same calendar: employment income tax is an
    # Ethiopian month and the other three are Gregorian months today. A figure
    # without its period is the defect this whole change was about.
    print(
        "SAPIAN-LANDING figure %-16s %-12s %-28s %s"
        % (
            line.key,
            ("%.2f" % line.value) if line.available else "UNAVAILABLE",
            line.period_label or "-",
            line.unavailable_reason or "",
        )
    )
# EVERY unavailable figure must carry a reason. Asserted here as well as in the
# tests because this is the run that looks at a real tenant's data, and a blank
# cell on a client's screen is the failure this whole feature is about.
blank = missing.filtered(lambda ln: not ln.unavailable_reason)
print("SAPIAN-LANDING blank_without_reason=%d" % len(blank))
