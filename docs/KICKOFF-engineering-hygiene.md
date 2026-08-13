# KICKOFF — engineering hygiene

Standing backlog for the things that keep the repo safe to work in. Ordered:
item 1 is the one that has already cost us twice.

---

## 1. Secret scanning — gitleaks, as a PRE-COMMIT HOOK  *(done, Aug 2026)*

**Status: implemented.** Kept at the front of this list because it is the item
most likely to be quietly weakened later.

### What went wrong, twice

A live Odoo database master password (`admin_passwd`) sat in the git-tracked
`config/odoo.conf`.

- **First time**, during the ops-hardening review: `provision_client.sh` was
  appending the generated per-tenant secret to the tracked template. Fixed by
  writing secrets to a gitignored `config/odoo.runtime.conf` instead.
- **Second time**, found Aug 2026: the tracked `config/odoo.conf` again carried
  a real 31-character master password, plus a live `dbfilter = ^sapian_prod$`,
  both under comments literally reading *"LOCAL SECRET, DO NOT COMMIT"*.

The mechanism was the same both times and it was structural, not careless:
**the template and the working file were the same tracked path.** An operator
customising the file for their own instance was, unavoidably, editing a tracked
file. The comment saying "do not commit" is not a control; it is a wish.

### The controls now in place

| Control | Where | What it does |
|---|---|---|
| Template/working split | `config/odoo.conf.example` (tracked) vs `config/odoo.runtime.conf` (gitignored) | There is no tracked file an operator has any reason to edit with a real value. |
| `config/odoo.conf` gitignored | `.gitignore` | The old path cannot come back even by habit or by `git add -A`. |
| Placeholder is not a password | template ships `admin_passwd = CHANGEME` | — and `ensure_runtime_conf` treats CHANGEME as UNSET, generates a real secret, and **fails hard if CHANGEME survives**. Otherwise the fix would ship instances whose master password is the string CHANGEME: green because nothing happened. |
| **gitleaks pre-commit hook — THE ONLY CONTROL** | `.githooks/pre-commit`, `.gitleaks.toml` | Blocks the commit before it exists. Per-clone; see its limits below. |
| CI secret scan — **advisory** | `.github/workflows/secret-scan.yml` | Runs on every push and PR and turns red. **Cannot block a merge on this plan.** |
| Hook installer | `scripts/install_hooks.sh` | `core.hooksPath = .githooks`. |
| Placeholder assertion | secret-scan workflow | Independent of the pattern rules: fails if `config/odoo.conf.example` stops shipping `CHANGEME`. |

### Both layers, their real limits, and which one actually holds

Each layer has a genuine weakness. Neither is a guarantee. Write both down,
because a control described more strongly than it behaves is how the next leak
gets waved through.

**CI cannot block a merge here.** The repository is private on the GitHub
**Free** plan: rulesets require Team, classic branch protection requires Pro.
`secret-scan.yml` runs on every push and every pull request and turns the
`gitleaks` check red — but on Free a red check is a notification, not a gate.
Anyone can merge past it. **CI is ADVISORY.**

**A check that runs after the commit cannot stop the commit anyway.** By the
time CI speaks, the secret is in the object database, in the push, and in every
clone that fetched. Even required, CI would be containment, not prevention.

**The hook can prevent — but cannot be guaranteed to exist.** `core.hooksPath`
is per-clone git config and **cannot be committed**. On a fresh clone the hook
silently does not run, and *its absence produces no output at all* — the purest
form of the failure this repo keeps meeting: a success signal produced by doing
nothing. Demonstrated on 2026-08-11, when a test `admin_passwd` value was
staged into `config/odoo.conf.example` and committed cleanly (`cf25f3d`, local
only, reverted) on a machine where the installer had never been run. The tell
was `create mode 100644` in the commit output: the hook file was *new to that
checkout*, so the hook config had only ever been set in another environment.

So, as things actually stand:

- **The hook is the control.** It is the only mechanism that can stop a secret
  from becoming a commit. It is per-clone and manual, so installing and
  *verifying* it on every machine is a real operational step, not a nicety.
- **CI is the alarm.** A red `gitleaks` check means *a secret is already in the
  repository* — rotate it, do not merely fix the diff. `secret-scan.yml` is kept
  a separate workflow from `ci.yml` so it has a stable check name (ready to
  require if the plan ever changes) and so an unrelated failing lint step can
  never cancel it.

