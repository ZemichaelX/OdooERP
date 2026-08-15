# CLAUDE.md — SapianERP

## What this project is
A configurable ERP product for Ethiopian companies, built as custom Odoo 19 Community
addon modules. Two module families:
- `l10n_et_*` : reusable Ethiopian localization (tax, payroll, calendar, Amharic, compliance)
- `sapian_*`  : product features (onboarding, theme, dashboards, integrations)

Each client runs an isolated Dockerized Odoo instance. Design every module to also work
in a future multi-tenant SaaS (no hard-coded company assumptions; respect `company_id`).

## Absolute rules
1. NEVER modify Odoo core. Extend via Python inheritance (`_inherit`) and XML view
   inheritance (`xpath`) only. All product code lives in `addons/`.
2. One responsibility per module. Every model field, method, and view ships with a
   test and a docstring.
3. Respect multi-company: filter by `company_id`; never leak data across companies.
4. Tax rates, PAYE bands, pension %, thresholds are CONFIGURATION DATA in dedicated
   config models / data files with effective dates — NEVER hard-coded in business logic.
   Changing a future rate must never alter historical payslips/entries.
5. Money uses Odoo currency rounding utilities, never naive floats.
6. Secrets (SMTP, Telebirr keys, DB creds) come from environment variables or a
   gitignored runtime file, never committed. See also "A secret in a transcript is a
   published secret" below.
7. All user-facing strings use Odoo translation (`_()`), so Amharic can be added.
8. Least privilege: define security groups + `ir.model.access.csv` (+ record rules where
   multi-company/portal-exposed) for every new model.
9. Do not add a Python dependency without noting it in the module manifest.
10. Business logic testable without a running Odoo (e.g. tax math) lives in a plain-Python
    `reference/` file with pytest tests, and the Odoo model calls it.

## Repo layout
- addons/          custom modules (l10n_et_*, sapian_*)
- vendor/          third-party addons copied VERBATIM at a pinned upstream commit.
                   Never edited in place; never linted as ours (our .pylintrc
                   requires our own author). `scripts/check_vendor.sh` proves each
                   tree still hashes to its pin. See vendor/README.md.
- docker/          Dockerfile, docker-compose
- config/          odoo.conf.example — TEMPLATE ONLY, never a real value
- scripts/         provisioning, backup helpers
- data-templates/  spreadsheet import templates for onboarding
- docs/            architecture & module docs (the master planning package)

## How to run locally
    ./scripts/install_hooks.sh    # once per clone: gitleaks pre-commit secret scan
    cp .env.example docker/.env   # set DB_PASSWORD etc. (compose's project dir
                                  # is docker/, so it reads docker/.env)
    cp config/odoo.conf.example config/odoo.runtime.conf   # runtime config compose mounts
                                  # (gitignored; replace admin_passwd = CHANGEME.
                                  #  provision_client.sh generates one for you)
    docker compose -f docker/docker-compose.yml up -d
    # open http://localhost:8069

Install / update modules:
    docker compose -f docker/docker-compose.yml run --rm odoo \
      odoo -d sapianerp -i sapian_core,l10n_et_payroll --stop-after-init

Run Odoo module tests:
    docker compose -f docker/docker-compose.yml run --rm odoo \
      odoo -d sapianerp -u l10n_et_payroll --test-enable --stop-after-init

Run the fast pure-Python payroll tests (no Odoo needed):
    pytest addons/l10n_et_payroll/reference/

## A secret in a transcript is a published secret
A generated secret is written to its gitignored destination and **never echoed**.
Not to stdout, not into a report, not into a PR body, not into a commit message,
not into a log file. Say WHERE it lives, never WHAT it is.

This rule was missing, and its absence burned a password within minutes of that
password being created: the master password was rotated correctly into
`config/odoo.runtime.conf` — and then printed in plain text in a handover report,
which is a chat log, which is storage. Rotating a secret and then publishing it
is not rotation. The second password had to be rotated too.

Concretely:
- Generate straight into the destination file. `python3 - >/dev/null` or a
  redirect, so the value has no path to a terminal.
- Report the SHAPE only: "master password regenerated in
  `config/odoo.runtime.conf`, 40 characters". That is enough for the operator to
  confirm the work happened.
- The operator reads it from the file. That is the handover channel.
- After any rotation, grep the tracked tree, the full history, commit messages,
  the PR body and the scratch directory for the old value, and say where you
  looked.
- The same applies to anything a scanner would flag: API tokens, DSNs, dumps
  containing customer data. If you would not commit it, do not type it.

