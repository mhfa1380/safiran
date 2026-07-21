/**
 * انتخاب منبع آشنایی — کارت‌ها + شبکه اجتماعی + جزئیات
 */
(function (global) {
    "use strict";

    var SRC_SOCIAL = "social";
    var SRC_GOOGLE = "google";
    var SRC_OTHER = "other";

    function qs(sel, root) {
        return (root || document).querySelector(sel);
    }
    function qsa(sel, root) {
        return Array.prototype.slice.call((root || document).querySelectorAll(sel));
    }

    function getHidden(root, name) {
        return root.querySelector('input[type="hidden"][name="' + name + '"]');
    }

    function setPressed(btn, on) {
        if (!btn) return;
        btn.classList.toggle("is-selected", !!on);
        btn.setAttribute("aria-pressed", on ? "true" : "false");
    }

    function updateDetailPanel(root, src) {
        var panel = qs('[data-ref-panel="detail"]', root);
        var label = qs("[data-ref-detail-label]", root);
        var input = qs(".ref-src__detail-input", root) || getHidden(root, "referral_detail");
        if (!panel) return;

        if (src === SRC_GOOGLE) {
            panel.hidden = false;
            if (label) {
                label.textContent = "چه عبارتی در گوگل جستجو کردید؟";
                var opt = document.createElement("span");
                opt.className = "ref-src__optional";
                opt.textContent = " (اختیاری)";
                label.textContent = "چه عبارتی در گوگل جستجو کردید؟ (اختیاری)";
            }
            if (input && input.tagName === "INPUT") {
                input.placeholder = "مثلاً مهاجرت تحصیلی کانادا، ارزیابی رایگان…";
                input.removeAttribute("required");
            }
            return;
        }
        if (src === SRC_OTHER) {
            panel.hidden = false;
            if (label) label.textContent = "منبع را بنویسید";
            if (input && input.tagName === "INPUT") {
                input.placeholder = "مثلاً رادیو، نمایشگاه، کانال یوتیوب…";
                input.setAttribute("required", "required");
            }
            return;
        }
        panel.hidden = true;
        if (input && input.tagName === "INPUT") {
            input.value = "";
            input.removeAttribute("required");
        }
    }

    function updateSocialPanel(root, src) {
        var panel = qs('[data-ref-panel="social"]', root);
        if (!panel) return;
        var show = src === SRC_SOCIAL;
        panel.hidden = !show;
        if (!show) {
            var socialInp = getHidden(root, "referral_social_platform");
            if (socialInp) socialInp.value = "";
            qsa("[data-ref-social]", root).forEach(function (b) {
                setPressed(b, false);
            });
        }
    }

    function selectSource(root, value) {
        var inp = getHidden(root, "referral_source");
        if (inp) inp.value = value || "";
        qsa("[data-ref-src]", root).forEach(function (btn) {
            setPressed(btn, btn.getAttribute("data-ref-src") === value);
        });
        root.classList.remove("is-invalid");
        updateSocialPanel(root, value);
        updateDetailPanel(root, value);
    }

    function selectSocial(root, value) {
        var inp = getHidden(root, "referral_social_platform");
        if (inp) inp.value = value || "";
        qsa("[data-ref-social]", root).forEach(function (btn) {
            setPressed(btn, btn.getAttribute("data-ref-social") === value);
        });
        var panel = qs('[data-ref-panel="social"]', root);
        if (panel) panel.classList.remove("is-invalid");
    }

    function init(root) {
        if (!root || root.getAttribute("data-referral-inited") === "1") return;
        root.setAttribute("data-referral-inited", "1");

        var srcInp = getHidden(root, "referral_source");
        var initial = srcInp ? srcInp.value : "";
        if (initial) {
            selectSource(root, initial);
            var socInp = getHidden(root, "referral_social_platform");
            if (socInp && socInp.value) selectSocial(root, socInp.value);
        }

        qsa("[data-ref-src]", root).forEach(function (btn) {
            btn.addEventListener("click", function () {
                selectSource(root, btn.getAttribute("data-ref-src"));
            });
        });
        qsa("[data-ref-social]", root).forEach(function (btn) {
            btn.addEventListener("click", function () {
                selectSocial(root, btn.getAttribute("data-ref-social"));
            });
        });
    }

    function validate(root) {
        if (!root) return true;
        var ok = true;
        var srcInp = getHidden(root, "referral_source");
        var src = srcInp ? String(srcInp.value || "").trim() : "";

        root.classList.remove("is-invalid");
        var socialPanel = qs('[data-ref-panel="social"]', root);
        var detailPanel = qs('[data-ref-panel="detail"]', root);
        if (socialPanel) socialPanel.classList.remove("is-invalid");
        if (detailPanel) detailPanel.classList.remove("is-invalid");

        if (!src) {
            root.classList.add("is-invalid");
            ok = false;
        }

        if (src === SRC_SOCIAL) {
            var socInp = getHidden(root, "referral_social_platform");
            if (!socInp || !String(socInp.value || "").trim()) {
                if (socialPanel) socialPanel.classList.add("is-invalid");
                ok = false;
            }
        }

        if (src === SRC_OTHER) {
            var detailInp = qs(".ref-src__detail-input", root);
            if (!detailInp || !String(detailInp.value || "").trim()) {
                if (detailPanel) detailPanel.classList.add("is-invalid");
                if (detailInp) detailInp.classList.add("is-invalid");
                ok = false;
            }
        }

        if (!ok) {
            var first = qs(".ref-src__card", root);
            if (first && typeof first.focus === "function") {
                try {
                    first.focus();
                } catch (e) {
                    /* ignore */
                }
            }
        }
        return ok;
    }

    function initAll(scope) {
        qsa("[data-referral-picker]", scope || document).forEach(init);
    }

    global.SafiranReferralSource = {
        init: init,
        initAll: initAll,
        validate: validate,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            initAll(document);
        });
    } else {
        initAll(document);
    }
})(typeof window !== "undefined" ? window : this);
