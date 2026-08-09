# -*- coding: utf-8 -*-
"""THE DEMO CATALOGUE — products, units, prices and trade names, in one place.

This file exists so prices can be checked against the market and edited in one
edit, without reading the provisioning logic. A materials trader spots a wrong
price instantly, and a wrong price costs the meeting.

=============================================================================
PRICES — RE-CHECK BEFORE EVERY RECORDING. Ethiopian materials prices move
weekly. Each entry is marked with where the figure came from.

  [RANGE]      inside a range supplied by the business owner.
  [DERIVED]    computed from a supplied range (e.g. per bag = per quintal / 2).
  [UNVERIFIED] a plausible placeholder. NOBODY HAS CHECKED THIS. Set it
               yourself before recording — these are listed in the session
               report for exactly that reason.

Supplied ranges (July 2026):
    Cement      1,300 – 1,650 birr per QUINTAL
    Rebar         165 –   175 birr per kg
    Sheet G32   around 800 birr per piece
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

# --- Prices (birr) ----------------------------------------------------------
PRICES = {
    # Cement — sale per BAG, purchase per QUINTAL.
    "cement_bag_sale": 800.0,  # [DERIVED] 1,600/quintal ÷ 2, inside 1,300–1,650
    "cement_quintal_cost": 1450.0,  # [RANGE] within 1,300–1,650 per quintal
    # Rebar — per kg.
    "rebar_sale": 170.0,  # [RANGE] within 165–175
    "rebar_cost": 170.0,  # [RANGE] within 165–175
    # Corrugated sheet — per piece.
    "sheet_sale": 800.0,  # [RANGE] "around 800"
    "sheet_cost": 640.0,  # [UNVERIFIED] assumed 20% margin off the 800 sale
    # ---- NOBODY HAS CHECKED THE FOUR BELOW. Set them before recording. ----
    "hcb_sale": 14.0,  # [UNVERIFIED] hollow concrete block 20 cm, per piece
    "hcb_cost": 11.0,  # [UNVERIFIED]
    "sand_sale": 1800.0,  # [UNVERIFIED] per m³ delivered
    "sand_cost": 1400.0,  # [UNVERIFIED]
    "binding_wire_sale": 190.0,  # [UNVERIFIED] per kg
    "binding_wire_cost": 155.0,  # [UNVERIFIED]
    # Services (used for the punitive-WHT and foreign-digital demos).
    "delivery_service": 15000.0,  # [UNVERIFIED] truck hire + loading, one job
    "software_subscription": 8000.0,  # [UNVERIFIED] foreign SaaS, one month
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
        PRICES["cement_bag_sale"],
        PRICES["cement_quintal_cost"] / BAGS_PER_QUINTAL,
    ),
    (
        "cement_habesha",
        "Cement PPC Habesha 50kg",
        "ሲሚንቶ ሐበሻ",
        "bag",
        PRICES["cement_bag_sale"],
        PRICES["cement_quintal_cost"] / BAGS_PER_QUINTAL,
    ),
    (
        "cement_derba",
        "Cement PPC Derba 50kg",
        "ሲሚንቶ ደርባ",
        "bag",
        PRICES["cement_bag_sale"],
        PRICES["cement_quintal_cost"] / BAGS_PER_QUINTAL,
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
# Suppliers: the three compliance profiles the withholding demo needs.
SUPPLIER_COMPLIANT = "Derba Midroc Cement Depot — ደርባ ሚድሮክ"  # TIN + licence -> 3%
SUPPLIER_NO_TIN = "Yonas Transport & Loading — ዮናስ ትራንስፖርት"  # NO TIN -> 30%
SUPPLIER_FOREIGN = "BuildSoft Cloud Ltd."  # foreign digital -> 15%
