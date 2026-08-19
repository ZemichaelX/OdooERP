#!/usr/bin/env python3
"""Assert that one module is loaded before another, from Odoo's own log.

WHY THIS READS A LOG AND NOT THE DATABASE
-----------------------------------------
The obvious source is `ir_module_module`, ordered by id. That is DISCOVERY
order — an alphabetical scan of the addons path — not LOAD order, so it would
answer a different question from the one being asked and would happen to look
right most of the time. Odoo prints the real thing as it works:

    Loading module mail_bot (26/30)

Those are the very numbers the defect was reported in: `sapian_theme_mail`
moved between 26/30 and 27/30 across identical runs, and the system partner's
name moved with it.

Usage:
    ci_assert_load_order.py <logfile> <earlier-module> <later-module> [...]

Exits 0 and prints the positions when every named module appears and each is
loaded strictly before the next. Exits 1 otherwise, saying which.
"""

import re
import sys

_LOADING = re.compile(r"Loading module ([a-z_0-9]+) \((\d+)/(\d+)\)")


def positions(path):
    """Map module name -> the position Odoo reported for it, first sighting."""
    found = {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = _LOADING.search(line)
            if match:
                found.setdefault(match.group(1), int(match.group(2)))
    return found


def main(argv):
    if len(argv) < 4:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    logfile, expected = argv[1], argv[2:]

    found = positions(logfile)
    if not found:
        # An empty result is the do-nothing success signal this repo keeps
        # getting caught by: no "Loading module" lines at all means the log is
        # the wrong file or the run never started, not that the order is fine.
        print(
            "::error::%s contains no 'Loading module' lines at all, so nothing "
            "was measured. A log with no loader output is not evidence of a "
            "correct load order." % logfile,
            file=sys.stderr,
        )
        return 1

    missing = [name for name in expected if name not in found]
    if missing:
        print(
            "::error::these modules never appear in the loader output: %s"
            % ", ".join(missing),
            file=sys.stderr,
        )
        return 1

    for earlier, later in zip(expected, expected[1:]):
        if found[earlier] >= found[later]:
            print(
                "::error::%s loaded at %d and %s at %d — %s must load first, "
                "or the fix is back to depending on which sibling the graph "
                "happens to visit second."
                % (earlier, found[earlier], later, found[later], earlier),
                file=sys.stderr,
            )
            return 1

    print(
        "OK — load order is as required: %s"
        % ", ".join("%s %d" % (name, found[name]) for name in expected)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
