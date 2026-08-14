"""SapianERP app icons v3 — geometry.

Judge only from PROOF-VS-ODOO.png, at the 23px row, with Odoo's icons in the
same frame. Full size lies — every failed pass of this set failed because it
was judged large.

Three rules, each earned by a failure:
  * COOL + WARM in every icon. v2 paired a hue with a tint of itself and the
    result had no separation at 23px.
  * Subject fills 32-480. v2 sat inside 64-448 and looked small next to Odoo's.
  * No more than three of ten may share a dominant hue. v2 was six-of-ten teal
    and the sidebar read as one smear.
"""
from sys_ import *

# ---------------------------------------------------------------- SapianERP
# The four-blade logo pinwheel does NOT survive 23px — tested at nudge 34/55/
# 75/95 and every setting collapsed into an orange blob, because the blades'
# mass sits at the outer end and they occlude each other when pulled together.
# Two blades read as two dots; three the same. So the mark is SIMPLIFIED for
# the tile: four swirled quarters, one per brand colour, white hub. It keeps
# what the logo means — four parts, rotational — and drops what does not
# survive downscaling. The full pinwheel remains the print/lockup mark.
BLADE = "M256 256 C 236 156 300 74 256 44 A212 212 0 0 1 468 256 Z"
render("sapian_core",
  '<g transform="rotate(-14 256 256)">' +
  "".join(f'<g transform="rotate({i*90} 256 256)"><path d="{BLADE}" fill="{c}"/></g>'
          for i, c in enumerate([T, A, O, G])) +
  '<circle cx="256" cy="256" r="52" fill="#fff"/></g>')

# ------------------------------------------------------------------ Payroll
# COOL sheet + WARM coin.
render("l10n_et_payroll", f'''
 <rect x="46" y="70" width="330" height="372" rx="46" fill="{T2}"/>
 <rect x="96" y="42" width="330" height="372" rx="46" fill="{T}"/>
 <rect x="146" y="112" width="200" height="34" rx="17" fill="{W}"/>
 <rect x="146" y="180" width="140" height="34" rx="17" fill="{W}"/>
 <circle cx="368" cy="374" r="112" fill="{A}"/>
 <circle cx="368" cy="374" r="44"  fill="{W}"/>
''')

# --------------------------------------------------------------- Compliance
# WARM shield, white tick. A shield says *verified*; Invoicing owns "document"
# so we must not use one.
render("l10n_et_reports", f'''
 <path d="M256 34 L470 116 V300 C470 396 372 456 256 490
          C140 456 42 396 42 300 V116 Z" fill="{O}"/>
 <path d="M256 34 L470 116 V300 C470 396 372 456 256 490 V34 Z" fill="{A}"/>
 <path d="M162 262 L228 330 L354 190" stroke="{W}" stroke-width="56"
       stroke-linecap="round" stroke-linejoin="round" fill="none"/>
''')

# ------------------------------------------------------------ Ethiopian base
# Tax engine. GREEN price tag, WARM eyelet, white percent.
render("l10n_et_base", f'''
 <path d="M232 40 H430 C458 40 472 54 472 82 V280 L228 490
          C210 506 186 506 170 490 L34 354 C18 338 18 314 34 296 Z" fill="{G}"/>
 <circle cx="386" cy="126" r="52" fill="{A}"/>
 <circle cx="150" cy="248" r="42" fill="{W}"/>
 <circle cx="268" cy="366" r="42" fill="{W}"/>
 <path d="M292 216 L134 380" stroke="{W}" stroke-width="34" stroke-linecap="round"/>
''')

# ------------------------------------------------------------------- Pharma
# Capsule, COOL / WARM across the diagonal. Enlarged from v3-pass-1, where it
# was the smallest silhouette in the set and vanished at 23px.
render("vertical_pharma", f'''
 <g transform="rotate(-45 256 256)">
   <rect x="56" y="150" width="400" height="212" rx="106" fill="{A}"/>
   <path d="M162 150 H256 V362 H162 A106 106 0 0 1 162 150 Z" fill="{T}"/>
   <rect x="56" y="150" width="200" height="212" rx="106" fill="{T}"/>
   <rect x="226" y="186" width="34" height="40" rx="17" fill="{W}" opacity=".85"/>
 </g>
''')

# -------------------------------------------------------------------- Theme
# Brand/appearance. WARM droplet with one COOL quarter.
render("sapian_theme", f'''
 <path d="M256 26 C356 150 452 232 452 320 A196 196 0 0 1 60 320
          C60 232 156 150 256 26 Z" fill="{O}"/>
 <path d="M256 26 C356 150 452 232 452 320 A196 196 0 0 1 256 516 Z" fill="{T}"/>
 <circle cx="256" cy="330" r="66" fill="{W}" opacity=".92"/>
''')

# --------------------------------------------------------------- Demo trader
# Retail/wholesale. WARM crate, COOL strap.
render("sapian_demo_trader", f'''
 <path d="M256 26 L472 132 V380 L256 486 L40 380 V132 Z" fill="{A}"/>
 <path d="M256 26 L472 132 V380 L256 486 Z" fill="{O}"/>
 <rect x="206" y="132" width="100" height="354" fill="{T}"/>
 <path d="M40 132 L256 238 L472 132" stroke="{W}" stroke-width="30"
       fill="none" stroke-linejoin="round" opacity=".9"/>
''')

# --------------------------------------------------------------- Demo pharma
# A dispensing jar — GREEN body, WARM lid, white cross. Silhouette differs
# from the trader crate, which matters more at 23px than colour does.
render("sapian_demo_pharma", f'''
 <rect x="112" y="34"  width="288" height="96"  rx="42" fill="{A}"/>
 <rect x="72"  y="146" width="368" height="332" rx="76" fill="{G}"/>
 <rect x="228" y="216" width="56"  height="192" rx="28" fill="{W}"/>
 <rect x="160" y="284" width="192" height="56"  rx="28" fill="{W}"/>
''')

# ----------------------------------------------------------- Dress rehearsal
# The demo runner. WARM rounded square, white play mark, COOL corner.
render("sapian_dress_rehearsal", f'''
 <rect x="34" y="34" width="444" height="444" rx="112" fill="{O}"/>
 <path d="M478 240 V366 C478 428 428 478 366 478 H240 Z" fill="{T}"/>
 <path d="M196 148 L378 256 L196 364 Z" fill="{W}" stroke="{W}"
       stroke-width="44" stroke-linejoin="round"/>
''')

# ------------------------------------------------------------------- Sentry
# Monitoring. COOL lid, WARM iris. No fine detail at all — that is why it
# survives 23px where a magnifier or a gauge would not.
render("sapian_sentry", f'''
 <path d="M256 100 C388 100 476 190 502 256 C476 322 388 412 256 412
          C124 412 36 322 10 256 C36 190 124 100 256 100 Z" fill="{T}"/>
 <circle cx="256" cy="256" r="118" fill="{A}"/>
 <circle cx="256" cy="256" r="52"  fill="{W}"/>
''')
