document.addEventListener("DOMContentLoaded", () => {
  const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
  function toFaDigits(value) {
    return String(value ?? "").replace(/\d/g, (d) => FA_DIGITS[d]);
  }

  function persianizeTextNodes(root) {
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        const tag = parent.tagName;
        if (tag === "SCRIPT" || tag === "STYLE" || tag === "TEXTAREA" || tag === "NOSCRIPT") {
          return NodeFilter.FILTER_REJECT;
        }
        if (parent.closest("input, textarea, select, code, pre, [data-no-fa-digits]")) {
          return NodeFilter.FILTER_REJECT;
        }
        if (!/\d/.test(node.nodeValue || "")) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((node) => {
      node.nodeValue = toFaDigits(node.nodeValue);
    });
  }

  persianizeTextNodes(document.body);

  function openSheet(el) {
    if (!el) return;
    if (typeof el.showModal === "function") el.showModal();
    else el.setAttribute("open", "open");
  }
  function closeSheet(el) {
    if (!el) return;
    if (typeof el.close === "function") el.close();
    else el.removeAttribute("open");
  }

  document.querySelectorAll("[data-open-sheet]").forEach((btn) => {
    btn.addEventListener("click", () => {
      openSheet(document.getElementById(btn.dataset.openSheet));
    });
  });

  document.querySelectorAll("[data-close-sheet]").forEach((btn) => {
    btn.addEventListener("click", () => {
      closeSheet(btn.closest("dialog"));
    });
  });

  document.querySelectorAll("dialog.pnl-sheet").forEach((dlg) => {
    dlg.addEventListener("click", (e) => {
      const panel = dlg.querySelector(".pnl-sheet-panel");
      if (panel && !panel.contains(e.target)) closeSheet(dlg);
    });
  });

  function wireCustomDate(root) {
    if (!root) return;
    const preset = root.querySelector("#id_follow_preset, select[name='follow_preset']");
    const custom = root.querySelector("#id_custom_jalali_date, input[name='custom_jalali_date']");
    if (!preset || !custom) return;
    const field = custom.closest(".pnl-field");
    const sync = () => {
      if (field) field.classList.toggle("is-hidden", preset.value !== "custom");
    };
    preset.addEventListener("change", sync);
    sync();
  }

  document.querySelectorAll("form, dialog").forEach((node) => wireCustomDate(node));

  const quickDialog = document.getElementById("pnlQuickCall");
  const quickForm = document.getElementById("pnlQuickCallForm");
  const quickTitle = document.getElementById("pnlQuickTitle");
  const quickMeta = document.getElementById("pnlQuickMeta");
  const quickNext = document.getElementById("pnlQuickNext");

  if (quickDialog && quickForm) {
    document.querySelectorAll(".pnl-quick-call").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        quickForm.action = `/panel/cases/${btn.dataset.caseId}/call/`;
        if (quickTitle) quickTitle.textContent = `تماس سریع — ${btn.dataset.caseName || ""}`;
        if (quickMeta) quickMeta.textContent = btn.dataset.casePhone || "";
        if (quickNext) quickNext.value = window.location.pathname + window.location.search;
        openSheet(quickDialog);
      });
    });
  }

  const input = document.getElementById("pnlSearchInput");
  const box = document.getElementById("pnlSuggestBox");
  let timer = null;
  if (input && box) {
    input.addEventListener("input", () => {
      clearTimeout(timer);
      const q = input.value.trim();
      if (q.length < 2) {
        box.hidden = true;
        box.innerHTML = "";
        return;
      }
      timer = setTimeout(async () => {
        try {
          const res = await fetch(`/panel/search/suggest/?q=${encodeURIComponent(q)}`);
          const data = await res.json();
          if (!data.results?.length) {
            box.hidden = true;
            box.innerHTML = "";
            return;
          }
          box.innerHTML = data.results
            .map(
              (r) =>
                `<a href="${r.url}"><strong>${r.name}</strong><span>${toFaDigits(r.phone)} · ${toFaDigits(r.code)} · ${r.stage}</span></a>`
            )
            .join("");
          box.hidden = false;
          persianizeTextNodes(box);
        } catch (_) {
          box.hidden = true;
        }
      }, 200);
    });
    document.addEventListener("click", (e) => {
      if (!box.contains(e.target) && e.target !== input) box.hidden = true;
    });
  }

  setTimeout(() => {
    document.querySelectorAll(".pnl-flash").forEach((el) => {
      el.style.transition = "opacity .35s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    });
  }, 4200);

  // ── Notifications + menu badges ─────────────────────
  const LS_SINCE = "pnl_notif_since";
  const LS_SEEN = "pnl_notif_seen";
  const LS_PERM = "pnl_notif_pref";
  const baseTitle = toFaDigits(document.title.replace(/^\(\d+\)\s*/, ""));

  function readSeen() {
    try {
      return new Set(JSON.parse(localStorage.getItem(LS_SEEN) || "[]"));
    } catch (_) {
      return new Set();
    }
  }
  function writeSeen(set) {
    const arr = [...set].slice(-80);
    localStorage.setItem(LS_SEEN, JSON.stringify(arr));
  }

  function formatBadge(n) {
    if (!n || n < 1) return "";
    return n > 99 ? "۹۹+" : toFaDigits(n);
  }

  function applyCounts(counts) {
    if (!counts) return;
    document.querySelectorAll("[data-badge-key]").forEach((el) => {
      const key = el.dataset.badgeKey;
      const n = Number(counts[key] || 0);
      const badge = el.querySelector(".pnl-nav-badge");
      if (!badge) return;
      if (n > 0) {
        badge.hidden = false;
        badge.textContent = formatBadge(n);
      } else {
        badge.hidden = true;
        badge.textContent = "۰";
      }
    });
    const total = Number(counts.followup || counts.dashboard || 0);
    document.title = total > 0 ? `(${toFaDigits(total)}) ${baseTitle}` : baseTitle;
  }

  function canNotify() {
    return (
      localStorage.getItem(LS_PERM) === "1" &&
      "Notification" in window &&
      Notification.permission === "granted"
    );
  }

  function syncNotifBtn() {
    const btn = document.getElementById("pnlNotifBtn");
    if (!btn || !("Notification" in window)) {
      if (btn) btn.hidden = true;
      return;
    }
    btn.classList.toggle("is-on", Notification.permission === "granted" && localStorage.getItem(LS_PERM) === "1");
    btn.classList.toggle("is-denied", Notification.permission === "denied");
    if (Notification.permission === "granted" && localStorage.getItem(LS_PERM) === "1") {
      btn.textContent = "اعلان ✓";
    } else if (Notification.permission === "denied") {
      btn.textContent = "اعلان مسدود";
    } else {
      btn.textContent = "اعلان";
    }
  }

  async function enableNotifications() {
    if (!("Notification" in window)) {
      alert("مرورگر شما اعلان را پشتیبانی نمی‌کند.");
      return;
    }
    const perm = await Notification.requestPermission();
    if (perm === "granted") {
      localStorage.setItem(LS_PERM, "1");
      new Notification("پنل سفیران", {
        body: "اعلان‌ها فعال شد. موارد جدید اینجا می‌آید.",
        icon: "/static/panel/favicon-48.png",
        tag: "pnl-enabled",
      });
    } else {
      localStorage.setItem(LS_PERM, "0");
    }
    syncNotifBtn();
  }

  const notifBtn = document.getElementById("pnlNotifBtn");
  if (notifBtn) {
    notifBtn.addEventListener("click", enableNotifications);
    syncNotifBtn();
  }

  function showBrowserEvents(events) {
    if (!canNotify() || !events?.length) return;
    const seen = readSeen();
    let changed = false;
    for (const ev of events) {
      if (seen.has(ev.id)) continue;
      seen.add(ev.id);
      changed = true;
      try {
        const n = new Notification(ev.title || "پنل سفیران", {
          body: ev.body || "",
          icon: "/static/panel/favicon-48.png",
          tag: ev.id,
          data: { url: ev.url },
        });
        n.onclick = () => {
          window.focus();
          if (ev.url) window.location.href = ev.url;
          n.close();
        };
      } catch (_) {
        /* ignore */
      }
    }
    if (changed) writeSeen(seen);
  }

  async function pollNotifications() {
    try {
      let since = localStorage.getItem(LS_SINCE);
      if (!since) {
        // اولین بار: فقط شمارنده‌ها؛ از الان به بعد ایونت‌ها
        since = new Date(Date.now() - 60 * 1000).toISOString();
      }
      const res = await fetch(`/panel/api/notifications/?since=${encodeURIComponent(since)}`, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      if (!res.ok) return;
      const data = await res.json();
      applyCounts(data.counts);
      showBrowserEvents(data.events || []);
      if (data.server_time) localStorage.setItem(LS_SINCE, data.server_time);
    } catch (_) {
      /* offline / login expired */
    }
  }

  pollNotifications();
  setInterval(pollNotifications, 35000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) pollNotifications();
  });

  // ── Follow-up inbox tabs ────────────────────────────
  const fuRoot = document.querySelector("[data-fu-root]");
  if (fuRoot) {
    const tabs = [...fuRoot.querySelectorAll("[data-fu-tab]")];
    const panels = [...fuRoot.querySelectorAll("[data-fu-panel]")];
    const dockN = fuRoot.querySelector("[data-fu-dock-n]");
    const dockL = fuRoot.querySelector("[data-fu-dock-l]");
    const labels = {
      overdue: "عقب‌افتاده",
      today: "موعد امروز",
      all: "در صف کار",
    };

    function setFuTab(key) {
      tabs.forEach((btn) => {
        const on = btn.dataset.fuTab === key;
        btn.classList.toggle("is-active", on);
        btn.setAttribute("aria-pressed", on ? "true" : "false");
      });
      panels.forEach((panel) => {
        panel.hidden = panel.dataset.fuPanel !== key;
      });
      const active = tabs.find((b) => b.dataset.fuTab === key);
      if (dockN && active) {
        const n = active.querySelector("strong");
        if (n) dockN.textContent = n.textContent.trim();
      }
      if (dockL) dockL.textContent = labels[key] || "در صف کار";
      try {
        sessionStorage.setItem("pnl_fu_tab", key);
      } catch (_) {}
    }

    let initial = fuRoot.dataset.defaultTab || "overdue";
    try {
      const saved = sessionStorage.getItem("pnl_fu_tab");
      if (saved && ["overdue", "today", "all"].includes(saved)) initial = saved;
    } catch (_) {}

    tabs.forEach((btn) => {
      btn.addEventListener("click", () => setFuTab(btn.dataset.fuTab));
    });
    setFuTab(initial);
  }
});
