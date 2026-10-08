#!/usr/bin/env python3
"""Build the Tlete site (English + Arabic) into site/.

    python3 build.py            # writes site/
    python3 -m http.server -d site 8124   # preview at http://localhost:8124/tlete/ (base path kept)

Settings: data/site.json (URL, base path, WhatsApp, forms endpoint), data/pricing.json (the price formula).
"""
import html
import json
import math
import shutil
import struct
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "site"
S = json.loads((ROOT / "data" / "site.json").read_text())
P = json.loads((ROOT / "data" / "pricing.json").read_text())
BASE = S["base_path"].rstrip("/")
ORIGIN = S["site_url"].rstrip("/")
WA = S["whatsapp"]
TODAY = date.today().isoformat()
OUT_ROOT = OUT / BASE.strip("/") if BASE else OUT

e = html.escape


def url(path):  # absolute URL for canonical/hreflang/sitemap
    return ORIGIN + BASE + path


def href(path):  # site-relative link
    return BASE + path


def money(v):
    s = f"{v:.2f}"
    return "$" + (s[:-3] if s.endswith(".00") else s)


# ---------- price the examples with the same formula as assets/js/mesh.js ----------

def read_stl(path):
    b = path.read_bytes()
    n = struct.unpack_from("<I", b, 80)[0]
    tris = []
    for i in range(n):
        f = struct.unpack_from("<12f", b, 84 + i * 50)
        tris.append((f[3:6], f[6:9], f[9:12]))
    return tris


def measure(tris):
    vol = area = 0.0
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for a, b, c in tris:
        vol += a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        area += math.sqrt(sum(x * x for x in n)) / 2
        for p in (a, b, c):
            for i in range(3):
                lo[i], hi[i] = min(lo[i], p[i]), max(hi[i], p[i])
    return {"volume_cm3": abs(vol) / 6 / 1000, "area_cm2": area / 100, "size_mm": [hi[i] - lo[i] for i in range(3)]}


def price(m, material="PLA", infill=None, quality="standard", qty=1):
    infill = P["infill_default"] if infill is None else infill
    mat = P["materials"][material]
    vol, area = m["volume_cm3"], m["area_cm2"]
    shell = min(vol, area * P["shell_mm"] / 10)
    solid = shell + (vol - shell) * infill / 100
    grams = solid * mat["density"] * P["waste_factor"]
    hours = P["setup_hours"] + grams / mat["grams_per_hour"] * P["quality"][quality]
    piece = grams * mat["per_gram"] + hours * P["per_hour"]
    total = math.ceil(max(P["min_order"], piece * qty + P["handling"]) * 2) / 2
    return {"grams": grams, "hours": hours, "total": total}


EXAMPLES = [
    # slug, material, EN name, AR name, EN line, AR line
    ("cedar-keychain", "PLA", "Cedar keychain", "ميدالية أرزة",
     "A Lebanese cedar for your keys or bag. Initials on the back on request.", "أرزة لبنانية لمفاتيحك أو شنطتك. منكتب الأحرف الأولى على ضهرها إذا بدّك."),
    ("phone-stand", "PLA", "Phone stand", "ستاند للتلفون",
     "Holds a phone upright or sideways on a desk, with a gap for the charger cable.", "بيحمل التلفون واقف أو بالعرض عالمكتب، وفيه فتحة لشريط الشحن."),
    ("appliance-knob", "PETG", "Replacement knob", "مقبض بديل",
     "Lost the knob on your oven, fan or washing machine? Send a photo with measurements and we model it.", "ضاع مقبض الفرن أو المروحة أو الغسالة؟ ابعتلنا صورة مع القياسات ومنرسمو."),
    ("lebanon-map", "PLA", "Lebanon map plaque", "لوحة خريطة لبنان",
     "A small map of Lebanon for a shelf, a fridge (magnet on request) or a gift.", "خريطة لبنان صغيرة للرف، للبرّاد (مع مغناطيس إذا بدّك) أو هدية."),
    ("hex-planter", "PETG", "Hex planter", "حوض زرع سداسي",
     "A small planter for succulents or herbs. PETG handles water and sun better than PLA.", "حوض صغير للصبّار أو الحبق. الـPETG بيتحمّل المي والشمس أكتر من الـPLA."),
    ("cable-organiser", "PLA", "Cable organiser", "منظّم شرطان",
     "Keeps chargers and cables in their place on the desk.", "بيخلّي الشواحن والشرطان بمحلّن عالمكتب."),
]
EX = {}
for slug, mat, *_ in EXAMPLES:
    m = measure(read_stl(ROOT / "assets" / "models" / f"{slug}.stl"))
    EX[slug] = {"m": m, "q": price(m, mat), "mat": mat}


# ---------- shared bits ----------

LOGO = """<svg viewBox="0 0 40 40" aria-hidden="true"><rect x="4" y="7" width="32" height="7" rx="3.5" fill="#e8572a"/><rect x="9" y="17" width="27" height="7" rx="3.5" fill="#f08a4f"/><rect x="4" y="27" width="32" height="7" rx="3.5" fill="#e8572a"/></svg>"""
WA_ICON = """<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.7.8-.8 1-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.7-1.4a.5.5 0 0 0 0-.5l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6a2.7 2.7 0 0 0 1.8-1.2 2.2 2.2 0 0 0 .1-1.3c0-.1-.2-.2-.5-.3Z"/></svg>"""

L = {
    "en": {
        "dir": "ltr", "other": "ar", "other_label": "عربي", "skip": "Skip to content", "menu": "Menu",
        "nav": [("/", "Home"), ("/quote/", "Instant quote"), ("/request/", "Custom request"), ("/delivery/", "Delivery & payment"), ("/faq/", "FAQ")],
        "wa_label": "WhatsApp us", "tagline": "3D printing in Lebanon",
        "footer_about": "Tlete (تلاتة, \"three\" in Lebanese Arabic) is a small 3D-printing studio in Lebanon with one Bambu Lab A1 Mini printer. We print your files and your ideas in PLA, PETG and TPU, and hand them over or send them anywhere in Lebanon.",
        "footer_pages": "Pages", "footer_contact": "Contact", "privacy": "Privacy",
        "render_note": "Example render, not a photo of a customer order",
    },
    "ar": {
        "dir": "rtl", "other": "en", "other_label": "English", "skip": "انتقل إلى المحتوى", "menu": "القائمة",
        "nav": [("/", "الرئيسية"), ("/quote/", "تسعير فوري"), ("/request/", "طلب خاص"), ("/delivery/", "التوصيل والدفع"), ("/faq/", "أسئلة شائعة")],
        "wa_label": "راسلنا على واتساب", "tagline": "طباعة ثلاثية الأبعاد بلبنان",
        "footer_about": "تلاتة (Tlete) استوديو صغير للطباعة الثلاثية الأبعاد بلبنان، عندو طابعة وحدة Bambu Lab A1 Mini. منطبع ملفاتك وأفكارك بالـPLA والـPETG والـTPU، ومنسلّمك ياهن باليد أو منبعتن لأي منطقة بلبنان.",
        "footer_pages": "الصفحات", "footer_contact": "تواصل", "privacy": "الخصوصية",
        "render_note": "صورة تصميم ثلاثي الأبعاد للتوضيح، مش صورة طلب زبون",
    },
}


def lp(lang, path):  # language-prefixed path
    return ("/ar" + path) if lang == "ar" else path


