# -*- coding: utf-8 -*-
"""THE DEMO CATALOGUE — products, units, prices and trade names, in one place.

This file exists so prices can be checked against the market and edited in one
edit, without reading the provisioning logic. A materials trader spots a wrong
price instantly, and a wrong price costs the meeting.

=============================================================================
PRICES — every figure is sourced. Ethiopian materials prices move weekly, so
re-check before a recording even so; each entry says where it came from.

SOURCES
  [LIST]   Con Proxy / @MaterialProxy_Bot, daily Addis Ababa construction
           price list, 23 July 2026. Prices are BEFORE VAT and aggregated
           across suppliers.
  [OWNER]  Zemichael, 10 August 2026.
  [DERIVED] computed from one of the above — a cost derived from a sale price
           at the ≈9% gross margin the sourced cement pair implies, or a
           per-bag figure derived from a sourced per-quintal one.
  [DEMO]   not a market price: a figure chosen to drive a compliance path, and
           load-bearing for that reason. Only the two services are [DEMO], and
           each says what it drives.

Sourced headline figures (before VAT):
    Cement OPC (Dangote)         2,200 birr per QUINTAL   [OWNER]
    Cement PPC (Habesha, Derba)  2,000 birr per QUINTAL   [OWNER]
    Rebar, local G-75              193 birr per kg        [LIST]
    Binding wire 1.5 mm            220 birr per kg        [OWNER]
    Corrugated sheet G32           880 birr per piece     [LIST] (EGA 32 gauge)
    HCB 20 cm                       76 birr per piece     [LIST]
    Sand                         8,000 birr per m³ sold,  [OWNER]
                                 bought at 115,000 per 16 m³ Sino truck
=============================================================================
"""

# --- Units ------------------------------------------------------------------
# Cement is BOUGHT by the quintal and SOLD by the bag: 1 quintal = 2 bags of
# 50 kg. In Odoo 19 there are no UoM *categories* — units form a tree via
# `relative_uom_id` / `relative_factor`, and a product offers extra units
# through `uom_ids`. So: bag is the product's stock unit, quintal is a related
# unit worth 2 bags, and a purchase line in quintals lands as bags in stock.
UOM_BAG_NAME = "Bag (50 kg)"
UOM_QUINTAL_NAME = "Quintal (100 kg)"
BAGS_PER_QUINTAL = 2

# Sand is bought by the truckload and sold by the cube — a real margin, not an
# assumed one, which is why the truck figures are kept here rather than folded
# into a single number.
SAND_TRUCK_PRICE = 115000.0  # [OWNER] one 16 m³ Sino truck, delivered
SAND_TRUCK_M3 = 16.0

# --- Prices (birr, before VAT) ----------------------------------------------
# Cement is priced per QUINTAL because that is how it is bought and quoted;
# the per-bag figures the products carry are these ÷ BAGS_PER_QUINTAL.
# OPC and PPC are DIFFERENT products at different prices — three cements
# sharing one price is exactly what a materials trader notices first.
PRICES = {
    # Cement OPC — Dangote.
    "cement_opc_quintal_sale": 2200.0,  # [OWNER]
    "cement_opc_quintal_cost": 2000.0,  # [DERIVED] ≈9% margin on the sale
    # Cement PPC — Habesha, Derba.
    "cement_ppc_quintal_sale": 2000.0,  # [OWNER]
    "cement_ppc_quintal_cost": 1820.0,  # [DERIVED] ≈9% margin on the sale
    # Rebar — per kg, local G-75.
    "rebar_sale": 193.0,  # [LIST]
    "rebar_cost": 176.0,  # [DERIVED] ≈9% margin on the sale
    # Binding wire — per kg.
    "binding_wire_sale": 220.0,  # [OWNER]
    "binding_wire_cost": 200.0,  # [DERIVED] ≈9% margin on the sale
    # Corrugated sheet — per piece, EGA 32 gauge.
    "sheet_sale": 880.0,  # [LIST]
    "sheet_cost": 800.0,  # [DERIVED] ≈9% margin on the sale
    # Hollow concrete block 20 cm — per piece.
    "hcb_sale": 76.0,  # [LIST]
    "hcb_cost": 69.0,  # [DERIVED] ≈9% margin on the sale
    # Sand — per m³. Both ends sourced: bought by the truck, sold by the cube,
    # a real 10.2% margin rather than an assumed one.
    "sand_sale": 8000.0,  # [OWNER]
    "sand_cost": SAND_TRUCK_PRICE / SAND_TRUCK_M3,  # [OWNER] 115,000 ÷ 16
    # Services — these drive the withholding demonstrations and are chosen for
    # that, not quoted from a market. DO NOT lower the delivery figure: it must
    # stay above the 10,000 birr services threshold or the 30% punitive moment
    # disappears from the demo.
    "delivery_service": 15000.0,  # [DEMO] drives 30% punitive WHT (no-TIN supplier)
    "software_subscription": 8000.0,  # [DEMO] drives 15% foreign-digital WHT
}