**Verified on Windows** by the maintainer on 2026-08-11 — Git Bash, gitleaks
8.30.1, `core.hooksPath` set, and both branches proved: refused to commit with
gitleaks absent, refused again with `SECRET DETECTED` once installed. That
closes the UNVERIFIED-on-Windows item below.

### If the plan ever moves to Pro or Team

Only then can `gitleaks` become a required status check and CI stop being
advisory: **Settings → Branches → branch protection rule for `master` → Require
status checks to pass before merging → add `gitleaks`.**

```bash
gh api repos/ZemichaelX/OdooERP/branches/master/protection \
  --jq '.required_status_checks.contexts'
# EXPECT the list to contain: gitleaks
# On Free this returns 404 Branch not protected — the current, expected state.
```

### The hook fails LOUD when gitleaks is missing

`.githooks/pre-commit` **exits non-zero if gitleaks is not on PATH**, with
install instructions. It does not skip.

That is deliberate and it is the whole point: a scanner that passes when it
cannot run is a success signal produced by doing nothing — the failure shape
recorded in `CLAUDE.md`. Every developer therefore installs gitleaks once, and
in exchange the green tick means something.

### Prove it discriminates

An untested guard is another thing that passes by doing nothing. Make the bad
thing happen on purpose and watch it go red:

```bash
./scripts/install_hooks.sh
# Generate the planted value — do not paste a literal password-shaped string
# into a file in this repo. .gitleaks.toml has NO path exemptions, so this
# document is scanned too, and rightly so.
printf '[options]\nadmin_passwd = %s\n' \
  "$(head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-32)" \
  > config/leaktest.conf
git add -f config/leaktest.conf
git commit -m "this must be blocked"     # EXPECT: non-zero exit, commit refused
git reset config/leaktest.conf && rm config/leaktest.conf
```

If that commit succeeds, **the hook is not installed in this clone** — which is
the failure mode above, and exactly what the verification exists to surface. Run
`git config --get core.hooksPath` (must print `.githooks`) and re-run the
installer.

The CI side proves itself on every run: the `Prove the scanner discriminates`
step plants a generated secret and fails the job unless gitleaks reports it. It
asserts on the report **content**, not the exit code, because gitleaks exits
non-zero on a config panic too — RE2 rejects lookahead, this ruleset was first
written with one, and the crash read as "secret found" while nothing was
scanned.

### Windows — VERIFIED

The ops scripts are run from **Git Bash on Windows**, and per `CLAUDE.md` a
platform-specific claim needs platform evidence. That evidence exists:

**2026-08-11, verified end to end by the maintainer on Windows / Git Bash,
gitleaks 8.30.1.** `core.hooksPath` set by the installer, and *both* branches
proved — the hook refused to commit while gitleaks was absent, and refused again
with `SECRET DETECTED` once installed. This item is closed, not argued.

### Full-history audit (2026-08-11)

**The repository is PUBLIC** — confirmed in an incognito window. The leaked
password was world-readable for the whole time it was in the tree.

History was scanned for every secret class, four independent ways. All four
converge on **exactly one real secret**.

| Pass | Method | Findings |
|---|---|---|
| A | stock gitleaks ruleset (~170 rules: cloud keys, private keys, API tokens), forced with a config that only sets `useDefault` | 1 — same blob, as `generic-api-key` |
| B | project ruleset | 1 |
| C | project ruleset with **every allowlist stripped** | 12 — 11 confirmed placeholders (`CHANGEME`, `change_me`, `${VAR}`), 1 real |
| D | **every blob in the object database** (549 blobs, reachable + dangling), not just commit diffs | 1 |

Both rulesets were validated against freshly generated planted secrets first —
AWS keypair, RSA private key, GitHub PAT, Slack bot token, Sentry DSN. Stock
caught 4/5; ours caught 5/5 (stock misses the Sentry DSN, which is why we carry
that rule). Note that gitleaks skips merge commits: 70 commits total, 15 merges,
**55 non-merge commits scanned** — pass D covers the remainder by scanning
objects rather than diffs.

**The one finding:**

