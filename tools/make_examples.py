#!/usr/bin/env python3
"""Generate the example models (binary STL) and their renders (WebP + PNG).

These are honest renders of simple models we designed in code, shown on the
site as "example render" until Nizar sends photos of real prints. Output:
assets/models/<slug>.stl and assets/img/<slug>.webp (+ .png for og:image).

    python3 tools/make_examples.py
"""
import math
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "assets" / "models"
IMG = ROOT / "assets" / "img"


# ---------- geometry ----------

def area2(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))


def ccw(poly):
    return poly if area2(poly) > 0 else poly[::-1]


def ear_clip(poly):
    """Triangulate a simple CCW polygon; returns index triples."""
    idx = list(range(len(poly)))
    tris = []

    def inside(p, a, b, c):
        def s(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        n = len(idx)
        for k in range(n):
            i0, i1, i2 = idx[(k - 1) % n], idx[k], idx[(k + 1) % n]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 0:
                continue
            if any(inside(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


def extrude(poly, z0, z1):
    """Closed prism from a simple polygon in XY."""
    poly = ccw(poly)
    out = []
    for a, b, c in ear_clip(poly):
        pa, pb, pc = poly[a], poly[b], poly[c]
        out.append(((pa[0], pa[1], z1), (pb[0], pb[1], z1), (pc[0], pc[1], z1)))
        out.append(((pa[0], pa[1], z0), (pc[0], pc[1], z0), (pb[0], pb[1], z0)))
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        out.append(((p[0], p[1], z0), (q[0], q[1], z0), (q[0], q[1], z1)))
        out.append(((p[0], p[1], z0), (q[0], q[1], z1), (p[0], p[1], z1)))
    return out


def extrude_ring(outer, inner, z0, z1):
    """Prism with one hole; outer and inner have the same vertex count and winding."""
    outer, inner = ccw(outer), ccw(inner)
    n = len(outer)
    out = []
    for i in range(n):
        o0, o1, i0, i1 = outer[i], outer[(i + 1) % n], inner[i], inner[(i + 1) % n]
        # top and bottom quads
        out += [((o0[0], o0[1], z1), (o1[0], o1[1], z1), (i1[0], i1[1], z1)), ((o0[0], o0[1], z1), (i1[0], i1[1], z1), (i0[0], i0[1], z1))]
        out += [((o0[0], o0[1], z0), (i1[0], i1[1], z0), (o1[0], o1[1], z0)), ((o0[0], o0[1], z0), (i0[0], i0[1], z0), (i1[0], i1[1], z0))]
        # outer wall (faces out) and inner wall (faces in)
        out += [((o0[0], o0[1], z0), (o1[0], o1[1], z0), (o1[0], o1[1], z1)), ((o0[0], o0[1], z0), (o1[0], o1[1], z1), (o0[0], o0[1], z1))]
        out += [((i0[0], i0[1], z0), (i1[0], i1[1], z1), (i1[0], i1[1], z0)), ((i0[0], i0[1], z0), (i0[0], i0[1], z1), (i1[0], i1[1], z1))]
    return out


def circle(r, n=48, cx=0, cy=0, phase=0):
    return [(cx + r * math.cos(phase + 2 * math.pi * i / n), cy + r * math.sin(phase + 2 * math.pi * i / n)) for i in range(n)]


def rot_x90(tris, y_shift=0):
    """Stand a profile drawn in XY (Y up) upright: (x, y, z) -> (x, z, y)."""
    return [tuple((v[0], v[2] + y_shift, v[1]) for v in t[::-1]) for t in tris]


def move(tris, dx=0, dy=0, dz=0):
    return [tuple((v[0] + dx, v[1] + dy, v[2] + dz) for v in t) for t in tris]


# ---------- models ----------

def cedar():
    """Cedar keychain: a layered cedar silhouette with a key ring loop."""
    pts = [(0, 48)]
    tiers = [(7, 44), (15, 40), (9, 36), (23, 31), (13, 27), (29, 20), (17, 16), (32, 8)]
    right = [(x, y) for x, y in tiers]
    left = [(-x, y) for x, y in reversed(tiers)]
    pts += right + [(4, 5), (4, -2), (-4, -2), (-4, 5)] + left
    tris = extrude(pts, 0, 4)
    tris += extrude_ring(circle(5, 32, 0, 53), circle(2.6, 32, 0, 53), 0, 3)
    return tris


def phone_stand():
    """Phone stand: side profile extruded 70 mm wide."""
    prof = [(0, 0), (80, 0), (80, 6), (24, 6), (30, 14), (26, 16), (18, 6), (12, 6), (52, 92), (46, 95), (4, 6), (0, 6)]
    return rot_x90(extrude(prof, 0, 70))


def planter():
    """Hexagonal planter with a 2 mm wall and a solid base."""
    tris = extrude_ring(circle(40, 6, phase=math.pi / 6), circle(37.5, 6, phase=math.pi / 6), 3, 70)
    tris += extrude(circle(40, 6, phase=math.pi / 6), 0, 3)
    return tris


def stand_up(tris):
    """Show a flat piece standing on its edge, the way it reads best in a photo."""
    return rot_x90(tris)


def lebanon_map():
    """Lebanon outline magnet, 5 mm thick (approximate border, for display)."""
    lonlat = [(35.10, 33.09), (35.19, 33.27), (35.37, 33.56), (35.47, 33.90), (35.62, 33.98), (35.64, 34.12), (35.66, 34.25),
              (35.80, 34.45), (35.97, 34.64), (36.35, 34.64), (36.45, 34.50), (36.62, 34.20), (36.35, 33.83), (36.07, 33.65),
              (35.95, 33.45), (35.82, 33.30), (35.62, 33.27), (35.55, 33.10)]
    k = 85 / (34.64 - 33.09)
    c = math.cos(math.radians(33.9))
    pts = [((lon - 35.1) * c * k, (lat - 33.09) * k) for lon, lat in lonlat]
    return extrude(pts, 0, 5)


def knob():
    """Replacement appliance knob: knurled grip on a round base, D-shaft socket ignored for display."""
    grip = []
    for i in range(60):
        r = 15 if i % 2 == 0 else 13.6
        a = 2 * math.pi * i / 60
        grip.append((r * math.cos(a), r * math.sin(a)))
    tris = extrude(circle(18, 64), 0, 3)
    tris += extrude(grip, 3, 18)
    tris += extrude([(-1.2, 4), (1.2, 4), (1.2, 13), (-1.2, 13)], 18, 19.5)  # pointer ridge
    return tris


def cable_clip():
    """Desk cable organiser: a comb of five slots."""
    tris = extrude([(0, 0), (64, 0), (64, 18), (0, 18)], 0, 4)
    for i in range(6):
        x0 = i * 12
        tris += extrude([(x0, 0), (x0 + 4, 0), (x0 + 4, 18), (x0, 18)], 4, 16)
    return tris


EXAMPLES = {
    "cedar-keychain": (cedar, (0.18, 0.55, 0.32)),
    "phone-stand": (phone_stand, (0.93, 0.36, 0.16)),
    "hex-planter": (planter, (0.95, 0.93, 0.88)),
    "lebanon-map": (lebanon_map, (0.85, 0.16, 0.18)),
    "appliance-knob": (knob, (0.17, 0.17, 0.19)),
    "cable-organiser": (cable_clip, (0.20, 0.42, 0.85)),
}
SHOW_STANDING = {"cedar-keychain", "lebanon-map"}  # printed flat, photographed upright


# ---------- STL + stats ----------

def write_stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"Tlete example model".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            n = normal(t)
            f.write(struct.pack("<12fH", *n, *t[0], *t[1], *t[2], 0))


def normal(t):
    a, b, c = t
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    m = math.sqrt(sum(x * x for x in n)) or 1
    return tuple(x / m for x in n)


def stats(tris):
    vol = sum(a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0]) for a, b, c in tris) / 6
    xs = [v[i] for t in tris for v in t for i in (0,)]
    ys = [v[1] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    return abs(vol) / 1000, (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))


# ---------- render ----------

def subdivide(tris, max_edge):
    """Split long triangles so the painter's sort draws them in the right order."""
    out = []
    stack = list(tris)
    while stack:
        a, b, c = stack.pop()
        e = max(math.dist(a, b), math.dist(b, c), math.dist(c, a))
        if e <= max_edge:
            out.append((a, b, c))
            continue
        ab = tuple((a[i] + b[i]) / 2 for i in range(3))
        bc = tuple((b[i] + c[i]) / 2 for i in range(3))
        ca = tuple((c[i] + a[i]) / 2 for i in range(3))
        stack += [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
    return out

def render(tris, colour, path, size=(800, 600), label="3D render", yaw_deg=-35):
    ss = 2
    W, H = size[0] * ss, size[1] * ss
    img = Image.new("RGB", (W, H), (246, 242, 235))
    d = ImageDraw.Draw(img)
    # soft vertical gradient
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(250 - 14 * k), int(247 - 15 * k), int(241 - 16 * k)))
    yaw, pitch = math.radians(yaw_deg), math.radians(24)
    tris = subdivide(tris, 4.0)
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)

    def view(v):  # world Z up -> screen
        x, y, z = v
        x1 = x * cy - y * sy
        y1 = x * sy + y * cy
        return (x1, z * cp - y1 * sp, z * sp + y1 * cp)  # sx, sy(up), depth(toward viewer = smaller)

    cx = sum(v[0] for t in tris for v in t) / (3 * len(tris))
    cyy = sum(v[1] for t in tris for v in t) / (3 * len(tris))
    zmin = min(v[2] for t in tris for v in t)
    moved = [tuple((v[0] - cx, v[1] - cyy, v[2] - zmin) for v in t) for t in tris]
    proj = [[view(v) for v in t] for t in moved]
    xs = [p[0] for t in proj for p in t]
    ys = [p[1] for t in proj for p in t]
    span = max(max(xs) - min(xs), (max(ys) - min(ys)) * W / H)
    scale = W * 0.62 / span
    ox = W / 2 - (max(xs) + min(xs)) / 2 * scale
    oy = H * 0.52 + (max(ys) + min(ys)) / 2 * scale

    # floor shadow
    sh = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(sh)
    for t in moved:
        flat = [view((v[0], v[1], 0)) for v in t]
        sd.polygon([(ox + p[0] * scale, oy - p[1] * scale) for p in flat], fill=70)
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(18 * ss))
    img.paste((205, 198, 186), (0, 0), sh)

    light = (-0.35, 0.45, 0.82)
    lm = math.sqrt(sum(x * x for x in light))
    light = tuple(x / lm for x in light)
    faces = []
    for t, p in zip(moved, proj):
        n = normal(t)
        nv = view(n)
        # back-face cull: larger depth is closer to the camera, so visible faces have a positive depth component
        if nv[2] < -1e-6:
            continue
        lam = max(0.0, n[0] * light[0] + n[1] * light[1] + n[2] * light[2])
        shade = 0.42 + 0.58 * lam
        rgb = tuple(int(255 * min(1, c * shade + 0.06 * (1 - shade))) for c in colour)
        depth = sum(q[2] for q in p) / 3
        faces.append((depth, [(ox + q[0] * scale, oy - q[1] * scale) for q in p], rgb))
    faces.sort(key=lambda f: f[0])
    for _, pts, rgb in faces:
        d.polygon(pts, fill=rgb, outline=rgb)
    img = img.resize(size, Image.LANCZOS)
    dd = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    tw = dd.textlength(label, font=font)
    dd.rounded_rectangle([size[0] - tw - 28, size[1] - 36, size[0] - 10, size[1] - 10], 8, fill=(255, 255, 255))
    dd.text((size[0] - tw - 19, size[1] - 32), label, fill=(90, 84, 76), font=font)
    img.save(path.with_suffix(".webp"), quality=86, method=6)
    img.save(path.with_suffix(".png"), optimize=True)


if __name__ == "__main__":
    MODELS.mkdir(parents=True, exist_ok=True)
    IMG.mkdir(parents=True, exist_ok=True)
    for slug, (fn, colour) in EXAMPLES.items():
        tris = fn()
        write_stl(MODELS / f"{slug}.stl", tris)
        render(stand_up(tris) if slug in SHOW_STANDING else tris, colour, IMG / slug, yaw_deg=-18 if slug in SHOW_STANDING else -35)
        vol, dims = stats(tris)
        print(f"{slug}: {len(tris)} tris, {vol:.1f} cm3, {dims[0]:.0f}x{dims[1]:.0f}x{dims[2]:.0f} mm")
