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
    const custom = root.querySelector("#id_custom_jalali_date, input[name='custom_jalali_date']");
    if (!custom) return;
    const field = custom.closest(".pnl-call-custom-date, .pnl-field");
    const radios = root.querySelectorAll("input[name='follow_preset']");
    const select = root.querySelector("select[name='follow_preset']");
    const sync = () => {
      let val = "";
      if (radios.length) {
        const checked = root.querySelector("input[name='follow_preset']:checked");
        val = checked ? checked.value : "";
      } else if (select) {
        val = select.value;
      }
      if (field) field.classList.toggle("is-hidden", val !== "custom");
    };
    radios.forEach((r) => r.addEventListener("change", sync));
    if (select) select.addEventListener("change", sync);
    sync();
  }

  document.querySelectorAll("form, dialog").forEach((node) => wireCustomDate(node));

  // Quick note chips → append to call report textarea
  document.querySelectorAll(".pnl-call-note-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const form = btn.closest("form");
      const ta = form?.querySelector("textarea[name='notes']");
      if (!ta) return;
      const chunk = (btn.dataset.note || "").trim();
      if (!chunk) return;
      const cur = ta.value.trim();
      ta.value = cur ? `${cur}\n${chunk}` : chunk;
      ta.focus();
      ta.dispatchEvent(new Event("input", { bubbles: true }));
    });
  });

  function csrfToken() {
    return (
      document.querySelector("input[name=csrfmiddlewaretoken]")?.value
      || document.cookie.match(/csrftoken=([^;]+)/)?.[1]
      || ""
    );
  }

  function caseAiUrlFromForm(form) {
    const action = form?.getAttribute("action") || "";
    const m = action.match(/\/panel\/cases\/(\d+)\/call\/?/);
    return m ? `/panel/cases/${m[1]}/ai/` : "";
  }

  async function postCaseAi(url, fields) {
    const body = new URLSearchParams(fields || {});
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken(),
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: body.toString(),
      credentials: "same-origin",
    });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || "خطای AI");
    return data;
  }

  document.querySelectorAll("[data-ai-assist]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const form = btn.closest("form");
      if (!form) return;
      const url = caseAiUrlFromForm(form);
      if (!url) {
        alert("ابتدا پرونده را انتخاب کنید.");
        return;
      }
      const result = form.querySelector("input[name='contact_result']:checked")?.value || "answered";
      const notes = form.querySelector("textarea[name='notes']")?.value || "";
      const hint = form.querySelector("[data-ai-hint]");
      btn.disabled = true;
      if (hint) {
        hint.hidden = false;
        hint.textContent = "AI در حال پیشنهاد گزارش و موعد…";
      }
      try {
        const data = await postCaseAi(url, {
          action: "call_assist",
          contact_result: result,
          draft_notes: notes,
        });
        const ta = form.querySelector("textarea[name='notes']");
        if (ta && data.notes) ta.value = data.notes;
        const follow = data.follow_preset;
        if (follow) {
          const radio = form.querySelector(`input[name='follow_preset'][value='${follow}']`);
          if (radio) {
            radio.checked = true;
            radio.dispatchEvent(new Event("change", { bubbles: true }));
          }
        }
        if (hint) {
          const tip = (data.tips && data.tips[0]) || data.follow_reason || "پیشنهاد آماده شد.";
          hint.textContent = tip;
        }
      } catch (err) {
        if (hint) {
          hint.hidden = false;
          hint.textContent = err.message || "خطا";
        }
      } finally {
        btn.disabled = false;
      }
    });
  });

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

  // Case AI analyze / personalized script
  const aiBox = document.getElementById("pnlAiBox");
  if (aiBox) {
    const runBtn = document.getElementById("pnlAiRun");
    const copyBtn = document.getElementById("pnlAiCopy");
    const statusEl = document.getElementById("pnlAiStatus");
    const bodyEl = document.getElementById("pnlAiBody");
    const csrf = document.querySelector("input[name=csrfmiddlewaretoken]")?.value
      || document.cookie.match(/csrftoken=([^;]+)/)?.[1]
      || "";

    function setStatus(text, isError) {
      if (!statusEl) return;
      statusEl.hidden = !text;
      statusEl.textContent = text || "";
      statusEl.classList.toggle("is-error", !!isError);
    }

    function fillList(ul, items) {
      if (!ul) return;
      ul.innerHTML = "";
      const list = (items && items.length) ? items : ["—"];
      list.forEach((item, idx) => {
        const li = document.createElement("li");
        li.textContent = item;
        if (!items || !items.length) li.classList.add("is-muted");
        ul.appendChild(li);
      });
    }

    function renderAi(data) {
      if (bodyEl) bodyEl.hidden = false;
      const profile = document.getElementById("pnlAiProfile");
      const next = document.getElementById("pnlAiNext");
      const tone = document.getElementById("pnlAiTone");
      const script = document.getElementById("pnlAiScript");
      if (profile) profile.textContent = data.profile || "";
      if (next) next.textContent = data.next_action || "";
      if (tone) tone.textContent = data.tone ? `لحن: ${data.tone}` : "";
      fillList(document.getElementById("pnlAiStrengths"), data.strengths || []);
      fillList(document.getElementById("pnlAiRisks"), data.risks || []);
      if (script) {
        script.innerHTML = "";
        (data.script_lines || []).forEach((line) => {
          const li = document.createElement("li");
          li.textContent = line;
          script.appendChild(li);
        });
      }
      if (copyBtn) copyBtn.hidden = !(data.script_lines && data.script_lines.length);
      if (runBtn) runBtn.textContent = "بازنویسی";
      persianizeTextNodes(aiBox);
    }

    async function runAi(force) {
      if (!aiBox.dataset.aiUrl) return;
      if (aiBox.dataset.aiEnabled !== "1") {
        setStatus("کلید MiMo تنظیم نشده است.", true);
        return;
      }
      aiBox.classList.add("is-loading");
      setStatus("در حال تحلیل فرم و نوشتن اسکریپت…");
      try {
        const body = new URLSearchParams();
        body.set("force", force ? "1" : "0");
        const res = await fetch(aiBox.dataset.aiUrl, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrf,
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: body.toString(),
          credentials: "same-origin",
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.error || "خطا در تحلیل");
        }
        renderAi(data);
        if (data.fallback) {
          setStatus(data.error || "حالت پشتیبان: اسکریپت ثابت مرحله.", true);
        } else if (data.cached) {
          setStatus("از کش قبلی بارگذاری شد.");
        } else {
          setStatus("تحلیل آماده است.");
        }
      } catch (err) {
        setStatus(err.message || "خطا", true);
      } finally {
        aiBox.classList.remove("is-loading");
      }
    }

    runBtn?.addEventListener("click", () => runAi(true));
    copyBtn?.addEventListener("click", async () => {
      const lines = [...(document.querySelectorAll("#pnlAiScript li") || [])]
        .map((li) => li.textContent.trim())
        .filter(Boolean);
      if (!lines.length) return;
      try {
        await navigator.clipboard.writeText(lines.join("\n"));
        setStatus("اسکریپت کپی شد.");
      } catch (_) {
        setStatus("کپی نشد؛ دستی انتخاب کنید.", true);
      }
    });

    const waBtn = document.getElementById("pnlAiWa");
    const waBox = document.getElementById("pnlAiWaBox");
    waBtn?.addEventListener("click", async () => {
      if (aiBox.dataset.aiEnabled !== "1") {
        setStatus("کلید MiMo تنظیم نشده است.", true);
        return;
      }
      aiBox.classList.add("is-loading");
      setStatus("در حال نوشتن پیش‌نویس واتساپ…");
      try {
        const data = await postCaseAi(aiBox.dataset.aiUrl, { action: "whatsapp" });
        const shortEl = document.getElementById("pnlAiWaShort");
        const formalEl = document.getElementById("pnlAiWaFormal");
        const noEl = document.getElementById("pnlAiWaNo");
        if (shortEl) shortEl.textContent = data.short || "";
        if (formalEl) formalEl.textContent = data.formal || "";
        if (noEl) noEl.textContent = data.no_answer || "";
        if (waBox) waBox.hidden = false;
        setStatus(data.fallback ? "پیش‌نویس پیش‌فرض آماده شد." : "پیش‌نویس واتساپ آماده است.");
        persianizeTextNodes(waBox);
      } catch (err) {
        setStatus(err.message || "خطا", true);
      } finally {
        aiBox.classList.remove("is-loading");
      }
    });

    document.querySelectorAll("[data-copy-wa]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const el = document.getElementById(btn.dataset.copyWa);
        const text = el?.textContent?.trim() || "";
        if (!text) return;
        try {
          await navigator.clipboard.writeText(text);
          setStatus("پیام کپی شد.");
        } catch (_) {
          setStatus("کپی نشد.", true);
        }
      });
    });
  }
});
