#!/usr/bin/env python3
"""Draw the notebook's paper bits as SVG and write them into a CSS file as
data-URI custom properties, so the book needs no image files.

    python3 theme/gen-assets.py > theme/paper-assets.css

Change a seed to get a different tear / fern / stain."""
import math
import random
from urllib.parse import quote


def uri(svg):
    svg = " ".join(svg.split())
    return 'url("data:image/svg+xml,' + quote(svg, safe=" /:=',;()-.!*~") + '")'


def f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def wave(period, amp, terms, rnd):
    """smooth periodic noise, so a tile repeats without a seam"""
    comps = [(k, rnd.uniform(0, 6.283), rnd.uniform(.4, 1) / k ** .9) for k in range(1, terms + 1)]
    norm = sum(a for _, _, a in comps)
    return lambda x: amp * sum(a * math.sin(6.283 * k * x / period + p) for k, p, a in comps) / norm


# ── torn (deckle) edge: a frame used as a 9-slice mask ──────────────────
# corners stay put, the edge pieces repeat, so any box gets torn sides.
S, C = 240, 24          # frame size, slice size
SEG = S - 2 * C          # repeating edge piece; the tear is periodic over it


def torn(seed, depth=9.0):
    rnd = random.Random(seed)
    e = []
    for _ in range(4):
        big, fine = wave(SEG, 3.4, 5, rnd), wave(SEG, 1.3, 48, rnd)
        e.append(lambda u, big=big, fine=fine: depth + big(u) + fine(u))
    top, right, bot, left = e
    a = depth + 3                 # where the corner curve meets the edges
    r = range(int(a), S - int(a) + 1, 2)
    pts = [f"M{f(a)} {f(top(a - C))}"]
    pts += [f"L{f(x)} {f(top(x - C))}" for x in r]
    pts += [f"Q{f(S - right(-C))} {f(top(S - C))} {f(S - right(a - C))} {f(a)}"]
    pts += [f"L{f(S - right(y - C))} {f(y)}" for y in r]
    pts += [f"Q{f(S - right(S - C))} {f(S - bot(S - C))} {f(S - a)} {f(S - bot(S - a - C))}"]
    pts += [f"L{f(x)} {f(S - bot(x - C))}" for x in reversed(r)]
    pts += [f"Q{f(left(S - C))} {f(S - bot(-C))} {f(left(S - a - C))} {f(S - a)}"]
    pts += [f"L{f(left(y - C))} {f(y)}" for y in reversed(r)]
    pts += [f"Q{f(left(-C))} {f(top(-C))} {f(a)} {f(top(a - C))}Z"]
    return uri(f"""<svg xmlns='http://www.w3.org/2000/svg' width='{S}' height='{S}'>
      <filter id='b' filterUnits='userSpaceOnUse' x='0' y='0' width='{S}' height='{S}'>
        <feTurbulence type='fractalNoise' baseFrequency='.5' numOctaves='2' seed='{seed}' stitchTiles='stitch'/>
        <feDisplacementMap in='SourceGraphic' scale='3' xChannelSelector='R' yChannelSelector='G'/>
        <feGaussianBlur stdDeviation='.4'/></filter>
      <path d='{' '.join(pts)}' filter='url(#b)'/></svg>""")


# ── paper: fine embossed grain + big soft mottling ───────────────────────
grain = uri("""<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'>
  <filter id='g' x='0' y='0' width='100%' height='100%'>
    <feTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='3' seed='11' stitchTiles='stitch'/>
    <feDiffuseLighting lighting-color='#fff' surfaceScale='1.3' diffuseConstant='1.05'>
      <feDistantLight azimuth='225' elevation='58'/></feDiffuseLighting>
    <feComponentTransfer>
      <feFuncR type='linear' slope='.4' intercept='.64'/>
      <feFuncG type='linear' slope='.4' intercept='.64'/>
      <feFuncB type='linear' slope='.4' intercept='.64'/></feComponentTransfer>
  </filter>
  <filter id='k' x='0' y='0' width='100%' height='100%'>
    <feTurbulence type='fractalNoise' baseFrequency='.35' numOctaves='1' seed='23' stitchTiles='stitch'/>
    <feColorMatrix values='0 0 0 0 .42  0 0 0 0 .33  0 0 0 0 .2  16 0 0 0 -11.6'/>
  </filter>
  <rect width='100%' height='100%' filter='url(#g)'/>
  <rect width='100%' height='100%' filter='url(#k)' opacity='.3'/></svg>""")

mottle = uri("""<svg xmlns='http://www.w3.org/2000/svg' width='700' height='700'>
  <filter id='m' x='0' y='0' width='100%' height='100%'>
    <feTurbulence type='fractalNoise' baseFrequency='.006' numOctaves='4' seed='4' stitchTiles='stitch'/>
    <feColorMatrix values='0 0 0 0 .55  0 0 0 0 .45  0 0 0 0 .3  .36 0 0 0 -.12'/>
  </filter>
  <rect width='100%' height='100%' filter='url(#m)'/></svg>""")

