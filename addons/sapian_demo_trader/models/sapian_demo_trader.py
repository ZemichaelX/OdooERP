# -*- coding: utf-8 -*-
"""Provisioning of the 'Selam General Trading PLC' demo tenant.

The company is onboarded through the REAL sapian.onboarding.wizard (dogfooding
the Epic C wizard), then one July-2026 month of trading data is created through
the REAL business flows (quotation → delivery → invoice, PO → receipt → bill,
payroll batch), so the tenant doubles as the sales demo with every compliance
feature visibly firing:

- 15% VAT on sales and purchases (Proc 1341/2024)
- 3% WHT on a compliant supplier, 30% punitive on a domestic no-TIN supplier
  (red MISSING row on the WHT summary), 15% on a foreign digital provider
  ("N/A (foreign)" TIN column)
- payroll with a taxable-overtime case and one employee missing a POESSA
  pension ID (fix-before-filing banner on the pension schedule)

Hand-computed month totals (tests enforce): output VAT 17,295 on 115,300; input
VAT 13,770 on 91,800; net VAT +3,525 PAYABLE; WHT 2,064 + 4,500 + 1,200 = 7,764;
payroll gross 58,300, PAYE 11,525, pension 3,941/6,193, net 42,834.

The tenant also carries a SALES PIPELINE — three draft quotations, one sent,
one confirmed and delivered but deliberately not invoiced — so the Sales app
opens on something to walk through. None of it posts to the ledger, so none of
the totals above move with it.

These follow from demo_catalogue.py: every order line takes its price_unit from
cat.PRICES, so the month's totals are DOWNSTREAM of the catalogue, not an
independent golden. Change a price and these move — recompute them, do not
"fix" the prices to match. July deliberately ends in a VAT PAYABLE: a materials
retailer buys stock and turns it within weeks, so a normal month has output
above input; a credit only happens in a heavy stocking-up month.

All dates are pinned inside July 2026 so every statutory report has one clean
period window with exact GL tie-outs, independent of the wall clock.
"""

import base64
import logging

from odoo import Command, api, models
from odoo.exceptions import UserError
from odoo.tools import file_open

from . import demo_catalogue as cat

_logger = logging.getLogger(__name__)

DEMO_COMPANY_NAME = "Selam General Trading PLC"
PERIOD_FROM = "2026-07-01"
PERIOD_TO = "2026-07-31"

# The support line the demo's login page and backend footer carry.
#
# A plausible Ethiopian number, and deliberately NOT a real one: +251 is
# Ethiopia's country code and 011 is the Addis Ababa landline prefix, so it
# reads correctly to an Ethiopian prospect. It belongs to the demo tenant, the
# same way "Selam General Trading PLC" does — a real client's number is
# configured at provisioning, not shipped in a demo module.
DEMO_SUPPORT_CONTACT = "+251 11 123 4567 / support@selamtrading.example"

# Where Odoo stores the "Customer Account" setting. Used only as a fallback
# when `auth_signup` is not installed and the field cannot be asked — see
# _signup_scope_param.
SIGNUP_SCOPE_PARAM = "auth_signup.invitation_scope"

# The catalog tiers the demo tenant actually installs. The `optional` tier —
# CRM, Manufacturing, Project, Email Marketing, Fleet, Repair, Maintenance,
# Website & eCommerce — is deliberately left OUT, and the manifest does not
# depend on those modules either. Both halves are required: picking fewer
# entries here only unblocks the removal, the manifest is what installs them.
#
# The reason is the main menu bar, not the catalog page. Installing those apps
# puts Manufacturing, Project, Fleet, Repair, Maintenance and Website in the
# menu of a tenant built for a 2–5 person hardware shop, and the menu bar is in
# every frame of a screen recording.
#
# They are NOT hidden: every catalog entry is still seeded, so the catalog shows
# what is enabled alongside what is available. "Here is what you are buying, here
# is what is there when you want it" is a better answer to "so it does
# manufacturing?" than pretending the apps do not exist.
#
# HOW THE DEMO PICKS, and why it is no longer by tier.
#
# The contract is: every entry handed to the wizard is already a manifest
# dependency of this module, so the wizard's install step is a guaranteed no-op
# and no registry replacement happens mid-provision. Tier used to be a proxy for
# that — core+common happened to coincide with this module's dependencies while
# the catalog held 15 curated entries.
#
# It stopped coinciding the moment the catalog became the FULL app catalogue:
# `common` now contains crm, project, point_of_sale, calendar, contacts, board
# and the hr_* apps, none of which this module depends on. Picking by tier would
# have handed the wizard nine modules to install mid-load — exactly the failure
# the contract exists to prevent.
#
# So the demo now picks on the PROPERTY ITSELF: catalog entries that are
# reachable dependencies of sapian_demo_trader. The guarantee is true by
# construction rather than by a coincidence nobody re-checked.
#
# DEMO_CATALOG_TIERS is deliberately GONE rather than left unused: a constant
# that no longer selects anything is a comment that looks like code, and the
# next reader would reasonably assume tiers still drive the demo.