# --- Products ---------------------------------------------------------------
# (key, English name, Amharic suffix, unit, sale price, cost price)
# `unit` is one of: "bag" (cement, with the quintal pair), "kg", "piece", "m3",
# "service".
PRODUCTS = [
    (
        "cement_dangote",
        "Cement OPC Dangote 50kg",
        "ሲሚንቶ ዳንጎቴ",
        "bag",
        PRICES["cement_opc_quintal_sale"] / BAGS_PER_QUINTAL,
        PRICES["cement_opc_quintal_cost"] / BAGS_PER_QUINTAL,
    ),
    (
        "cement_habesha",
        "Cement PPC Habesha 50kg",
        "ሲሚንቶ ሐበሻ",
        "bag",
        PRICES["cement_ppc_quintal_sale"] / BAGS_PER_QUINTAL,
        PRICES["cement_ppc_quintal_cost"] / BAGS_PER_QUINTAL,
    ),
    (
        "cement_derba",
        "Cement PPC Derba 50kg",
        "ሲሚንቶ ደርባ",
        "bag",
        PRICES["cement_ppc_quintal_sale"] / BAGS_PER_QUINTAL,
        PRICES["cement_ppc_quintal_cost"] / BAGS_PER_QUINTAL,
    ),
    ("rebar_8", "Rebar 8 mm", "ብረት ዘንግ 8ሚሜ", "kg", PRICES["rebar_sale"], PRICES["rebar_cost"]),
    (
        "rebar_12",
        "Rebar 12 mm",
        "ብረት ዘንግ 12ሚሜ",
        "kg",
        PRICES["rebar_sale"],
        PRICES["rebar_cost"],
    ),
    (
        "rebar_16",
        "Rebar 16 mm",
        "ብረት ዘንግ 16ሚሜ",
        "kg",
        PRICES["rebar_sale"],
        PRICES["rebar_cost"],
    ),
    (
        "binding_wire",
        "Binding Wire 1.5 mm",
        "ማሰሪያ ሽቦ",
        "kg",
        PRICES["binding_wire_sale"],
        PRICES["binding_wire_cost"],
    ),
    (
        "sheet_g32",
        "Corrugated Sheet G32",
        "ቆርቆሮ G32",
        "piece",
        PRICES["sheet_sale"],
        PRICES["sheet_cost"],
    ),
    (
        "hcb_20",
        "HCB 20 cm (Hollow Concrete Block)",
        "ኤች.ሲ.ቢ 20ሳሜ",
        "piece",
        PRICES["hcb_sale"],
        PRICES["hcb_cost"],
    ),
    ("sand", "Sand (washed)", "አሸዋ", "m3", PRICES["sand_sale"], PRICES["sand_cost"]),
    # Services — not stock, but the demo needs them for the WHT paths.
    (
        "delivery",
        "Site Delivery & Loading",
        "የማጓጓዣ አገልግሎት",
        "service",
        PRICES["delivery_service"],
        0.0,
    ),
    (
        "software",
        "Cloud Design Software Subscription",
        "",
        "service",
        PRICES["software_subscription"],
        0.0,
    ),
]

