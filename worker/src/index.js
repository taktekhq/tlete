// Tlete forms Worker: stores quote and custom requests (with the 3D file, up to 8 MB) in KV.
// POST /api/request (JSON). Anonymous log line per request; no IPs stored (hashed, daily salt, rate limit only).
const ALLOWED = ["https://taktek.io", "https://tlete3d.com", "https://www.tlete3d.com", "http://127.0.0.1:8124", "http://localhost:8124"];
const MAX_FILE = 8 * 1024 * 1024;
const LIMIT_PER_DAY = 10; // requests per IP per day

function cors(req) {
  const o = req.headers.get("origin");
  return { "access-control-allow-origin": ALLOWED.includes(o) ? o : ALLOWED[0], "access-control-allow-methods": "POST,OPTIONS", "access-control-allow-headers": "content-type", vary: "origin" };
}
const json = (req, body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...cors(req) } });

async function sha(s) {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(b)].slice(0, 8).map(x => x.toString(16).padStart(2, "0")).join("");
}
const str = (v, n) => String(v ?? "").trim().slice(0, n);

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(req) });
    if (url.pathname === "/") return json(req, { name: "tlete forms" });
    if (url.pathname !== "/api/request" || req.method !== "POST") return json(req, { error: "not_found" }, 404);
    if (!ALLOWED.includes(req.headers.get("origin") || "")) return json(req, { error: "forbidden" }, 403);
    if (+(req.headers.get("content-length") || 0) > MAX_FILE * 1.4 + 64 * 1024) return json(req, { error: "too_large" }, 413);

    let b; try { b = await req.json(); } catch { return json(req, { error: "bad_request" }, 400); }
    if (b.website) return json(req, { ok: true }); // honeypot
    const phone = str(b.phone, 40).replace(/[^\d+]/g, "");
    const email = str(b.email, 200);
    if (!str(b.name, 120) || phone.replace(/\D/g, "").length < 7 || (email && !/^[^@\s]{1,100}@[^@\s]+\.[^@\s]{2,}$/.test(email))) return json(req, { error: "bad_request" }, 400);

    const day = Math.floor(Date.now() / 8.64e7);
    const k = `rl:${await sha((req.headers.get("cf-connecting-ip") || "?") + ":" + day + ":" + (env.SALT || "tlete"))}:${day}`;
    const n = parseInt((await env.KV.get(k)) || "0", 10) + 1;
    if (n > LIMIT_PER_DAY) return json(req, { error: "rate_limited" }, 429);
    await env.KV.put(k, String(n), { expirationTtl: 172800 });

    const at = new Date().toISOString();
    const ref = str(b.ref, 12).replace(/[^A-Z0-9]/gi, "") || at;
    let file = null;
    if (b.file && b.file.b64) {
      const bytes = Uint8Array.from(atob(String(b.file.b64)), c => c.charCodeAt(0));
      if (bytes.length > MAX_FILE) return json(req, { error: "too_large" }, 413);
      const key = `file:${at}:${ref}`;
      await env.KV.put(key, bytes, { expirationTtl: 365 * 86400, metadata: { name: str(b.file.name, 120), type: str(b.file.type, 80), size: bytes.length } });
      file = { key, name: str(b.file.name, 120), size: bytes.length };
    }
    const q = b.quote && typeof b.quote === "object" ? b.quote : null;
    const rec = {
      kind: b.kind === "quote" ? "quote" : "custom", ref, name: str(b.name, 120), phone, email, city: str(b.city, 80), delivery: str(b.delivery, 20),
      notes: str(b.notes, 2000), lang: b.lang === "ar" ? "ar" : "en", quote: q && JSON.parse(JSON.stringify(q).slice(0, 2000)), file,
      country: req.cf?.country || null, at,
    };
    await env.KV.put(`req:${at}:${ref}`, JSON.stringify(rec), { expirationTtl: 365 * 86400 });
    console.log(JSON.stringify({ evt: "tlete_request", kind: rec.kind, material: q?.material || null, est: q?.total_usd || null, has_file: !!file, lang: rec.lang, country: rec.country }));
    return json(req, { ok: true, ref });
  },
};
