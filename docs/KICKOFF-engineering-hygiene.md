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
| **gitleaks pre-commit hook** | `.githooks/pre-commit`, `.gitleaks.toml` | Blocks the commit. Not a report, not a comment on a PR. |
| Hook installer | `scripts/install_hooks.sh` | `core.hooksPath = .githooks`, so hooks are tracked and update with a pull. |
| CI backstop | `.github/workflows/ci.yml` | Catches commits made with `--no-verify` or from a clone that never ran the installer. |

### Why the hook and not just CI

**A check that runs after the commit cannot stop the commit.** By the time CI
speaks, the secret is in the object database, in the push, and in every clone
that fetched. Rotation is then mandatory and history rewriting is on the table.
The hook's whole value is that it runs while the blast radius is still zero.

This is the same lesson as pylint-odoo, which was CI-only and therefore found
four issues *after* a push rather than before one.

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

If that commit succeeds, the guard is decoration — fix it before trusting it.

### Windows note

The ops scripts are run from **Git Bash on Windows**. `core.hooksPath` and the
hook script are POSIX-shell and platform-neutral, but per `CLAUDE.md` that is
Linux evidence: the hook is **UNVERIFIED on Windows** until an operator runs
`./scripts/install_hooks.sh` and the discrimination test above in Git Bash and
reports back. `winget install gitleaks` is the expected install path there.

### What is NOT done

- **History scrub.** The leaked value is dead (rotated), but it remains in the
  git history of this repo. Rewriting every SHA breaks every branch and every
  clone, so it is only proportionate if the repository is or has been public.
  **Decision pending on repository visibility.** If public: scrub with
  `git filter-repo` and force-push, and treat every other credential that ever
  shared that file as compromised too.

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