`scripts/lib/preflight.sh::ensure_runtime_conf` deliberately prints the password
it generates — that is an OPERATOR-facing terminal, run by the person who needs
the value, and it is the documented handover for provisioning. An agent report is
not that terminal.

## A success signal that can be produced by doing nothing is not a success signal
Four failures in two days shared one shape: the happy path and the do-nothing
path were indistinguishable.

- `backup.sh` wrote seven **0-byte** files that looked like backups.
- the catalog sync reported **success on an empty table**.
- the PAYE migration **skipped an archived company** and said nothing.
- the Odoo suite **exited 0 having run 10 tests instead of 222**, because a
  failed database drop made `-i` a no-op. Nothing failed, so nothing failed.

Before trusting any check, ask: *if the work had not happened at all, would this
still be green?* If yes, the check is decoration. Fix it by asserting the
positive and the size, never the absence of an error:

- assert a MINIMUM (tests executed, rows migrated, bytes written) — zero and
  "nearly zero" must both be failures.
- assert the operation REPORTED (a result line, a status file), not merely that
  no error appeared.
- make preconditions HARD: if a database drop, a container start, or a file
  removal fails, abort — do not continue against whatever was already there.
- prove a new guard **discriminates**: make the bad thing happen on purpose and
  watch the check go red. An untested guard is another thing that passes by
  doing nothing.

Enforced in CI at `.github/workflows/ci.yml` (`MIN_EXPECTED_TESTS`), in
`scripts/backup.sh` (size + `pg_restore --list` + `tar tzf`, and a written
`LAST_BACKUP_STATUS`), and in `scripts/build_demo.sh` (the `CHECK` block).

## A run that could not start is not a run that failed

Same family as the rule above, and it bites in the opposite direction: instead
of a green that means nothing, a RED that means nothing — and a red that means
nothing gets written into a README as evidence.

Caught by one turn's margin. A loop measuring how often a flaky test fails
recorded **8 of 8 red**. Postgres had stopped; every one of the eight was
`connection refused` before a single test ran. Reported as-is it would have put
a fabricated 8-of-8 before-rate into the module README, the changelog and a PR
body, and made the fix that followed look far more valuable than it was.

So any measurement loop **asserts its own preconditions on every iteration**,
and reports three outcomes, never two:

- **ABORTED** — the precondition failed (database unreachable, container down,
  fixture missing). The iteration measured nothing. Do not count it.
- **INVALID** — it ran but produced no result line to read. Also not a failure;
  it is an unusable sample.
- **RED** — the thing under test actually failed.

Concretely: check `pg_isready` (or the equivalent) inside the loop rather than
once before it; require the tool's own result line to be present before
recording an outcome; and print the distinct label, so the tally cannot silently
absorb infrastructure into signal. The pattern is in
`scratchpad`-style measurement scripts and in `scripts/build_demo.sh`'s phase
assertions.

## Zero failures after a fix proves the fix broke nothing

It proves a **cure** only if there was an observed failure before it. Say which
one you have, in the same sentence as the number.

Two measurements taken the same week, both reported as "0 red of 10", and only
one of them was a fix:

- `TestSapianAppRailOverflow` — **3 red of 4 runs** before the settle wait, 0 of
  10 after. That is a cure, and the before-figure is what makes it one.
- `RAIL_RENDERS_JS` — **0 red of 10** at 14 apps and **0 red of 8** at 36 apps
  BEFORE any change. It had never failed. The change removed an assertion that
  could not fail (every tile fitted, so the scroll was a no-op) and replaced
  accidental protection with a stated one. 0-red afterwards proves only that
  nothing broke.

Both are worth doing. Only the first is worth describing as fixing a flake.
When the before-rate is zero, write that the change is prophylactic and say what
it removes — do not let a green after-figure imply a cure that was never
demonstrated. The same applies to sample sizes: an invented denominator is worse
than an ugly one, so report the sample you actually ran even when the two halves
do not match.

## Platform-specific fixes must be verified on that platform
A fix for a platform-specific failure is NOT verified until it is verified on
that platform. Linux evidence is not proof for a Windows bug.

This rule was written after a Windows-only backup failure was "fixed" with
Linux-only verification: every check passed, and the delivered script could not
run on Windows at all — strictly worse than before, because nothing backed up
until it was found by hand.

- If the platform is not available in the session, say so **explicitly in the
  report** and mark the item **UNVERIFIED**. Do not present Linux evidence as
  proof of a Windows fix.
