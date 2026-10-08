#!/usr/bin/env python3
"""CI checks for the built site: SEO tags, JSON-LD, internal links, EN/AR pairs, and JS/Python price parity.

    python3 build.py && python3 tools/check.py
"""
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

OUT = build.OUT_ROOT
BASE = build.BASE
errors = []


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ld, self.meta, self.title, self._ld, self._t, self.html_attrs, self.h1 = [], [], {}, "", None, False, {}, 0

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "html":
            self.html_attrs = a
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag in ("img", "script", "link") and (a.get("src") or (tag == "link" and a.get("rel") in ("stylesheet", "icon"))):
            self.links.append(a.get("src") or a.get("href"))
        if tag == "meta" and a.get("name"):
            self.meta[a["name"]] = a.get("content", "")
        if tag == "link" and a.get("rel") in ("canonical", "alternate"):
            self.meta[a["rel"] + ":" + a.get("hreflang", "")] = a["href"]
        if tag == "script" and a.get("type") == "application/ld+json":
            self._ld = ""
        if tag == "title":
            self._t = True
        if tag == "h1":
            self.h1 += 1

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            self.ld.append(self._ld)
            self._ld = None
        if tag == "title":
            self._t = False

    def handle_data(self, d):
        if self._ld is not None:
            self._ld += d
        if self._t:
            self.title += d


files = sorted(OUT.rglob("*.html"))
for f in files:
    rel = f.relative_to(OUT)
    p = Page()
    p.feed(f.read_text())
    if not p.title.strip():
        errors.append(f"{rel}: no title")
    if len(p.meta.get("description", "")) < 50:
        errors.append(f"{rel}: description missing or short")
    if rel.name != "404.html":
        for k in ("canonical:", "alternate:en", "alternate:ar", "alternate:x-default"):
            if k not in p.meta:
                errors.append(f"{rel}: missing {k}")
        if p.h1 != 1:
            errors.append(f"{rel}: {p.h1} h1 tags")
        if not p.ld:
            errors.append(f"{rel}: no JSON-LD")
    want_lang = "ar" if str(rel).startswith("ar/") else "en"
    if p.html_attrs.get("lang") != want_lang:
        errors.append(f"{rel}: lang should be {want_lang}")
    for raw in p.ld:
        try:
            json.loads(raw)
        except ValueError as ex:
            errors.append(f"{rel}: bad JSON-LD ({ex})")
    for h in p.links:
        if h.startswith(("http", "mailto:", "#", "tel:")):
            continue
        path = h.split("?")[0].split("#")[0]
        if not path.startswith(BASE + "/"):
            errors.append(f"{rel}: link outside base {h}")
            continue
        target = OUT / path[len(BASE) + 1:]
        if path.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            errors.append(f"{rel}: broken link {h}")

# every EN page has an AR twin
for f in files:
    rel = f.relative_to(OUT)
    if rel.name == "404.html" or str(rel).startswith("ar/"):
        continue
    if not (OUT / "ar" / rel).exists():
        errors.append(f"{rel}: no Arabic twin")

# price parity: the browser formula (assets/js/mesh.js) must match build.py's for every example
js = r"""
const fs = require("fs"); const M = require(process.argv[1] + "/assets/js/mesh.js");
const P = JSON.parse(fs.readFileSync(process.argv[1] + "/data/pricing.json"));
const out = {};
for (const s of JSON.parse(process.argv[2])) {
  const b = fs.readFileSync(process.argv[1] + "/assets/models/" + s[0] + ".stl");
  const m = M.measure(M.parseSTL(b.buffer.slice(b.byteOffset, b.byteOffset + b.length)));
  out[s[0]] = M.price(m, {material: s[1], infill: P.infill_default, quality: "standard", qty: 1, scale: 1}, P);
}
console.log(JSON.stringify(out));
"""
try:
    res = subprocess.run(["node", "-e", js, str(ROOT), json.dumps([[s, x["mat"]] for s, x in build.EX.items()])], capture_output=True, text=True, check=True)
    got = json.loads(res.stdout)
    for slug, x in build.EX.items():
        if abs(got[slug]["total"] - x["q"]["total"]) > 1e-9 or abs(got[slug]["grams"] - x["q"]["grams"]) > 0.05:
            errors.append(f"price parity {slug}: js {got[slug]['total']} / {got[slug]['grams']:.2f} g vs py {x['q']['total']} / {x['q']['grams']:.2f} g")
except (subprocess.CalledProcessError, FileNotFoundError) as ex:
    errors.append(f"node parity check failed: {getattr(ex, 'stderr', ex)}")

sm = (OUT / "sitemap.xml").read_text()
if len(re.findall(r"<loc>", sm)) != 12:
    errors.append("sitemap should list 12 URLs")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"ok: {len(files)} pages, links, SEO tags, JSON-LD, AR twins, price parity")