def wa_link(lang, text=None, where="page"):
    t = text or ("مرحبا Tlete، عندي سؤال عن الطباعة." if lang == "ar" else "Hi Tlete, I have a question about a print.")
    from urllib.parse import quote
    return f"https://wa.me/{WA}?text={quote(t)}", where


def wa_btn(lang, label=None, cls="btn wa", where="page", text=None):
    h, w = wa_link(lang, text, where)
    return f'<a class="{cls}" href="{e(h)}" data-where="{w}" rel="noopener" target="_blank">{WA_ICON}{e(label or L[lang]["wa_label"])}</a>'


def page(lang, path, title, desc, body, ld=(), scripts=(), crumbs=None, og_image="/assets/img/phone-stand.png"):
    t = L[lang]
    other = t["other"]
    twin = "/" if path == "/404" else path  # the same page in the other language
    alt_en, alt_ar = url(path), url("/ar" + path)
    canonical = alt_ar if lang == "ar" else alt_en
    nav = "".join(
        f'<a href="{href(lp(lang, p))}"{" aria-current=page" if p == path else ""}>{e(n)}</a>' for p, n in t["nav"]
    )
    nav += f'<a class="lang" href="{href(lp(other, twin))}" hreflang="{other}" lang="{other}">{t["other_label"]}</a>'
    crumb_html = ""
    if crumbs:
        home = t["nav"][0][1]
        crumb_html = f'<div class="wrap crumbs"><a href="{href(lp(lang, "/"))}">{e(home)}</a> / {e(crumbs)}</div>'
        ld = list(ld) + [{
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": home, "item": url(lp(lang, "/"))},
                {"@type": "ListItem", "position": 2, "name": crumbs, "item": canonical},
            ]}]
    ld_html = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    js = "".join(f'<script src="{href(s)}" defer></script>' for s in scripts)
    foot_links = "".join(f'<li><a href="{href(lp(lang, p))}">{e(n)}</a></li>' for p, n in t["nav"][1:]) + f'<li><a href="{href(lp(lang, "/privacy/"))}">{e(t["privacy"])}</a></li>'
    form_cfg = json.dumps(S["form"])
    doc = f"""<!doctype html>
<html lang="{lang}" dir="{t['dir']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{alt_en}">
<link rel="alternate" hreflang="ar" href="{alt_ar}">
<link rel="alternate" hreflang="x-default" href="{alt_en}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Tlete">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{url(og_image)}">
<meta property="og:locale" content="{'ar_LB' if lang == 'ar' else 'en_US'}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f7f3ec">
<link rel="icon" href="{href('/assets/img/favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{href('/assets/css/style.css')}">
{'<link rel="preload" href="' + href('/assets/fonts/noto-kufi-arabic-arabic.woff2') + '" as="font" type="font/woff2" crossorigin>' if lang == 'ar' else ''}
<script async src="https://www.googletagmanager.com/gtag/js?id={S['ga4']}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{S['ga4']}',{{site:'tlete'}});
window.TLETE_BASE={json.dumps(BASE)};window.TLETE_WA={json.dumps(WA)};window.TLETE_FORM={form_cfg};window.TLETE_PRICING={json.dumps(P)};</script>
{ld_html}
</head>
<body>
<a class="skip" href="#main">{e(t['skip'])}</a>
<header class="top"><div class="wrap">
<a class="logo" href="{href(lp(lang, '/'))}" aria-label="Tlete">{LOGO}<span>tlete</span><small>تلاتة</small></a>
<button id="menu-btn" aria-expanded="false" aria-controls="nav">{e(t['menu'])}</button>
<nav class="main" id="nav" aria-label="{e(t['menu'])}">{nav}</nav>
</div></header>
{crumb_html}
<main id="main">
{body}
</main>
<footer><div class="wrap">
<div class="cols">
<div><a class="logo" href="{href(lp(lang, '/'))}" style="color:#fff">{LOGO}<span>tlete</span></a><p style="margin-top:12px">{e(t['footer_about'])}</p></div>
<div><h3>{e(t['footer_pages'])}</h3><ul>{foot_links}</ul></div>
<div><h3>{e(t['footer_contact'])}</h3><ul><li>{wa_btn(lang, S['whatsapp_display'], cls='', where='footer')}</li><li><a href="{href(lp(other, twin))}" hreflang="{other}">{t['other_label']}</a></li></ul></div>
</div>
<p class="small">© {date.today().year} Tlete · {e(t['tagline'])}</p>
</div></footer>
{wa_btn(lang, t['wa_label'], cls='btn wa wa-float', where='float')}
<script src="{href('/assets/js/site.js')}" defer></script>
{js}
</body>
</html>
"""
    dest = OUT_ROOT / lp(lang, path).strip("/") / "index.html" if path != "/404" else OUT_ROOT / "404.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(doc)
    return dest


# ---------- structured data ----------

def business_ld(lang):
    ar = lang == "ar"
    return {
        "@context": "https://schema.org", "@type": "LocalBusiness", "@id": url("/#business"),
        "name": "Tlete" if not ar else "تلاتة (Tlete)", "alternateName": ["تلاتة", "Tlete 3D"],
        "description": L[lang]["footer_about"], "url": url(lp(lang, "/")), "image": url("/assets/img/phone-stand.png"),
        "logo": url("/assets/img/logo.png"),
        "telephone": "+" + WA, "priceRange": f"from {money(P['min_order'])}", "currenciesAccepted": "USD",
        "paymentAccepted": "Cash, Whish Money", "areaServed": {"@type": "Country", "name": "Lebanon"},
        "knowsLanguage": ["en", "ar"],
        "contactPoint": {"@type": "ContactPoint", "contactType": "orders", "telephone": "+" + WA, "availableLanguage": ["English", "Arabic"]},
    }


def service_ld(lang):
    ar = lang == "ar"
    return {
        "@context": "https://schema.org", "@type": "Service", "serviceType": "3D printing",
        "name": "طباعة ثلاثية الأبعاد حسب الطلب" if ar else "3D printing on demand",
        "provider": {"@id": url("/#business")}, "areaServed": {"@type": "Country", "name": "Lebanon"},
        "offers": {
            "@type": "Offer", "priceCurrency": "USD", "url": url(lp(lang, "/quote/")),
            "priceSpecification": [
                {"@type": "UnitPriceSpecification", "price": P["materials"]["PLA"]["per_gram"], "priceCurrency": "USD", "unitText": "gram of PLA"},
                {"@type": "UnitPriceSpecification", "price": P["materials"]["PETG"]["per_gram"], "priceCurrency": "USD", "unitText": "gram of PETG"},
                {"@type": "UnitPriceSpecification", "price": P["materials"]["TPU"]["per_gram"], "priceCurrency": "USD", "unitText": "gram of TPU"},
                {"@type": "UnitPriceSpecification", "price": P["per_hour"], "priceCurrency": "USD", "unitText": "print hour"},
                {"@type": "PriceSpecification", "price": P["handling"], "priceCurrency": "USD", "name": "handling per order"},
                {"@type": "PriceSpecification", "minPrice": P["min_order"], "priceCurrency": "USD", "name": "minimum order"},
            ],
        },
    }