# --- Trade names ------------------------------------------------------------
# Customers: contractors and hardware retailers — who a materials shop sells to.
CUSTOMER_MEBRAT = "Mebrat Construction PLC — መብራት ኮንስትራክሽን"
CUSTOMER_ABYSSINIA = "Abyssinia Hardware & Building Supplies — አቢሲኒያ ሐርድዌር"
# Pipeline-only customers. They exist so the Sales list is not two names
# repeated five times — a prospect reads a pipeline as a picture of the
# business, and one where every quotation is for the same two companies reads
# as a fixture rather than a month's work.
CUSTOMER_RIFT_VALLEY = "Rift Valley Contractors PLC — ሪፍት ቫሊ ኮንትራክተርስ"
CUSTOMER_HAWASSA = "Hawassa Homes Real Estate — ሐዋሳ ሆምስ"
CUSTOMER_TSEHAY = "Tsehay Hardware — ፀሐይ ሐርድዌር"
# Suppliers: the three compliance profiles the withholding demo needs.
SUPPLIER_COMPLIANT = "Derba Midroc Cement Depot — ደርባ ሚድሮክ"  # TIN + licence -> 3%
SUPPLIER_NO_TIN = "Yonas Transport & Loading — ዮናስ ትራንስፖርት"  # NO TIN -> 30%
SUPPLIER_FOREIGN = "BuildSoft Cloud Ltd."  # foreign digital -> 15%

# --- Payroll roster ---------------------------------------------------------
# THE ROSTER IS CHOSEN TO MAKE THE PAYE TABLE VISIBLE, and that is the whole
# point of it. Proclamation 1395/2025 has six monthly bands; a payroll run that
# only lands in three of them shows a progressive tax that looks flat, and the
# thing most likely to differentiate us cannot be pointed at on screen.
#
# So every band gets exactly one employee, bottom to top, at a wage a 2–5 person
# Addis hardware shop would actually pay:
#
#   band        monthly range        rate   who                 wage
#   -------------------------------------------------------------------
#   1           0 – 2,000            0 %    Cleaner             1,800
#   2           2,000 – 4,000        15 %   Office Assistant    3,500
#   3           4,000 – 7,000        20 %   Storekeeper         6,000
#   4           7,000 – 10,000       25 %   Sales Officer      10,000
#   5           10,000 – 14,000      30 %   Driver & Loader    10,000 + 2,000 OT
#   6           above 14,000         35 %   General Manager    25,000
#
# The driver reaches band 5 through TAXABLE OVERTIME, not through his basic
# wage, which is the second thing the demo shows: an input line moves an
# employee up a band, and the pension base does not follow it (pension is on
# the basic wage). Two employees on the same 10,000 basic landing in different
# bands is the clearest possible statement of that.
#
# WAGES ARE NOT GOLDENS. The payslip figures are computed by the real payroll
# engine from these; if a wage changes here, recompute the totals in
# tests/test_demo_trader_e2e.py by hand — never copy them out of a test run.
#
# (key, name, job title, monthly basic wage, TIN, POESSA pension id, bank a/c)
EMPLOYEES = [
    (
        "chaltu",
        "Chaltu Deme — ጫልቱ ደሜ",
        "Cleaner",
        1800.0,
        "0014141414",
        # Deliberately missing: drives the fix-before-filing banner on the
        # pension schedule. Do not "fix" it.
        False,
        "1000200030003",
    ),
    (
        "hanna",
        "Hanna Mekonnen — ሃና መኮንን",
        "Office Assistant",
        3500.0,
        "0015151515",
        "POESSA-005566",
        "1000200030004",
    ),
    (
        "solomon",
        "Solomon Abera — ሰለሞን አበራ",
        "Storekeeper",
        6000.0,
        "0016161616",
        "POESSA-007788",
        "1000200030005",
    ),
    (
        "almaz",
        "Almaz Tadesse — አልማዝ ታደሰ",
        "Sales Officer",
        10000.0,
        "0012121212",
        "POESSA-001122",
        "1000200030001",
    ),
    (
        "bekele",
        "Bekele Worku — በቀለ ወርቁ",
        "Driver & Loader",
        10000.0,
        "0013131313",
        "POESSA-003344",
        "1000200030002",
    ),
    (
        "tigist",
        "Tigist Haile — ትዕግስት ኃይሉ",
        "General Manager",
        25000.0,
        "0017171717",
        "POESSA-009900",
        "1000200030006",
    ),
]

