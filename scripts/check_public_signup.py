#!/usr/bin/env python3
"""Can a stranger get an account on this tenant? Asked over HTTP, answered from the database.

WHY THIS EXISTS AND THE SETTING DOES NOT COUNT
-----------------------------------------------
Three guards in this repository have already been correct when written and wrong
afterwards, each time because they read a SETTING instead of the thing the
setting was supposed to cause:

  * `login_primary` was green while the login page said "Powered by Odoo";
  * `is_redirect_home` was True while `action_id` decided where a user landed;
  * `auth_signup.invitation_scope` read b2b while the served page offered free
    sign-up, because `website` had taken over the decision.

So this asks the question a stranger would ask, in the way a stranger would ask
it: fetch the login page, fetch the sign-up page, POST the sign-up form, and
then COUNT THE USERS IN THE DATABASE. The count is read with psycopg2 straight
off Postgres — not through Odoo's ORM, not through its API — so nothing the
product believes about itself can make this agree.

The property is "no user was created". Everything else printed here is context
for whoever reads a failure.

USAGE
    python3 scripts/check_public_signup.py --base-url http://localhost:8069 \
        --db ci_signup [--expect-open]

`--expect-open` inverts the verdict, and is how the guard is proved to
discriminate: run it against a tenant where sign-up was deliberately turned on
and it must report a user WAS created. A guard that has never been seen to fail
is another thing that passes by doing nothing (CLAUDE.md).

Exit codes: 0 the verdict matched what was expected, 1 it did not, 2 the check
could not run at all — which is ABORTED, not a pass and not a failure.
"""

import argparse
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# A login no real tenant would hold, and recognisable in a database dump if one
# ever survives. Timestamp-free on purpose: a fixed login means a second run
# against an already-breached tenant reports "already exists" rather than
# quietly creating a second account and calling it a new breach.
STRANGER_LOGIN = "sapian-signup-probe@example.invalid"
STRANGER_NAME = "Uninvited Stranger"
STRANGER_PASSWORD = "Pr0be-Passw0rd-!x9"

_CSRF = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')
# Odoo's own login template only renders this when signup is enabled.
_OFFERS_SIGNUP = re.compile(r"/web/signup", re.IGNORECASE)


def _connect(dsn):
    import psycopg2  # noqa: PLC0415 - only needed when the check actually runs

    return psycopg2.connect(dsn)


def count_users(dsn):
    """Users in the database, straight from Postgres."""
    with _connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM res_users")
        return cursor.fetchone()[0]


def stranger_exists(dsn):
    with _connect(dsn) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT login FROM res_users WHERE login = %s", (STRANGER_LOGIN,))
        row = cursor.fetchone()
    return row[0] if row else None


class Session:
    """The smallest possible browser: cookies, forms, and no JavaScript.

    Deliberately not `requests` and deliberately not Odoo's test client. A
    stranger has neither.
    """

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.cookie = ""

    def _request(self, path, data=None):
        url = path if path.startswith("http") else self.base_url + path
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        request = urllib.request.Request(url, data=body)
        request.add_header("User-Agent", "sapian-signup-probe/1")
        if self.cookie:
            request.add_header("Cookie", self.cookie)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, text, final = response.status, response.read().decode(
                    "utf-8", "replace"
                ), response.geturl()
                self._remember(response)
        except urllib.error.HTTPError as error:
            status, text, final = error.code, error.read().decode("utf-8", "replace"), url
            self._remember(error)
        return status, text, final

    def _remember(self, response):
        raw = response.headers.get("Set-Cookie")
        if raw:
            self.cookie = raw.split(";", 1)[0]

    def get(self, path):
        return self._request(path)

    def post(self, path, data):
        return self._request(path, data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--label", default="")
    parser.add_argument(
        "--expect-open",
        action="store_true",
        help="Invert the verdict: the check passes only if a user WAS created. "
        "Used to prove the guard discriminates.",
    )
    args = parser.parse_args()

    dsn = os.environ.get("SAPIAN_PROBE_DSN") or "dbname=%s host=%s user=%s password=%s port=%s" % (
        args.db,
        os.environ.get("PGHOST", "db"),
        os.environ.get("PGUSER", "odoo"),
        os.environ.get("PGPASSWORD", "odoo"),
        os.environ.get("PGPORT", "5432"),
    )

    label = args.label or args.db
    try:
        before = count_users(dsn)
    except Exception as error:  # noqa: BLE001 - reported as ABORTED, not as a pass
        print("SAPIAN-SIGNUP ABORTED could not read the user count: %s" % error)
        return 2

    session = Session(args.base_url)
    login_status, login_html, _url = session.get("/web/login?db=%s" % args.db)
    offers = 1 if _OFFERS_SIGNUP.search(login_html) else 0

    get_status, signup_html, signup_url = session.get("/web/signup?db=%s" % args.db)
    token = _CSRF.search(signup_html)
    form = {
        "login": STRANGER_LOGIN,
        "name": STRANGER_NAME,
        "password": STRANGER_PASSWORD,
        "confirm_password": STRANGER_PASSWORD,
        "redirect": "",
    }
    if token:
        form["csrf_token"] = token.group(1)
    post_status, post_html, post_url = session.post("/web/signup?db=%s" % args.db, form)

    after = count_users(dsn)
    created = 1 if after > before else 0
    stranger = stranger_exists(dsn)

    print("SAPIAN-SIGNUP tenant=%s" % label)
    print("SAPIAN-SIGNUP login_page=%s offers_signup=%d" % (login_status, offers))
    print(
        "SAPIAN-SIGNUP signup_get=%s csrf=%d landed=%s"
        % (get_status, 1 if token else 0, urllib.parse.urlparse(signup_url).path)
    )
    print(
        "SAPIAN-SIGNUP signup_post=%s landed=%s"
        % (post_status, urllib.parse.urlparse(post_url).path)
    )
    print(
        "SAPIAN-SIGNUP users_before=%d users_after=%d created=%d stranger=%s"
        % (before, after, created, stranger or "none")
    )

    breached = created or bool(stranger)
    verdict = "OPEN" if breached else "CLOSED"
    print("SAPIAN-SIGNUP verdict=%s expected=%s" % (verdict, "OPEN" if args.expect_open else "CLOSED"))

    if args.expect_open:
        if not breached:
            print(
                "SAPIAN-SIGNUP FAIL this tenant was opened on purpose and the probe "
                "still could not create an account — the probe is not exercising "
                "sign-up, so its CLOSED verdicts elsewhere prove nothing."
            )
            return 1
        return 0
    if breached:
        print(
            "SAPIAN-SIGNUP FAIL a stranger created %s on this tenant. Public "
            "sign-up is open." % (stranger or "an account")
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