# Odoo default/demo placeholder companies: a demo DB's company switcher must
# only show real companies, and a fresh login must land in the real one.
PLACEHOLDER_COMPANY_NAMES = [
    "My US Company",
    "My Company (Chicago)",
    "My Company (San Francisco)",
    "YourCompany",
    # The name the base company carries when Odoo demo data is DISABLED — the
    # build_demo.sh path adopts it instead, but a plain install would leave it
    # sitting in the company switcher next to the demo tenant.
    "My Company",
]


class SapianDemoTrader(models.AbstractModel):
    _name = "sapian.demo.trader"
    _description = "SapianERP Demo Trader Provisioning"

    @api.model
    def _provision_demo_tenant_on_install(self):
        """Entry point for data/demo_trader.xml — ADOPTS the existing company.

        Said out loud here rather than inferred: scripts/build_demo.sh creates
        the database with `base` only, sets the single company's country to
        Ethiopia, and only then installs this module, so the 'et' chart loads
        onto that company and this provisioning configures the same one. The
        result is a database with exactly ONE company, built by the same path
        a real client is built by.
        """
        return self._provision_demo_tenant(adopt_existing=True)

    @api.model
    def _demo_installable_names(self):
        """Technical names this module already brings in, transitively.

        The set the demo may safely hand to the onboarding wizard: every one is
        a manifest dependency, hence already installed when this module loads,
        hence a no-op for the wizard's install step (which only touches modules
        in state 'uninstalled').
        """
        return self.env["sapian.module.catalog"]._reachable_module_names("sapian_demo_trader")

    def _provision_demo_tenant(self, company_name=DEMO_COMPANY_NAME, adopt_existing=False):
        """Provision the full demo tenant (idempotent by company name).

        ``adopt_existing`` — when True, configure the database's single
        existing company as the demo tenant instead of creating a new one.
        Deliberately an explicit flag and not a "is there one unconfigured
        company?" heuristic: a predicate over what "unconfigured" means would
        drift and surprise somebody later. Both call sites state what they
        want (data/ passes True via the wrapper above; the tests pass nothing
        and get the create path).

        Returns the demo company. Idempotent on BOTH paths — data/ means this
        re-runs on every module upgrade.
        """
        # Before the early return, so a demo database provisioned before this
        # existed picks the setting up on its next run.
        self._enable_multi_uom()
        existing = self.env["res.company"].search([("name", "=", company_name)], limit=1)
        if existing:
            if company_name == DEMO_COMPANY_NAME:
                # Re-running on an already-provisioned DB (module upgrade)
                # still applies the login cleanup — older demo DBs predate it.
                self._configure_demo_login(existing)
            return existing
        company = self._onboard_company(company_name, adopt_existing=adopt_existing)
        self._set_company_logo(company)
        # stock only auto-creates warehouses for new companies in TEST mode
        # (stock/models/res_company.py); at demo-load time we must create it
        # ourselves or SO confirmation finds no delivery rule.
        warehouse_model = self.env["stock.warehouse"].sudo()
        if not warehouse_model.search_count([("company_id", "=", company.id)]):
            warehouse_model.create({"company_id": company.id})
        env = self.env(context=dict(self.env.context, allowed_company_ids=company.ids))
        demo = env["sapian.demo.trader"].with_company(company)
        products = demo._create_products()
        partners = demo._create_partners()
        demo._create_opening_stock(products)
        employees = demo._create_employees()
        demo._run_sales_flow(partners, products)
        # After the invoiced flow, so the pipeline's one confirmed order draws
        # on what July actually leaves on hand rather than on opening stock.
        demo._create_quotations(partners, products)
        demo._run_purchase_flow(partners, products)
        demo._create_direct_bills(partners, products)
        demo._run_payroll(employees)
        demo._create_report_periods()
        if company_name == DEMO_COMPANY_NAME:
            self._configure_demo_login(company)
        return company

    @api.model
    def _enable_multi_uom(self):
        """Turn ON Settings → Inventory → "Units of Measure & Packagings".

        The quintal/bag pair is the demo's headline moment, and Odoo gates
        every UoM field on ``uom.group_uom``: with the setting off the product
        form shows no unit at all and the purchase line has no unit column, so
        the conversion the whole re-theme was built around is data nobody can
        see. Creating it without enabling its display is the same fault class
        as seeding a catalog nothing ever calls.

        This is exactly what ``res.config.settings`` does for a ``group_``
        field — link the implied group into ``base.group_user``
        (product/models/res_config_settings.py: ``group_uom =
        fields.Boolean(..., implied_group='uom.group_uom')``, and a group field
        with no ``group=`` attribute applies to ``base.group_user``). Done
        directly rather than through ``res.config.settings.execute()`` because
        that method also installs and uninstalls modules from its ``module_``
        fields, which must never happen during provisioning. Idempotent:
        ``_apply_group`` skips groups that already imply it.
        """
        # sudo: group administration, same as the rest of provisioning.
        self.env.ref("base.group_user").sudo()._apply_group(self.env.ref("uom.group_uom"))

    @api.model
    def _set_company_logo(self, company):
        """Give the demo tenant its OWN mark — deliberately not the Sapian one.

        WHOSE LOGO THIS IS, because it is the whole argument.

        Selam General Trading PLC is the demo CLIENT: a fictional Addis
        building-materials trader. Putting the Sapian logo on its invoices
        would teach a prospect exactly the wrong thing — that documents printed
        out of the system carry the VENDOR's brand — in the same session where
        we claim the product is white-labelled. The moment the demo needs is
        "this is YOUR letterhead, and one field changes it", and that moment
        only exists if the letterhead is visibly the client's.

        Leaving Odoo's default is worse still: `uses_default_logo` renders the
        stock Odoo wordmark on every invoice, which contradicts the branding
        claim on screen while it is being made. That is why this is not
        optional and why a test asserts `uses_default_logo` is False rather
        than merely asserting the field is filled — the field is ALWAYS filled
        (`res.company.logo` has `default=_get_logo`), so "non-empty" is a check
        that passes by doing nothing.

        static/img/selam_logo.png is a generated geometric mark: a rounded tile
        in the tenant's own primary colour carrying a stack of six blocks (the
        HCB it sells), beside a plain sans wordmark. Generic on purpose. It is
        demo furniture with no brand status — replace it freely; the real brand
        assets live in brand/.
        """
        with file_open("sapian_demo_trader/static/img/selam_logo.png", "rb") as logo_file:
            company.sudo().logo = base64.b64encode(logo_file.read())

    @api.model
    def _configure_demo_login(self, company):
        """A fresh admin login lands in the real demo company, never in an
        Odoo placeholder: admin defaults to ``company`` (allowed: the real
        companies only), every user is moved off the placeholders, and ALL
        placeholder companies — including the original main company — are
        archived. Idempotent."""
        # The demo company went through the wizard by construction; demo DBs
        # provisioned before the completion flag existed must not reopen it.
        company.sapian_onboarding_done = True
        et_demo = self.env.ref("base.demo_company_et", raise_if_not_found=False)
        real_companies = company | (et_demo or self.env["res.company"])
        placeholders = self.env["res.company"].search(
            [
                ("name", "in", PLACEHOLDER_COMPANY_NAMES),
                ("id", "not in", real_companies.ids),
            ]
        )
        # sudo: user/company administration during demo provisioning.
        users = (
            self.env["res.users"]
            .sudo()
            .with_context(active_test=False)
            .search([("company_ids", "in", placeholders.ids)])
        )
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        for user in users:
            kept = real_companies if user == admin else user.company_ids - placeholders
            if not kept:
                kept = company
            # The new default must be one of the user's OWN kept companies —
            # anything else violates the company_id-in-company_ids constraint.
            new_default = user.company_id if user.company_id not in placeholders else kept[0]
            user.write(
                {
                    "company_ids": [Command.set(kept.ids)],
                    "company_id": new_default.id,
                }
            )
        if admin:
            admin.sudo().write(
                {
                    "company_ids": [Command.set(real_companies.ids)],
                    "company_id": company.id,
                }
            )
        if placeholders:
            placeholders.sudo().write({"active": False})
        self._configure_login_page()

    @api.model
    def _configure_login_page(self):
        """The two system parameters the login page a prospect sees depends on.

        SIGNUP OFF. Odoo's default is `b2c` — FREE SIGN UP — declared on
        `res.config.settings.auth_signup_uninvited`
        (auth_signup/models/res_config_settings.py:13). Nothing in this repo
        changed it, so every demo login page has been offering "Don't have an
        account?" on a private company ERP. `b2b` means invitation only:
        existing users can still be sent a signup link, a stranger cannot make
        themselves one.

        The parameter KEY is read off Odoo's own field rather than typed here.
        The setting is called `auth_signup_uninvited` but it stores itself
        under `auth_signup.invitation_scope`, and a literal of either name is a
        string that can silently stop matching. Asking the field means we
        follow a rename instead of failing quietly under it.

        SUPPORT CONTACT. sapian_theme reads `sapian_theme.support_contact` on
        the login page and in the backend footer, and renders NOTHING when it is
        empty — which is what the demo did: the feature existed, a test asserted
        it renders when configured, and no build ever configured it. A feature
        nobody switches on is indistinguishable from a feature nobody wrote.

        Both are set unconditionally rather than only-if-absent: this is the
        demo tenant, and its login page is a scripted artefact, not a place to
        preserve somebody's local experiment.
        """
        params = self.env["ir.config_parameter"].sudo()
        params.set_param(self._signup_scope_param(), "b2b")
        params.set_param("sapian_theme.support_contact", DEMO_SUPPORT_CONTACT)

    @api.model
    def _signup_scope_param(self):
        """The system-parameter key behind the "Customer Account" setting.

        Read from the field so a rename in Odoo follows automatically. The
        fallback is the documented key, used only when `auth_signup` is not
        installed — in which case there is no signup route to disable and
        writing the parameter is simply harmless.
        """
        field = self.env["res.config.settings"]._fields.get("auth_signup_uninvited")
        return getattr(field, "config_parameter", None) or SIGNUP_SCOPE_PARAM

    @api.model
    def _onboard_company(self, company_name, adopt_existing=False):
        """Create (or adopt) a company and push it through the onboarding wizard.

        The wizard applies profile, branding, catalog and Ethiopian defaults.
        No module installation can occur here: the wizard is handed the
        entries that are already its own dependencies, and every one of those is a
        manifest dependency of this module, so the wizard's install step is a
        guaranteed no-op (no registry replacement mid-provision). The
        `optional` tier is seeded into the catalog but not picked, so it shows
        as available-and-not-enabled — see _demo_installable_names.

        With ``adopt_existing`` the database's single company is reused, which
        is what yields a one-company demo. It RAISES if that company already
        carries a chart of accounts that is not the Ethiopian one: Odoo does
        not allow switching charts afterwards, so silently adopting a
        generic_coa company would produce a demo tenant on the wrong books —
        wrong in a way that is invisible until an accountant looks.
        """
        company = False
        if adopt_existing:
            candidate = self.env["res.company"].search([], order="id", limit=1)
            # Adoption is only safe on a company that has NOT already taken a
            # foreign chart: Odoo does not allow switching charts afterwards,
            # so adopting a generic_coa company would produce a demo tenant on
            # the wrong books — wrong in a way that stays invisible until an
            # accountant looks. scripts/build_demo.sh sets the country to
            # Ethiopia before the accounting modules install, which is what
            # makes adoption safe there.
            #
            # Anywhere else (a database built WITH Odoo demo data, e.g. the CI
            # integration job) the request cannot be honoured. That is not a
            # reason to fail the install: fall back to creating a separate
            # company, but SAY SO — a silent fallback is how you end up with a
            # demo on the wrong chart and no idea why.
            if candidate and candidate.chart_template in (False, "et"):
                candidate.write({"name": company_name})
                company = candidate
            else:
                _logger.warning(
                    "sapian_demo_trader: cannot adopt company %s (chart %r); "
                    "creating a separate demo company instead. For a "
                    "one-company demo build with scripts/build_demo.sh, which "
                    "sets the country BEFORE the accounting modules install.",
                    candidate.display_name if candidate else "<none>",
                    candidate.chart_template if candidate else None,
                )
        if not company:
            company = self.env["res.company"].create({"name": company_name})
        catalog = self.env["sapian.module.catalog"]._ensure_default_catalog(company)
        picks = catalog._filter_safe_to_pick("sapian_demo_trader")
        wizard = (
            self.env["sapian.onboarding.wizard"]
            .with_company(company)
            .create(
                {
                    "company_id": company.id,
                    "company_name": company_name,
                    "tin": "0088776655",
                    "street": "Africa Avenue (Bole Road)",
                    "city": "Addis Ababa",
                    "fiscal_year": "ethiopian",
                    "primary_color": "#1a7f5a",
                    "module_catalog_ids": [Command.set(picks.ids)],
                }
            )
        )
        wizard.action_apply()
        return company

    def _create_uoms(self):
        """The cement unit pair: 1 quintal = 2 bags of 50 kg.

        Odoo 19 has no UoM *categories* — units form a tree through
        ``relative_uom_id``/``relative_factor`` (a Dozen is 12 Units the same
        way), and a product offers additional units via ``uom_ids``. So the
        BAG is the stock unit and the QUINTAL is a related unit worth two of
        them: a purchase line for 30 quintals lands as 60 bags in stock, which
        is the conversion a materials trader checks first.
        """
        uom_model = self.env["uom.uom"].sudo()
        bag = uom_model.search([("name", "=", cat.UOM_BAG_NAME)], limit=1)
        if not bag:
            bag = uom_model.create({"name": cat.UOM_BAG_NAME, "relative_factor": 1.0})
        quintal = uom_model.search([("name", "=", cat.UOM_QUINTAL_NAME)], limit=1)
        if not quintal:
            quintal = uom_model.create(
                {
                    "name": cat.UOM_QUINTAL_NAME,
                    "relative_uom_id": bag.id,
                    "relative_factor": cat.BAGS_PER_QUINTAL,
                }
            )
        return bag, quintal

    def _create_products(self):
        """The building-materials catalogue, in the units of the trade.

        Names, units and every price live in demo_catalogue.py so they can be
        checked against the market without reading this file.
        """
        self.env["product.pricelist"].create(
            {
                "name": "ETB Retail Pricelist",
                "currency_id": self.env.ref("base.ETB").id,
                "company_id": self.env.company.id,
            }
        )
        bag, quintal = self._create_uoms()
        unit_by_key = {
            "kg": self.env.ref("uom.product_uom_kgm"),
            "piece": self.env.ref("uom.product_uom_unit"),
            "m3": self.env.ref("uom.product_uom_cubic_meter"),
        }
        categories = self._create_product_categories()
        product_model = self.env["product.product"]
        products = {}
        for key, name, amharic, unit, sale, cost in cat.PRODUCTS:
            label = f"{name} — {amharic}" if amharic else name
            vals = {
                "name": label,
                "list_price": sale,
                "standard_price": cost,
                # Never left to fall back on "All": that category carries Odoo's
                # default periodic valuation, which posts no cost-of-goods entry
                # at all. See _create_product_categories.
                "categ_id": categories[cat.CATEGORY_BY_PRODUCT[key]].id,
            }
            if unit == "service":
                vals["type"] = "service"
            else:
                vals.update({"type": "consu", "is_storable": True})
                if unit == "bag":
                    # Sold in bags, bought in quintals — both offered on lines.
                    vals["uom_id"] = bag.id
                    vals["uom_ids"] = [Command.set([bag.id, quintal.id])]
                else:
                    vals["uom_id"] = unit_by_key[unit].id
            products[key] = product_model.create(vals)
        return products

    def _account(self, code):
        """One account of the tenant's own chart, by code, or a clear failure.

        Resolved by CODE rather than xmlid so this works on any chart that
        carries the code, and so a missing account is a named error instead of
        a silent False that would later post nowhere.
        """
        account = self.env["account.account"].search(
            [
                *self.env["account.account"]._check_company_domain(self.env.company),
                ("code", "=", code),
            ],
            limit=1,
        )
        if not account:
            raise UserError(
                self.env._(
                    "The demo needs account %(code)s and this company's chart does "
                    "not carry it. Perpetual stock valuation cannot be configured "
                    "without it, and without that the profit & loss reports a cost "
                    "of sales of zero.",
                    code=code,
                )
            )
        return account

    def _create_product_categories(self):
        """Categories that actually value stock, which is the whole point.

        WHAT WAS WRONG. No product carried a category, so every one of them sat
        in "All". `stock_account/data/stock_account_data.xml` sets the system
        default `property_valuation = 'periodic'` on product.category, and
        periodic means "the accounting entries are suggested manually in the
        inventory valuation report" — i.e. none are posted. The gate is
        `stock_account/models/account_move.py`:

            if not line._eligible_for_stock_account() \
                    or line.product_id.valuation != 'real_time':
                continue

        called unconditionally from `_post`. There is no anglo-saxon condition;
        `real_time` plus the two accounts is the whole requirement. Without it
        the July profit & loss showed revenue 115,300.00 and cost of sales
        0.00 — a trader who sold building materials that cost nothing, which is
        the first thing an accountant disbelieves.

        WHY FIFO. `standard` costing would value the cost of sales at the
        product's standard price and push any difference against the real
        purchase price into a price-difference account — a line the demo would
        then have to explain. FIFO values each receipt at what was actually paid
        for it, so the cost of sales IS the cost of those goods, and no
        price-difference account is needed.

        NO INTERIM ACCOUNTS ARE SET, and that is not an omission. Odoo 19
        removed `property_stock_account_input_categ_id` and
        `property_stock_account_output_categ_id` from product.category — a
        search of the whole 19.0 tree finds no reference to either — and setting
        them would raise on create. The fields that survive are
        property_valuation, property_cost_method, property_stock_journal,
        property_stock_valuation_account_id and
        property_price_difference_account_id. FIFO needs no price-difference
        account, because each receipt is valued at what was actually paid.
        """
        category_model = self.env["product.category"]
        valuation = self._account(cat.STOCK_VALUATION_CODE)
        cogs = self._account(cat.COGS_CODE)
        service_expense = self._account(cat.SERVICE_EXPENSE_CODE)
        journal = self.env["account.journal"].search(
            [
                ("company_id", "=", self.env.company.id),
                ("type", "=", "general"),
            ],
            limit=1,
        )
        created = {}
        for key, name, amharic in cat.CATEGORIES:
            vals = {"name": f"{name} — {amharic}" if amharic else name}
            if key == "services":
                # An operating expense account, so service bills stop falling
                # back on the company default and accumulating in 230100.
                vals["property_account_expense_categ_id"] = service_expense.id
            else:
                # Goods. Valuation accounts belong only here — putting them on a
                # category that holds no stock is configuration a reader has to
                # discount rather than read.
                vals.update(
                    {
                        "property_cost_method": "fifo",
                        "property_valuation": "real_time",
                        "property_stock_valuation_account_id": valuation.id,
                        "property_stock_journal": journal.id,
                        "property_account_expense_categ_id": cogs.id,
                    }
                )
            created[key] = category_model.create(vals)
        return created

    def _create_partners(self):
        """Customers + the three supplier compliance profiles.

        Names come from demo_catalogue.py. The compliance SHAPES are load
        bearing and must not change: one supplier with TIN + licence (3%), one
        domestic supplier with NO TIN (30% punitive — the strongest moment in
        the demo), one foreign digital provider (15%).
        """
        partner_model = self.env["res.partner"]
        ethiopia = self.env.ref("base.et")
        return {
            "mebrat": partner_model.create(
                {
                    "name": cat.CUSTOMER_MEBRAT,
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Addis Ababa",
                    "l10n_et_tin": "0022334455",
                    "l10n_et_name_amharic": "መብራት ኮንስትራክሽን",
                }
            ),
            "abyssinia": partner_model.create(
                {
                    "name": cat.CUSTOMER_ABYSSINIA,
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Adama",
                    "l10n_et_tin": "0033445566",
                }
            ),
            # Pipeline-only customers — quotations, no invoices. They all carry
            # a TIN: a quotation that would become a non-compliant invoice is
            # not a quotation anybody should be shown.
            "rift_valley": partner_model.create(
                {
                    "name": cat.CUSTOMER_RIFT_VALLEY,
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Bishoftu",
                    "l10n_et_tin": "0044556677",
                }
            ),
            "hawassa": partner_model.create(
                {
                    "name": cat.CUSTOMER_HAWASSA,
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Hawassa",
                    "l10n_et_tin": "0055667788",
                }
            ),
            "tsehay": partner_model.create(
                {
                    "name": cat.CUSTOMER_TSEHAY,
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "city": "Addis Ababa",
                    "l10n_et_tin": "0066778899",
                }
            ),
            # Compliant supplier: TIN + valid licence -> standard 3% WHT.
            "depot": partner_model.create(
                {
                    "name": cat.SUPPLIER_COMPLIANT,
                    "is_company": True,
                    "country_id": ethiopia.id,
                    "l10n_et_tin": "0011223344",
                    "l10n_et_business_licence_no": "AA/5678/2015",
                    "l10n_et_business_licence_expiry": "2030-06-30",
                }
            ),
            # Domestic supplier WITHOUT a TIN -> punitive 30% + MISSING row.
            # Keep this profile: it is the withholding demonstration.
            "yonas": partner_model.create(
                {
                    "name": cat.SUPPLIER_NO_TIN,
                    "is_company": True,
                    "country_id": ethiopia.id,
                }
            ),
            # Foreign digital provider -> 15% WHT, "N/A (foreign)" TIN column.
            "buildsoft": partner_model.create(
                {
                    "name": cat.SUPPLIER_FOREIGN,
                    "is_company": True,
                    "country_id": self.env.ref("base.us").id,
                    "l10n_et_is_foreign_digital": True,
                }
            ),
        }

    def _create_employees(self):
        """One employee per PAYE band, plus the job titles that make it read.

        The roster and the reasoning live in demo_catalogue.EMPLOYEES: six
        people, one in each of Proclamation 1395/2025's six monthly bands, so
        the progressive table is visible at a glance on the payslip list rather
        than being something a salesperson has to describe. Chaltu's missing
        POESSA id and Bekele's overtime are both deliberate and both explained
        there.

        Job titles are not decoration: "Cleaner 1,800 — no tax" next to
        "General Manager 25,000 — 35%" is the demonstration. Without them the
        list is six names and six numbers.
        """
        company = self.env.company
        ethiopia = self.env.ref("base.et")
        bank = self.env["res.bank"].create(
            {"name": "Commercial Bank of Ethiopia", "bic": "CBETETAA"}
        )
        employee_model = self.env["hr.employee"]

        def employee(name, job_title, wage, tin, pension_id, account_number):
            record = employee_model.create(
                {
                    "name": name,
                    "job_title": job_title,
                    "company_id": company.id,
                    "country_id": ethiopia.id,
                    "l10n_et_tin": tin,
                    "l10n_et_pension_id": pension_id,
                }
            )
            # sudo: wage/bank fields are HR-group restricted; provisioning runs
            # as the superuser anyway, sudo keeps it explicit.
            record.sudo().version_id.write({"wage": wage})
            if record.work_contact_id:
                account = self.env["res.partner.bank"].create(
                    {
                        "partner_id": record.work_contact_id.id,
                        "bank_id": bank.id,
                        "acc_number": account_number,
                    }
                )
                record.sudo().bank_account_ids = [Command.link(account.id)]
            return record

        return {row[0]: employee(*row[1:]) for row in cat.EMPLOYEES}

    @api.model
    def _demo_salesperson(self):
        """The user every demo sale order is assigned to, and why it matters.

        Odoo's Sales app opens on `sale.action_quotations_with_onboarding`,
        whose context is `{'search_default_my_quotation': 1}` — a default
        filter of `user_id = uid`. Provisioning runs through `odoo shell`,
        where `env.user` is OdooBot (uid 1), so every order was being stamped
        with OdooBot as salesperson and the demo login (admin, uid 2) opened
        Sales on ZERO rows.

        Odoo does not leave that void empty. It renders its ONBOARDING SAMPLE
        DATA over the list: ghosted quotations for Henry Campbell, John Miller
        and Thomas Passot, priced in DOLLARS, under a "Beat competitors with
        stunning quotations!" video. A prospect being sold Ethiopian software
        sees American names and USD — the same class of fault as the US
        placeholder companies this module already archives, and it survived
        precisely because "there are orders in the database" was true.

        So the salesperson is set explicitly to the account the demo is
        presented from, on every order including the invoiced ones. Never left
        to default.
        """
        return self.env.ref("base.user_admin")

    def _create_quotations(self, partners, products):
        """The sales pipeline: drafts, one sent, one confirmed-not-invoiced.

        Without these the Sales app opens on an empty list, and the demo has
        nothing to walk from quotation to invoice — the single most ordinary
        thing an ERP is bought to do. The set and the reasoning are in
        demo_catalogue.QUOTATIONS.

        NOTHING HERE POSTS TO THE LEDGER. Draft and sent orders create no
        accounting entries at all, and the one confirmed order is deliberately
        left uninvoiced, so every VAT, WHT and payroll golden in this module is
        untouched BY CONSTRUCTION rather than by luck. That is the property to
        preserve if this list grows: add drafts freely, invoice nothing.
        """
        order_model = self.env["sale.order"]
        salesperson = self._demo_salesperson()
        pricelist = self.env["product.pricelist"].search(
            [
                ("currency_id", "=", self.env.ref("base.ETB").id),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        created = order_model
        for state, customer_key, lines, order_date in cat.QUOTATIONS:
            order = order_model.create(
                {
                    "partner_id": partners[customer_key].id,
                    "pricelist_id": pricelist.id,
                    "user_id": salesperson.id,
                    "date_order": "%s 09:00:00" % order_date,
                    "validity_date": "2026-08-31",
                    "order_line": [
                        Command.create(
                            {
                                "product_id": products[product_key].id,
                                "product_uom_qty": quantity,
                                "price_unit": price,
                            }
                        )
                        for product_key, quantity, price in lines
                    ],
                }
            )
            if state == "sent":
                # Odoo's own transition, rather than writing `state` — a demo
                # built by poking fields is a demo that stops matching the
                # product the first time the transition grows a side effect.
                order.action_quotation_sent()
            elif state == "sale":
                order.action_confirm()
                # Same rewrite as the invoiced flow above: confirmation resets
                # date_order to now().
                order.date_order = "%s 09:00:00" % order_date
                self._validate_pickings(order.picking_ids)
            created |= order
        return created

    def _validate_pickings(self, pickings):
        """Set full quantities and validate (delivery/receipt)."""
        for picking in pickings:
            picking.action_assign()
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
                move.picked = True
            picking.button_validate()

    def _create_opening_stock(self, products):
        """Opening stock for what the month sells.

        Without it the July deliveries drive on-hand negative, which is the
        first thing a materials trader looks at. Cement is deliberately LEFT
        OUT: its only movement is the 30-quintal purchase, so the 60 bags that
        land in stock are unambiguously the quintal->bag conversion.
        """
        quant_model = self.env["stock.quant"].sudo()
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        # Sized for a month at the real trading volume (see _run_sales_flow).
        # hcb_20 is DELIBERATELY short of what July sells: 4,000 opening against
        # 8,800 sold, with 6,000 bought in during the month. That is what makes
        # it the product the demo can be traced through — opening, purchase,
        # sale and a closing figure that is none of them by accident.
        opening = {"sheet_g32": 500, "rebar_12": 1200, "hcb_20": 4000}
        for key, quantity in opening.items():
            quant_model.with_context(inventory_mode=True).create(
                {
                    "product_id": products[key].id,
                    "location_id": warehouse.lot_stock_id.id,
                    "inventory_quantity": quantity,
                }
            )._apply_inventory()

    def _run_sales_flow(self, partners, products):
        """Two quotation -> delivery -> invoice flows with 15% VAT.

        Output VAT golden: 35,200 + 80,100 = 115,300 base -> 17,295 VAT.
          Mebrat:    40 sheets G32 @ 880             = 35,200
          Abyssinia: 100 kg rebar 12 @ 193 = 19,300
                     + 800 HCB @ 76        = 60,800 = 80,100

        The 800-block line is the one demo QUANTITY tuned to the month's shape
        rather than to a product: it puts output VAT comfortably above input so
        July reads as a normal trading month (payable), not a stocking-up one.
        It is 40% of the 2,000-block opening stock, so nothing goes negative.
        Orders use the ETB pricelist so the invoices are priced and reported
        in the company currency, not Odoo's default USD pricelist.
        """
        order_model = self.env["sale.order"]
        pricelist = self.env["product.pricelist"].search(
            [
                ("currency_id", "=", self.env.ref("base.ETB").id),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        salesperson = self._demo_salesperson()
        order_mebrat = order_model.create(
            {
                "partner_id": partners["mebrat"].id,
                "pricelist_id": pricelist.id,
                "user_id": salesperson.id,
                "date_order": "%s 09:00:00" % cat.INVOICED_ORDER_DATES["mebrat"],
                "order_line": [
                    Command.create(
                        {
                            "product_id": products["sheet_g32"].id,
                            "product_uom_qty": 440,
                            "price_unit": cat.PRICES["sheet_sale"],
                        }
                    )
                ],
            }
        )
        order_abyssinia = order_model.create(
            {
                "partner_id": partners["abyssinia"].id,
                "pricelist_id": pricelist.id,
                "user_id": salesperson.id,
                "date_order": "%s 09:00:00" % cat.INVOICED_ORDER_DATES["abyssinia"],
                "order_line": [
                    Command.create(
                        {
                            "product_id": products["rebar_12"].id,
                            "product_uom_qty": 1100,
                            "price_unit": cat.PRICES["rebar_sale"],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": products["hcb_20"].id,
                            "product_uom_qty": 8800,
                            "price_unit": cat.PRICES["hcb_sale"],
                        }
                    ),
                ],
            }
        )
        for order in order_mebrat | order_abyssinia:
            ordered_on = order.date_order
            order.action_confirm()
            # Odoo stamps date_order with now() on confirmation
            # (sale.order._prepare_confirmation_values), so a scripted demo
            # order ends up dated the day the database was BUILT. Put the July
            # date back — an order list where every row reads "15:51 today" is
            # worse than no dates at all.
            order.date_order = ordered_on
            self._validate_pickings(order.picking_ids)
            invoices = order._create_invoices()
            # Set the due date alongside the invoice date: with no payment term
            # the due date is otherwise left at the (earlier) creation date,
            # producing a due-before-issued document.
            invoices.write({"invoice_date": "2026-07-10", "invoice_date_due": "2026-08-09"})
            invoices.action_post()

    def _run_purchase_flow(self, partners, products):
        """PO -> receipt -> vendor bill from the COMPLIANT supplier.

        THE UNIT MOMENT: cement is ordered in QUINTALS and lands in stock as
        BAGS, 30 -> 60. Nothing else moves cement, so the 60 bags on hand are
        the conversion and nothing else.

        Base 482,800 -> 3% WHT 14,484, input VAT 72,420:
            30 quintals cement OPC @ 2,000 =  60,000
            50 kg rebar 8 mm       @   176 =   8,800
            6,000 HCB 20           @    69 = 414,000

        The 30 quintals are load-bearing and must not be reduced to make a
        rounder WHT figure: they are what produces the 60 bags on hand.

        The 6,000 blocks are load-bearing for a different reason: they are the
        only line in the demo that buys a product the same month also sells,
        which is what lets one product be followed the whole way through.
        """
        quintal = self.env["uom.uom"].search([("name", "=", cat.UOM_QUINTAL_NAME)], limit=1)
        order = self.env["purchase.order"].create(
            {
                "partner_id": partners["depot"].id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": products["cement_dangote"].id,
                            "product_qty": 30,
                            "product_uom_id": quintal.id,
                            "price_unit": cat.PRICES["cement_opc_quintal_cost"],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": products["rebar_8"].id,
                            "product_qty": 50,
                            "price_unit": cat.PRICES["rebar_cost"],
                        }
                    ),
                    # THE SAME SKU THE MONTH SELLS. Until this line the demo
                    # bought two products and sold three different ones, so no
                    # single product could be followed from purchase order to
                    # delivery note. 6,000 blocks in, 8,800 out against 4,000
                    # opening, leaving 1,200 on hand.
                    Command.create(
                        {
                            "product_id": products["hcb_20"].id,
                            "product_qty": 6000,
                            "price_unit": cat.PRICES["hcb_cost"],
                        }
                    ),
                ],
            }
        )
        order.button_confirm()
        self._validate_pickings(order.picking_ids)
        order.action_create_invoice()
        bill = order.invoice_ids
        bill.write({"invoice_date": "2026-07-15"})
        bill.action_post()

    def _create_direct_bills(self, partners, products):
        """Two direct vendor bills: the punitive-WHT and foreign-digital paths.

        Yonas Transport (no TIN), 15,000 -> 30% WHT 4,500 + 2,250 input VAT.
        BuildSoft (foreign digital), 8,000 -> 15% WHT 1,200 + 1,200 input VAT.
        Amounts unchanged; only who is billed and for what.
        """
        move_model = self.env["account.move"]
        for partner, product, price, date in (
            (partners["yonas"], products["delivery"], 15000, "2026-07-18"),
            (partners["buildsoft"], products["software"], 8000, "2026-07-20"),
        ):
            bill = move_model.create(
                {
                    "move_type": "in_invoice",
                    "partner_id": partner.id,
                    "invoice_date": date,
                    "company_id": self.env.company.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "quantity": 1,
                                "price_unit": price,
                            }
                        )
                    ],
                }
            )
            bill.action_post()

    def _run_payroll(self, employees):
        """July 2026 payroll: one payslip per PAYE band, posted + bank file.

        July 2026 is the most recent CLOSED month for this tenant, and it is
        pinned rather than computed from the wall clock for the same reason
        every other date here is: the statutory reports need one clean period
        window with exact GL tie-outs, and a demo whose numbers move with the
        calendar cannot have goldens at all.

        EVERY FIGURE ON EVERY PAYSLIP IS COMPUTED BY THE REAL ENGINE. Nothing
        below writes an amount: the run generates payslips from
        `hr.version.wage`, one taxable input line is added, and
        `action_confirm` computes PAYE and pension through
        l10n_et_payroll. A hand-written payslip is a number nobody can defend,
        and it would eventually get quoted at a prospect.
        """
        run = self.env["l10n.et.payroll.run"].create(
            {
                "company_id": self.env.company.id,
                "date_from": PERIOD_FROM,
                "date_to": PERIOD_TO,
                "employee_ids": [Command.set([emp.id for emp in employees.values()])],
            }
        )
        run.action_generate_payslips()
        # The overtime line is what lifts one of the two 10,000-birr employees
        # out of the 25% band into the 30% one, while the pension base stays on
        # the basic wage. See demo_catalogue.EMPLOYEES.
        overtime_slip = run.payslip_ids.filtered(
            lambda slip: slip.employee_id == employees[cat.OVERTIME_EMPLOYEE_KEY]
        )
        self.env["l10n.et.payslip.input"].create(
            {
                "payslip_id": overtime_slip.id,
                "name": "Overtime July",
                "category": "earning",
                "taxable": True,
                "amount": cat.OVERTIME_AMOUNT,
            }
        )
        run.action_confirm()
        run.action_export_bank_file()
        return run

    def _create_report_periods(self):
        """The July statutory report records, ready to print in the demo."""
        period = {
            "company_id": self.env.company.id,
            "date_from": PERIOD_FROM,
            "date_to": PERIOD_TO,
        }
        self.env["l10n.et.vat.declaration"].create(dict(period))
        self.env["l10n.et.wht.summary"].create(dict(period))
