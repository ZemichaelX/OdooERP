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