| | |
|---|---|
| What | Odoo database master password, `admin_passwd` (31 chars) |
| Where | `config/odoo.conf` line 29, blob `a34a1015` |
| Entered at | **`a231a9a`** — 2026-08-09 13:05 +0300, *"feat: Sentry error monitoring via sapian_sentry server-wide module"* |
| Reachable from | `origin/master`, `origin/feat/sentry-monitoring`, the working branch |
| On the public default branch | **yes** |
| Removed at | `e0530ed` (2026-08-11) |
| Exposed | ~2 days, publicly, and still present in history until the scrub |
| Also in that commit | `dbfilter = ^sapian_prod$` — a production database name, not a credential but an infrastructure detail |

**A second `admin_passwd` exists in history and is NOT a secret.** The initial
commit `74f7910` (blob `880e0ad2`) carries `admin_passwd = ${ODOO_ADMIN_PASSWD}`
— env-var indirection, correctly unflagged by all three rulesets. It is recorded
here because a bare grep for `admin_passwd` finds it and it should not restart
the alarm.

**Nothing else.** No `.env` file was ever committed (only `.env.example`, which
holds `change_me_*` placeholders). No dumps, keys, certificates or archives have
ever existed in the tree — every path ever added is source, docs, scripts, or
the seven `samples/*.pdf` demo documents, which contain fictional demo-tenant
data. No Telebirr/Chapa/SantimPay key, no Sentry DSN, no API token.

### Incident closed — history scrub deliberately NOT performed

**Decision, 2026-08-11: no scrub. The incident is closed.** This is a considered
choice, not a deferral, and the reasoning is recorded so nobody reopens it out of
unease:

- **The password is dead.** Rotated twice (the second time because the
  replacement was printed in a handover report — see the CLAUDE.md rule that now
  exists because of it). The value in history unlocks nothing.
- **A scrub would not make it unretrievable anyway.** `git filter-repo` plus a
  force-push rewrites the branch, but GitHub retains the old objects through its
  own API and reflogs; a commit SHA stays fetchable long after it is unreachable
  from any ref. We demonstrated exactly this during this work: `ca4541b` was
  still served by the API after being force-pushed off the branch tip. So the
  scrub buys the appearance of removal, not removal.
- **The cost is real.** Rewriting every SHA breaks every clone and every open
  PR, for a value that is already worthless and would remain retrievable.
- **The repository is now private**, so the ongoing exposure is closed by
  access control rather than by rewriting.

What actually contained this incident: rotation, plus the structural change that
makes the same mistake much harder (template/working-file split, gitignore, hook,
CI alarm).

**The audit above stands as the permanent record of what was exposed and for how
long.** Treat the value as permanently burned, because it is.

### Still open

- **CI cannot gate merges** while the repo is private on the Free plan. This is
  a known, accepted limitation, not an oversight — the hook is the control. See
  above for what to change if the plan moves to Pro or Team.

---

## 2. pylint-odoo in the pre-commit hook

Same shape as item 1, lower stakes. pylint-odoo currently runs in CI only, which
means its findings arrive after a push. Add it to `.githooks/pre-commit`, scoped
to the staged Python files so the hook stays fast enough to keep.

Open question: run time. A full-addons pylint-odoo pass is slow enough that
developers will start using `--no-verify` out of habit, which would also
disarm the gitleaks check sharing the hook. Scope it to staged files, and
measure before committing to it.

---

## 3. `.env` and credential hygiene beyond odoo.conf

`docker/.env` carries `DB_PASSWORD` and is gitignored; `.env.example` is the
tracked template. The gitleaks ruleset covers `DB_PASSWORD` and
`POSTGRES_PASSWORD` patterns in `.env*`, `*.conf`, `*.yml`. Still to do:

- an operator-facing list of every secret a deployment holds, and where each one
  lives, so rotation is a checklist rather than an archaeology exercise;
- rotation procedure for the per-tenant `admin_passwd` (it is currently
  "generated once, printed once, stored in a vault" with no documented rotation
  path).

---

## 4. Dependency and image pinning

`docker/Dockerfile` builds from `odoo:19`, a moving tag. A rebuild can therefore
change the Odoo point release under a client without any commit in this repo.
Pin by digest, and record the upgrade as a deliberate commit.

---

## 5. CI module list is hand-maintained

The integration job's `--test-tags` list names modules explicitly. A new module
with tests is invisible to CI until someone remembers to add it — a test suite
that silently covers less than it appears to. Derive the list from the addons
directory instead.