def products_ld(lang):
    items = []
    for i, (slug, mat, en, ar, en_d, ar_d) in enumerate(EXAMPLES, 1):
        q = EX[slug]["q"]
        items.append({"@type": "ListItem", "position": i, "item": {
            "@type": "Product", "name": ar if lang == "ar" else en, "description": ar_d if lang == "ar" else en_d,
            "image": url(f"/assets/img/{slug}.png"), "material": mat, "brand": {"@type": "Brand", "name": "Tlete"},
            "offers": {"@type": "Offer", "price": q["total"], "priceCurrency": "USD", "availability": "https://schema.org/MadeToOrder",
                       "url": url(lp(lang, "/quote/")) + f"?try={slug}", "areaServed": "LB",
                       "description": "Estimated price, final quote confirmed on WhatsApp"},
        }})
    return {"@context": "https://schema.org", "@type": "ItemList", "name": "Example prints" if lang == "en" else "أمثلة طباعة", "itemListElement": items}


# ---------- content ----------

def pr(slug):
    return money(EX[slug]["q"]["total"])


FAQ = {
    "en": [
        ("How much does 3D printing cost in Lebanon?",
         f"At Tlete the price is material + print time + handling: {money(P['materials']['PLA']['per_gram'])} per gram of PLA ({money(P['materials']['PETG']['per_gram'])} PETG, {money(P['materials']['TPU']['per_gram'])} TPU), plus {money(P['per_hour'])} per print hour, plus {money(P['handling'])} per order, with a {money(P['min_order'])} minimum. A cedar keychain comes to about {pr('cedar-keychain')} and a phone stand to about {pr('phone-stand')}. Upload your file to the instant quote for your exact estimate; we confirm the final price on WhatsApp before printing."),
        ("What files can I send?",
         "STL, OBJ and 3MF files work in the instant quote. If you only have a photo, a sketch or a broken part, send it through the custom request form or on WhatsApp with the measurements, and we tell you if we can model it and what it costs."),
        ("What is the biggest thing you can print?",
         "One piece can be up to 180 × 180 × 180 mm, the build volume of our Bambu Lab A1 Mini. Bigger objects can be printed in parts and glued, which we quote case by case."),
        ("Which materials do you print with?",
         "PLA for decor, gifts, models and most everyday objects; PETG for parts that need to be tougher or handle water, sun and some heat; TPU for flexible things like bumpers and grips. We don't print ABS, ASA, nylon, resin or metal."),
        ("Can you print in several colours?",
         "Single-colour prints are the default, in the colours we have in stock. Ask on WhatsApp if you need more than one colour in a single print; we confirm what's possible for your model."),
        ("How long does an order take?",
         "The instant quote shows the print time of your model. We confirm the ready date on WhatsApp before we start, based on the queue that day. Courier delivery inside Lebanon usually takes 1–3 days after that."),
        ("How do I pay?",
         "Cash on delivery or at hand-over, or Whish Money. Prices are in US dollars. For large orders we may ask for part of the price upfront by Whish; we tell you before printing."),
        ("Do you deliver outside Beirut?",
         "Yes, anywhere in Lebanon by courier, cash on delivery. The courier fee (usually about $4–5) is added to your order. You can also pick up or arrange a hand-over."),
        ("Do you ship abroad?",
         "We can quote courier shipping abroad, but for a single small print the shipping often costs more than the print itself. It makes sense for bigger orders; message us with your country and we quote it."),
        ("Can you copy or fix a broken part?",
         "Often, yes. Send a photo of the part next to a ruler, its measurements and what it does. Simple knobs, clips, covers and brackets are good candidates; parts that carry heavy loads or get hot (above about 70 °C) are not."),
        ("Is my file safe with you?",
         "The instant quote reads your file inside your browser; it is not uploaded unless you send a request. We use your file only to print your order and never share or sell it."),
        ("Is there anything you won't print?",
         "We only print files you have the right to use, and we don't print weapons or weapon parts, or anything meant to harm."),
    ],
    "ar": [
        ("قدّيش بتكلّف الطباعة الثلاثية الأبعاد بلبنان؟",
         f"عند تلاتة السعر = المادة + وقت الطباعة + التحضير: {money(P['materials']['PLA']['per_gram'])} للغرام PLA ({money(P['materials']['PETG']['per_gram'])} للـPETG، {money(P['materials']['TPU']['per_gram'])} للـTPU)، زائد {money(P['per_hour'])} لكل ساعة طباعة، زائد {money(P['handling'])} عن كل طلب، والحد الأدنى {money(P['min_order'])}. ميدالية الأرزة بتطلع تقريبًا {pr('cedar-keychain')} وستاند التلفون تقريبًا {pr('phone-stand')}. حمّل ملفك بالتسعير الفوري لتعرف سعرك التقديري، ومنأكّد السعر النهائي على واتساب قبل ما نطبع."),
        ("شو أنواع الملفات اللي فيني ابعتها؟",
         "التسعير الفوري بيقرا ملفات STL وOBJ و3MF. إذا عندك بس صورة أو رسمة أو قطعة مكسورة، ابعتها بنموذج الطلب الخاص أو على واتساب مع القياسات، ومنقلّك إذا فينا نرسمها وقدّيش بتكلّف."),
        ("شو أكبر قطعة فيكن تطبعوها؟",
         "القطعة الوحدة لحد 180 × 180 × 180 ملم، وهيدا حجم الطباعة بطابعتنا Bambu Lab A1 Mini. الأغراض الأكبر منطبعها قطع ومنلزّقها، ومنسعّرها حسب كل حالة."),
        ("شو المواد اللي بتطبعوا فيها؟",
         "PLA للديكور والهدايا والمجسّمات ومعظم الأغراض اليومية؛ PETG للقطع اللي بدها تكون أقوى أو تتحمّل المي والشمس وشوية حرارة؛ TPU للأغراض المرنة متل الحمايات والمساكات. ما منطبع ABS أو ASA أو نايلون أو ريزن أو معدن."),
        ("فيكن تطبعوا بأكتر من لون؟",
         "الطباعة بلون واحد هي الأساس، بالألوان اللي عنا بالمخزون. إذا بدك أكتر من لون بنفس القطعة اسألنا على واتساب ومنقلّك شو بيزبط لموديلك."),
        ("قدّيش بياخد الطلب وقت؟",
         "التسعير الفوري بيورجيك وقت طباعة القطعة. منأكّدلك تاريخ التسليم على واتساب قبل ما نبلّش، حسب الطلبات اللي قبلك. التوصيل بالبريد السريع جوّا لبنان بياخد عادةً من يوم لـ3 أيام بعدها."),
        ("كيف بدفع؟",
         "كاش عند التسليم أو عبر Whish Money. الأسعار بالدولار الأميركي. للطلبات الكبيرة فينا نطلب جزء من السعر سلف عبر Whish، ومنقلّك قبل الطباعة."),
        ("بتوصّلوا لبرّا بيروت؟",
         "إيه، لكل لبنان بالبريد السريع، والدفع عند الاستلام. أجرة التوصيل (عادةً حوالي 4–5 دولار) بتنزاد عالطلب. وفيك كمان تستلم بنفسك أو نتّفق على تسليم باليد."),
        ("بتبعتوا لبرّا لبنان؟",
         "فينا نسعّرلك الشحن لبرّا، بس لقطعة صغيرة وحدة الشحن غالبًا بيكلّف أكتر من الطباعة نفسها. بيكون منطقي للطلبات الأكبر؛ ابعتلنا بلدك ومنسعّرلك."),
        ("فيكن تنسخوا أو تصلّحوا قطعة مكسورة؟",
         "بأغلب الأحيان إيه. ابعت صورة القطعة حدّ مسطرة، مع قياساتها وشو بتعمل. المقابض والكبّاسات والأغطية والحوامل البسيطة بتزبط منيح؛ القطع اللي بتحمل تقل كبير أو بتسخن (فوق حوالي 70 درجة) ما بتزبط."),
        ("ملفي بأمان معكن؟",
         "التسعير الفوري بيقرا الملف جوّا متصفّحك، وما بينرفع إلا إذا بعتت طلب. منستعمل ملفك بس لطباعة طلبك وما منشاركو ولا منبيعو."),
        ("في شي ما بتطبعوه؟",
         "منطبع بس الملفات اللي إلك حق تستعملها، وما منطبع أسلحة أو قطع أسلحة أو أي شي هدفو الأذى."),
    ],
}


