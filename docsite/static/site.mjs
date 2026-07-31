// The Manual's one script: theme toggle, sidebar on small screens, and client search over the
// build-time index. Document-relative paths via import.meta.url only -- no <base>, no absolutes
// (the platform laws the Mist Codex build paid for).

const ROOT = new URL("..", import.meta.url);          // static/ sits one level under the site root
const html = document.documentElement;

// ---- theme -----------------------------------------------------------------------------------
const themeBtn = document.querySelector(".theme");
themeBtn.addEventListener("click", () => {
  const dark = html.dataset.theme
    ? html.dataset.theme === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;
  html.dataset.theme = dark ? "light" : "dark";
  localStorage.setItem("dwix-theme", html.dataset.theme);
});

// ---- sidebar (small screens) -----------------------------------------------------------------
const side = document.querySelector(".side");
document.querySelector(".navbtn").addEventListener("click", () => side.classList.toggle("open"));

// ---- search ----------------------------------------------------------------------------------
const input = document.querySelector(".search");
const panel = document.querySelector(".results");
let index = null;
let sel = -1;

async function ensureIndex() {
  if (!index) {
    index = await (await fetch(new URL("static/search.json", ROOT))).json();
  }
  return index;
}

function score(entry, q) {
  let s = 0;
  const t = entry.t.toLowerCase(), b = entry.b.toLowerCase();
  if (t.includes(q)) s += t === q ? 40 : 14;
  for (const h of entry.h) if (h.toLowerCase().includes(q)) { s += 6; break; }
  const first = b.indexOf(q);
  if (first >= 0) {
    s += 2;
    let n = 0, i = first;
    while (i >= 0 && n < 20) { n++; i = b.indexOf(q, i + q.length); }
    s += Math.min(n, 8);
  }
  return { s, first };
}

function snippet(body, at, q) {
  if (at < 0) return "";
  const from = Math.max(0, at - 60);
  const raw = body.slice(from, at + q.length + 90);
  const esc = raw.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const rx = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
  return (from ? "…" : "") + esc.replace(rx, m => `<mark>${m}</mark>`) + "…";
}

async function run(q) {
  q = q.trim().toLowerCase();
  sel = -1;
  if (q.length < 2) { panel.hidden = true; panel.innerHTML = ""; return; }
  const idx = await ensureIndex();
  const hits = idx
    .map(e => { const { s, first } = score(e, q); return { e, s, first }; })
    .filter(r => r.s > 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, 20);
  panel.innerHTML = hits.length
    ? hits.map(r =>
        `<a href="${new URL(r.e.u, ROOT).href}"><span class="rt">${r.e.t}</span>` +
        `<div class="rs">${snippet(r.e.b, r.first, q)}</div></a>`).join("")
    : `<div class="none">No matches for “${q.replace(/[&<>]/g, "")}”.</div>`;
  panel.hidden = false;
}

let deb = 0;
input.addEventListener("input", () => { clearTimeout(deb); deb = setTimeout(() => run(input.value), 120); });
input.addEventListener("focus", () => { if (panel.innerHTML) panel.hidden = false; ensureIndex(); });
input.addEventListener("keydown", ev => {
  const rows = [...panel.querySelectorAll("a")];
  if (ev.key === "Escape") { panel.hidden = true; input.blur(); }
  else if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
    ev.preventDefault();
    sel = Math.max(0, Math.min(rows.length - 1, sel + (ev.key === "ArrowDown" ? 1 : -1)));
    rows.forEach((r, i) => r.classList.toggle("sel", i === sel));
    rows[sel]?.scrollIntoView({ block: "nearest" });
  } else if (ev.key === "Enter" && rows.length) {
    (rows[Math.max(sel, 0)]).click();
  }
});
document.addEventListener("click", ev => {
  if (!panel.contains(ev.target) && ev.target !== input) panel.hidden = true;
});
document.addEventListener("keydown", ev => {
  if (ev.key === "/" && document.activeElement !== input) { ev.preventDefault(); input.focus(); }
});
