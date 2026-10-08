/* Tlete instant quote: load a model, show it, size-check it against the A1 Mini bed, price it. */
(function () {
  "use strict";
  const P = window.TLETE_PRICING;
  const AR = document.documentElement.lang === "ar";
  const T = AR ? {
    loading: "نقرأ الملف…", bad: "ما قدرنا نقرأ هالملف. جرّب STL أو OBJ أو 3MF.", big: "الملف أكبر من 60 ميغابايت. ابعتلنا ياه على واتساب.",
    fits: "بيركب على الطابعة (180 × 180 × 180 ملم)", nofit: "أكبر من 180 ملم: منقسمو قطع ومنلزّقها، أو صغّرو بالحجم",
    tiny: "القطعة صغيرة كتير. يمكن الملف بالإنش أو بالسنتيم؟ غيّر الوحدة.", min: "الحد الأدنى للطلب", per: "للقطعة",
    material: "المادة", time: "وقت الطباعة", handling: "تحضير وتسليم", grams: "g", hours: "h", total: "السعر التقديري",
    wa: "مرحبا Tlete، بدي اطبع هالقطعة:", file: "الملف", size: "الحجم", qty: "العدد", infill: "الحشوة", quality: "الجودة", colour: "اللون", est: "السعر التقديري",
  } : {
    loading: "Reading the file…", bad: "We couldn't read that file. Try STL, OBJ or 3MF.", big: "That file is over 60 MB. Send it to us on WhatsApp instead.",
    fits: "Fits the printer (180 × 180 × 180 mm)", nofit: "Bigger than 180 mm: we can split it into parts and glue them, or scale it down",
    tiny: "This is very small. Is the file in inches or cm? Change the unit.", min: "minimum order", per: "each",
    material: "Material", time: "Print time", handling: "Handling", grams: "g", hours: "h", total: "Estimated price",
    wa: "Hi Tlete, I'd like to print this:", file: "File", size: "Size", qty: "Quantity", infill: "Infill", quality: "Quality", colour: "Colour", est: "Estimated price",
  };
  const $ = s => document.querySelector(s);
  const money = v => "$" + (Math.round(v * 100) / 100).toFixed(2).replace(/\.00$/, "");
  const fmt = v => (v >= 100 ? v.toFixed(0) : v.toFixed(1)).replace(/\.0$/, "");

  let tri = null, base = null, fileName = "", fileObj = null, lastSent = "";
  const state = window.TleteQuote = { current: null, file: null };

  const drop = $("#drop"), input = $("#qfile"), status = $("#qstatus"), panel = $("#qresult");
  const opts = $("#qopts");

  function setStatus(msg, bad) { status.textContent = msg || ""; status.classList.toggle("bad", !!bad); }

  async function load(name, buf, file) {
    setStatus(T.loading);
    try {
      tri = await TleteMesh.parseFile(name, buf);
      if (!tri.length) throw new Error("empty");
    } catch (e) { setStatus(T.bad, true); return; }
    base = TleteMesh.measure(tri);
    fileName = name; fileObj = file || new File([buf], name);
    state.file = fileObj;
    setStatus("");
    panel.hidden = false;
    $("#qname").textContent = name;
    view.set(tri, base);
    update(true);
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  input.addEventListener("change", () => { const f = input.files[0]; if (f) readFile(f); });
  function readFile(f) {
    if (f.size > 60 * 1024 * 1024) { setStatus(T.big, true); return; }
    f.arrayBuffer().then(b => load(f.name, b, f));
  }
  ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => { const f = e.dataTransfer.files[0]; if (f) readFile(f); });
  document.querySelectorAll("[data-example]").forEach(b => b.addEventListener("click", () => loadExample(b.dataset.example)));
  function loadExample(slug) {
    fetch(window.TLETE_BASE + "/assets/models/" + slug + ".stl").then(r => r.arrayBuffer()).then(b => load(slug + ".stl", b));
  }
  const tryParam = new URLSearchParams(location.search).get("try");
  if (tryParam && /^[a-z-]+$/.test(tryParam)) loadExample(tryParam);

  opts.addEventListener("input", () => update(false));
  opts.addEventListener("change", () => update(false));

  function options() {
    const unit = +opts.unit.value;
    return {
      material: opts.material.value, colour: opts.colour.value, infill: +opts.infill.value, quality: opts.quality.value,
      qty: Math.max(1, Math.min(500, parseInt(opts.qty.value, 10) || 1)), scale: unit * Math.max(1, Math.min(1000, +opts.scale.value || 100)) / 100,
      unitLabel: opts.unit.options[opts.unit.selectedIndex].text, scalePct: +opts.scale.value || 100,
    };
  }

  function update(fresh) {
    if (!base) return;
    const o = options();
    const q = TleteMesh.price(base, o, P);
    const fit = TleteMesh.fits(q.size, P.bed_mm);
    const tiny = Math.max(...q.size) < 6;
    $("#qsize").textContent = q.size.map(v => fmt(v)).join(" × ") + " mm";
    const fb = $("#qfit");
    fb.textContent = tiny ? T.tiny : fit ? T.fits : T.nofit;
    fb.className = "fit " + (tiny ? "warn" : fit ? "ok" : "warn");
    $("#qtotal").textContent = money(q.total);
    $("#qbreak").innerHTML =
      `<li><span>${T.material}: <bdi dir="ltr">${fmt(q.grams)} ${T.grams} × ${money(P.materials[o.material].per_gram)}</bdi></span><b>${money(q.materialCost)}</b></li>` +
      `<li><span>${T.time}: <bdi dir="ltr">${fmt(q.hours)} ${T.hours} × ${money(P.per_hour)}</bdi></span><b>${money(q.timeCost)}</b></li>` +
      (o.qty > 1 ? `<li><span><bdi dir="ltr">× ${o.qty}</bdi></span><b>${money(q.piece * o.qty)}</b></li>` : "") +
      `<li><span>${T.handling}</span><b>${money(P.handling)}</b></li>` +
      (q.minApplied ? `<li class="min"><span>${T.min}</span><b>${money(P.min_order)}</b></li>` : "");
    $("#qper").textContent = o.qty > 1 ? `${money(q.total / o.qty)} ${T.per}` : "";
    state.current = {
      file: fileName, material: o.material, colour: o.colour, infill: o.infill, quality: o.quality, qty: o.qty, scale_pct: o.scalePct, unit: o.unitLabel,
      size_mm: q.size.map(v => Math.round(v * 10) / 10), grams: Math.round(q.grams), hours: Math.round(q.hours * 10) / 10, total_usd: q.total, fits: fit,
    };
    const c = state.current;
    const msg = `${T.wa}\n${T.file}: ${c.file}\n${T.size}: ${c.size_mm.join(" × ")} mm\n${T.material}: ${c.material}, ${T.colour}: ${optText("colour")}\n${T.infill}: ${c.infill}%, ${T.quality}: ${optText("quality")}\n${T.qty}: ${c.qty}\n${T.est}: ${money(c.total_usd)}`;
    $("#qwa").href = "https://wa.me/" + window.TLETE_WA + "?text=" + encodeURIComponent(msg);
    // One quote_calculated per distinct quote, after the customer stops fiddling for a moment.
    clearTimeout(update.t);
    update.t = setTimeout(() => {
      const key = JSON.stringify([c.file, c.material, c.infill, c.quality, c.qty, c.scale_pct]);
      if (key === lastSent) return;
      lastSent = key;
      if (window.gtag) gtag("event", "quote_calculated", { material: c.material, quantity: c.qty, value: c.total, currency: "USD", fits: c.fits ? "yes" : "no", example: /^(cedar-keychain|phone-stand|hex-planter|lebanon-map|appliance-knob|cable-organiser)\.stl$/.test(c.file) ? "yes" : "no" });
    }, fresh ? 300 : 1500);
  }
  const optText = n => opts[n].options[opts[n].selectedIndex].text;

  $("#qsend").addEventListener("click", () => {
    const f = $("#reqform");
    f.hidden = false;
    f.scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(() => f.querySelector("input[name=name]").focus(), 400);
  });

  // ---------- viewer: flat-shaded painter's renderer on a 2D canvas, drag to turn ----------
  const view = (function () {
    const cv = $("#qview"), ctx = cv.getContext("2d");
    let tris = null, center = [0, 0, 0], radius = 1, yaw = -0.6, pitch = 0.45, drag = null, raf = 0;
    const colours = { black: "#2a2a2d", white: "#efece6", grey: "#9a9a9e", red: "#c8302c", blue: "#2f62d0", green: "#2f8a52", yellow: "#e8b622", orange: "#e8662a" };
    function set(t, m) {
      // Keep at most ~40k triangles for display; measurements always use the full mesh.
      const n = t.length / 9, step = Math.max(1, Math.ceil(n / 40000));
      if (step > 1) { const k = Math.floor(n / step), s = new Float32Array(k * 9); for (let i = 0; i < k; i++) s.set(t.subarray(i * step * 9, i * step * 9 + 9), i * 9); tris = s; } else tris = t;
      center = [0, 1, 2].map(a => (m.min[a] + m.max[a]) / 2);
      radius = Math.max(...m.size_mm) / 2 || 1;
      draw();
    }
    function draw() {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(paint);
    }
    function paint() {
      const dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
      cv.width = W * dpr; cv.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      if (!tris) return;
      const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
      const sc = Math.min(W, H) * 0.42 / radius;
      const n = tris.length / 9, depth = new Float32Array(n), pts = new Float32Array(n * 6), shade = new Float32Array(n), order = [];
      const L = [-0.35, 0.45, 0.82];
      for (let i = 0; i < n; i++) {
        const o = i * 9;
        const ax = tris[o] - center[0], ay = tris[o + 1] - center[1], az = tris[o + 2] - center[2];
        const bx = tris[o + 3] - center[0], by = tris[o + 4] - center[1], bz = tris[o + 5] - center[2];
        const qx = tris[o + 6] - center[0], qy = tris[o + 7] - center[1], qz = tris[o + 8] - center[2];
        let nx = (by - ay) * (qz - az) - (bz - az) * (qy - ay), ny = (bz - az) * (qx - ax) - (bx - ax) * (qz - az), nz = (bx - ax) * (qy - ay) - (by - ay) * (qx - ax);
        const nl = Math.hypot(nx, ny, nz) || 1; nx /= nl; ny /= nl; nz /= nl;
        let d = 0;
        for (let k = 0; k < 3; k++) {
          const x = tris[o + k * 3] - center[0], y = tris[o + k * 3 + 1] - center[1], z = tris[o + k * 3 + 2] - center[2];
          const x1 = x * cy - y * sy, y1 = x * sy + y * cy;
          pts[i * 6 + k * 2] = W / 2 + x1 * sc;
          pts[i * 6 + k * 2 + 1] = H / 2 - (z * cp - y1 * sp) * sc;
          d += z * sp + y1 * cp;
        }
        depth[i] = d;
        // No back-face culling: many STLs have flipped triangles, and the depth sort hides the far side anyway.
        shade[i] = 0.42 + 0.58 * Math.abs(nx * L[0] + ny * L[1] + nz * L[2]);
        order.push(i);
      }
      order.sort((a, b) => depth[a] - depth[b]);
      const hex = colours[opts.colour.value] || "#e8662a";
      const base = [1, 3, 5].map(k => parseInt(hex.slice(k, k + 2), 16));
      for (const i of order) {
        const s = shade[i];
        const c = `rgb(${base.map(v => Math.min(255, Math.round(v * s + 14 * (1 - s)))).join(",")})`;
        ctx.fillStyle = c; ctx.strokeStyle = c; ctx.lineWidth = 0.6;
        ctx.beginPath(); ctx.moveTo(pts[i * 6], pts[i * 6 + 1]); ctx.lineTo(pts[i * 6 + 2], pts[i * 6 + 3]); ctx.lineTo(pts[i * 6 + 4], pts[i * 6 + 5]); ctx.closePath(); ctx.fill(); ctx.stroke();
      }
    }
    cv.addEventListener("pointerdown", e => { drag = [e.clientX, e.clientY, yaw, pitch]; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener("pointermove", e => { if (!drag) return; yaw = drag[2] + (e.clientX - drag[0]) * 0.01; pitch = Math.max(-1.4, Math.min(1.4, drag[3] + (e.clientY - drag[1]) * 0.01)); draw(); });
    cv.addEventListener("pointerup", () => { drag = null; });
    window.addEventListener("resize", draw);
    opts.colour.addEventListener("change", draw);
    return { set, draw };
  })();
})();