def faq_ld(lang):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ[lang]]}


def faq_html(lang, items):
    return "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in items)


def example_cards(lang):
    t = L[lang]
    out = []
    for slug, mat, en, ar, en_d, ar_d in EXAMPLES:
        x = EX[slug]
        sz = " × ".join(f"{v:.0f}" for v in x["m"]["size_mm"])
        name, d = (ar, ar_d) if lang == "ar" else (en, en_d)
        about = "حوالي" if lang == "ar" else "about"
        meta = f"{mat} · <bdi dir=\"ltr\">{sz} mm</bdi> · <bdi dir=\"ltr\">{x['q']['grams']:.0f} g</bdi>"
        cta = "جرّب سعرو بالتسعير الفوري ←" if lang == "ar" else "Price it in the instant quote →"
        batch = ""
        if x["q"]["total"] <= P["min_order"]:  # small pieces hit the minimum; show what a batch of 10 costs
            ten = price(x["m"], mat, qty=10)["total"]
            batch = f' <span class="meta">· {"10 قطع حوالي" if lang == "ar" else "10 for about"} {money(ten)}</span>'
        out.append(f"""<article class="card">
<img src="{href(f'/assets/img/{slug}.webp')}" width="800" height="600" alt="{e(name)}: {e(t['render_note'])}" loading="lazy">
<div class="body"><h3>{e(name)}</h3><p>{e(d)}</p><div class="meta">{meta}</div>
<div class="price">{about} {pr(slug)}{batch}</div>
<a class="try" href="{href(lp(lang, '/quote/'))}?try={slug}">{cta}</a></div>
<div class="label">{e(t['render_note'])}</div></article>""")
    return '<div class="grid">' + "".join(out) + "</div>"


def formula_block(lang):
    m = P["materials"]
    if lang == "ar":
        return f"""<div class="formula">price = grams × rate + print hours × {money(P['per_hour'])} + {money(P['handling'])} (min {money(P['min_order'])})</div>
<div class="tablewrap" style="margin-top:14px"><table><tr><th>المادة</th><th>للغرام</th><th>بتنفع لـ</th></tr>
<tr><td>PLA</td><td>{money(m['PLA']['per_gram'])}</td><td>هدايا، ديكور، مجسّمات، أغراض يومية</td></tr>
<tr><td>PETG</td><td>{money(m['PETG']['per_gram'])}</td><td>قطع أقوى، مي، شمس، حرارة خفيفة</td></tr>
<tr><td>TPU</td><td>{money(m['TPU']['per_gram'])}</td><td>أغراض مرنة: حمايات، مساكات</td></tr></table></div>
<p class="note">الغرامات = حجم القطعة (الجدران الخارجية + نسبة الحشوة من الداخل) × كثافة المادة، مع {round((P['waste_factor'] - 1) * 100)}% للدعامات والهدر. الأرقام تقديرية، ومنأكّد السعر النهائي على واتساب قبل الطباعة.</p>"""
    return f"""<div class="formula">price = grams × rate + print hours × {money(P['per_hour'])} + {money(P['handling'])} (min {money(P['min_order'])})</div>
<div class="tablewrap" style="margin-top:14px"><table><tr><th>Material</th><th>Per gram</th><th>Good for</th></tr>
<tr><td>PLA</td><td>{money(m['PLA']['per_gram'])}</td><td>Gifts, decor, models, everyday objects</td></tr>
<tr><td>PETG</td><td>{money(m['PETG']['per_gram'])}</td><td>Tougher parts, water, sun, mild heat</td></tr>
<tr><td>TPU</td><td>{money(m['TPU']['per_gram'])}</td><td>Flexible things: bumpers, grips</td></tr></table></div>
<p class="note">Grams = the model's volume (outer walls plus your infill share of the inside) × the material's density, plus {round((P['waste_factor'] - 1) * 100)}% for supports and waste. It's an estimate: we confirm the final price on WhatsApp before printing.</p>"""


