# -*- coding: utf-8 -*-
"""Odoo's name and face in Discuss, asserted on what is SERVED.

WHAT EACH HALF READS, AND WHY THAT IS THE HONEST BOUNDARY
--------------------------------------------------------
The bot's NAME, EMAIL and AVATAR are a record, so the served surface is the
record and the bytes the avatar route hands back — never the data file, which
in this module does not exist (see models/res_partner.py for why a data record
could not have worked at all).

The four JS strings are a different case and the difference is worth stating
rather than papering over. Our fix is three `patch()` calls, and a patch ADDS
code to the bundle; it never removes the code it patches. So `"Install Odoo"`
is still a string inside the served `web.assets_backend` while the menu renders
"Install SapianERP", and no assertion of the form "Odoo's string is gone from
the bundle" can ever pass. Pretending otherwise would mean writing a test that
must fail, or one that reads the source instead — both worse. What is asserted
instead:

  * ours is IN the served bundle. That is the failure that actually happens on
    this tree: a module `installed` in the database but absent from the SERVING
    process's addons_path delivers zero JS and zero CSS, silently, and `state`
    still reads `installed` (CLAUDE.md, "AND THE PATH IS NOT ENOUGH EITHER").
  * the strings and paths we intercept are still the ones upstream ships, read
    out of the served bundle — so an upstream rename turns a test red instead
    of turning an interception into a no-op.
  * the set of Odoo-identity strings on this surface has not GROWN. That is the
    sweep, and it is scoped to two surfaces on purpose: a blanket "no 'Odoo'
    anywhere" assertion over a 20 MB bundle is noise, and noise is how a guard
    gets deleted.

WHAT WAS MEASURED BEFORE, on the all-apps demo tenant:

    res.partner(2)  name  'OdooBot'
                    email 'odoobot@example.com'
                    image mail/static/src/img/odoobot.png  (0% transparent)

and "OdooBot — Product created" in the chatter of product.template 7 (Binding
Wire 1.5 mm).
"""

import base64
import hashlib
import os
import re
import struct
import zlib

from odoo import SUPERUSER_ID
from odoo.tests import HttpCase, tagged
from odoo.tools import file_open

from odoo.addons.sapian_theme import vendor

# Odoo's own two images, for comparison. `odoobot.png` is the avatar (a filled
# purple tile) and `odoobot_transparent.png` is the desktop-notification icon;
# Odoo keeps two because a tray icon renders over an unknown background.
ODOO_AVATAR = "mail/static/src/img/odoobot.png"
ODOO_PUSH_ICON = "/mail/static/src/img/odoobot_transparent.png"

# What `/web/image/...` answers with when the caller may not read the record.
# Named here because it is the thing an unauthenticated fetch silently gets,
# and because a test comparing against it by accident would look like a pass.
ODOO_PLACEHOLDER = "web/static/img/placeholder.png"

# Ours. One file for both slots, which is a measurement and not a shortcut:
# `sapian_core__icon.png` is already transparent-backed — 45.5% of its pixels
# are fully transparent and all four corners are alpha 0 — so it satisfies the
# tray requirement that Odoo needed a second file for.
# `test_the_avatar_is_transparent_backed` is that measurement, kept as a guard.
SAPIAN_AVATAR = "sapian_theme_mail/static/src/img/sapian_bot.png"
SAPIAN_PUSH_ICON = "/sapian_theme_mail/static/src/img/sapian_bot.png"

# The brand original the shipped copy must equal, byte for byte. Relative to
# the repository root, which is two levels above this addon — the same relation
# in CI (${GITHUB_WORKSPACE}/addons/...) and locally.
BRAND_AVATAR = "brand/icons/deliver/sapian_core__icon.png"

# The three upstream files whose served content this file sweeps. Odoo wraps
# each JS module in the bundle as `odoo.define("@mail/core/web/...")`, so the
# bundle can be sliced back into per-file regions without reading any source.
MESSAGING_MENU_SURFACE = (
    "@mail/core/web/messaging_menu_patch",
    "@mail/core/common/notification_permission_service",
    "@mail/core/common/out_of_focus_service",
)


