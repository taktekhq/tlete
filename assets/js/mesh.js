/* Tlete mesh tools: read STL (binary/ASCII), OBJ and 3MF in the browser, measure them, price them.
   No libraries. The file never leaves the browser unless the customer sends a request. */
(function (root) {
  "use strict";

  // ---------- parsers: each returns a Float32Array of triangle soup (9 floats per triangle) ----------

  function parseSTL(buf) {
    const dv = new DataView(buf);
    if (buf.byteLength >= 84) {
      const n = dv.getUint32(80, true);
      if (84 + n * 50 === buf.byteLength) return binarySTL(dv, n);
    }
    const text = new TextDecoder().decode(new Uint8Array(buf));
    if (/^\s*solid/.test(text) && /facet/.test(text)) return asciiSTL(text);
    if (buf.byteLength >= 84) return binarySTL(dv, Math.min(dv.getUint32(80, true), Math.floor((buf.byteLength - 84) / 50)));
    throw new Error("bad_stl");
  }

  function binarySTL(dv, n) {
    const out = new Float32Array(n * 9);
    for (let i = 0; i < n; i++) {
      const o = 84 + i * 50 + 12;
      for (let k = 0; k < 9; k++) out[i * 9 + k] = dv.getFloat32(o + k * 4, true);
    }
    return out;
  }

  function asciiSTL(text) {
    const re = /vertex\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)/g;
    const v = [];
    let m;
    while ((m = re.exec(text))) v.push(+m[1], +m[2], +m[3]);
    return new Float32Array(v.slice(0, v.length - (v.length % 9)));
  }

  function parseOBJ(text) {
    const verts = [], out = [];
    for (const line of text.split("\n")) {
      const p = line.trim().split(/\s+/);
      if (p[0] === "v") verts.push([+p[1], +p[2], +p[3]]);
      else if (p[0] === "f") {
        const idx = p.slice(1).map(s => { const i = parseInt(s, 10); return i < 0 ? verts.length + i : i - 1; });
        for (let k = 1; k + 1 < idx.length; k++) for (const j of [idx[0], idx[k], idx[k + 1]]) { const q = verts[j]; if (!q) throw new Error("bad_obj"); out.push(q[0], q[1], q[2]); }
      }
    }
    return new Float32Array(out);
  }

  // 3MF = zip of XML. Read the central directory, inflate every *.model, collect meshes.
  async function parse3MF(buf) {
    const u8 = new Uint8Array(buf), dv = new DataView(buf);
    let eocd = -1;
    for (let i = u8.length - 22; i >= Math.max(0, u8.length - 65557); i--) if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    if (eocd < 0) throw new Error("bad_3mf");
    const count = dv.getUint16(eocd + 10, true);
    let p = dv.getUint32(eocd + 16, true);
    const out = [];
    for (let e = 0; e < count; e++) {
      if (dv.getUint32(p, true) !== 0x02014b50) break;
      const method = dv.getUint16(p + 10, true), csize = dv.getUint32(p + 20, true);
      const nlen = dv.getUint16(p + 28, true), xlen = dv.getUint16(p + 30, true), clen = dv.getUint16(p + 32, true);
      const local = dv.getUint32(p + 42, true);
      const name = new TextDecoder().decode(u8.subarray(p + 46, p + 46 + nlen));
      p += 46 + nlen + xlen + clen;
      if (!/\.model$/i.test(name)) continue;
      const start = local + 30 + dv.getUint16(local + 26, true) + dv.getUint16(local + 28, true);
      let data = u8.subarray(start, start + csize);
      if (method === 8) data = new Uint8Array(await new Response(new Blob([data]).stream().pipeThrough(new DecompressionStream("deflate-raw"))).arrayBuffer());
      else if (method !== 0) continue;
      meshFromModelXML(new TextDecoder().decode(data), out);
    }
    if (!out.length) throw new Error("bad_3mf");
    return new Float32Array(out);
  }

  function meshFromModelXML(xml, out) {
    const meshes = xml.split(/<(?:\w+:)?mesh[\s>]/).slice(1);
    for (const m of meshes) {
      const vs = [];
      const vre = /<(?:\w+:)?vertex\s+([^>]*)\/?>/g;
      let r;
      while ((r = vre.exec(m))) vs.push([attr(r[1], "x"), attr(r[1], "y"), attr(r[1], "z")]);
      const tre = /<(?:\w+:)?triangle\s+([^>]*)\/?>/g;
      while ((r = tre.exec(m))) for (const k of ["v1", "v2", "v3"]) { const q = vs[attr(r[1], k)]; if (q) out.push(q[0], q[1], q[2]); }
    }
  }
  const attr = (s, k) => +((s.match(new RegExp("\\b" + k + "=\"([^\"]*)\"")) || [])[1] || 0);

  async function parseFile(name, buf) {
    const ext = (name.split(".").pop() || "").toLowerCase();
    if (ext === "stl") return parseSTL(buf);
    if (ext === "obj") return parseOBJ(new TextDecoder().decode(new Uint8Array(buf)));
    if (ext === "3mf") return parse3MF(buf);
    throw new Error("bad_type");
  }

  // ---------- measure ----------

  function measure(tri) {
    let vol = 0, area = 0;
    const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < tri.length; i += 9) {
      const ax = tri[i], ay = tri[i + 1], az = tri[i + 2], bx = tri[i + 3], by = tri[i + 4], bz = tri[i + 5], cx = tri[i + 6], cy = tri[i + 7], cz = tri[i + 8];
      vol += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx);
      const ux = bx - ax, uy = by - ay, uz = bz - az, vx = cx - ax, vy = cy - ay, vz = cz - az;
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      area += Math.sqrt(nx * nx + ny * ny + nz * nz) / 2;
      for (let k = 0; k < 9; k++) { const a = k % 3, v = tri[i + k]; if (v < min[a]) min[a] = v; if (v > max[a]) max[a] = v; }
    }
    return {
      triangles: tri.length / 9,
      volume_cm3: Math.abs(vol) / 6 / 1000,
      area_cm2: area / 100,
      size_mm: [max[0] - min[0], max[1] - min[1], max[2] - min[2]],
      min, max,
    };
  }

  // Fits if some axis-aligned orientation fits the bed (sorted sides against sorted bed).
  function fits(size, bed) {
    const s = size.slice().sort((a, b) => a - b), b = bed.slice().sort((a, b) => a - b);
    return s.every((v, i) => v <= b[i]);
  }

  // ---------- price: the same formula is printed on the site ----------
  // grams = (shell + infill share of the inside) x density x waste; hours = setup + grams / speed x quality
  function price(m, opt, P) {
    const s = opt.scale;
    const mat = P.materials[opt.material];
    const vol = m.volume_cm3 * s * s * s, area = m.area_cm2 * s * s;
    const shell = Math.min(vol, area * P.shell_mm / 10);
    const solid = shell + (vol - shell) * opt.infill / 100;
    const grams = solid * mat.density * P.waste_factor;
    const hours = P.setup_hours + grams / mat.grams_per_hour * P.quality[opt.quality];
    const materialCost = grams * mat.per_gram, timeCost = hours * P.per_hour;
    const piece = materialCost + timeCost;
    const raw = piece * opt.qty + P.handling;
    const total = Math.ceil(Math.max(P.min_order, raw) * 2) / 2;
    return { grams, hours, materialCost, timeCost, piece, raw, total, minApplied: raw < P.min_order, size: m.size_mm.map(v => v * s) };
  }

  root.TleteMesh = { parseFile, parseSTL, measure, fits, price };
  if (typeof module !== "undefined") module.exports = root.TleteMesh;
})(typeof window !== "undefined" ? window : globalThis);
