"""SapianERP icon system v2 — rebuilt as a designer would.

WHAT WAS WRONG IN v1: blunt rect+circle geometry, muddy multiply overlaps,
generic concepts, no tonal depth. Odoo's own icons use 2-3 tones of ONE hue
plus an accent, soft large radii, and white as a cut-out — never mud.

SYSTEM v2
  Grid      512 canvas, subject inside 64-448, optical centre not maths centre
  Depth     an offset BACK PLANE in a lighter tint of the identity hue.
            Tints, never multiply — mud is what made v1 look cheap.
  Tones     identity hue + its 32% tint + one palette accent. Three, no more.
  Radius    generous and consistent (rx ~ 14% of the form's short side)
  Detail    white cut-outs only; nothing thinner than 26/512 (survives 23px)
  Family    every icon is a SOFT SHIELD/BLADE-cornered mass with an accent
            element breaking one corner — the pinwheel's own logic: a fat
            lobe with one decisive point.
"""
import cairosvg, io
from PIL import Image

TEAL, GREEN, ORANGE, AMBER = "#14454F", "#2F7E4F", "#C05628", "#E39A42"

def tint(hex_c, pct):
    """Blend toward white — the tonal ladder Odoo uses for depth."""
    r, g, b = (int(hex_c[i:i+2], 16) for i in (1, 3, 5))
    f = lambda v: int(v + (255 - v) * pct)
    return f"#{f(r):02X}{f(g):02X}{f(b):02X}"

def shade(hex_c, pct):
    r, g, b = (int(hex_c[i:i+2], 16) for i in (1, 3, 5))
    f = lambda v: int(v * (1 - pct))
    return f"#{f(r):02X}{f(g):02X}{f(b):02X}"

HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" '
        'viewBox="0 0 512 512">')

def render(name, body, size=512):
    svg = HEAD + body + "</svg>"
    open(f"{name}.svg", "w").write(svg)
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size)
    Image.open(io.BytesIO(png)).convert("RGBA").save(f"{name}.png")
    print("rendered", name, flush=True)