def home(lang):
    ar = lang == "ar"
    if ar:
        body = f"""<section class="hero"><div class="wrap"><div>
<span class="eyebrow">طباعة ثلاثية الأبعاد · لبنان</span>
<h1>منطبعلك ياها، وبتعرف سعرها قبل ما تسأل.</h1>
<p class="lead">حمّل ملف STL أو 3MF وبتشوف السعر التقديري بثواني. منطبع على Bambu Lab A1 Mini بالـPLA والـPETG والـTPU، ومنوصّل لكل لبنان.</p>
<div class="btns"><a class="btn primary" href="{href('/ar/quote/')}">احسب السعر هلّق</a>{wa_btn(lang, where='hero')}</div>
<div class="answer" style="margin-top:22px"><p><strong>قدّيش بتكلّف؟</strong> {money(P['materials']['PLA']['per_gram'])} للغرام PLA + {money(P['per_hour'])} لساعة الطباعة + {money(P['handling'])} للطلب، والحد الأدنى {money(P['min_order'])}. ميدالية أرزة حوالي {pr('cedar-keychain')}، ستاند تلفون حوالي {pr('phone-stand')}.</p></div>
</div><div class="hero-art"><img src="{href('/assets/img/phone-stand.webp')}" width="800" height="600" alt="ستاند تلفون: {e(L[lang]['render_note'])}"><span class="tag">{e(L[lang]['render_note'])}</span></div></div></section>

<section class="alt" id="print"><div class="wrap">
<h2>شو منطبع</h2>
<p>قطع بديلة، هدايا بأسماء، أغراض للمكتب والبيت، أغراض لبنانية، ومجسّمات من ملفاتك. هول أمثلة رسمناها نحنا؛ الأسعار محسوبة بنفس المعادلة اللي بالتسعير الفوري. صور الطلبات الحقيقية جايي قريبًا.</p>
{example_cards(lang)}
</div></section>

<section><div class="wrap">
<h2>كيف بتمشي</h2>
<ol class="steps">
<li><h3>ابعت ملف أو فكرة</h3><p>حمّل ملفك بالتسعير الفوري، أو اوصفلنا شو بدّك بطلب خاص (صورة، رسمة، قياسات).</p></li>
<li><h3>منأكّد على واتساب</h3><p>منراجع الملف ومنأكّدلك السعر النهائي واللون وتاريخ التسليم. ما منطبع قبل موافقتك.</p></li>
<li><h3>منطبع ومنسلّم</h3><p>استلام باليد أو توصيل لكل لبنان، والدفع كاش عند الاستلام أو عبر Whish.</p></li>
</ol></div></section>

<section class="alt"><div class="wrap prose">
<h2>الأسعار بالتفصيل</h2>
{formula_block(lang)}
<p><a href="{href('/ar/quote/')}">جرّب التسعير الفوري</a> · <a href="{href('/ar/delivery/')}">التوصيل والدفع</a></p>
</div></section>

<section><div class="wrap prose">
<h2>شو ما منعمل (لنكون واضحين)</h2>
<ul>
<li>قطعة وحدة أكبر من 180 ملم بأي اتجاه (منقسمها قطع إذا بيزبط).</li>
<li>ABS أو ASA أو نايلون أو ريزن أو معدن: طابعتنا مش مسكّرة وهي FDM. التفاصيل الصغيرة كتير (متل مجسّمات 2 سم) بيبيّن فيها خطوط الطبقات.</li>
<li>قطع بتسخن فوق حوالي 70 درجة أو بتحمل أوزان كبيرة.</li>
</ul>
<h2>أسئلة سريعة</h2>
{faq_html(lang, FAQ[lang][:4])}
<p><a href="{href('/ar/faq/')}">كل الأسئلة ←</a></p>
<h2>برّا لبنان؟</h2>
<p>فينا نسعّرلك الشحن، بس لقطعة صغيرة الشحن بيكلّف أكتر من الطباعة. للطلبات الأكبر <a href="{href('/ar/request/')}">ابعتلنا طلب</a>.</p>
</div></section>"""
        title = "تلاتة: طباعة ثلاثية الأبعاد بلبنان مع تسعير فوري | Tlete"
        desc = f"طباعة ثلاثية الأبعاد بلبنان: حمّل ملف STL وبتعرف السعر بثواني. PLA وPETG وTPU، من {money(P['min_order'])}، توصيل لكل لبنان والدفع عند الاستلام أو Whish."
    else:
        body = f"""<section class="hero"><div class="wrap"><div>
<span class="eyebrow">3D printing · Lebanon</span>
<h1>3D printing in Lebanon, priced before you ask.</h1>
<p class="lead">Upload an STL or 3MF and see an estimated price in seconds. We print on a Bambu Lab A1 Mini in PLA, PETG and TPU, and deliver anywhere in Lebanon.</p>
<div class="btns"><a class="btn primary" href="{href('/quote/')}">Get an instant quote</a>{wa_btn(lang, where='hero')}</div>
<div class="answer" style="margin-top:22px"><p><strong>How much?</strong> {money(P['materials']['PLA']['per_gram'])} per gram of PLA + {money(P['per_hour'])} per print hour + {money(P['handling'])} per order, minimum {money(P['min_order'])}. A cedar keychain is about {pr('cedar-keychain')}, a phone stand about {pr('phone-stand')}.</p></div>
</div><div class="hero-art"><img src="{href('/assets/img/phone-stand.webp')}" width="800" height="600" alt="Phone stand: {e(L[lang]['render_note'])}"><span class="tag">{e(L[lang]['render_note'])}</span></div></div></section>

<section class="alt" id="print"><div class="wrap">
<h2>What we print</h2>
<p>Replacement parts, personalised gifts, desk and home objects, Lebanon-themed pieces, and models from your own files. These are examples we designed ourselves, priced with the same formula as the instant quote. Photos of real orders are coming soon.</p>
{example_cards(lang)}
</div></section>

<section><div class="wrap">
<h2>How it works</h2>
<ol class="steps">
<li><h3>Send a file or an idea</h3><p>Upload your model to the instant quote, or describe what you need in a custom request (photo, sketch, measurements).</p></li>
<li><h3>We confirm on WhatsApp</h3><p>We check the file and confirm the final price, colour and ready date. Nothing prints until you say yes.</p></li>
<li><h3>We print and hand it over</h3><p>Pick up, hand-over, or courier anywhere in Lebanon. Pay cash on delivery or with Whish.</p></li>
</ol></div></section>

<section class="alt"><div class="wrap prose">
<h2>Prices, in full</h2>
{formula_block(lang)}
<p><a href="{href('/quote/')}">Try the instant quote</a> · <a href="{href('/delivery/')}">Delivery & payment</a></p>
</div></section>

<section><div class="wrap prose">
<h2>What we don't do (so you know upfront)</h2>
<ul>
<li>Single pieces bigger than 180 mm in any direction (we can split them into parts when that works).</li>
<li>ABS, ASA, nylon, resin or metal: our printer is an open FDM machine. Very fine detail (2 cm figurines) shows layer lines.</li>
<li>Parts that get hotter than about 70 °C or carry heavy loads.</li>
</ul>
<h2>Quick answers</h2>
{faq_html(lang, FAQ[lang][:4])}
<p><a href="{href('/faq/')}">All questions →</a></p>
<h2>Outside Lebanon?</h2>
<p>We can quote courier shipping, but for one small print it usually costs more than the print. For bigger orders, <a href="{href('/request/')}">send us a request</a>.</p>
</div></section>"""
        title = "Tlete: 3D printing in Lebanon with an instant quote"
        desc = f"3D printing in Lebanon: upload an STL and see your price in seconds. PLA, PETG and TPU from {money(P['min_order'])}, delivery anywhere in Lebanon, cash on delivery or Whish."
    page(lang, "/", title, desc, body, ld=[business_ld(lang), service_ld(lang), products_ld(lang)])


def request_form(lang, with_file):
    ar = lang == "ar"
    f = lambda en, a: a if ar else en  # noqa: E731
    file_field = f'<label>{f("File (STL, 3MF, OBJ, photo or sketch, optional)", "ملف (STL أو 3MF أو OBJ أو صورة أو رسمة، اختياري)")}<input type="file" name="file" accept=".stl,.3mf,.obj,image/*,.pdf"></label>' if with_file else ""
    email_req = "required" if S["form"].get("emailRequired") else ""
    return f"""<form id="reqform" class="stack panel" {'hidden' if not with_file else ''} novalidate>
<h2 style="margin:0">{f("Send this to Tlete", "ابعت الطلب لتلاتة")}</h2>
<p class="note" style="margin:0">{f("We reply on WhatsApp with the final price and ready date. Nothing prints until you confirm.", "منردّ عليك على واتساب بالسعر النهائي وتاريخ التسليم. ما منطبع شي قبل ما توافق.")}</p>
<label>{f("Your name", "اسمك")}<input name="name" autocomplete="name" required maxlength="120"></label>
<label>{f("WhatsApp number", "رقم الواتساب")}<input name="phone" type="tel" autocomplete="tel" inputmode="tel" required placeholder="+961 …" dir="ltr"></label>
<label>{f("Email" + (" (we send the quote here too)" if email_req else " (optional)"), "البريد الإلكتروني" + (" (منبعتلك السعر عليه كمان)" if email_req else " (اختياري)"))}<input name="email" type="email" autocomplete="email" {email_req} dir="ltr"></label>
<label>{f("City or area", "المدينة أو المنطقة")}<input name="city" autocomplete="address-level2" maxlength="80"></label>
<label>{f("Delivery", "التسليم")}<select name="delivery"><option value="courier">{f("Courier, cash on delivery", "توصيل، دفع عند الاستلام")}</option><option value="pickup">{f("Pick-up / hand-over", "استلام باليد")}</option><option value="abroad">{f("Outside Lebanon (quote shipping)", "برّا لبنان (سعّرولي الشحن)")}</option></select></label>
{file_field}
<label>{f("What do you need?" if with_file else "Anything we should know? (colour, deadline, use)", "شو بدّك بالضبط؟" if with_file else "في شي لازم نعرفو؟ (اللون، الموعد، الاستعمال)")}<textarea name="notes" maxlength="1800" {'required' if with_file else ''} placeholder="{f('e.g. a replacement knob for a Beko oven, 35 mm wide, black', 'مثلًا: مقبض بديل لفرن Beko، عرضو 35 ملم، أسود') if with_file else ''}"></textarea></label>
<label class="hp" aria-hidden="true">Website<input name="website" tabindex="-1" autocomplete="off"></label>
<button class="btn primary" type="submit">{f("Send request", "ابعت الطلب")}</button>
<div class="form-status" role="status" aria-live="polite"></div>
<p class="note">{f("We use these details only to answer this request.", "منستعمل هالمعلومات بس لنرد على طلبك.")} <a href="{href(lp(lang, '/privacy/'))}">{f("Privacy", "الخصوصية")}</a></p>
</form>
<div id="reqdone" class="done" hidden role="status">
<h2 style="margin-top:0">{f("Got it, thank you!", "وصلنا طلبك، شكرًا!")}</h2>
<p>{f("Your request number is", "رقم طلبك")} <strong class="ref"></strong>. {f("We reply on WhatsApp, usually the same day.", "منردّ عليك على واتساب، عادةً بنفس النهار.")}</p>
<p class="need-file" hidden><strong>{f("One more step: send us the file on WhatsApp so we can check it.", "خطوة بعد: ابعتلنا الملف على واتساب لنشيّك عليه.")}</strong></p>
<a class="btn wa" data-where="request_done" href="https://wa.me/{WA}" target="_blank" rel="noopener">{WA_ICON}{f("Open WhatsApp", "افتح واتساب")}</a>
</div>"""