- State the exact commands the operator should run on the real platform, and
  treat the item as open until they report back.
- The ops scripts are run from **Git Bash on Windows**. Anything touching
  paths, `docker compose -f`, MSYS argument conversion, forking, or line
  endings is platform-sensitive by default — assume it needs Windows proof.

## Definition of Done (every task)
- Tests pass (pytest reference tests + Odoo module tests where relevant)
- Lint clean — run `./scripts/lint.sh`, which is the SAME script CI's lint job
  and the pre-push hook run, and which gates on exit codes. Do not run the three
  tools by hand and read their output: pylint prints "rated at 10.00/10" and
  still exits 4 on warnings, and a red CI build has already come from exactly
  that misreading.
- Security/access rules defined for new models
- Strings translatable; Amharic .po updated if user-facing
- Module README updated; no changes to Odoo core

## When unsure
Prefer configuration over code. Prefer extending an existing Odoo app over a new one.
Re-verify tax/PAYE/pension figures against the Ministry of Revenue before a payroll go-live.

## Build backlog
Implemented so far: repo skeleton (S0), sapian_core starter (S0-4/S1-1/S1-2),
l10n_et_payroll PAYE + pension engine (S1-7/S1-8) with tests, l10n_et_base
Ethiopian accounting (Epic 3: extends core l10n_et chart 'et'; WHT automation
3%/30%/15% with effective-dated config incl. punitive_respects_thresholds flag;
cash cap warn/block; partner TIN/licence compliance; WHT certificate + ET VAT
invoice reports; 33 Odoo tests + 45 fast goldens), Epic A payroll workflow
(l10n_et_payroll v2: batch runs on hr.version wages — no hr_contract in Odoo 19;
input lines; aggregated PAY-journal posting; bank CSV; payslip PDF; PAYE
declaration + pension remittance with missing-TIN/POESSA-ID warnings; employee
TIN + pension ID fields; 21 Odoo tests), Epic B statutory reports
(l10n_et_reports: monthly VAT declaration + WHT summary, live from posted moves,
GL tie-out with visible MISMATCH warnings, PDF + CSV, MISSING-TIN markers;
18 Odoo tests; verify layouts vs current MoR forms before filing), and Epic C
onboarding + demo tenant (sapian_core wizard: profile/TIN/fiscal year/ETB/logo/
primary color/module picks, unattended fresh-DB proof; sapian_demo_trader:
"Selam General Trading PLC" provisioned via the wizard with a golden-tested
July-2026 month exercising every compliance path; 14 Odoo tests), and pharma
vertical session 1 (vertical_pharma: is_pharma batch discipline w/ mandatory
expiry + FEFO, expiry escalation states + one-digest-per-company cron,
expired-delivery block/warn policy, GS1 DataMatrix capture in
reference/pharma_calc.py, import dossiers IMP/..., branded batch recall report
with customer phone/city, EFDA export stub pending specs; 13 Odoo tests + 12
fast goldens; sapian_demo_pharma: "Tena Pharma Import PLC" pitch tenant with
730-day shelf lives, three-stage batches, pre-fired digest and the B-123
recall golden incl. precision-by-exclusion; 7 Odoo tests; both installed on
scratch_final).

Navigation (Aug 2026): OCA `web_responsive` is vendored at a pinned commit in
`vendor/oca_web/` and is now in the SHIPPED default set — `provision_client.sh`,
`build_demo.sh` and CI's main install list — for the same reason `sapian_theme`
is: it is the product's navigation, and a tenant without it opens on the Module
Catalog, a configuration screen. `sapian_theme` defaults its two per-user
settings so a user lands on the fullscreen launcher in the house brand.

INSTALLING IT IS NOT ENOUGH, and this is the trap: the admin of a demo or client
tenant is created in the `-i base` phase, BEFORE web_responsive owns the field,
so `default_get` never reaches it and the column default (Module Catalog, lilac)
wins for the one user in every screen recording. Both scripts therefore call
`env['res.users']._sapian_apply_launcher_defaults(dry_run=False)` during
provisioning — a provisioning step, never a migration — and then assert the
result from the artefact via `verify_launcher` (scripts/lib/check_launcher.py).
For a tenant that already exists, that one call is the fix.

AND THE PATH IS NOT ENOUGH EITHER. A module that is `installed` in the database
but absent from the SERVING process's addons_path delivers zero JS and zero CSS
with no warning and no exception — `ir.asset` reads manifests from
`registry._init_modules`, so an unreachable module is skipped in silence while
`state` still reads `installed` and the page still looks branded. Two guards,
both proved red: `assert_addons_path` before phase 1, and `verify_launcher`,
which fetches the backend bundle the webclient loads and asserts the launcher
component is in it BY NAME. Note that a running server keeps the path it
started with — fixing the config means restarting the stack.

