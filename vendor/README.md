# vendor/ — third-party Odoo addons, pinned

Code in this directory is **not ours**. It is copied verbatim from an upstream
repository at a specific commit, and it is on the Odoo addons path alongside
`addons/`.

## Why it is not in `addons/`

`addons/` is SapianERP code, and the whole lint suite is pointed at it:
`ruff check addons`, `black --check addons`, `pylint addons` with
`manifest-required-authors = Sapian Technologies PLC` in `.pylintrc`. Vendored
OCA code fails that last one by construction — its manifest names LasLabs,
Tecnativa, ITerra, Onestein and the OCA, because they wrote it. Moving the
boundary is the honest fix: our lint keeps checking our code, and nobody is
tempted to "fix" a lint error by editing somebody else's module.

The separation also states the rule the directory exists to enforce: **nothing
in here is edited in place.** A local change to vendored code is invisible at
review time, survives no upgrade, and turns "we run web_responsive 19.0.1.1.0"
into a claim about a version that does not exist anywhere else. If we need
different behaviour, it goes in one of our own modules, extending this one the
same way we extend Odoo core.

## Why a commit SHA and not a branch

`19.0` is a moving branch. OCA merges into it continuously — between the two
most recent commits touching `web_responsive` alone there is a dark-mode change
to the apps menu. If we tracked the branch, the navigation our clients use
would change whenever somebody re-pulled, and the first we would hear of it is
a client asking why the menu looks different. Same reasoning as the digest pins
on the `odoo:19.0` and `postgres:16` images in `docker/Dockerfile` and
`.github/workflows/ci.yml`: a tag or a branch is a name, and names get
reassigned.

## What is pinned here

| | |
|---|---|
| Upstream | <https://github.com/OCA/web> |
| Branch | `19.0` |
| **Pinned commit** | **`e6ced50b0969b4c6635dae60d96532b54e5edb8e`** |
| Commit date | 2026-08-11T12:48:07+00:00 |
| Vendored on | 2026-08-14 |
| Module | `web_responsive` |
| Module version | 19.0.1.1.0 |
| License | LGPL-3 (compatible with our own LGPL-3 modules) |
| `development_status` | Production/Stable |
| Upstream `depends` | `web`, `web_tour`, `mail` |
| Upstream `excludes` | `web_enterprise` |
| Files vendored | 112 (8 Python) |
| Last upstream commit touching `web_responsive` | `89ca180fa54c75277eed47b0a00a91497a010254` (2026-08-05) |

The pinned commit is the branch tip on the day it was vendored; the module's own
last change is three commits and six days older, which is why both are recorded.
Everything between them is other modules in the same repository.

### The tree hash, which is the part that is actually checkable

```
vendor/oca_web/web_responsive  ->  f1e9c8dfadbdf32603a6fb0cea2e0031438e779b
```

That is git's own object ID for the `web_responsive` directory in OCA/web at the
pinned commit — and, because git tree objects are content-addressed, it is *also*
the object ID our copy hashes to. It matches today:

```
$ git -C <oca-web-clone> rev-parse e6ced50b:web_responsive
f1e9c8dfadbdf32603a6fb0cea2e0031438e779b
$ scripts/check_vendor.sh
f1e9c8dfadbdf32603a6fb0cea2e0031438e779b
```

A SHA written in prose is a claim; this one is an assertion. `scripts/check_vendor.sh`
recomputes the hash from the working tree and fails on any difference — a changed
byte, a changed file mode, a deleted file, an extra file. It runs in CI.