# The employee who gets a taxable overtime input line, and how much. Kept here
# with the roster because it is what puts that employee in band 5.
OVERTIME_EMPLOYEE_KEY = "bekele"
OVERTIME_AMOUNT = 2000.0

# --- Sales pipeline ---------------------------------------------------------
# Quotations that are NOT invoiced, so the Sales app opens on a pipeline a
# salesperson can walk through instead of on an empty list. Nothing here posts
# to the general ledger, so every VAT / WHT / payroll golden is untouched by
# design, not by luck.
#
# Only the CONFIRMED one moves stock. Its quantities are checked against what
# July leaves on hand (opening stock minus the month's deliveries: 80 sheets,
# 300 kg of 12 mm rebar, 1,200 blocks), so nothing goes negative — the first
# number a materials trader looks at.
#
# NO PAYMENTS are created anywhere in the demo, so the ETB 50,000 cash cap
# (l10n_et_base/models/account_payment.py, which validates account.payment and
# nothing else) cannot be tripped by any of this.
#
# Even so, EVERY QUOTATION HERE TOTALS UNDER 50,000 INCLUDING VAT, and a test
# asserts it. The cap binds the payment and not the invoice, so a larger
# quotation would be perfectly legal — but a presenter who registers a cash
# receipt against one on camera gets blocked by our own validator, and "that is
# fine, it would be a bank sale" is not a sentence anyone wants to say
# mid-demo. The pipeline is the part a salesperson improvises on, so it is kept
# safe to improvise on. That is what caps the Rift Valley quotation at 20 bags
# rather than 60.
#
# The INVOICED July flow is deliberately not held to the same rule: the
# Abyssinia invoice is 92,115, a normal credit sale to a hardware wholesaler,
# and precisely the sort of transaction the cash cap exists to keep out of
# cash. It is unchanged.
#
# Prices are the same sourced figures the invoiced flows use, taken from PRICES
# rather than restated, so a price correction moves the pipeline with the rest
# of the demo. Cement is quoted per BAG here because that is how it is sold.
_CEMENT_OPC_BAG_SALE = PRICES["cement_opc_quintal_sale"] / BAGS_PER_QUINTAL

# (state, customer key, [(product key, qty, unit price)], order date)
QUOTATIONS = [
    (
        "draft",
        "rift_valley",
        [("cement_dangote", 20, _CEMENT_OPC_BAG_SALE), ("rebar_16", 60, PRICES["rebar_sale"])],
        "2026-07-27",
    ),
    ("draft", "tsehay", [("hcb_20", 400, PRICES["hcb_sale"])], "2026-07-28"),
    (
        "draft",
        "hawassa",
        [("sand", 4, PRICES["sand_sale"]), ("binding_wire", 25, PRICES["binding_wire_sale"])],
        "2026-07-29",
    ),
    (
        "sent",
        "mebrat",
        [
            ("sheet_g32", 30, PRICES["sheet_sale"]),
            ("binding_wire", 40, PRICES["binding_wire_sale"]),
        ],
        "2026-07-24",
    ),
    # Confirmed and delivered, deliberately NOT invoiced: the demo's live
    # moment is pressing "Create Invoice" on a real order in front of the
    # prospect. Delivered rather than left pending so the tenant carries no
    # half-finished picking, which reads as an unfinished demo rather than as
    # a business.
    ("sale", "abyssinia", [("sheet_g32", 20, PRICES["sheet_sale"])], "2026-07-30"),
]
