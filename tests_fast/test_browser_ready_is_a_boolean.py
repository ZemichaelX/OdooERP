# -*- coding: utf-8 -*-
"""Every `browser_js` ready expression evaluates to a BOOLEAN.

THE FAILURE THIS CATCHES LOOKS EXACTLY LIKE A BROKEN FEATURE. Odoo's
`ChromeBrowser._wait_ready` polls the ready expression over CDP and compares the
result against ``{'type': 'boolean', 'value': True}`` — nothing else is ever
ready. Hand it a bare module path (``"web.Chrome"``, the pre-19 idiom) or a bare
``document.querySelector(...)`` returning an Element, and the browser sits there
until the timeout and the suite reports

    TimeoutError: Runtime.evaluate({'expression': 'try { web.Chrome } catch {}'})

which reads as "the page never loaded" — a bug hunt through the component under
test, when the defect is one argument in the test itself.

It has now bitten three times in this repository: twice while the app rail's
browser tests were written (both are commented in place at
`sapian_theme/tests/test_app_rail.py`), and once on the landing page's grid
toggle, where the CI job burned 85 seconds waiting for `web.Chrome`. A comment
in two files is not a guard — every NEW browser test is written by somebody who
has not read those two files.

Pure Python: it reads the source with `ast`, so it costs nothing and runs in the
lint job with the rest of `tests_fast/`.
"""

import ast
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDONS = os.path.join(REPO, "addons")

# A bare JS identifier or dotted path: `web.Chrome`, `owl`, `odoo.__DEBUG__`.
# This is the shape that has actually gone wrong, and it can never be a boolean.
_BARE_PATH = re.compile(r"^[A-Za-z_$][\w$]*(\.[A-Za-z_$][\w$]*)*$")

# Something in the expression has to PRODUCE a boolean. `!!` is the house idiom;
# the others are admitted because they are equally boolean and a guard that
# forced one spelling would be about style rather than about the defect.
_BOOLEAN_MAKERS = ("!!", "===", "!==", ">=", "<=", "typeof ", ".includes(", ".has(")


def _browser_js_calls():
    """(path, lineno, ready_ast_node) for every `*.browser_js(...)` in addons."""
    for root, _dirs, files in os.walk(ADDONS):
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            # utf-8-SIG: `l10n_et_payroll/tests/test_payroll_reports.py` carries
            # a byte-order mark, and `ast.parse` on a str containing one raises
            # SyntaxError. Odoo itself reads modules with `tokenize.open`, which
            # strips it, so the file is fine at runtime — but a guard that dies
            # on it is a guard nobody keeps.
            with open(path, encoding="utf-8-sig") as handle:
                source = handle.read()
            tree = ast.parse(source, filename=path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (isinstance(func, ast.Attribute) and func.attr == "browser_js"):
                    continue
                ready = node.args[2] if len(node.args) >= 3 else None
                for keyword in node.keywords:
                    if keyword.arg == "ready":
                        ready = keyword.value
                yield os.path.relpath(path, REPO), node.lineno, ready, tree


def _resolve(node, tree):
    """The ready expression as a string, following one level of indirection.

    `self.SEED_AND_READY` is a class attribute holding a concatenated literal;
    resolving it is the difference between checking that call and skipping it.
    Returns None when the value cannot be read statically — reported as a
    failure rather than passed over, because an unreadable ready expression is
    exactly the one nobody is checking.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) or isinstance(node, ast.JoinedStr):
        try:
            return ast.literal_eval(node)
        except (ValueError, SyntaxError):
            return None
    name = None
    if isinstance(node, ast.Attribute):
        name = node.attr
    elif isinstance(node, ast.Name):
        name = node.id
    if not name:
        return None
    for candidate in ast.walk(tree):
        if isinstance(candidate, ast.Assign):
            targets = [t.id for t in candidate.targets if isinstance(t, ast.Name)]
            if name in targets:
                try:
                    return ast.literal_eval(candidate.value)
                except (ValueError, SyntaxError):
                    return None
    return None


def test_every_browser_js_call_passes_a_ready_expression():
    """A missing ready argument defaults to something no test chose."""
    missing = [
        "%s:%d" % (path, lineno) for path, lineno, ready, _tree in _browser_js_calls()
        if ready is None
    ]
    assert not missing, "browser_js called with no ready expression at: %s" % missing


def test_every_ready_expression_can_produce_a_boolean():
    bad = []
    for path, lineno, ready, tree in _browser_js_calls():
        if ready is None:
            continue  # reported by the test above
        text = _resolve(ready, tree)
        if text is None:
            bad.append("%s:%d ready is not a readable literal" % (path, lineno))
            continue
        if _BARE_PATH.match(text.strip()):
            bad.append(
                "%s:%d ready=%r is a bare JS path — it is never a boolean, so "
                "_wait_ready times out" % (path, lineno, text)
            )
            continue
        if not any(marker in text for marker in _BOOLEAN_MAKERS):
            bad.append(
                "%s:%d ready=%r produces no boolean; prefix the check with `!!`"
                % (path, lineno, text[:60])
            )
    assert not bad, "\n".join(bad)


def test_the_guard_rejects_the_expression_that_actually_broke():
    """It DISCRIMINATES. An untested guard is another thing that passes by
    doing nothing, so the two shapes that have gone wrong are named here."""
    assert _BARE_PATH.match("web.Chrome")
    assert not any(m in "web.Chrome" for m in _BOOLEAN_MAKERS)
    element = "document.querySelector('.o_main_navbar')"
    assert not any(m in element for m in _BOOLEAN_MAKERS)
    assert any(m in "!!" + element for m in _BOOLEAN_MAKERS)
