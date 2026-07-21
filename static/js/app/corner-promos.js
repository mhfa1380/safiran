/**
 * پاپ‌آپ گوشه: ارزیابی چپ، بله راست.
 * وضعیت در localStorage: expanded | minimized (۳۰ روز) | dismissed (برای همیشه با چک‌باکس).
 */
(function () {
    "use strict";

    var STORAGE_PREFIX = "safiran_corner_";
    var MINIMIZE_MS = 30 * 24 * 60 * 60 * 1000;

    /** وضعیت اولیه بدون localStorage: بله باز، ارزیابی بسته (فقط دکمه پایین). */
    function defaultState(id) {
        if (id === "eval") {
            return "minimized";
        }
        if (id === "bale") {
            return "expanded";
        }
        return "expanded";
    }

    function readState(id) {
        var raw = null;
        try {
            raw = localStorage.getItem(STORAGE_PREFIX + id);
        } catch (e) {
            return defaultState(id);
        }
        if (!raw) {
            return defaultState(id);
        }
        try {
            var data = JSON.parse(raw);
            if (data.dismissed) {
                return "hidden";
            }
            if (data.minimizedUntil && Date.now() < data.minimizedUntil) {
                return "minimized";
            }
            if (data.minimizedUntil) {
                try {
                    localStorage.removeItem(STORAGE_PREFIX + id);
                } catch (err) {
                    /* ignore */
                }
            }
            return defaultState(id);
        } catch (e2) {
            return defaultState(id);
        }
    }

    function writeMinimized(id) {
        try {
            localStorage.setItem(
                STORAGE_PREFIX + id,
                JSON.stringify({ minimizedUntil: Date.now() + MINIMIZE_MS })
            );
        } catch (e) {
            /* ignore */
        }
    }

    function writeDismissed(id) {
        try {
            localStorage.setItem(STORAGE_PREFIX + id, JSON.stringify({ dismissed: true }));
        } catch (e) {
            /* ignore */
        }
    }

    function applyState(el, state) {
        el.classList.remove("is-minimized", "is-hidden", "is-expanded");
        if (state === "hidden") {
            el.classList.add("is-hidden");
            el.hidden = true;
            refreshStack();
            return;
        }
        el.hidden = false;
        if (state === "minimized") {
            el.classList.add("is-minimized");
        } else {
            el.classList.add("is-expanded");
        }
        refreshStack();
    }

    function refreshStack() {
        var root = document.getElementById("cornerPromos");
        if (!root) {
            return;
        }
        window.requestAnimationFrame(function () {
            recalcStack(root);
        });
    }

    function minimize(el, id, never) {
        if (never) {
            writeDismissed(id);
            applyState(el, "hidden");
            return;
        }
        writeMinimized(id);
        applyState(el, "minimized");
        var neverInput = el.querySelector("[data-corner-never]");
        if (neverInput) {
            neverInput.checked = false;
        }
    }

    function bindPromo(el) {
        var id = el.getAttribute("data-corner-promo");
        if (!id) {
            return;
        }

        var state = readState(id);
        applyState(el, state);

        var fab = el.querySelector("[data-corner-fab]");
        var closeBtn = el.querySelector("[data-corner-close]");
        var cta = el.querySelector("[data-corner-cta]");
        var neverInput = el.querySelector("[data-corner-never]");

        if (fab) {
            fab.addEventListener("click", function () {
                if (el.classList.contains("is-minimized")) {
                    applyState(el, "expanded");
                }
            });
        }

        if (closeBtn) {
            closeBtn.addEventListener("click", function () {
                var never = neverInput && neverInput.checked;
                minimize(el, id, never);
            });
        }

        if (cta) {
            cta.addEventListener("click", function () {
                minimize(el, id, false);
            });
        }
    }

    function init() {
        var root = document.getElementById("cornerPromos");
        if (!root) {
            return;
        }
        var promos = root.querySelectorAll("[data-corner-promo]");
        for (var i = 0; i < promos.length; i++) {
            bindPromo(promos[i]);
        }
        refreshStack();
    }

    function recalcStack(root) {
        var promos = root.querySelectorAll("[data-corner-promo]");
        var groups = { left: [], right: [] };
        var anchors = ["left", "right"];
        var i;
        var j;
        var el;
        var anchor;

        for (i = 0; i < promos.length; i++) {
            el = promos[i];
            el.style.setProperty("--corner-stack-offset", "0px");
            if (el.classList.contains("is-hidden")) {
                continue;
            }
            anchor = el.getAttribute("data-corner-anchor") || "left";
            if (!groups[anchor]) {
                anchor = "left";
            }
            groups[anchor].push(el);
        }

        for (j = 0; j < anchors.length; j++) {
            anchor = anchors[j];
            var offset = 0;
            var list = groups[anchor];
            for (i = 0; i < list.length; i++) {
                el = list[i];
                var fab = el.querySelector(".corner-promo__fab");
                var panel = el.querySelector(".corner-promo__panel");
                var h = 0;
                if (el.classList.contains("is-minimized") && fab) {
                    h = fab.offsetHeight || 52;
                } else if (panel && panel.offsetHeight) {
                    h = panel.offsetHeight;
                } else {
                    h = el.classList.contains("is-minimized") ? 52 : 140;
                }
                el.style.setProperty("--corner-stack-offset", offset + "px");
                offset += h + 12;
            }
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.addEventListener("resize", function () {
        var root = document.getElementById("cornerPromos");
        if (root) {
            recalcStack(root);
        }
    });
})();
