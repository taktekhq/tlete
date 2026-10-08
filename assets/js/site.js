/* Tlete: menu, WhatsApp click tracking, request form. */
(function () {
  "use strict";
  const AR = document.documentElement.lang === "ar";
  const $ = s => document.querySelector(s);

  const menu = $("#menu-btn");
  if (menu) menu.addEventListener("click", () => {
    const open = document.body.classList.toggle("menu-open");
    menu.setAttribute("aria-expanded", open ? "true" : "false");
  });

  // Every WhatsApp link counts, wherever it sits on the page.
  document.addEventListener("click", e => {
    const a = e.target.closest && e.target.closest("a[href*='wa.me/']");
    if (a && window.gtag) gtag("event", "whatsapp_click", { link_location: a.dataset.where || "page", page_path: location.pathname });
  });

  const form = $("#reqform");
  if (!form) return;
  const T = AR ? {
    sending: "عم نبعت…", fail: "ما زبط الإرسال. ابعتلنا على واتساب بدل.", phone: "اكتب رقم واتساب صحيح.", email: "اكتب بريد إلكتروني صحيح.",
    wa: "مرحبا Tlete، بعتت طلب من الموقع. رقم الطلب:", file: "ملف", big: "الملف أكبر من 8 ميغابايت: ابعتو على واتساب بعد ما تبعت الطلب.",
  } : {
    sending: "Sending…", fail: "That didn't go through. Please message us on WhatsApp instead.", phone: "Please enter a valid WhatsApp number.", email: "Please enter a valid email.",
    wa: "Hi Tlete, I sent a request on your website. Request:", file: "File", big: "That file is over 8 MB: send it on WhatsApp after you submit.",
  };
  const cfg = window.TLETE_FORM;
  const status = form.querySelector(".form-status");

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(form).entries());
    const phone = String(d.phone || "").replace(/[^\d+]/g, "");
    if (phone.replace(/\D/g, "").length < 7) return say(T.phone, true);
    const email = String(d.email || "").trim();
    if ((cfg.emailRequired || email) && !/^[^@\s]{1,100}@[^@\s]+\.[^@\s]{2,}$/.test(email)) return say(T.email, true);

    const quote = window.TleteQuote && window.TleteQuote.current;
    const fileInput = form.querySelector("input[type=file]");
    const file = (window.TleteQuote && window.TleteQuote.file) || (fileInput && fileInput.files[0]) || null;
    const kind = quote ? "quote" : "custom";
    const ref = "T" + Date.now().toString(36).toUpperCase().slice(-6);
    const summary = [
      "Ref " + ref, "Lang " + (AR ? "ar" : "en"),
      quote ? `Quote: ${quote.file} | ${quote.size_mm.join("x")} mm | ${quote.filament} | infill ${quote.infill}% | ${quote.quality} | qty ${quote.qty} | ~${quote.grams} g, ~${quote.hours} h | est $${quote.total_usd}${quote.fits ? "" : " | DOES NOT FIT 180mm"}` : "",
      file ? `File: ${file.name} (${Math.round(file.size / 1024)} KB)` : "File: none",
      d.city ? "City: " + d.city : "", d.delivery ? "Delivery: " + d.delivery : "",
      "Notes: " + (d.notes || ""),
    ].filter(Boolean).join("\n");

    say(T.sending);
    form.querySelector("button[type=submit]").disabled = true;
    let ok = false, uploaded = false;
    try {
      let body;
      if (cfg.mode === "tlete") {
        let fileData = null;
        if (file && file.size <= 8 * 1024 * 1024) { fileData = { name: file.name, type: file.type || "application/octet-stream", b64: await b64(file) }; uploaded = true; }
        body = { kind, ref, name: d.name, phone, email, city: d.city || "", delivery: d.delivery || "", notes: d.notes || "", lang: AR ? "ar" : "en", quote, file: fileData, website: d.website || "" };
      } else {
        // Interim: the shared Taktek forms Worker (stores to KV, no file upload). The file follows on WhatsApp.
        body = { source: "work", package: "Tlete 3D: " + kind, business: String(d.name || "").slice(0, 160) || "Tlete customer", where: (phone + (d.city ? " / " + d.city : "")).slice(0, 300), email, notes: summary.slice(0, 2000), website: d.website || "" };
      }
      const r = await fetch(cfg.url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      ok = r.ok;
    } catch (err) { ok = false; }
    form.querySelector("button[type=submit]").disabled = false;
    if (!ok) return say(T.fail, true);

    if (window.gtag) gtag("event", "request_sent", { request_kind: kind, has_file: file ? "yes" : "no", file_uploaded: uploaded ? "yes" : "no", value: quote ? quote.total_usd : undefined, currency: "USD" });
    say("");
    form.hidden = true;
    const done = $("#reqdone");
    done.hidden = false;
    done.querySelector(".ref").textContent = ref;
    const wa = done.querySelector("a.wa");
    const needFile = file && !uploaded;
    done.querySelector(".need-file").hidden = !needFile;
    wa.href = "https://wa.me/" + window.TLETE_WA + "?text=" + encodeURIComponent(`${T.wa} ${ref}${file ? "\n" + T.file + ": " + file.name : ""}`);
    done.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  const fi = form.querySelector("input[type=file]");
  if (fi) fi.addEventListener("change", () => { if (fi.files[0] && fi.files[0].size > 8 * 1024 * 1024) say(T.big); else say(""); });

  function say(msg, bad) { status.textContent = msg; status.classList.toggle("bad", !!bad); }
  function b64(file) {
    return new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1]); r.onerror = rej; r.readAsDataURL(file); });
  }
})();
