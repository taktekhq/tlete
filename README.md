# Tlete (تلاتة): 3D printing in Lebanon

Static site for Tlete, a one-printer 3D-printing studio in Lebanon (Bambu Lab A1 Mini). It is English and Arabic, with an instant quote: drop an STL/3MF/OBJ and it is measured, size-checked against the 180 mm bed and priced from a transparent formula, all in the browser.

Preview: https://taktek.io/tlete/ (until tlete3d.com is bought).

## Build
```sh
python3 tools/make_examples.py   # only when the example models change (writes assets/models + assets/img)
python3 build.py                 # writes site/tlete/
python3 tools/check.py           # SEO tags, JSON-LD, links, AR twins, JS/Python price parity (needs node)
python3 -m http.server -d site 8124   # http://localhost:8124/tlete/
```
GitHub Actions builds, checks and deploys to Pages on every push to main.

## Where things live
- `data/pricing.json`: the price formula (rates, minimum, materials, colours). It is shown on the pages and used by the quote.
- `data/site.json`: URL, base path, WhatsApp number, GA4 id, forms endpoint.
- `assets/js/mesh.js`: STL/OBJ/3MF parsing, volume/area/size, `price()`. `quote.js` holds the quote UI and viewer, `site.js` the menu, WhatsApp tracking and request form.
- `worker/`: the `tlete-forms` Cloudflare Worker (stores requests and files in KV). Not deployed yet; see worker/README.md.
- GA4 events: `quote_calculated`, `request_sent`, `whatsapp_click`.

## Moving to tlete3d.com
1. Buy the domain, then point DNS at GitHub Pages (A records 185.199.108-111.153, `www` CNAME taktekhq.github.io).
2. `data/site.json`: `site_url` = `https://tlete3d.com`, `base_path` = `""`. Add a `CNAME` file containing `tlete3d.com`. In repo Settings → Pages set the custom domain and enforce HTTPS.
3. Add the domain to the forms Worker's `ALLOWED` list (the shared taktek-audit Worker too, while it is in use).
4. Resubmit the sitemap in Search Console and Bing, and ping IndexNow.

The example images are renders of models we designed in code (`tools/make_examples.py`), labelled as such. Replace them with real photos of real prints once they exist.