def quote(lang):
    ar = lang == "ar"
    f = lambda en, a: a if ar else en  # noqa: E731
    ex_btns = "".join(f'<button type="button" data-example="{s}">{e(a if ar else n)}</button>' for s, _, n, a, *_ in EXAMPLES)
    mats = "".join(f'<option value="{k}">{k}</option>' for k in P["materials"])
    cn = {"black": ("Black", "أسود"), "white": ("White", "أبيض"), "grey": ("Grey", "رمادي"), "red": ("Red", "أحمر"), "blue": ("Blue", "أزرق"), "green": ("Green", "أخضر"), "yellow": ("Yellow", "أصفر"), "orange": ("Orange", "برتقالي")}
    cols = "".join(f'<option value="{c}">{cn[c][1] if ar else cn[c][0]}</option>' for c in P["colours"])
    infills = "".join(f'<option value="{i}"{" selected" if i == P["infill_default"] else ""}>{i}%{f(" (default)", " (عادي)") if i == P["infill_default"] else ""}</option>' for i in P["infills"])
    body = f"""<div class="wrap pagehead">
<h1>{f("Instant 3D printing quote", "تسعير فوري للطباعة الثلاثية الأبعاد")}</h1>
<p class="lead">{f("Drop your model, pick a material and see the estimated price, size and print time. The file stays on your device until you send a request.", "حطّ ملفك، نقّي المادة، وبتشوف السعر التقديري والحجم ووقت الطباعة. الملف بيضل على جهازك لحد ما تبعت الطلب.")}</p>
</div>
<section style="padding-top:8px"><div class="wrap">
<div class="drop" id="drop">
<p style="font-weight:700;font-size:1.1rem;margin:0">{f("Drop an STL, 3MF or OBJ file here", "حطّ ملف STL أو 3MF أو OBJ هون")}</p>
<input type="file" id="qfile" accept=".stl,.3mf,.obj">
<label for="qfile" class="btn primary">{f("Choose a file", "اختار ملف")}</label>
<p class="note" style="margin:0">{f("No file? Try an example:", "ما عندك ملف؟ جرّب مثال:")}</p>
<div class="examples">{ex_btns}</div>
<div id="qstatus" role="status" aria-live="polite"></div>
</div>

<div id="qresult" hidden>
<div class="qgrid">
<div class="panel">
<div id="qname"></div>
<canvas id="qview" aria-label="{f("3D preview of your model, drag to turn", "معاينة ثلاثية الأبعاد لموديلك، اسحب لتدوّرها")}"></canvas>
<div><strong>{f("Size", "الحجم")}:</strong> <span id="qsize" dir="ltr"></span></div>
<div id="qfit" class="fit"></div>
</div>
<div class="panel">
<form id="qopts" onsubmit="return false">
<div class="fields">
<label>{f("Material", "المادة")}<select name="material">{mats}</select></label>
<label>{f("Colour", "اللون")}<select name="colour">{cols}</select></label>
<label>{f("Infill", "الحشوة")}<select name="infill">{infills}</select></label>
<label>{f("Quality", "الجودة")}<select name="quality"><option value="draft">{f("Draft (0.28 mm)", "سريع (0.28 ملم)")}</option><option value="standard" selected>{f("Standard (0.20 mm)", "عادي (0.20 ملم)")}</option><option value="fine">{f("Fine (0.12 mm)", "ناعم (0.12 ملم)")}</option></select></label>
<label>{f("Quantity", "العدد")}<input name="qty" type="number" min="1" max="500" value="1" inputmode="numeric"></label>
<label>{f("Scale %", "الحجم %")}<input name="scale" type="number" min="1" max="1000" value="100" inputmode="decimal"></label>
<label>{f("File units", "وحدة الملف")}<select name="unit"><option value="1">mm</option><option value="10">cm</option><option value="25.4">inch</option></select></label>
</div>
</form>
<div class="total" id="qtotal"></div><div id="qper"></div>
<ul id="qbreak"></ul>
<p class="confirm">{f("Estimate only. We check your file and confirm the final price on WhatsApp before printing.", "سعر تقديري. منشيّك عالملف ومنأكّد السعر النهائي على واتساب قبل الطباعة.")}</p>
<div class="btns"><a id="qwa" class="btn wa" data-where="quote" href="https://wa.me/{WA}" target="_blank" rel="noopener">{WA_ICON}{f("Order on WhatsApp", "اطلب على واتساب")}</a>
<button id="qsend" class="btn ghost" type="button">{f("Send with my file", "ابعت مع الملف")}</button></div>
</div>
</div>
<div style="margin-top:22px">{request_form(lang, False)}</div>
</div>
</div></section>

<section class="alt"><div class="wrap prose">
<h2>{f("How the estimate is calculated", "كيف منحسب السعر")}</h2>
{formula_block(lang)}
<h2>{f("Tips for a good print", "نصايح لطباعة منيحة")}</h2>
<ul>
<li>{f("Export in millimetres. If the size looks 25× too small, switch the unit to inch.", "صدّر الملف بالملّيمتر. إذا الحجم طالع أصغر بـ25 مرّة، غيّر الوحدة لإنش.")}</li>
<li>{f("15% infill is fine for decor; use 25–50% for parts that take force.", "حشوة 15% بتكفي للديكور؛ استعمل 25–50% للقطع اللي بتتحمّل ضغط.")}</li>
<li>{f("Bigger than 180 mm? Scale it down, or ask us to split it into parts.", "أكبر من 180 ملم؟ صغّرو، أو اطلب منّا نقسمو قطع.")}</li>
<li>{f("No file yet?", "ما عندك ملف؟")} <a href="{href(lp(lang, '/request/'))}">{f("Send a custom request", "ابعت طلب خاص")}</a>.</li>
</ul>
</div></section>"""
    ld = [{"@context": "https://schema.org", "@type": "WebApplication", "name": f("Tlete instant 3D printing quote", "تسعير تلاتة الفوري"),
           "url": url(lp(lang, "/quote/")), "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any (web browser)",
           "offers": {"@type": "Offer", "price": 0, "priceCurrency": "USD"}, "provider": {"@id": url("/#business")}}, service_ld(lang)]
    page(lang, "/quote/", f("Instant 3D printing quote: upload STL, get a price | Tlete", "تسعير فوري للطباعة الثلاثية الأبعاد: حمّل STL وخود السعر | تلاتة"),
         f(f"Upload an STL, 3MF or OBJ and get an instant 3D printing price in Lebanon: size check for 180 mm, PLA, PETG or TPU, infill and quantity. From {money(P['min_order'])}.",
           f"حمّل ملف STL أو 3MF أو OBJ وخود سعر الطباعة الثلاثية الأبعاد بلبنان فورًا: فحص الحجم لـ180 ملم، PLA أو PETG أو TPU، الحشوة والعدد. من {money(P['min_order'])}."),
         body, ld=ld, scripts=["/assets/js/mesh.js", "/assets/js/quote.js"], crumbs=f("Instant quote", "تسعير فوري"))