# desk: woven cotton, very quiet
linen = uri("""<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'>
  <filter id='n' x='0' y='0' width='100%' height='100%'>
    <feTurbulence type='fractalNoise' baseFrequency='.9 .35' numOctaves='2' seed='2' stitchTiles='stitch'/>
    <feColorMatrix values='0 0 0 0 .2  0 0 0 0 .25  0 0 0 0 .15  0 0 0 .55 -.18'/>
  </filter>
  <rect width='100%' height='100%' filter='url(#n)'/></svg>""")


# ── coffee ring ───────────────────────────────────────────────────────────
def coffee(seed):
    rnd = random.Random(seed)
    c, r = 110, 86
    rings = []
    for _ in range(7):
        dash = " ".join(str(rnd.randint(8, 160)) + " " + str(rnd.randint(2, 30)) for _ in range(4))
        rings.append(
            f"<circle cx='{f(c + rnd.uniform(-1.5, 1.5))}' cy='{f(c + rnd.uniform(-1.5, 1.5))}' "
            f"r='{f(r + rnd.uniform(-2.5, 1.5))}' stroke-width='{f(rnd.uniform(.8, 3.2))}' "
            f"stroke-opacity='{f(rnd.uniform(.12, .32))}' stroke-dasharray='{dash}' "
            f"transform='rotate({rnd.randint(0, 359)} {c} {c})'/>")
    return uri(f"""<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'>
      <filter id='w'><feTurbulence baseFrequency='.04' numOctaves='2' seed='{seed}'/>
        <feDisplacementMap in='SourceGraphic' scale='6'/><feGaussianBlur stdDeviation='.5'/></filter>
      <g filter='url(#w)'>
        <circle cx='{c}' cy='{c}' r='{r - 3}' fill='#8a5a2b' fill-opacity='.05'/>
        <g fill='none' stroke='#7a4a1e'>{''.join(rings)}</g>
      </g></svg>""")


