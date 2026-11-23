// Site chrome: «Menú» panel and docked pill (N10), then the «Buscar …» spotlight (N13).
// Copied from mockups/vibe/ab-v6/index.html; two changes: Enter in the spotlight follows the page link,
// and a same-page anchor in «Menú» closes the panel.
(() => {
  const root = document.documentElement;
  const toggle = document.querySelector(".menu-toggle");
  const panel = document.getElementById("indice");
  const mast = document.querySelector(".mast");
  const dock = document.querySelector(".dock");
  const holder = document.querySelector(".dock-holder");
  let timer = 0;
  const isOpen = () => toggle.getAttribute("aria-expanded") === "true";
  const open = () => {
    clearTimeout(timer);
    panel.classList.remove("is-closing");
    panel.style.display = "block";
    void panel.offsetHeight;
    panel.style.display = "";
    panel.classList.add("is-open");
    toggle.setAttribute("aria-expanded", "true");
  };
  const close = (refocus) => {
    toggle.setAttribute("aria-expanded", "false");
    panel.classList.remove("is-open");
    panel.classList.add("is-closing");
    const ms = parseFloat(getComputedStyle(panel).transitionDuration) * 1000 || 0;
    timer = setTimeout(() => panel.classList.remove("is-closing"), ms);
    if (refocus) toggle.focus();
  };
  toggle.addEventListener("click", () => (isOpen() ? close(false) : open()));
  panel.addEventListener("click", (e) => {
    const a = e.target.closest("a[href]");
    if (a && a.hash && a.pathname === location.pathname && isOpen()) close(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && isOpen()) {
      const inside = panel.contains(document.activeElement) || document.activeElement === document.body;
      close(inside || document.activeElement === toggle);
    }
  });
  document.addEventListener("click", (e) => {
    if (root.classList.contains("is-docked") && isOpen() && !panel.contains(e.target) && !toggle.contains(e.target)) close(false);
  });

  let docked = false;
  let ticking = false;
  const threshold = () => mast.offsetHeight - 80;
  const setHeights = () => {
    if (!docked) holder.style.minHeight = dock.offsetHeight + "px";
    else root.style.setProperty("--dock-h", dock.offsetHeight + "px");
  };
  const update = () => {
    const next = window.scrollY > threshold();
    if (next === docked) return;
    docked = next;
    if (docked) {
      holder.style.minHeight = dock.offsetHeight + "px";
      root.classList.remove("is-undocking");
      root.classList.add("is-docked");
      root.style.setProperty("--dock-h", dock.offsetHeight + "px");
    } else {
      root.classList.add("is-undocking");
      const done = () => { if (!docked) root.classList.remove("is-docked", "is-undocking"); };
      dock.addEventListener("animationend", done, { once: true });
      setTimeout(done, 400);
    }
  };
  window.addEventListener("scroll", () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { update(); ticking = false; });
  }, { passive: true });
  window.addEventListener("resize", setHeights);
  setHeights();
  update();
})();
(() => {
  const root = document.documentElement;
  const pill = document.querySelector(".searchpill");
  const dlg = document.getElementById("cmdk");
  const input = document.getElementById("cmdk-input");
  const list = document.getElementById("cmdk-list");
  const empty = document.getElementById("cmdk-empty");
  const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
  if (!mac) pill.querySelector(".searchpill__mod").textContent = "Ctrl";
  const norm = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const pages = [];
  document.querySelectorAll("#indice .index__item").forEach((item) => {
    const top = item.querySelector(".index__link");
    const parent = { title: top.textContent.trim(), href: top.getAttribute("href"), sub: false, kids: [] };
    pages.push(parent);
    item.querySelectorAll(".index__sublink").forEach((a) => {
      const kid = { title: a.textContent.trim(), href: a.getAttribute("href"), sub: true, parent, lang: a.getAttribute("lang") };
      parent.kids.push(kid);
      pages.push(kid);
    });
  });
  let shown = [];
  let active = -1;
  let opener = null;
  const ext = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6.5 17.5l11-11M9 6.5h8.5V15" fill="none" stroke="currentColor" stroke-width="2.16" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const mark = (title, q) => {
    if (!q) return title.replace(/&/g, "&amp;").replace(/</g, "&lt;");
    const i = norm(title).indexOf(q);
    if (i < 0) return title.replace(/&/g, "&amp;").replace(/</g, "&lt;");
    const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;");
    return esc(title.slice(0, i)) + "<b>" + esc(title.slice(i, i + q.length)) + "</b>" + esc(title.slice(i + q.length));
  };
  const setActive = (i) => {
    const opts = list.querySelectorAll(".cmdk__opt");
    opts.forEach((o, n) => o.setAttribute("aria-selected", String(n === i)));
    active = i;
    if (i >= 0 && opts[i]) {
      input.setAttribute("aria-activedescendant", opts[i].id);
      opts[i].scrollIntoView({ block: "nearest" });
    } else input.removeAttribute("aria-activedescendant");
  };
  const render = () => {
    const q = norm(input.value.trim());
    const hit = (p) => !q || norm(p.title).includes(q);
    shown = pages.filter((p) => p.sub ? (hit(p) || hit(p.parent)) : (hit(p) || p.kids.some(hit)));
    list.innerHTML = shown.map((p, n) => `<li class="cmdk__opt${p.sub ? " is-sub" : ""}" id="cmdk-opt-${n}" role="option" aria-selected="false"${p.lang ? ` lang="${p.lang}"` : ""}><span>${mark(p.title, q)}</span>${/^https?:/.test(p.href) ? ext : ""}</li>`).join("");
    setActive(shown.length ? 0 : -1);
    empty.textContent = shown.length ? "" : "No se han encontrado resultados.";
  };
  const go = (i) => {
    const p = shown[i];
    if (!p) return;
    dlg.close();
    if (/^https?:/.test(p.href)) window.open(p.href, "_blank", "noopener");
    else window.location.href = p.href;
  };
  const openDlg = (first) => {
    if (dlg.open) return;
    opener = document.activeElement;
    input.value = first || "";
    render();
    root.classList.add("is-locked");
    dlg.showModal();
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  };
  dlg.addEventListener("close", () => {
    root.classList.remove("is-locked");
    (opener && opener.focus ? opener : pill).focus();
  });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  pill.addEventListener("click", () => openDlg(""));
  pill.addEventListener("keydown", (e) => {
    if (e.key.length === 1 && e.key !== " " && !e.metaKey && !e.ctrlKey && !e.altKey) { e.preventDefault(); openDlg(e.key); }
  });
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (dlg.open) dlg.close(); else openDlg("");
    }
  });
  input.addEventListener("input", render);
  input.addEventListener("keydown", (e) => {
    const n = shown.length;
    if (e.key === "ArrowDown" && n) { e.preventDefault(); setActive((active + 1) % n); }
    else if (e.key === "ArrowUp" && n) { e.preventDefault(); setActive((active - 1 + n) % n); }
    else if (e.key === "Enter" && active >= 0) { e.preventDefault(); go(active); }
  });
  list.addEventListener("mousemove", (e) => {
    const o = e.target.closest(".cmdk__opt");
    if (o) setActive([...list.children].indexOf(o));
  });
  list.addEventListener("click", (e) => {
    const o = e.target.closest(".cmdk__opt");
    if (o) go([...list.children].indexOf(o));
  });
})();
