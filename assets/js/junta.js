// Junta Directiva: year selector (ARIA tabs, mockups/inner/a/junta-2-selector.html).
// A link to #curso-AAAA-AAAA, or to anything inside a course (#historico), opens that course.
// Without JavaScript the CSS shows every board.
(() => {
  const tabs = [...document.querySelectorAll('.years__tabs [role="tab"]')];
  if (!tabs.length) return;
  const panels = tabs.map((t) => document.getElementById(t.getAttribute("aria-controls")));
  const select = (k, focus) => {
    tabs.forEach((t, i) => {
      const on = i === k;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
      panels[i].hidden = !on;
    });
    if (focus) tabs[k].focus();
  };
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => select(i, false));
    t.addEventListener("keydown", (e) => {
      const n = tabs.length;
      const to = { ArrowRight: (i + 1) % n, ArrowLeft: (i - 1 + n) % n, Home: 0, End: n - 1 }[e.key];
      if (to !== undefined) { e.preventDefault(); select(to, true); }
    });
  });
  const fromHash = () => {
    const el = location.hash.length > 1 && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    const k = el ? panels.findIndex((p) => p.contains(el)) : -1;
    if (k >= 0) select(k, false);
  };
  fromHash();
  window.addEventListener("hashchange", fromHash);
})();
