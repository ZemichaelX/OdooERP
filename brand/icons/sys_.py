"""SapianERP icon system v3.

WHAT WAS WRONG IN v2 — found by putting our icons next to Odoo's sixteen at
39px instead of judging our own proof sheet in isolation:

  1. LOW HUE CONTRAST. v2 paired each hue with a *tint of itself* for depth.
     Odoo pairs CONTRASTING HUES — purple against teal, orange against purple.
     Green-on-lighter-green has almost no separation at 23px; it reads as one
     dull blob. This is the single biggest reason ours looked flat.

  2. TOO DARK. The brand palette is built for text and print, where #14454F
     on white is correct. As a 39px tile among Odoo's turquoise and magenta,
     it reads as dour. Icons need the same HUES at higher lightness and
     saturation — still ours, no longer muddy.

  3. TOO MUCH PADDING. v2 kept the subject inside 64-448. Odoo's icons run
     essentially edge to edge. Small padding = small-looking icon.

  4. sapian_core did not resolve. Four blades nudged 9u still read as four
     loose dots. A mark at 23px must be ONE connected mass.

SYSTEM v3
  Grid      512 canvas, subject inside 32-480 — fills the frame like Odoo's
  Colour    vivid() raises lightness+saturation, preserving hue. Brand hues,
            icon-weight values.
  Pairing   every icon uses TWO CONTRASTING HUES from the palette, never a
            hue plus its own tint. Cool + warm, always.
  Detail    white cut-outs only; nothing thinner than 30/512
  Family    one bold silhouette per icon, a second hue overlapping it — the
            shape reads first, the accent gives it depth.
"""
import cairosvg, io, colorsys
from PIL import Image

# Brand values — correct for print and text, too dark for a 39px tile.
TEAL, GREEN, ORANGE, AMBER = "#14454F", "#2F7E4F", "#C05628", "#E39A42"

def _hex2rgb(h): return tuple(int(h[i:i+2], 16) / 255 for i in (1, 3, 5))
def _rgb2hex(r, g, b): return "#%02X%02X%02X" % tuple(min(255, max(0, round(v*255))) for v in (r, g, b))

def vivid(hex_c, light=None, sat=None):
    """Raise lightness/saturation, keep the hue. This is what makes a brand
    colour work at 39px without becoming a different colour."""
    r, g, b = _hex2rgb(hex_c)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if light is not None: l = light
    if sat is not None:   s = sat
    return _rgb2hex(*colorsys.hls_to_rgb(h, l, s))

def tint(hex_c, pct):
    r, g, b = (int(hex_c[i:i+2], 16) for i in (1, 3, 5))
    f = lambda v: int(v + (255 - v) * pct)
    return f"#{f(r):02X}{f(g):02X}{f(b):02X}"

# ---- The icon palette: same four hues, tile-weight values -------------------
# Measured target: Odoo's icons sit around L=0.45-0.62, S=0.55-0.80.
T  = vivid(TEAL,   light=0.38, sat=0.68)   # deep turquoise — still the brand teal
T2 = vivid(TEAL,   light=0.55, sat=0.55)   # lighter partner tone
G  = vivid(GREEN,  light=0.42, sat=0.55)
G2 = vivid(GREEN,  light=0.58, sat=0.48)
O  = vivid(ORANGE, light=0.52, sat=0.72)
A  = vivid(AMBER,  light=0.62, sat=0.82)
W  = "#FFFFFF"

HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" '
        'viewBox="0 0 512 512">')

def render(name, body, size=512):
    svg = HEAD + body + "</svg>"
    open(f"{name}.svg", "w").write(svg)
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size)
    Image.open(io.BytesIO(png)).convert("RGBA").save(f"{name}.png")
    print("rendered", name, flush=True)

if __name__ == "__main__":
    for n, v in [("T",T),("T2",T2),("G",G),("G2",G2),("O",O),("A",A)]:
        print(f"{n:<3} {v}")