# ── pressed fern ──────────────────────────────────────────────────────────
def fern(seed, w=260, h=660, pairs=24):
    rnd = random.Random(seed)
    P = [(w * .47, h - 4), (w * .38, h * .62), (w * .64, h * .30), (w * .55, 12)]

    def bez(t):
        a = [(1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3]
        return sum(a[i] * P[i][0] for i in range(4)), sum(a[i] * P[i][1] for i in range(4))

    def tangent(t):
        x0, y0 = bez(max(0, t - .005))
        x1, y1 = bez(min(1, t + .005))
        n = math.hypot(x1 - x0, y1 - y0)
        return (x1 - x0) / n, (y1 - y0) / n

    greens = ["#76804a", "#7f874f", "#868a54", "#8e8d59", "#79784a", "#94895a"]
    shapes, ribs = [], []
    n = pairs * 2
    for i in range(n):
        t = .2 + .78 * i / (n - 1)
        side = 1 if i % 2 else -1
        x, y = bez(t)
        tx, ty = tangent(t)
        nx, ny = -ty * side, tx * side
        s = (t - .2) / .78
        L = w * .44 * (1 - s) ** .85 * (.62 + .38 * min(1, s / .22)) + 5
        tilt = math.radians(rnd.uniform(38, 52))
        dx, dy = nx * math.cos(tilt) + tx * math.sin(tilt), ny * math.cos(tilt) + ty * math.sin(tilt)
        ox, oy = -dy * side, dx * side           # across the pinna, toward the tip side
        curl = rnd.uniform(.05, .16)
        lobes = max(3, int(L / 6.5))
        W0 = L * .17 + 1.5
        upper, lower = [], []
        steps = lobes * 3
        for k in range(steps + 1):
            u = k / steps
            bend = curl * L * u * u
            ax, ay = x + dx * L * u + tx * bend, y + dy * L * u + ty * bend
            wd = W0 * (1 - u) ** .75 * (.35 + .65 * abs(math.sin(math.pi * lobes * u)) ** .6)
            upper.append((ax + ox * wd, ay + oy * wd))
            wd2 = W0 * (1 - u) ** .75 * (.35 + .65 * abs(math.sin(math.pi * lobes * u + 1.2)) ** .6)
            lower.append((ax - ox * wd2 * .9, ay - oy * wd2 * .9))
        pts = upper + lower[::-1]
        d = "M" + " L".join(f"{f(a)} {f(b)}" for a, b in pts) + "Z"
        col = rnd.choice(greens) if s < .9 else "#9a8a58"
        shapes.append(f"<path d='{d}' fill='{col}' fill-opacity='{f(rnd.uniform(.82, .95))}'/>")
        ex, ey = x + dx * L * .92 + tx * curl * L * .85, y + dy * L * .92 + ty * curl * L * .85
        ribs.append(f"M{f(x)} {f(y)} L{f(ex)} {f(ey)}")
    stem = "M" + " L".join(f"{f(a)} {f(b)}" for a, b in (bez(k / 40) for k in range(41)))
    return uri(f"""<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}'>
      <filter id='s' x='-10%' y='-10%' width='120%' height='120%'>
        <feDropShadow dx='1.5' dy='2.5' stdDeviation='1.6' flood-color='#2f3a22' flood-opacity='.28'/></filter>
      <g filter='url(#s)'>{''.join(shapes)}
        <path d='{' '.join(ribs)}' stroke='#5b6236' stroke-width='.6' stroke-opacity='.55' fill='none'/>
        <path d='{stem}' stroke='#6a6a3c' stroke-width='2.2' fill='none' stroke-linecap='round'/>
      </g></svg>""")


# ── ink marks ─────────────────────────────────────────────────────────────
def ellipse(seed, color):
    """a pen circle that overshoots where it closes"""
    rnd = random.Random(seed)
    pts = []
    a0 = rnd.uniform(2.6, 3.2)
    for k in range(73):
        a = a0 + (6.283 + .55) * k / 72
        drift = k / 72
        rx = 95 + 2.5 * math.sin(2 * a + 1) - drift * 3
        ry = 34 + 2 * math.sin(3 * a) - drift * 3
        pts.append((100 + rx * math.cos(a) + drift * 2, 40 + ry * math.sin(a) + drift * 3))
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
    return uri(f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 80' preserveAspectRatio='none'>
      <path d='{d}' fill='none' stroke='{color}' stroke-width='1.5' stroke-linecap='round'
        vector-effect='non-scaling-stroke' stroke-opacity='.85'/></svg>""")


def underline(color, double=False):
    second = ("<path d='M24 9.5 C70 7.5 120 10 176 8' fill='none' stroke='" + color +
              "' stroke-width='1.2' stroke-linecap='round' vector-effect='non-scaling-stroke' stroke-opacity='.7'/>"
              ) if double else ""
    return uri(f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 12' preserveAspectRatio='none'>
      <path d='M2 6 C40 3.5 85 7.5 130 5 S185 4 198 6.5' fill='none' stroke='{color}' stroke-width='1.6'
        stroke-linecap='round' vector-effect='non-scaling-stroke'/>{second}</svg>""")


def squiggle(color):
    pts = [(x, 6 + 3.2 * math.sin(x / 4.2) * (0.75 + .25 * math.sin(x / 23))) for x in range(2, 159)]
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
    return uri(f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 160 12'>
      <path d='{d}' fill='none' stroke='{color}' stroke-width='1.3' stroke-linecap='round' stroke-opacity='.8'/></svg>""")


def quote_mark(color):
    return uri(f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 26'>
      <g fill='{color}' fill-opacity='.85'>
      <path d='M11.5 3 C5 5.5 1.5 10.5 2 16.5 C2.3 20.5 5 23 8.3 22.6 C11.3 22.2 12.8 19.6 12.1 17 C11.4 14.6 9 13.5 6.6 14.2 C7 10.2 9.3 6.8 12.6 4.6 Z'/>
      <path d='M27.5 3 C21 5.5 17.5 10.5 18 16.5 C18.3 20.5 21 23 24.3 22.6 C27.3 22.2 28.8 19.6 28.1 17 C27.4 14.6 25 13.5 22.6 14.2 C23 10.2 25.3 6.8 28.6 4.6 Z'/>
      </g></svg>""")


droid = uri("""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 52'>
  <g stroke='#b5583a' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' fill='#d98a63' fill-opacity='.45'>
    <path d='M11.2 22.4 C10.6 12.6 17.4 7.2 24.2 7.4 C31 7.6 37.6 12.8 36.9 22.2 Z'/>
    <path d='M10.8 25.4 L37.2 25.1 L37.4 39.6 C37.4 42 35.6 43.6 33.4 43.6 L14.8 43.8 C12.6 43.8 11 42.2 11 40 Z'/>
    <path d='M6.2 26.6 L6 37.2 M42 26.2 L42.2 37' fill='none'/>
    <path d='M19.2 44 L19 50.2 M29 44 L29.2 50' fill='none'/>
    <path d='M16.4 9.6 L12.6 3.4 M31.8 9.4 L35.6 3.2' fill='none'/>
  </g>
  <circle cx='18.6' cy='15.6' r='1.5' fill='#7d3a24'/><circle cx='29.4' cy='15.4' r='1.5' fill='#7d3a24'/>
</svg>""")

INK_BLUE = "#34507a"
TERRA = "#b5583a"
PENCIL = "#8a8a7c"

vars_ = {
    "--torn": torn(3),
    "--torn-2": torn(17, depth=8),
    "--grain": grain,
    "--mottle": mottle,
    "--linen": linen,
    "--coffee": coffee(5),
    "--fern-1": fern(7),
    "--fern-2": fern(19, w=200, h=470, pairs=17),
    "--circle": ellipse(4, INK_BLUE),
    "--circle-terra": ellipse(9, TERRA),
    "--underline": underline(PENCIL),
    "--underline-ink": underline(INK_BLUE, double=True),
    "--squiggle": squiggle(PENCIL),
    "--quote-mark": quote_mark(TERRA),
    "--droid": droid,
}

print("/* generated by gen-assets.py, do not edit by hand */")
print(":root {")
for k, v in vars_.items():
    print(f"  {k}: {v};")
print("}")