def png_alpha(data, points):
    """Alpha at the given (x, y) points of a PNG, decoded by hand.

    PIL is not a dependency of this repo and adding one to read four pixels
    would be a poor trade.

    Two colour types are handled: 8-bit palette with `tRNS` (what our icon set
    and Odoo's bot images are) and 8-bit RGBA (what Odoo's own placeholder is,
    and what the image routes fall back to). Anything else RAISES rather than
    guessing — a decoder that quietly returned zeros would make every
    transparency assertion below unconditional, which is the failure mode this
    whole file is written against.
    """
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos, idat, trns, header = 8, b"", None, None
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        kind = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"tRNS":
            # PLTE is deliberately not read: only the alpha channel matters
            # here, and tRNS is indexed by the same palette index.
            trns = chunk
        elif kind == b"IDAT":
            idat += chunk
        pos += 12 + length
    width, height, depth, colour = header[0], header[1], header[2], header[3]
    if depth != 8 or colour not in (3, 6):
        raise ValueError(
            "only 8-bit palette or RGBA PNGs are decoded here, got colour "
            "type %s at depth %s" % (colour, depth)
        )
    channels = 4 if colour == 6 else 1
    raw = zlib.decompress(idat)
    stride, rows, prev, at = width * channels, [], bytearray(width * channels), 0

    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        return a if pa <= pb and pa <= pc else (b if pb <= pc else c)

    for _ in range(height):
        filt = raw[at]
        at += 1
        line = bytearray(raw[at : at + stride])
        at += stride
        # `back` is the distance to the pixel on the left: one byte for a
        # palette image, four for RGBA. Getting it wrong decodes garbage that
        # still looks like numbers, so it is derived rather than assumed.
        back = channels
        if filt == 1:
            for x in range(back, stride):
                line[x] = (line[x] + line[x - back]) & 255
        elif filt == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif filt == 3:
            for x in range(stride):
                left = line[x - back] if x >= back else 0
                line[x] = (line[x] + (left + prev[x]) // 2) & 255
        elif filt == 4:
            for x in range(stride):
                left = line[x - back] if x >= back else 0
                upper_left = prev[x - back] if x >= back else 0
                line[x] = (line[x] + paeth(left, prev[x], upper_left)) & 255
        rows.append(line)
        prev = line

    def alpha_at(x, y):
        if channels == 4:
            return rows[y][x * 4 + 3]
        index = rows[y][x]
        return trns[index] if trns and index < len(trns) else 255

    return [alpha_at(x, y) for (x, y) in points], (width, height)


class BotIdentityCase(HttpCase):
    """The record, the bytes it serves, and the bundle the browser is handed."""

    def bot(self):
        """`base.partner_root`, browsed rather than searched.

        It ships ARCHIVED (`base/data/res_partner_data.xml` sets active=False),
        so the obvious `search([('name', '=', ...)])` finds nothing and a test
        written that way would pass by measuring an empty recordset.
        """
        partner = self.env.ref("base.partner_root", raise_if_not_found=False)
        self.assertTrue(partner, "base.partner_root is missing from this database")
        return partner.sudo().with_context(active_test=False)

    def row_state(self):
        """The row as the database holds it, for a failure message.

        WHY THIS IS IN THE MESSAGE AND NOT A COMMENT. CI once failed the three
        name/email assertions while all four record-reading AVATAR assertions
        passed on the same database — a combination that cannot happen if one
        `write` set all three fields. Inferring the row from a query count got
        nowhere; the row itself, printed by the run that failed, is the datum.
        `write_uid`/`write_date` say WHO touched it last, which is what
        distinguishes "our hook never ran" from "our hook ran and something
        wrote name and email back afterwards".
        """
        bot = self.bot()
        bot.invalidate_recordset()
        image = base64.b64decode(bot.image_1920 or b"")
        return (
            "row: id=%s name=%r email=%r write_uid=%s write_date=%s "
            "image_sha1=%s image_bytes=%d | ours=%s odoos=%s"
            % (
                bot.id,
                bot.name,
                bot.email,
                bot.write_uid.id,
                bot.write_date,
                hashlib.sha1(image).hexdigest() if image else "(empty)",
                len(image),
                hashlib.sha1(self.shipped(SAPIAN_AVATAR)).hexdigest(),
                hashlib.sha1(self.shipped(ODOO_AVATAR)).hexdigest(),
            )
        )

    def shipped(self, path):
        with file_open(path, "rb") as handle:
            return handle.read()

    def repo_file(self, relative):
        """A path relative to the repository root, for the brand originals."""
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.abspath(os.path.join(here, "..", "..", ".."))
        return os.path.join(root, relative)

    def served_avatar(self, field="image_1920"):
        """The avatar bytes a logged-in user's browser receives.

        AUTHENTICATED, and that is not a detail — it is a measurement. Fetched
        anonymously, this route answers 200 with Odoo's own 6078-byte
        placeholder, because `base.partner_root` is archived and a record rule
        denies the public user (`odoo.addons.base.models.ir_rule: Access Denied
        ... uid: 3`). An earlier version of this file read that placeholder,
        compared it against the mark we ship and failed — correctly, and for
        entirely the wrong reason. A test that fetches it unauthenticated is
        measuring Odoo's fallback, not our avatar, in both directions.
        """
        self.authenticate("admin", "admin")
        response = self.url_open("/web/image/res.partner/%d/%s" % (self.bot().id, field))
        self.assertEqual(response.status_code, 200, "the bot's avatar does not serve at all")
        self.assertGreater(
            len(response.content), 1000, "the served avatar is too small to be one"
        )
        self.assertNotEqual(
            response.content,
            self.shipped(ODOO_PLACEHOLDER),
            "the route answered with Odoo's placeholder, so this is not the "
            "bot's avatar and nothing measured from it means anything",
        )
        return response.content

    def backend_bundle(self):
        """Every JS asset the backend page links, fetched and concatenated.

        Taken from the page's own <script> tags rather than by guessing a
        bundle name, for the reason test_auth_pages.py takes its CSS the same
        way: the URL carries a content hash, and a test asserting against a
        file the page does not load is a test that passes while the user sees
        something else.
        """
        self.authenticate("admin", "admin")
        page = self.url_open("/odoo")
        self.assertEqual(page.status_code, 200, "the backend did not render")
        sources = re.findall(r'<script[^>]+src="([^"]+\.js[^"]*)"', page.text)
        self.assertTrue(sources, "the backend page links no script at all")
        bundle = ""
        for source in sources:
            got = self.url_open(source)
            if got.status_code == 200:
                bundle += got.text
        self.assertGreater(
            len(bundle), 200000, "the backend bundle came back too small to be the real one"
        )
        return bundle

    def surface_strings(self, bundle):
        """Quoted strings mentioning Odoo, within the messaging-menu surface.

        Sliced out of the SERVED bundle by Odoo's own module wrappers, so this
        reads what the browser got rather than what is on disk. Scoped to three
        files: a sweep over the whole bundle would return hundreds of true
        positives (module paths, urls, class names) and mean nothing.
        """
        found = set()
        for module in MESSAGING_MENU_SURFACE:
            start = bundle.find('odoo.define("%s"' % module)
            if start < 0:
                start = bundle.find("odoo.define('%s'" % module)
            self.assertGreaterEqual(
                start,
                0,
                "%s is not in the served bundle at all, so this sweep is "
                "looking at nothing" % module,
            )
            end = bundle.find("odoo.define(", start + 12)
            region = bundle[start : end if end > 0 else len(bundle)]
            for literal in re.findall(r'_t\(\s*"((?:[^"\\]|\\.)*)"', region):
                if "odoo" in literal.lower():
                    found.add(literal)
        return found


@tagged("post_install", "-at_install")
class TestTheSystemPartnerIsOurs(BotIdentityCase):
    """The author of every message nobody wrote."""

    def test_the_bot_is_not_named_after_odoo(self):
        self.assertNotIn(
            "odoo",
            (self.bot().name or "").lower(),
            "the partner that signs every automated message in every chatter "
            "is still named after Odoo. " + self.row_state(),
        )

    def test_the_bot_carries_our_name(self):
        """The positive half — absence of Odoo is not the deliverable.

        From the constant, never a literal: `vendor.py` is the single home and
        a hardcoded "SapianBot" here would keep passing after a rename while
        the chatter said something else.
        """
        self.assertEqual(self.bot().name, vendor.SAPIAN_BOT, self.row_state())

    def test_the_bot_address_is_ours(self):
        self.assertEqual(self.bot().email, vendor.SAPIAN_BOT_EMAIL, self.row_state())
        self.assertNotIn("odoo", (self.bot().email or "").lower(), self.row_state())

    def test_the_served_avatar_is_not_odoos(self):
        """Bytes, not a filename: the record could point anywhere."""
        self.assertNotEqual(
            self.served_avatar(),
            self.shipped(ODOO_AVATAR),
            "the bot still serves Odoo's own face",
        )

    def test_the_served_avatar_is_the_mark_we_ship(self):
        self.assertEqual(
            self.served_avatar(),
            self.shipped(SAPIAN_AVATAR),
            "the avatar being served is neither Odoo's nor ours — something "
            "re-encoded it, and what the client sees is unknown",
        )

    def test_the_avatar_is_transparent_backed(self):
        """THE REQUIREMENT THE TRAY SLOT ADDS, measured on the served bytes.

        A desktop notification renders on the OS tray over a background nobody
        controls, so the icon there cannot carry a filled square. Odoo ships
        two images for exactly this reason — `odoobot.png` is a filled purple
        tile with 0% transparency, `odoobot_transparent.png` is the safe one —
        and this module ships ONE file for both slots because it measured that
        the app-tile mark is already transparent-backed. That measurement is
        this test; without it the single-file decision is an assumption.
        """
        corners = [(0, 0), (255, 0), (0, 255), (255, 255)]
        alphas, size = png_alpha(self.served_avatar(), corners)
        self.assertEqual(size, (256, 256), "the served avatar is not the 256px icon")
        self.assertEqual(
            alphas,
            [0, 0, 0, 0],
            "the avatar has an opaque background square, so on a dark OS tray "
            "it renders as a light rectangle: corner alphas %s" % alphas,
        )

    def test_the_size_the_chatter_renders_is_ours_and_still_transparent(self):
        """`avatar_128`, which is what Discuss and the chatter actually request.

        A different surface from the one above and not a duplicate of it: Odoo
        RESIZES this variant rather than streaming the stored bytes (measured —
        1614 bytes against 3589), and a resize is exactly where an alpha
        channel gets flattened onto white. So the small one is checked on its
        own terms.
        """
        served = self.served_avatar("avatar_128")
        self.assertNotEqual(served, self.shipped(ODOO_AVATAR))
        alphas, size = png_alpha(served, [(0, 0), (127, 0), (0, 127), (127, 127)])
        self.assertEqual(size, (128, 128))
        self.assertEqual(
            alphas,
            [0, 0, 0, 0],
            "the resized avatar the chatter renders lost its transparency: "
            "corner alphas %s" % alphas,
        )


@tagged("post_install", "-at_install")
class TestTheFilesWeShip(BotIdentityCase):
    """DISK ONLY. These two read no record and CANNOT fail for a record change.

    They live in their own class, with their own name, because they were once
    counted as evidence about the partner and they are not. A CI run failed the
    three name/email assertions while six avatar assertions passed; mutation
    testing — setting the row to OdooBot + odoobot.png and re-running — showed
    that four of those six go red and these two do not. That is correct
    behaviour for both of them and it makes them useless as evidence that the
    identity reached the database.

    The upgrade job selects `TestTheSystemPartnerIsOurs` and
    `TestTheBotSignsTheChatter` by name. Keeping these out of those classes is
    what stops the next reader — or the next floor — from counting a file
    comparison as a record measurement.
    """

    def test_the_avatar_we_ship_is_the_brand_asset(self):
        """brand/README.md: "Never recreate or trace them".

        The module carries a copy because an addon must be self-contained, and
        a copy is exactly the thing that drifts into a redraw. This is the
        assertion that makes the copy safe.
        """
        original = self.repo_file(BRAND_AVATAR)
        self.assertTrue(
            os.path.exists(original),
            "%s is not where this test expects the repository root to be" % original,
        )
        with open(original, "rb") as handle:
            self.assertEqual(
                self.shipped(SAPIAN_AVATAR),
                handle.read(),
                "the avatar in this module is no longer byte-identical to the "
                "brand original — a redrawn logo that looks close is worse "
                "than a missing one",
            )

    def test_the_transparency_check_discriminates(self):
        """Odoo's avatar must FAIL the check the previous test passes.

        Without this, a decoder that returned 0 for everything — a wrong chunk
        offset, an unfiltered row — would make the guard above unconditional.
        """
        alphas, _size = png_alpha(self.shipped(ODOO_AVATAR), [(0, 0), (511, 511)])
        self.assertNotEqual(
            alphas,
            [0, 0],
            "Odoo's filled avatar reads as transparent, so the alpha decoder "
            "is not measuring anything",
        )


@tagged("post_install", "-at_install")
class TestTheBotSignsTheChatter(BotIdentityCase):
    """The reproduction: what a client reads at the bottom of a record."""

    def test_a_system_authored_message_is_signed_by_us(self):
        """The confirmed sighting, reduced to what causes it.

        "OdooBot — Product created" on the demo tenant is a message posted
        while the acting user was the root user, whose partner is this one. Any
        record and any body reproduces it; the product is incidental, and
        depending on `product` here would tie this module's tests to an app it
        does not require.
        """
        subject = self.env["res.partner"].create({"name": "Chatter Subject PLC"})
        message = subject.with_user(SUPERUSER_ID).message_post(
            body="<p>Created.</p>", message_type="notification"
        )
        self.assertEqual(
            message.author_id,
            self.bot(),
            "this message was not authored by the system partner, so it does "
            "not reproduce the defect and proves nothing about it",
        )
        self.assertEqual(message.author_id.name, vendor.SAPIAN_BOT, self.row_state())
        self.assertNotIn("odoo", (message.author_id.display_name or "").lower())


@tagged("post_install", "-at_install")
class TestTheApplierActuallyApplies(BotIdentityCase):
    """The method both the install hook and the migration call."""

    def test_it_repairs_a_partner_that_carries_odoos_identity(self):
        """THE DISCRIMINATION PROOF.

        Every assertion above passes on a database where the applier never ran
        but something else happened to set the name. So: put Odoo's identity
        back, run the applier, and require it to undo that.
        """
        bot = self.bot()
        bot.write(
            {
                "name": "OdooBot",
                "email": "odoobot@example.com",
                "image_1920": base64.b64encode(self.shipped(ODOO_AVATAR)),
            }
        )
        self.env.flush_all()
        self.assertTrue(
            self.env["res.partner"]._sapian_apply_bot_identity(),
            "the applier reported no change on a partner that plainly carried " "Odoo's name",
        )
        self.assertEqual(bot.name, vendor.SAPIAN_BOT)
        self.assertEqual(bot.email, vendor.SAPIAN_BOT_EMAIL)
        self.assertEqual(
            base64.b64decode(bot.image_1920),
            self.shipped(SAPIAN_AVATAR),
            "the applier left Odoo's face on the partner",
        )

    def test_running_it_again_changes_nothing(self):
        """Idempotent, because the migration and the hook can both reach it."""
        self.assertFalse(
            self.env["res.partner"]._sapian_apply_bot_identity(),
            "the applier rewrote a partner that already carried our identity, "
            "so it cannot be run twice without churning the record",
        )

    def test_the_xmlid_really_is_noupdate_so_a_data_record_could_not_work(self):
        """READ THE FLAG, do not trust the reasoning that cites it.

        models/res_partner.py argues at length that `<record
        id="base.partner_root">` in our own data file would be SKIPPED on every
        upgrade, because `_load_records` consults the noupdate flag STORED on
        the existing ir_model_data row rather than the one on our XML block.
        That argument is load-bearing — it is the entire reason this identity is
        written from Python — and until now it was only an argument.

        `base` creates the row inside `<data noupdate="True">`. If that ever
        stops being true, the Python route stops being necessary and this test
        should be the thing that says so.
        """
        row = self.env["ir.model.data"].search(
            [("module", "=", "base"), ("name", "=", "partner_root")]
        )
        self.assertEqual(len(row), 1, "base.partner_root has no ir_model_data row")
        self.assertTrue(
            row.noupdate,
            "base.partner_root is no longer noupdate, so an XML record at that "
            "xmlid would now apply on upgrade — the Python applier's whole "
            "justification has changed and models/res_partner.py needs revisiting",
        )

    def test_our_identity_survives_a_writer_that_runs_after_us(self):
        """ORDER-INDEPENDENCE, with the order deliberately against us.

        The defect this module shipped with was not that the applier was wrong.
        It was that the applier ran at this module's position in the graph, and
        that position moved between 26/30 and 27/30 across identical runs. When
        it landed second the name was ours; when it landed first, whatever came
        after won.

        So: run the applier FIRST, then let `mail`'s exact data write land on
        top of it — the write Odoo performs from mail/data/res_partner_data.xml,
        reproduced field for field — and require our identity to be restored by
        the same call the `end-` migration makes. That is the adversarial order,
        expressed as data rather than as a hope about the graph.
        """
        self.env["res.partner"]._sapian_apply_bot_identity()
        bot = self.bot()
        self.assertEqual(bot.name, vendor.SAPIAN_BOT)

        # Precisely what mail/data/res_partner_data.xml sets, landing AFTER us.
        bot.write(
            {
                "name": "OdooBot",
                "image_1920": base64.b64encode(self.shipped(ODOO_AVATAR)),
            }
        )
        self.env.flush_all()
        self.assertEqual(bot.name, "OdooBot", "the adversarial write did not land")

        self.assertTrue(
            self.env["res.partner"]._sapian_apply_bot_identity(),
            "a writer ran after us and the applier reported nothing to do",
        )
        self.assertEqual(
            bot.name,
            vendor.SAPIAN_BOT,
            "a module loading after ours took the bot's name and kept it",
        )
        self.assertEqual(
            base64.b64decode(bot.image_1920),
            self.shipped(SAPIAN_AVATAR),
            "a module loading after ours took the bot's face and kept it",
        )


@tagged("post_install", "-at_install")
class TestTheBundleCarriesOurPatches(BotIdentityCase):
    """The four JS leaks, read out of the bundle the browser is handed."""

    def setUp(self):
        super().setUp()
        self.bundle = self.backend_bundle()

    def test_our_patch_file_reaches_the_browser(self):
        """The failure this catches is silent and has happened on this tree.

        A module `installed` in the database but missing from the serving
        process's addons_path contributes nothing to `ir.asset`, with no
        warning and no exception — see CLAUDE.md. Every other assertion in this
        class would then be asserting about a file nobody loads.
        """
        self.assertTrue(
            "@sapian_theme_mail/js/sapian_bot" in self.bundle,
            "our Discuss patches are not in the served backend bundle at all",
        )

    def test_the_install_prompt_is_ours(self):
        """Asserted in two halves, because it is rendered in two halves.

        The template string is in the bundle; the product name comes from
        `session_info` (sapian_theme/models/ir_http.py) and is interpolated in
        the browser. Asserting the finished "Install SapianERP" would need a
        real browser with a PWA install event, which headless Chrome does not
        raise — so both inputs are asserted instead, and the composition is
        stated rather than implied.
        """
        self.assertTrue(
            "Install %(product)s" in self.bundle,
            "the patched install-prompt label is not in the served bundle",
        )
        session = self.url_open(
            "/web/session/get_session_info",
            data="{}",
            headers={
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(session.status_code, 200)
        self.assertIn(
            vendor.SAPIAN_PRODUCT,
            session.text,
            "the session payload does not carry the product name, so the "
            "prompt above would render with a missing word",
        )

    def test_the_notification_toasts_are_ours(self):
        for template in (
            "%(product)s will send notifications on this device!",
            "%(product)s will not send notifications on this device.",
        ):
            self.assertTrue(
                template in self.bundle,
                "the permission toast %r is not in the served bundle" % template,
            )

    def test_the_push_icon_we_substitute_is_actually_served(self):
        response = self.url_open(SAPIAN_PUSH_ICON)
        self.assertEqual(response.status_code, 200, "our tray icon 404s")
        self.assertEqual(
            response.content,
            self.shipped(SAPIAN_AVATAR),
            "the tray icon route serves something other than the mark we ship",
        )

    def test_the_icon_we_intercept_is_still_the_one_odoo_ships(self):
        """The interception is by value, so the value has to be checked.

        `OutOfFocusService.notify` writes the path as a bare literal in the
        middle of a method; the only way to replace it without copying forty
        lines of message formatting is to recognise it in `sendNotification`.
        If upstream renames the file, that recognition silently stops matching
        — and this assertion is what turns that into a red test.
        """
        self.assertTrue(
            ODOO_PUSH_ICON in self.bundle,
            "the icon path this module intercepts is no longer in mail's "
            "served code, so the substitution matches nothing and desktop "
            "notifications may be carrying a face we are not checking",
        )


@tagged("post_install", "-at_install")
class TestNoNewOdooIdentityAppears(BotIdentityCase):
    """The sweep, in the shape of the purple-template sweep in test_outgoing_email.

    Two surfaces only — the bot partner and the messaging menu — because those
    are the two this module owns. It goes red when the set GROWS, which is the
    regression worth catching: an Odoo release adding a fifth branded string to
    the messaging menu would otherwise ship to every client in silence.

    It is deliberately NOT "no 'Odoo' anywhere in the bundle": that assertion
    returns hundreds of module paths and framework identifiers, and a guard
    that cries every week is a guard somebody deletes.
    """

    # The Odoo-identity strings this surface ships at Odoo 19.0, each one
    # replaced by this module. Pinned, so a NEW one fails rather than joining
    # them silently.
    KNOWN_SURFACE_STRINGS = {
        "Install Odoo",
        "Odoo will send notifications on this device!",
        "Odoo will not send notifications on this device.",
    }

    def test_the_bot_record_carries_no_odoo_identity(self):
        bot = self.bot()
        for field in ("name", "email", "display_name"):
            self.assertNotIn(
                "odoo",
                (bot[field] or "").lower(),
                "the system partner's %s still names Odoo" % field,
            )
        self.assertNotEqual(base64.b64decode(bot.image_1920 or b""), self.shipped(ODOO_AVATAR))

    def test_no_new_odoo_string_appeared_on_the_messaging_menu(self):
        found = self.surface_strings(self.backend_bundle())
        new = found - self.KNOWN_SURFACE_STRINGS
        self.assertFalse(
            new,
            "Odoo's code on the messaging-menu surface carries identity "
            "strings this module does not replace, so they reach the client's "
            "screen: %s" % ", ".join(sorted(new)),
        )

    def test_the_pinned_set_has_not_gone_stale(self):
        """The other direction, and it matters as much.

        If upstream REWORDS one of the three, the sweep above still passes —
        the new wording would be a new string, so it would fail; but a string
        that DISAPPEARS leaves a stale entry in the baseline that quietly
        excuses a future string of the same text. So require every pinned entry
        to still be present.
        """
        found = self.surface_strings(self.backend_bundle())
        missing = self.KNOWN_SURFACE_STRINGS - found
        self.assertFalse(
            missing,
            "these strings are pinned as known and are no longer in the served "
            "bundle; the baseline is stale and the corresponding replacement "
            "in sapian_bot.js is probably now a no-op: %s" % ", ".join(sorted(missing)),
        )

    def test_the_sweep_can_actually_see_a_string(self):
        """THE DISCRIMINATION PROOF for the enumerator.

        Both assertions above pass if `surface_strings` silently returns the
        empty set — a changed wrapper format, a regex that never matches, a
        bundle that came back short. So hand it a region it must parse and
        require the planted string back.
        """
        planted = (
            'odoo.define("@mail/core/web/messaging_menu_patch", () => {'
            ' const x = _t("Odoo planted probe"); });'
            'odoo.define("@mail/core/common/notification_permission_service", () => {});'
            'odoo.define("@mail/core/common/out_of_focus_service", () => {});'
        )
        self.assertIn(
            "Odoo planted probe",
            self.surface_strings(planted),
            "the sweep did not notice a string it was handed directly, so its "
            "green result means nothing",
        )
