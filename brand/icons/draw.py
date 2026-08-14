from sys_ import *
import re, io, cairosvg
from PIL import Image

# ---------------------------------------------------------------- SapianERP
# The parent app carries the mark. Petals nudged 14u toward centre so the
# blades touch — at 23px a hairline join reads as four loose dots.
src = open("/home/claude/brand/Sapian Logo.svg").read()
petals = re.findall(r'<path d="([^"]+)" fill="(#[0-9A-Fa-f]{6})"/>', src)
NUDGE = {"#14454F": (9, 9), "#2F7E4F": (-9, 9),
         "#E39A42": (-9, -9), "#C05628": (9, -9)}
body = "".join(f'<g transform="translate({NUDGE[c][0]},{NUDGE[c][1]})">'
               f'<path d="{d}" fill="{c}"/></g>' for d, c in petals)
render("sapian_core", body)

# ------------------------------------------------------------------ Payroll
# A payslip with a coin breaking the corner. Back plane = 32% tint, giving the
# stack depth Odoo's icons have and v1 lacked.
render("l10n_et_payroll", f'''
 <rect x="64" y="128" width="330" height="216" rx="48" fill="{tint(GREEN,.40)}"/>
 <rect x="110" y="176" width="330" height="216" rx="48" fill="{GREEN}"/>
 <rect x="150" y="222" width="176" height="30" rx="15" fill="#fff"/>
 <rect x="150" y="278" width="118" height="30" rx="15" fill="#fff"/>
 <circle cx="392" cy="366" r="88" fill="{AMBER}"/>
 <circle cx="392" cy="366" r="34" fill="#fff" opacity=".92"/>
''')

# --------------------------------------------------------------- Compliance
# A shield, not a document — Invoicing already owns "document", and a shield
# says *verified* at 23px where a stamp does not. Split in two tones down the
# centre line, heraldic-style, for depth without mud.
render("l10n_et_reports", f'''
 <path d="M256 68 L424 132 V286 C424 372 348 424 256 452 V68 Z" fill="{shade(ORANGE,.14)}"/>
 <path d="M256 68 L88 132 V286 C88 372 164 424 256 452 V68 Z" fill="{ORANGE}"/>
 <path d="M176 262 L232 320 L344 200" stroke="#fff" stroke-width="46"
       stroke-linecap="round" stroke-linejoin="round" fill="none"/>
''')

# ------------------------------------------------------------ Ethiopian base
# Accounting/tax. A percent sign cut from a soft blade-cornered tile: three
# corners generous, one tightened — the pinwheel's "fat lobe, one point".
render("l10n_et_base", f'''
 <path d="M120 96 h240 a72 72 0 0 1 72 72 v200 a72 72 0 0 1 -72 72 h-240
          a72 72 0 0 1 -72 -72 v-200 a24 24 0 0 1 24 -24 Z" fill="{tint(TEAL,.34)}"/>
 <path d="M156 132 h236 a68 68 0 0 1 68 68 v196 a68 68 0 0 1 -68 68 h-236
          a68 68 0 0 1 -68 -68 v-196 a22 22 0 0 1 22 -22 Z" fill="{TEAL}"/>
 <circle cx="200" cy="238" r="40" fill="none" stroke="#fff" stroke-width="26"/>
 <circle cx="336" cy="378" r="40" fill="none" stroke="#fff" stroke-width="26"/>
 <path d="M348 216 L188 400" stroke="#fff" stroke-width="28" stroke-linecap="round"/>
''')

# ------------------------------------------------------------------- Pharma
# One capsule on the mark's diagonal, split like a real capsule, with a
# highlight. No stray dot — v1's floating pill read as an accident.
render("vertical_pharma", f'''
 <g transform="rotate(-42 256 256)">
   <path d="M126 190 h130 v132 h-130 a66 66 0 0 1 0 -132 Z" fill="{TEAL}"/>
   <path d="M256 190 h130 a66 66 0 0 1 0 132 h-130 Z" fill="{AMBER}"/>
   <rect x="164" y="214" width="58" height="18" rx="9" fill="#fff" opacity=".45"/>
 </g>
''')

# -------------------------------------------------------------------- Theme
# The house palette itself: a droplet quartered in the four brand colours.
render("sapian_theme", f'''
 <path d="M256 60 C340 168 400 232 400 306 a144 144 0 0 1 -288 0
          C112 232 172 168 256 60 Z" fill="{tint(TEAL,.30)}"/>
 <clipPath id="d"><path d="M256 60 C340 168 400 232 400 306
   a144 144 0 0 1 -288 0 C112 232 172 168 256 60 Z"/></clipPath>
 <g clip-path="url(#d)">
   <rect x="112" y="40" width="144" height="240" fill="{TEAL}"/>
   <rect x="256" y="40" width="144" height="240" fill="{GREEN}"/>
   <rect x="112" y="280" width="144" height="200" fill="{ORANGE}"/>
   <rect x="256" y="280" width="144" height="200" fill="{AMBER}"/>
 </g>
''')

# ------------------------------------------------------------- Demo: trader
# A goods crate: lid band in the accent, body in the identity hue.
render("sapian_demo_trader", f'''
 <path d="M96 176 h320 v212 a56 56 0 0 1 -56 56 h-208 a56 56 0 0 1 -56 -56 Z"
       fill="{ORANGE}"/>
 <rect x="68" y="112" width="376" height="92" rx="34" fill="{AMBER}"/>
 <rect x="212" y="240" width="88" height="32" rx="16" fill="#fff"/>
''')

# -------------------------------------------------------------- Demo: pharma
render("sapian_demo_pharma", f'''
 <path d="M96 176 h320 v212 a56 56 0 0 1 -56 56 h-208 a56 56 0 0 1 -56 -56 Z"
       fill="{GREEN}"/>
 <rect x="68" y="112" width="376" height="92" rx="34" fill="{tint(GREEN,.42)}"/>
 <path d="M256 246 v104 M204 298 h104" stroke="#fff" stroke-width="34"
       stroke-linecap="round"/>
''')

# --------------------------------------------------------- Dress rehearsal
# A play mark inside a soft tile — "run the whole thing end to end".
render("sapian_dress_rehearsal", f'''
 <rect x="72" y="72" width="368" height="368" rx="104" fill="{tint(ORANGE,.38)}"/>
 <rect x="104" y="104" width="336" height="336" rx="96" fill="{ORANGE}"/>
 <path d="M226 190 L344 272 L226 354 Z" fill="#fff" stroke="#fff"
       stroke-width="34" stroke-linejoin="round"/>
''')

# ------------------------------------------------------------------- Sentry
# An eye: the thing that watches production.
render("sapian_sentry", f'''
 <path d="M40 256 C118 148 194 108 256 108 s138 40 216 148
          c-78 108 -154 148 -216 148 S118 364 40 256 Z" fill="{tint(TEAL,.36)}"/>
 <path d="M92 256 C154 172 208 142 256 142 s102 30 164 114
          c-62 84 -116 114 -164 114 S154 340 92 256 Z" fill="{TEAL}"/>
 <circle cx="256" cy="256" r="74" fill="{AMBER}"/>
 <circle cx="232" cy="232" r="24" fill="#fff" opacity=".85"/>
''')
print("SET v2 COMPLETE")
