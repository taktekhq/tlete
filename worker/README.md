# tlete-forms Worker

Stores requests from the Tlete site (quote + custom request, with the customer's file up to 8 MB) in KV.

Until it is deployed, the site posts to the shared Taktek forms Worker (`taktek-audit`, `source: "work"`, package "Tlete 3D: …"): no file upload, email required, and the customer is asked to send the file on WhatsApp.

## Deploy (Mac, needs the Cloudflare token)
```sh
cd worker
npx wrangler kv namespace create TLETE        # paste the id into wrangler.toml
npx wrangler deploy                            # -> https://tlete-forms.<account>.workers.dev
```
Then in `data/site.json` set `form.url` to `https://tlete-forms.<account>.workers.dev/api/request`, `form.mode` to `tlete`, `form.emailRequired` to `false`, push.

## Read requests
```sh
npx wrangler kv key list --namespace-id <id> --prefix req:
npx wrangler kv key get --namespace-id <id> "req:<at>:<ref>"
npx wrangler kv key get --namespace-id <id> "file:<at>:<ref>" > model.stl
```
Logs: one anonymous `tlete_request` line per request (kind, material, estimate, has_file, lang, country) in Workers observability.