It also fails when the directory is *missing*, rather than reporting that nothing
was wrong with the nothing it found, and it asserts a file-count floor for the
same reason: this repo has been bitten four times by checks that were green
because the work had not happened (see CLAUDE.md, "A success signal that can be
produced by doing nothing is not a success signal"). The discrimination proof is
in the script's own `--self-test`.

## Known divergence: one upstream test fails, on purpose

`web_responsive`'s own `TestResUsers.test_compute_redirect_home` asserts that a
newly created user has `is_redirect_home == False`:

```python
record = new_test_user(self.env, login="jeant@mail.com")
self.assertFalse(record.is_redirect_home)
```

That is precisely the default `sapian_theme` overrides — landing a user on the
Module Catalog instead of the app launcher is the problem the module was
vendored to solve. So on any database carrying both modules, that one test
fails, and there is no version of "do the approved thing" in which it does not:
the vendored copy is never edited, and not overriding the default would mean
not making the change.

Upstream ships two test methods. `TestIrHttp.test_session_info` passes;
this one does not. Nothing else diverges.

### How the divergence is caught, from both ends

Not by asserting that this test fails. That was tried and it was wrong: on a
database where `account` is installed the test does not fail, it **errors before
running**. `-u web_responsive` reloads only that module, so its `at_install`
tests run at position 39 of 82 — before `account` — and `BaseCommon.setUpClass`
creating a `res.partner` hits `null value in column "autopost_bills" violates
not-null constraint`, because the column exists from the earlier full install
but its Python default is not registered yet. Zero tests run, and
`0 failures, 1 errors of 0 tests` does not match a grep for `N failed`, so the
error read as the test *passing*. CI caught that; the step is gone.

What actually covers it, and does so regardless of module load order:

- **Our side** — `sapian_theme`'s `TestLauncherDefaultValues` asserts that a
  user created on a database that HAS the field comes out `True`. That is the
  same claim upstream's test makes in reverse, made where we control the
  environment. It runs in the `launcher-defaults` job, alongside the browser
  tests that prove the default reaches the page.
- **Upstream's side** — the tree-hash pin. Any change to upstream, *including to
  that test*, changes `f1e9c8df…` and `scripts/check_vendor.sh` goes red. A
  refresh that flips upstream's own default therefore cannot pass silently; it
  stops at the pin, which is exactly the moment a human should look.

So: **a red `test_compute_redirect_home` is the expected state, not a broken
vendor copy.** Everything else being red is not.

## It is installed by default

Since the launcher work landed, `web_responsive` is in the shipped default set:
`scripts/provision_client.sh`'s `MODULES`, `scripts/build_demo.sh`'s install
list, and CI's `integration-tests` job. It is the product's navigation, not an
optional extra.

Installing it is **not sufficient**. Its two per-user settings decide what a
user actually lands on, and the admin of a demo or client tenant is created in
the `-i base` phase before this module owns those fields — so
`sapian_theme`'s defaults never reach it. Both scripts call
`env['res.users']._sapian_apply_launcher_defaults(dry_run=False)` during
provisioning and then verify the outcome from the served artefact
(`verify_launcher` in `scripts/lib/preflight.sh`). See
`addons/sapian_theme/README.md` for the measurement behind that.

One consequence for CI: this module's own `at_install` test cannot run on a
database that carries `account`. `-u web_responsive` reloads it at position
39/82, before `account`, and `BaseCommon.setUpClass` then hits a NOT NULL
`autopost_bills`. The `integration-tests` job therefore installs it without
selecting its tests; the `launcher-defaults` job runs them where the module is
loaded on its own terms.

## Refreshing the pin

Deliberate, in its own PR, with the UI evidence attached — not a drive-by bump.

```bash
git clone --branch 19.0 --single-branch https://github.com/OCA/web /tmp/oca-web
cd /tmp/oca-web && git rev-parse HEAD          # the new pin
rm -rf <repo>/vendor/oca_web/web_responsive
cp -a web_responsive <repo>/vendor/oca_web/
```

Then update the table above (commit, date, tree hash, file count), run
`scripts/check_vendor.sh`, and re-run the checks that cover the parts of the UI
this module touches — at minimum `sapian_theme`'s app-rail browser tests, which
are the ones that would notice the apps menu changing shape underneath them.
