/**
 * کپچای حروفی — نرمال‌سازی ورودی، کلیک برای کد جدید، به‌روزرسانی پس از خطا
 */
(function () {
    "use strict";

    var CAPTCHA_RE = /[^A-Za-z]/g;

    function normalizeCaptchaInput(input) {
        var start = input.selectionStart;
        var end = input.selectionEnd;
        var before = input.value;
        var after = before.replace(CAPTCHA_RE, "").toUpperCase();
        if (before === after) return;
        input.value = after;
        if (typeof start === "number" && typeof end === "number") {
            var removed = before.length - after.length;
            var pos = Math.max(0, (start || 0) - removed);
            try {
                input.setSelectionRange(pos, pos);
            } catch (err) {
                /* input types without selection */
            }
        }
    }

    function getRefreshUrl(block) {
        if (block && block.getAttribute("data-captcha-refresh-url")) {
            return block.getAttribute("data-captcha-refresh-url");
        }
        var cfg = window.PAGE_CONFIG || {};
        var base = cfg.captchaRefreshUrl || "";
        var formKey =
            (block && block.getAttribute("data-captcha-form")) ||
            cfg.captchaFormKey ||
            "";
        if (!base || !formKey) return "";
        var sep = base.indexOf("?") >= 0 ? "&" : "?";
        return base + sep + "form=" + encodeURIComponent(formKey);
    }

    function findBlock(el) {
        if (!el) return null;
        if (el.classList && el.classList.contains("form-captcha")) return el;
        return el.closest ? el.closest(".form-captcha") : null;
    }

    function findQuestionEl(block) {
        return block ? block.querySelector(".form-captcha__q") : null;
    }

    function findInputEl(block) {
        return block ? block.querySelector(".form-captcha__control") : null;
    }

    function clearCaptchaError(block) {
        if (!block) return;
        block.classList.remove("has-error");
        var err = block.querySelector(".form-captcha__error");
        if (err) err.textContent = "";
        var inp = findInputEl(block);
        if (inp) {
            inp.classList.remove("is-invalid");
            inp.removeAttribute("aria-invalid");
        }
    }

    function applyQuestion(block, question) {
        if (!block || !question) return;
        var q = findQuestionEl(block);
        if (q) q.textContent = question;
        var inp = findInputEl(block);
        if (inp) {
            inp.value = "";
            inp.focus({ preventScroll: true });
        }
        clearCaptchaError(block);
        block.classList.add("form-captcha--refreshed");
        window.setTimeout(function () {
            block.classList.remove("form-captcha--refreshed");
        }, 450);
    }

    function refreshBlock(block) {
        var url = getRefreshUrl(block);
        if (!url) return Promise.resolve(false);
        var q = findQuestionEl(block);
        if (q) q.setAttribute("aria-busy", "true");
        return fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                if (data && data.ok && data.question) {
                    applyQuestion(block, data.question);
                    return true;
                }
                return false;
            })
            .catch(function () {
                return false;
            })
            .finally(function () {
                if (q) q.removeAttribute("aria-busy");
            });
    }

    function bindQuestion(block) {
        var q = findQuestionEl(block);
        if (!q || q.dataset.captchaClickBound === "1") return;
        q.dataset.captchaClickBound = "1";
        q.setAttribute("role", "button");
        q.setAttribute("tabindex", "0");
        q.setAttribute("title", "کلیک برای نمایش کد جدید");
        q.setAttribute("aria-label", "کد امنیتی جدید — کلیک کنید");

        function onActivate(e) {
            if (e.type === "keydown" && e.key !== "Enter" && e.key !== " ") return;
            if (e.type === "keydown") e.preventDefault();
            refreshBlock(block);
        }

        q.addEventListener("click", onActivate);
        q.addEventListener("keydown", onActivate);
    }

    function bindInput(input) {
        if (!input || input.dataset.captchaBound === "1") return;
        input.dataset.captchaBound = "1";
        input.addEventListener("input", function () {
            normalizeCaptchaInput(input);
        });
        input.addEventListener("paste", function () {
            window.setTimeout(function () {
                normalizeCaptchaInput(input);
            }, 0);
        });
    }

    function initBlock(block) {
        if (!block || block.dataset.captchaInit === "1") return;
        block.dataset.captchaInit = "1";
        bindQuestion(block);
        var inp = findInputEl(block);
        if (inp) bindInput(inp);
    }

    function init(root) {
        var scope = root || document;
        scope.querySelectorAll(".form-captcha").forEach(initBlock);
    }

    window.SafiranCaptcha = {
        refresh: function (formKeyOrBlock) {
            var block =
                typeof formKeyOrBlock === "string"
                    ? document.querySelector(
                          '.form-captcha[data-captcha-form="' + formKeyOrBlock + '"]'
                      )
                    : findBlock(formKeyOrBlock);
            if (!block) return Promise.resolve(false);
            return refreshBlock(block);
        },
        applyQuestion: function (formKeyOrBlock, question) {
            var block =
                typeof formKeyOrBlock === "string"
                    ? document.querySelector(
                          '.form-captcha[data-captcha-form="' + formKeyOrBlock + '"]'
                      )
                    : findBlock(formKeyOrBlock);
            if (!block) return;
            applyQuestion(block, question);
        },
        init: init,
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            init(document);
        });
    } else {
        init(document);
    }
})();