def request_page(lang):
    ar = lang == "ar"
    f = lambda en, a: a if ar else en  # noqa: E731
    body = f"""<div class="wrap pagehead"><h1>{f("Custom 3D printing request", "طلب طباعة خاص")}</h1>
<p class="lead">{f("No 3D file? Tell us what you need: a broken part to copy, a gift with a name, a sign for your shop, or a batch for your business. Add a photo or sketch with measurements.", "ما عندك ملف ثلاثي الأبعاد؟ قلّنا شو بدّك: قطعة مكسورة لننسخها، هدية عليها اسم، يافطة لمحلّك، أو كمية لشغلك. زيد صورة أو رسمة مع القياسات.")}</p></div>
<section style="padding-top:8px"><div class="wrap">
{request_form(lang, True)}
</div></section>
<section class="alt"><div class="wrap prose">
<h2>{f("What helps us quote fast", "شو بيساعدنا نسعّر بسرعة")}</h2>
<ul>
<li>{f("A photo of the part next to a ruler, or its measurements in mm.", "صورة القطعة حدّ مسطرة، أو قياساتها بالملّيمتر.")}</li>
<li>{f("What it's for: decoration, a part that takes force, outdoor use, contact with water or heat.", "شو بتستعملها: ديكور، قطعة بتتحمّل ضغط، برّا البيت، مي أو حرارة.")}</li>
<li>{f("How many you need and by when.", "قدّيش بدّك منها وأيمتى.")}</li>
</ul>
<p>{f("Designing a model from scratch is quoted separately, depending on how complex it is. Simple parts usually cost little.", "رسم موديل من الصفر بيتسعّر لحالو حسب صعوبتو. القطع البسيطة عادةً ما بتكلّف كتير.")}</p>
<p>{f("Already have a file?", "عندك ملف؟")} <a href="{href(lp(lang, '/quote/'))}">{f("Use the instant quote", "استعمل التسعير الفوري")}</a>.</p>
</div></section>"""
    page(lang, "/request/", f("Custom 3D printing request in Lebanon: parts, gifts, signs | Tlete", "طلب طباعة ثلاثية الأبعاد خاص بلبنان: قطع، هدايا، يافطات | تلاتة"),
         f("No file? Send a photo, sketch or measurements: replacement parts, name gifts, shop signs and small batches, 3D printed in Lebanon. We reply on WhatsApp.",
           "ما عندك ملف؟ ابعت صورة أو رسمة أو قياسات: قطع بديلة، هدايا بأسماء، يافطات محلات وكميات صغيرة، مطبوعة بلبنان. منردّ على واتساب."),
         body, ld=[service_ld(lang)], crumbs=f("Custom request", "طلب خاص"))


def delivery(lang):
    ar = lang == "ar"
    f = lambda en, a: a if ar else en  # noqa: E731
    body = f"""<div class="wrap pagehead"><h1>{f("Delivery & payment", "التوصيل والدفع")}</h1>
<div class="answer"><p>{f("We deliver anywhere in Lebanon by courier (cash on delivery, the fee of about $4–5 is added to your order), or you pick up or meet us for a hand-over. Pay in US dollars, cash or Whish Money. Abroad: shipping quoted per order.", "منوصّل لكل لبنان بالبريد السريع (الدفع عند الاستلام، وأجرة التوصيل حوالي 4–5 دولار بتنزاد عالطلب)، أو بتستلم بنفسك أو منتلاقى ونسلّمك. الدفع بالدولار، كاش أو Whish Money. لبرّا لبنان: منسعّر الشحن حسب الطلب.")}</p></div></div>
<section><div class="wrap prose">
<h2>{f("Inside Lebanon", "جوّا لبنان")}</h2>
<div class="tablewrap"><table>
<tr><th>{f("Option", "الطريقة")}</th><th>{f("Cost", "الكلفة")}</th><th>{f("How it works", "كيف بتمشي")}</th></tr>
<tr><td>{f("Courier", "بريد سريع")}</td><td>{f("about $4–5, added to the order", "حوالي 4–5 دولار، بتنزاد عالطلب")}</td><td>{f("Anywhere in Lebanon, usually 1–3 days after printing. You pay the courier cash.", "لكل لبنان، عادةً يوم لـ3 أيام بعد الطباعة. بتدفع للموزّع كاش.")}</td></tr>
<tr><td>{f("Pick-up / hand-over", "استلام باليد")}</td><td>{f("free", "مجاني")}</td><td>{f("We agree a time and place on WhatsApp.", "منتّفق عالوقت والمحل على واتساب.")}</td></tr>
</table></div>
<h2>{f("Payment", "الدفع")}</h2>
<ul>
<li>{f("Cash on delivery or at hand-over (US dollars).", "كاش عند الاستلام أو التسليم (بالدولار).")}</li>
<li>{f("Whish Money: we send you the details or a payment link on WhatsApp.", "Whish Money: منبعتلك التفاصيل أو رابط دفع على واتساب.")}</li>
<li>{f("Larger orders: we may ask for part of the price upfront by Whish, and tell you before we print.", "للطلبات الكبيرة: فينا نطلب جزء من السعر سلف عبر Whish، ومنقلّك قبل ما نطبع.")}</li>
</ul>
<h2>{f("Outside Lebanon", "برّا لبنان")}</h2>
<p>{f("We can quote courier shipping (Aramex or DHL). Be aware that a small parcel abroad usually costs $25–45 plus your country's import fees, often more than the print itself, so it makes sense for bigger orders. Tell us your country in a request and we quote it. Digital design files you print yourself are coming later.", "فينا نسعّرلك الشحن (Aramex أو DHL). انتبه إنو طرد صغير لبرّا بيكلّف عادةً 25–45 دولار زائد رسوم الجمرك ببلدك، وغالبًا أكتر من الطباعة نفسها، فبيكون منطقي للطلبات الأكبر. قلّنا بلدك بطلب ومنسعّرلك. ملفات تصاميم رقمية تطبعها بنفسك جايي بعدين.")}</p>
<h2>{f("Before we print", "قبل الطباعة")}</h2>
<p>{f("Every order is confirmed on WhatsApp first: final price, colour, delivery and ready date. If a print fails on our side, we reprint it at our cost.", "كل طلب منأكّدو على واتساب بالأول: السعر النهائي، اللون، التوصيل وتاريخ التسليم. إذا فشلت الطباعة من عنّا، منعيدها على حسابنا.")}</p>
<div class="btns"><a class="btn primary" href="{href(lp(lang, '/quote/'))}">{f("Get an instant quote", "احسب السعر")}</a>{wa_btn(lang, where='delivery')}</div>
</div></section>"""
    page(lang, "/delivery/", f("Delivery & payment: courier across Lebanon, cash or Whish | Tlete", "التوصيل والدفع: لكل لبنان، كاش أو Whish | تلاتة"),
         f("How Tlete delivers 3D prints: courier anywhere in Lebanon with cash on delivery, free hand-over, Whish Money, and shipping abroad quoted per order.",
           "كيف بتوصّل تلاتة الطباعة: لكل لبنان والدفع عند الاستلام، تسليم باليد مجاني، Whish Money، والشحن لبرّا حسب الطلب."),
         body, ld=[business_ld(lang)], crumbs=f("Delivery & payment", "التوصيل والدفع"))