Our own app rail is kept: the two do not conflict, and the rail solves a problem
the launcher does not. Evidence and the refresh procedure are in
`vendor/README.md` and `addons/sapian_theme/README.md`.

BUILD PHASE COMPLETE except client-pitch work — next: sales (demo the trader
and pharma tenants, proposal from the DAT template in docs/plan-2026/01).
Pharma session 2 (medicine-request portal, delivery runs, partner directory,
SMS, EFDA live API) and everything in the DEFERRED list stay unbuilt until a
client signs.

REVISED ORDER (July 2026, token-conscious — supersedes the epic ordering in
docs/10-claude-code-roadmap.md and 01_CLAUDE_CODE_BUILD_SPEC §8 for now; those
remain the task-level detail):
- Epic A — Payroll workflow completion (l10n_et_payroll): payslip batch run,
  payroll journal posting (salary expense, PAYE/pension payables), bank salary
  transfer export, branded payslip PDF (EN), PAYE monthly declaration + pension
  remittance reports. Overtime = manual payslip input line in v1 (no attendance
  engine). Skip: severance calculator, Amharic payslip, Telebirr payout.
- Epic B — Statutory reports slice (l10n_et_reports): monthly VAT declaration
  export + WHT summary (certificate exists from Epic 3). Skip: EC-period columns,
  IFRS statement engine (use Odoo/OCA reports).
- Epic C — Thin onboarding + demo tenant: minimal company-profile wizard (TIN,
  fiscal year, ETB, module picks from sapian_core catalog), light branding only
  (logo + primary color), one demo tenant (stock, sale, purchase, account, hr +
  our modules) with realistic Ethiopian demo data.
- DEFERRED until a client signs (do NOT start even though specs exist):
  verticals other than pharma session 1 (built Jul 2026 as the DAT pitch),
  pharma session 2, payments/SMS, e-invoice, Ethiopian calendar, full
  theme/debrand, BI.
Goal: a sellable standalone Payroll+HR product and a sellable Essential/Business
ERP for a generic trader, with minimal token spend.

## Planning refresh (July 2026): docs/plan-2026/
docs/plan-2026/ is the v2 master-planning package (researched Jul 2026). Where it and the
older docs disagree, plan-2026 wins on: strategy/pricing/packaging (03), market facts and
CURRENT TAX RULES (02, 07 — e.g. WHT is now 3% with 20k/10k thresholds, TOT abolished,
VAT threshold 2M), customization/white-label spec (06), delivery methodology (09), and
high-level epic ordering (10). The older 01_CLAUDE_CODE_BUILD_SPEC remains the detailed
task-level spec; map its tasks into plan-2026 epics as you go. PAYE bands and pension
rates in the built payroll engine already match Proc 1395/2025 — no rework needed there.
plan-2026/CLAUDE.md is a reference copy; THIS file is authoritative.

## Accountant-verified tax facts (Jul 2026 review — seeded as config; supersede older figures)
- Cash cap: ETB 50,000 per party — single transaction OR same-day aggregate, whichever
  hits first (Art. 81, Proc 1395/2025; cross-verified vs KPMG's proclamation copy).
  The 30,000 figure in older docs is superseded.
- Allowances: transport exempt up to LOWER of 2,200/month or 25% of basic (excess
  taxable, engine-computed); hardship exempt; medical actual-cost exempt; housing and
  position TAXABLE. Per-diem = evidence-based input line, no monthly formula.
- Pension (Proc 1268/2022): mandatory for Ethiopian nationals; foreign nationals of
  Ethiopian origin voluntary (opt-in flag on employee); other foreigners excluded.
- WHT defaults CONFIRMED: either TIN or licence missing → 30% punitive; thresholds gate
  all WHT including punitive. Authority may aggregate deliberately split invoices.
- VAT: excess input VAT carries forward by default (refunds = exporter/investor
  processes). Reg 570/2025: real-time EFD + QR invoices for VAT-registered traders
  (simplified invoice ≤ 10,000) — fiscal-device integration is high priority for retail.
- Filing: Category A via etax.mor.gov.et, others via regional bureaus; pension via
  POESSA declaration + bank slip within 30 days. MoR beneficiary accounts (future
  payment-instruction printout): pension 1000140034057, VAT/profit tax 1000140046047.