def faq(lang):
    ar = lang == "ar"
    f = lambda en, a: a if ar else en  # noqa: E731
    body = f"""<div class="wrap pagehead"><h1>{f("3D printing questions, answered", "أسئلة عن الطباعة الثلاثية الأبعاد")}</h1></div>
<section style="padding-top:8px"><div class="wrap prose">{faq_html(lang, FAQ[lang])}
<p>{f("Didn't find your answer?", "ما لقيت جوابك؟")} {wa_btn(lang, cls='', where='faq', label=f('Ask us on WhatsApp', 'اسألنا على واتساب'))}</p></div></section>"""
    page(lang, "/faq/", f("3D printing in Lebanon: prices, files, sizes, delivery (FAQ) | Tlete", "الطباعة الثلاثية الأبعاد بلبنان: أسعار، ملفات، أحجام، توصيل | تلاتة"),
         f("Answers about 3D printing in Lebanon: how much it costs, which files work, the 180 mm size limit, PLA vs PETG vs TPU, payment and delivery.",
           "أجوبة عن الطباعة الثلاثية الأبعاد بلبنان: قدّيش بتكلّف، أي ملفات، حد الـ180 ملم، PLA وPETG وTPU، الدفع والتوصيل."),
         body, ld=[faq_ld(lang)], crumbs=f("FAQ", "أسئلة شائعة"))


def privacy(lang):
    ar = lang == "ar"
    f = lambda en, a: a if ar else en  # noqa: E731
    body = f"""<div class="wrap pagehead prose"><h1>{f("Privacy", "الخصوصية")}</h1>
<p>{f("The instant quote reads your 3D file inside your browser. It is not uploaded anywhere unless you send a request.", "التسعير الفوري بيقرا ملفك جوّا متصفّحك، وما بينرفع لأي محل إلا إذا بعتت طلب.")}</p>
<p>{f("When you send a request we store what you typed (name, WhatsApp number, email, city, notes, the quote details and, where supported, the file) for up to one year, only to answer and fulfil your order. We never sell or share it.", "لمّا تبعت طلب منحفظ اللي كتبتو (الاسم، رقم الواتساب، البريد، المدينة، الملاحظات، تفاصيل السعر، والملف إذا انبعت) لسنة كحد أقصى، بس لنرد عليك وننفّذ طلبك. ما منبيعو ولا منشاركو.")}</p>
<p>{f("We use Google Analytics to count visits and actions such as quotes and WhatsApp clicks. It does not receive your file or your form details.", "منستعمل Google Analytics لنعدّ الزيارات والأفعال متل التسعير وكبس واتساب. ما بيوصلو ملفك ولا معلومات النموذج.")}</p>
<p>{f("To have your data deleted, message us on WhatsApp.", "لتمحي معلوماتك، راسلنا على واتساب.")}</p></div>"""
    page(lang, "/privacy/", f("Privacy | Tlete", "الخصوصية | تلاتة"), f("How Tlete handles your 3D files, quotes and contact details: what we store, for how long, and how to have it deleted.", "كيف بتتعامل تلاتة مع ملفاتك ومعلومات التواصل: شو منحفظ، لقدّيش، وكيف تمحيها."), body, crumbs=f("Privacy", "الخصوصية"))


def not_found():
    body = f"""<div class="wrap pagehead prose"><h1>Page not found · الصفحة مش موجودة</h1>
<p><a href="{href('/')}">Home</a> · <a href="{href('/quote/')}">Instant quote</a> · <a href="{href('/ar/')}">الرئيسية</a></p></div>"""
    page("en", "/404", "Page not found | Tlete", "This page doesn't exist. Try the Tlete instant 3D printing quote or the home page.", body)
    p = OUT_ROOT / "404.html"
    p.write_text(p.read_text().replace('<link rel="canonical"', '<meta name="robots" content="noindex"><link rel="canonical"', 1))


def extras():
    pages = ["/", "/quote/", "/request/", "/delivery/", "/faq/", "/privacy/"]
    urls = []
    for pth in pages:
        for lang in ("en", "ar"):
            u = url(lp(lang, pth))
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{l2}" href="{url(lp(l2, pth))}"/>' for l2 in ("en", "ar"))
            urls.append(f"<url><loc>{u}</loc><lastmod>{TODAY}</lastmod>{alts}</url>")
    (OUT_ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(urls) + "\n</urlset>\n")
    (OUT_ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {url('/sitemap.xml')}\n")
    m = P["materials"]
    (OUT_ROOT / "llms.txt").write_text(f"""# Tlete (تلاتة)

> 3D printing on demand in Lebanon, with an instant online quote. One Bambu Lab A1 Mini printer; PLA, PETG and TPU; max 180 × 180 × 180 mm per piece. English and Arabic.

- Price formula: grams × rate (PLA {money(m['PLA']['per_gram'])}/g, PETG {money(m['PETG']['per_gram'])}/g, TPU {money(m['TPU']['per_gram'])}/g) + print hours × {money(P['per_hour'])} + {money(P['handling'])} handling per order; minimum order {money(P['min_order'])}. Final price confirmed on WhatsApp.
- Delivery: courier anywhere in Lebanon (cash on delivery, about $4–5), free hand-over or pick-up. Payment: cash or Whish Money. Abroad: shipping quoted per order.
- Orders: WhatsApp +{WA}

## Pages
- [Instant quote]({url('/quote/')}): upload STL/3MF/OBJ, size check, material, infill, quantity, estimated price
- [Custom request]({url('/request/')}): no file, photos/sketches/measurements, replacement parts, gifts, signs
- [Delivery & payment]({url('/delivery/')})
- [FAQ]({url('/faq/')})
- [Arabic home]({url('/ar/')})
""")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT_ROOT.mkdir(parents=True)
    shutil.copytree(ROOT / "assets", OUT_ROOT / "assets")
    for lang in ("en", "ar"):
        home(lang)
        quote(lang)
        request_page(lang)
        delivery(lang)
        faq(lang)
        privacy(lang)
    not_found()
    extras()
    if not BASE:
        cname = ROOT / "CNAME"
        if cname.exists():
            shutil.copy(cname, OUT / "CNAME")
    n = len(list(OUT.rglob("*.html")))
    print(f"built {n} pages into {OUT_ROOT.relative_to(ROOT)}")
    for slug, x in EX.items():
        print(f"  {slug}: {x['mat']} {x['q']['grams']:.1f} g {x['q']['hours']:.2f} h -> {money(x['q']['total'])}")


if __name__ == "__main__":
    import sys
    if "--print-root" in sys.argv:  # the folder GitHub Pages should publish
        print(OUT_ROOT.relative_to(ROOT))
    else:
        main()
