/**
 * فرم ارزیابی — ویزارد، اعتبارسنجی لایو، چیپ‌ها، کارت کشور
 */
(function () {
    "use strict";

    var form = document.getElementById("evalWizardForm");
    if (!form) return;

    var refreshCountrySuggest = function () {};

    var global = typeof window !== "undefined" ? window : {};
    var pageConfig = window.PAGE_CONFIG || {};

    var panels = form.querySelectorAll(".eval_wizard-panel");
    var steps = document.querySelectorAll(".eval_step-nav li");
    var mobileProgress = document.getElementById("evalMobileProgress");
    var sidebarProgress = document.getElementById("evalSidebarProgress");
    var sidebarGuideTitle = document.getElementById("evalSidebarGuideTitle");
    var sidebarGuideList = document.getElementById("evalSidebarGuideList");

    var SIDEBAR_GUIDE = {
        1: {
            title: "مرحله ۱ — اطلاعات شخصی",
            items: [
                "نام و شماره تماس برای تماس کارشناس و گزارش شخصی‌سازی‌شده لازم است.",
                "سال تولد و ایمیل اختیاری‌اند؛ در صورت تمایل وارد کنید.",
                "وضعیت تأهل و زمان اپلای به پیشنهاد مسیر کمک می‌کند.",
            ],
        },
        2: {
            title: "مرحله ۲ — سوابق تحصیلی",
            items: [
                "آخرین مدرک و رشته تحصیلی را دقیق از لیست یا به‌صورت دستی وارد کنید.",
                "معدل را از ۲۰ یا به‌صورت درصد (مثلاً ۸۵٪) وارد کنید.",
                "سال فارغ‌التحصیلی در صورت نیاز تکمیل شود.",
            ],
        },
        3: {
            title: "مرحله ۳ — زبان و دستاوردها (اختیاری)",
            items: [
                "کل این مرحله اختیاری است؛ می‌توانید «ندارم» بگذارید و به مرحله بعد بروید.",
                "اگر نمره وارد کنید، باید در بازه معتبر همان آزمون باشد.",
                "دستاوردهای علمی هم اختیاری‌اند.",
            ],
        },
        4: {
            title: "مرحله ۴ — اولویت‌ها",
            items: [
                "حداقل یک کشور مقصد و کد امنیتی الزامی است.",
                "رشته مورد نظر الزامی است؛ همکاری، ترم و توضیحات اختیاری‌اند.",
                "پس از ثبت، الگوریتم کشور، دانشگاه و رشته پیشنهاد می‌دهد.",
            ],
        },
    };
    var btnPrev = document.getElementById("evalPrev");
    var btnNext = document.getElementById("evalNext");
    var btnSubmit = document.getElementById("evalSubmit");
    var langWrap = document.getElementById("evalLangScoreWrap");
    var langSelect = form.querySelector('[name="language_test_type"]');
    var gpaFeedback = document.getElementById("evalGpaFeedback");
    var phoneFeedback = document.getElementById("evalPhoneFeedback");
    var langFeedback = document.getElementById("evalLangFeedback");

    var REAL_COUNTRIES = Array.isArray(pageConfig.evalRealCountryCodes)
        ? pageConfig.evalRealCountryCodes
        : ["canada", "spain", "china", "germany", "italy", "uk", "usa", "australia"];

    var LANG_RANGES = {
        ielts: { lo: 0, hi: 9, label: "IELTS" },
        toefl: { lo: 0, hi: 120, label: "TOEFL iBT" },
        duolingo: { lo: 0, hi: 160, label: "Duolingo" },
        pte: { lo: 0, hi: 90, label: "PTE" },
        delf: { lo: 1, hi: 4, label: "DELF/DALF" },
        testdaf: { lo: 1, hi: 5, label: "TestDaF" },
        sat: { lo: 400, hi: 1600, label: "SAT" },
        yos: { lo: 0, hi: 100, label: "YOS" },
    };

    var current = 1;
    var total = panels.length;

    var EVAL_FIELD_PANEL = {
        full_name: 1,
        phone: 1,
        email: 1,
        birth_year: 1,
        marital_status: 1,
        apply_timeline: 1,
        current_degree: 2,
        field_of_study: 2,
        average_grade: 2,
        graduation_year: 2,
        language_test_type: 3,
        language_score: 3,
        desired_countries: 4,
        desired_major: 4,
        service_scope: 4,
        preferred_intake: 4,
        notes: 4,
        referral_source: 4,
        referral_social_platform: 4,
        referral_detail: 4,
        captcha_answer: 4,
        captcha: 4,
    };

    var EVAL_FIELD_HINTS = {
        full_name: "نام و نام خانوادگی را وارد کنید.",
        phone: "شماره تماس را وارد کنید.",
        current_degree: "آخرین مدرک تحصیلی را انتخاب کنید.",
        field_of_study: "رشته تحصیلی را وارد کنید.",
        average_grade: "معدل را وارد کنید.",
        desired_countries: "حداقل یک کشور مقصد را انتخاب کنید.",
        captcha_answer: "کد امنیتی (کپچا) را وارد کنید.",
        captcha: "کد امنیتی (کپچا) را وارد کنید.",
        language_score: "نمره آزمون زبان را درست وارد کنید.",
        preferred_intake: "ترم / سال شروع را درست انتخاب کنید.",
        notes: "در صورت نیاز توضیحات تکمیلی را بنویسید.",
        desired_major: "رشته مورد نظر را وارد کنید.",
        service_scope: "نوع همکاری با موسسه را انتخاب کنید.",
        referral_source: "از کجا با ما آشنا شدید را انتخاب کنید.",
        referral_social_platform: "شبکه اجتماعی را انتخاب کنید.",
        referral_detail: "جزئیات منبع را بنویسید.",
    };

    /* فقط فیلدهای اجباری (مطابق مدل/سرور) در درصد فرم */
    var FORM_PROGRESS_FIELDS = [
        { key: "full_name", step: 1, label: "نام و نام خانوادگی" },
        { key: "phone", step: 1, label: "شماره تماس" },
        { key: "current_degree", step: 2, label: "آخرین مدرک" },
        { key: "field_of_study", step: 2, label: "رشته تحصیلی" },
        { key: "average_grade", step: 2, label: "معدل" },
        { key: "desired_countries", step: 4, type: "countries", label: "کشور مقصد" },
        { key: "desired_major", step: 4, label: "رشته مورد نظر" },
        { key: "captcha_answer", step: 4, label: "کد امنیتی (کپچا)" },
    ];

    var DRAFT_STORAGE_KEY = "safiran_eval_wizard_draft";
    var DRAFT_VERSION = 1;
    var DRAFT_TTL_MS = 7 * 24 * 60 * 60 * 1000;
    var DRAFT_SKIP_FIELDS = { csrfmiddlewaretoken: true, captcha_answer: true };
    var draftSaveTimer = null;
    var fieldProgressTimer = null;
    var draftRestored = false;

    function qs(name) {
        return form.querySelector('[name="' + name + '"]');
    }

    function toEnDigits(s) {
        return String(s || "")
            .replace(/[۰-۹]/g, function (c) {
                return String(c.charCodeAt(0) - 1728);
            })
            .replace(/[٠-٩]/g, function (c) {
                return String(c.charCodeAt(0) - 1632);
            })
            .replace(/٫/g, ".")
            .replace(/،/g, ".")
            .replace(/,/g, ".");
    }

    function firstNumber(s) {
        var m = toEnDigits(s).match(/(\d+(?:\.\d+)?)/);
        return m ? parseFloat(m[1]) : null;
    }

    function normalizeNumericFieldValue(raw, keepPercent) {
        var text = String(raw || "").trim();
        if (!text) return "";
        var hasPercent =
            keepPercent &&
            (text.indexOf("%") >= 0 || text.indexOf("٪") >= 0 || text.indexOf("درصد") >= 0);
        var norm = toEnDigits(text);
        var num = firstNumber(norm);
        if (num === null) return norm;
        var out = String(num);
        if (hasPercent) out += "%";
        return out;
    }

    function bindNumericInputNormalization(name, keepPercent) {
        var el = qs(name);
        if (!el || el.dataset.numericNormBound === "1") return;
        el.dataset.numericNormBound = "1";
        function applyNormalize() {
            var next = normalizeNumericFieldValue(el.value, keepPercent);
            if (next && next !== el.value) {
                el.value = next;
            }
        }
        el.addEventListener("blur", applyNormalize);
        el.addEventListener("change", applyNormalize);
    }

    function setFeedback(el, input, result) {
        if (!el) return;
        if (!result || !result.message) {
            el.hidden = true;
            el.textContent = "";
            el.className = "eval_feedback";
            if (input) input.classList.remove("is-invalid", "is-warn", "is-valid");
            return;
        }
        el.hidden = false;
        el.textContent = result.message;
        el.className = "eval_feedback eval_feedback--" + (result.status || "neutral");
        if (input) {
            input.classList.remove("is-invalid", "is-warn", "is-valid");
            if (result.status === "error") input.classList.add("is-invalid");
            else if (result.status === "warn") input.classList.add("is-warn");
            else if (result.status === "ok") input.classList.add("is-valid");
        }
    }

    function validateGpa(raw) {
        var text = String(raw || "").trim();
        if (!text) {
            return {
                status: "neutral",
                message: "معدل از ۰ تا ۲۰ (مثلاً ۱۷.۵). برای درصد: ۸۵٪",
            };
        }
        if (text.indexOf("%") >= 0 || text.indexOf("٪") >= 0 || text.indexOf("درصد") >= 0) {
            var pct = firstNumber(text);
            if (pct === null || pct <= 0 || pct > 100) {
                return { status: "error", message: "درصد معدل باید بین ۱ تا ۱۰۰ باشد." };
            }
            return {
                status: "warn",
                message: "درصد " + pct + "٪ → معادل " + (pct * 0.2).toFixed(1) + " از ۲۰.",
            };
        }
        var val = firstNumber(text);
        if (val === null) {
            return { status: "error", message: "فقط عدد وارد کنید (مثلاً ۱۷.۵)." };
        }
        if (val <= 4.5) {
            return {
                status: "ok",
                message: "مقیاس ۴ → معادل " + (val * 5).toFixed(1) + " از ۲۰.",
            };
        }
        if (val >= 5 && val <= 20) {
            return { status: "ok", message: "معدل " + val + " از ۲۰ — معتبر است." };
        }
        if (val > 20 && val <= 100) {
            return {
                status: "warn",
                message:
                    "عدد " +
                    val +
                    " بالاتر از ۲۰ است — به‌عنوان درصد (" +
                    val +
                    "٪) تفسیر می‌شود (معادل " +
                    (val * 0.2).toFixed(1) +
                    " از ۲۰).",
            };
        }
        return {
            status: "error",
            message:
                "معدل در مقیاس ایرانی بیش از ۲۰ نیست. برای درصد تا ۱۰۰٪ با علامت ٪ وارد کنید.",
        };
    }

    function validatePhone(raw) {
        var digits = toEnDigits(raw).replace(/\D/g, "");
        if (!digits) {
            return { status: "neutral", message: "شماره ۱۱ رقمی با ۰۹ (مثلاً ۰۹۱۲۳۴۵۶۷۸۹)." };
        }
        if (digits.indexOf("98") === 0 && digits.length >= 12) {
            digits = "0" + digits.slice(2);
        }
        if (digits.indexOf("09") !== 0) {
            return { status: "error", message: "شماره باید با ۰۹ شروع شود." };
        }
        if (digits.length !== 11) {
            return {
                status: "error",
                message: "شماره باید ۱۱ رقم باشد (فعلاً " + digits.length + " رقم).",
            };
        }
        return { status: "ok", message: "شماره تماس معتبر است." };
    }

    function validateLangScore(testType, raw) {
        if (!testType || testType === "none") {
            return { status: "neutral", message: "" };
        }
        var text = String(raw || "").trim();
        if (!text) {
            return { status: "neutral", message: "نمره آزمون را وارد کنید (اختیاری)." };
        }
        var val = firstNumber(text);
        if (val === null) {
            return { status: "error", message: "فقط عدد نمره را وارد کنید." };
        }
        var bounds = LANG_RANGES[testType];
        if (!bounds) {
            return { status: "ok", message: "نمره ثبت شد." };
        }
        if (val < bounds.lo || val > bounds.hi) {
            return {
                status: "error",
                message:
                    "برای " + bounds.label + " بازه معتبر حدود " + bounds.lo + " تا " + bounds.hi + " است.",
            };
        }
        return {
            status: "ok",
            message: "نمره " + val + " برای " + bounds.label + " در بازه معتبر است.",
        };
    }

    function isBlocking(result) {
        return result && result.status === "error";
    }

    function liveGpa() {
        var el = qs("average_grade");
        if (!el) return { status: "neutral", message: "" };
        var r = validateGpa(el.value);
        setFeedback(gpaFeedback, el, r);
        return r;
    }

    function livePhone() {
        var el = qs("phone");
        if (!el) return { status: "neutral", message: "" };
        var r = validatePhone(el.value);
        setFeedback(phoneFeedback, el, r);
        return r;
    }

    function liveLang() {
        var inp = qs("language_score");
        var test = langSelect ? langSelect.value : "none";
        var r = validateLangScore(test, inp ? inp.value : "");
        setFeedback(langFeedback, inp, r);
        return r;
    }

    function hasSelectedDestinationCountry() {
        return form.querySelectorAll('input[name="desired_countries"]:checked').length > 0;
    }

    function hideCountrySelectionError() {
        var countryError = document.getElementById("evalCountryError");
        if (countryError) countryError.hidden = true;
        var grid = document.getElementById("evalCountryGrid");
        if (grid) grid.classList.remove("is-invalid");
    }

    function updateWizardActions() {
        if (hasSelectedDestinationCountry()) hideCountrySelectionError();
    }

    function markCountryGridInvalid() {
        var grid = document.getElementById("evalCountryGrid");
        if (!grid) return;
        grid.classList.add("is-invalid", "eval_shake");
        setTimeout(function () {
            grid.classList.remove("eval_shake");
        }, 450);
        var countryError = document.getElementById("evalCountryError");
        if (countryError) countryError.hidden = false;
        grid.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function syncTargetCountry() {
        var target = qs("target_country");
        if (!target) return;
        var checked = form.querySelectorAll('input[name="desired_countries"]:checked');
        var i;
        for (i = 0; i < checked.length; i++) {
            if (REAL_COUNTRIES.indexOf(checked[i].value) >= 0) {
                target.value = checked[i].value;
                return;
            }
        }
        for (i = 0; i < checked.length; i++) {
            if (checked[i].value === "other") {
                target.value = "other";
                return;
            }
        }
        target.value = checked.length ? checked[0].value : "";
    }

    function syncHasIelts() {
        var hidden = qs("has_ielts");
        if (!hidden || !langSelect) return;
        hidden.value = langSelect.value && langSelect.value !== "none" ? "on" : "";
    }

    function toPersianDigits(n) {
        return String(n).replace(/\d/g, function (d) {
            return "۰۱۲۳۴۵۶۷۸۹"[parseInt(d, 10)];
        });
    }

    function langTestSelected() {
        return langSelect && langSelect.value && langSelect.value !== "none";
    }

    function isFieldFilledForProgress(spec) {
        if (spec.type === "countries") return hasSelectedDestinationCountry();
        var el = qs(spec.key);
        if (!el) return false;
        var val = String(el.value || "").trim();
        if (!val) return false;
        if (spec.key === "phone") return !isBlocking(livePhone());
        if (spec.key === "average_grade") return !isBlocking(liveGpa());
        return true;
    }

    function computeFieldProgress() {
        var totalW = 0;
        var filledW = 0;
        FORM_PROGRESS_FIELDS.forEach(function (spec) {
            totalW += 1;
            if (isFieldFilledForProgress(spec)) filledW += 1;
        });
        var complete = totalW > 0 ? Math.round((filledW / totalW) * 100) : 0;
        if (complete > 100) complete = 100;
        if (complete < 0) complete = 0;
        return { complete: complete, remain: 100 - complete };
    }

    function scheduleFieldProgressUpdate() {
        if (fieldProgressTimer) clearTimeout(fieldProgressTimer);
        fieldProgressTimer = setTimeout(function () {
            updateWizardProgressUI(current);
        }, 60);
    }

    function panelDefaultHint(step) {
        var panel = form.querySelector('.eval_wizard-panel[data-panel="' + step + '"]');
        return panel ? panel.getAttribute("data-hint") || "" : "";
    }

    function showValidationMessage(message) {
        document.querySelectorAll("[data-eval-validation]").forEach(function (node) {
            if (message) {
                node.textContent = message;
                node.hidden = false;
            } else {
                node.textContent = "";
                node.hidden = true;
            }
        });
        if (message) {
            setTextAll("[data-eval-hint]", message);
        } else {
            setTextAll("[data-eval-hint]", panelDefaultHint(current));
        }
    }

    function validationFail(message, el) {
        if (el) markInvalid(el);
        showValidationMessage(message);
        scrollWizardIntoView();
        if (el && typeof el.focus === "function") {
            setTimeout(function () {
                el.focus({ preventScroll: true });
            }, 200);
        }
        return false;
    }

    function setProgressBar(el, pct, label) {
        if (!el) return;
        el.style.width = pct + "%";
        el.setAttribute("aria-valuenow", String(Math.round(pct)));
        if (label) el.setAttribute("aria-label", label);
    }

    function setTextAll(selector, text) {
        document.querySelectorAll(selector).forEach(function (el) {
            el.textContent = text;
        });
    }

    function wizardHeaderOffset() {
        var nav = document.querySelector(".site-header") || document.querySelector(".main_menu");
        if (!nav) return 88;
        return Math.ceil(nav.getBoundingClientRect().height) + 16;
    }

    /** بعدی/قبلی — همیشه بالای کارت فرم (نه پایین صفحه) */
    function scrollWizardIntoView() {
        var target =
            document.querySelector(".eval_main-flow__form") ||
            document.querySelector(".eval_form-card");
        if (!target) return;
        var top = target.getBoundingClientRect().top + window.pageYOffset - wizardHeaderOffset();
        window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
    }

    function firstHintEl() {
        return document.querySelector("[data-eval-hint]");
    }

    function updateSidebarGuide(step) {
        var guide = SIDEBAR_GUIDE[step] || SIDEBAR_GUIDE[1];
        if (sidebarGuideTitle) sidebarGuideTitle.textContent = guide.title;
        if (!sidebarGuideList) return;
        sidebarGuideList.innerHTML = "";
        guide.items.forEach(function (text) {
            var li = document.createElement("li");
            li.textContent = text;
            sidebarGuideList.appendChild(li);
        });
    }

    function updateWizardProgressUI(step) {
        var p = computeFieldProgress();
        var faStep = toPersianDigits(step);
        var faTotal = toPersianDigits(total);
        var faComplete = toPersianDigits(p.complete);
        var faRemain = toPersianDigits(p.remain);
        var stepText = "مرحله " + faStep + " از " + faTotal;

        var barLabel = stepText + " — " + p.complete + "% از فیلدهای فرم";
        document.querySelectorAll("[data-eval-progress-bar]").forEach(function (el) {
            setProgressBar(el, p.complete, barLabel);
        });

        setTextAll("[data-eval-step-label]", stepText);
        setTextAll("[data-eval-percent]", faComplete + "٪");
        setTextAll("[data-eval-remain]", faRemain + "٪ تا پایان فرم");

        document.querySelectorAll("[data-eval-step-nav] li").forEach(function (li) {
            var s = parseInt(li.getAttribute("data-step"), 10);
            li.classList.toggle("is-active", s === step);
            li.classList.toggle("is-done", s < step);
        });

        var validationVisible = false;
        document.querySelectorAll("[data-eval-validation]").forEach(function (node) {
            validationVisible = validationVisible || !node.hidden;
        });
        if (!validationVisible) {
            setTextAll("[data-eval-hint]", panelDefaultHint(step));
        }

        updateSidebarGuide(step);
    }

    function showPanel(n, animate) {
        current = n;
        showValidationMessage("");
        if (n === total) hideCountrySelectionError();
        panels.forEach(function (panel) {
            var p = parseInt(panel.getAttribute("data-panel"), 10);
            var active = p === n;
            panel.hidden = !active;
            panel.classList.toggle("is-active", active);
            if (active && animate) {
                panel.classList.remove("eval_panel-enter");
                void panel.offsetWidth;
                panel.classList.add("eval_panel-enter");
            }
        });
        steps.forEach(function (li) {
            var s = parseInt(li.getAttribute("data-step"), 10);
            li.classList.toggle("is-active", s === n);
            li.classList.toggle("is-done", s < n);
            li.setAttribute("aria-selected", s === n ? "true" : "false");
            li.tabIndex = s === n ? 0 : -1;
        });
        updateWizardProgressUI(n);
        if (btnPrev) btnPrev.hidden = n <= 1;
        if (btnNext) btnNext.hidden = n >= total;
        if (btnSubmit) btnSubmit.hidden = n < total;
        updateWizardActions();
        if (animate) {
            scrollWizardIntoView();
        }
        var activePanel = form.querySelector('.eval_wizard-panel[data-panel="' + n + '"]');
        var first =
            activePanel &&
            activePanel.querySelector(
                "input.eval-input:not([type=hidden]):not(:disabled), textarea.eval-input, select.eval-input, button.eval_year-trigger"
            );
        if (first && animate) {
            setTimeout(function () {
                first.focus({ preventScroll: true });
            }, 420);
        }
        saveDraft();
        if (n === 4) refreshCountrySuggest();
    }

    function checkboxGroupSize(name) {
        return form.querySelectorAll('input[type="checkbox"][name="' + name + '"]').length;
    }

    function draftHasContent(fields) {
        if (!fields) return false;
        return Object.keys(fields).some(function (name) {
            var v = fields[name];
            if (Array.isArray(v)) return v.length > 0;
            return String(v || "").trim() !== "";
        });
    }

    function collectDraftFields() {
        var fields = {};
        form.querySelectorAll("input, select, textarea").forEach(function (el) {
            if (!el.name || DRAFT_SKIP_FIELDS[el.name]) return;
            if (el.type === "submit" || el.disabled) return;
            if (el.type === "checkbox") {
                if (checkboxGroupSize(el.name) > 1) {
                    if (!fields[el.name]) fields[el.name] = [];
                    if (el.checked) fields[el.name].push(el.value);
                } else {
                    fields[el.name] = el.checked ? el.value || "on" : "";
                }
                return;
            }
            if (el.type === "radio") {
                if (el.checked) fields[el.name] = el.value;
                return;
            }
            fields[el.name] = el.value;
        });
        return fields;
    }

    function saveDraft() {
        var fields = collectDraftFields();
        if (!draftHasContent(fields) && current <= 1) {
            clearDraft();
            return;
        }
        try {
            localStorage.setItem(
                DRAFT_STORAGE_KEY,
                JSON.stringify({
                    v: DRAFT_VERSION,
                    step: current,
                    fields: fields,
                    ts: Date.now(),
                })
            );
        } catch (err) {
            /* quota / private mode */
        }
    }

    function scheduleSaveDraft() {
        if (draftSaveTimer) clearTimeout(draftSaveTimer);
        draftSaveTimer = setTimeout(saveDraft, 350);
    }

    function clearDraft() {
        try {
            localStorage.removeItem(DRAFT_STORAGE_KEY);
        } catch (err) {
            /* ignore */
        }
    }

    function loadDraft() {
        try {
            var raw = localStorage.getItem(DRAFT_STORAGE_KEY);
            if (!raw) return null;
            var data = JSON.parse(raw);
            if (!data || data.v !== DRAFT_VERSION || !data.fields) return null;
            if (data.ts && Date.now() - data.ts > DRAFT_TTL_MS) {
                clearDraft();
                return null;
            }
            return data;
        } catch (err) {
            return null;
        }
    }

    function ensureSelectHasValue(select, value) {
        if (!select) return;
        if (!value) {
            select.value = "";
            return;
        }
        var val = String(value);
        var i;
        for (i = 0; i < select.options.length; i++) {
            if (select.options[i].value === val) {
                select.value = val;
                return;
            }
        }
        var opt = document.createElement("option");
        opt.value = val;
        opt.textContent = val;
        select.appendChild(opt);
        select.value = val;
    }

    function applyDraftValue(name, value) {
        var els = form.querySelectorAll('[name="' + name + '"]');
        if (!els.length) return;
        var first = els[0];
        if (first.tagName === "SELECT") {
            ensureSelectHasValue(first, value);
            return;
        }
        if (first.type === "checkbox") {
            if (Array.isArray(value)) {
                els.forEach(function (el) {
                    el.checked = value.indexOf(el.value) >= 0;
                });
            } else {
                els.forEach(function (el) {
                    el.checked = !!value;
                });
            }
            return;
        }
        if (first.type === "radio") {
            els.forEach(function (el) {
                el.checked = el.value === value;
            });
            return;
        }
        first.value = value == null ? "" : String(value);
    }

    function syncDraftUI() {
        form.querySelectorAll("[data-sync-select]").forEach(syncPickGroup);
        form.querySelectorAll("[data-year-picker]").forEach(function (trigger) {
            var name = trigger.getAttribute("data-year-picker");
            var select = qs(name);
            updateYearTrigger(trigger, select);
        });
        form.querySelectorAll(".eval_country-card").forEach(function (card) {
            var input = card.querySelector('input[type="checkbox"]');
            if (input) card.classList.toggle("is-selected", input.checked);
        });
        syncTargetCountry();
        toggleLangScore();
        liveGpa();
        livePhone();
        liveLang();
        updateWizardActions();
        scheduleFieldProgressUpdate();
    }

    function restoreDraft(draft) {
        if (!draft || !draft.fields) return false;
        if (!draftHasContent(draft.fields) && (!draft.step || draft.step <= 1)) return false;
        Object.keys(draft.fields).forEach(function (name) {
            applyDraftValue(name, draft.fields[name]);
        });
        syncDraftUI();
        draftRestored = true;
        return true;
    }

    function hasServerFormErrors() {
        return !!form.querySelector(".eval_error");
    }

    function resolveInitialStep(draft) {
        var serverInitial = parseInt(form.getAttribute("data-initial-step") || "1", 10);
        if (isNaN(serverInitial) || serverInitial < 1) serverInitial = 1;
        if (hasServerFormErrors()) return Math.min(serverInitial, total);
        if (draft && draft.step >= 1 && draft.step <= total) return draft.step;
        if (serverInitial > total) return total;
        return serverInitial;
    }

    function initDraftPersistence() {
        form.addEventListener("input", function () {
            scheduleSaveDraft();
            scheduleFieldProgressUpdate();
        });
        form.addEventListener("change", function () {
            scheduleSaveDraft();
            scheduleFieldProgressUpdate();
        });
    }

    function markInvalid(el) {
        if (!el) return;
        el.classList.add("is-invalid");
        var wrap = el.closest(
            ".eval_field, .eval_chips, .eval_country-grid, .eval_option-grid, .eval_service-scope, .eval_year-trigger, .major-combobox"
        );
        if (el.classList.contains("major-combobox__field")) {
            var combo = el.closest(".major-combobox");
            if (combo) combo.classList.add("is-invalid");
        }
        if (wrap) {
            wrap.classList.add("eval_shake");
            setTimeout(function () {
                wrap.classList.remove("eval_shake");
            }, 450);
        }
    }

    function pickLabel(select) {
        if (!select || !select.value) return "";
        var i;
        for (i = 0; i < select.options.length; i++) {
            if (select.options[i].value === select.value) {
                return select.options[i].text;
            }
        }
        return select.value;
    }

    function syncPickGroup(container) {
        var name = container.getAttribute("data-sync-select");
        var select = qs(name);
        if (!select) return;
        select.classList.add("eval_select-hidden");
        var val = select.value;
        container.querySelectorAll("[data-value]").forEach(function (btn) {
            btn.classList.toggle("is-selected", btn.getAttribute("data-value") === val);
        });
    }

    function yearPickerPlaceholder(select) {
        if (!select) return "انتخاب سال";
        if (select.name === "preferred_intake") return "انتخاب ترم / سال";
        return "انتخاب سال";
    }

    function updateYearTrigger(trigger, select) {
        if (!trigger || !select) return;
        var display = trigger.querySelector("[data-year-display]");
        var label = pickLabel(select);
        if (display) {
            display.textContent = label || yearPickerPlaceholder(select);
        }
        trigger.classList.toggle("is-placeholder", !select.value);
    }

    function clearInvalidInStep(n) {
        var panel = form.querySelector('.eval_wizard-panel[data-panel="' + n + '"]');
        if (!panel) return;
        panel.querySelectorAll(".is-invalid").forEach(function (el) {
            el.classList.remove("is-invalid");
        });
        panel.querySelectorAll(".major-combobox.is-invalid").forEach(function (el) {
            el.classList.remove("is-invalid");
        });
    }

    function normalizeDjangoError(raw) {
        if (raw == null || raw === "") return "";
        if (Array.isArray(raw)) {
            if (!raw.length) return "";
            return normalizeDjangoError(raw[0]);
        }
        if (typeof raw === "object" && raw.message) return String(raw.message).trim();
        return String(raw).trim();
    }

    function evalFieldMessage(field, serverMsg) {
        var msg = normalizeDjangoError(serverMsg);
        if (msg) return msg;
        if (EVAL_FIELD_HINTS[field]) return EVAL_FIELD_HINTS[field];
        return "لطفاً این بخش را تکمیل کنید.";
    }

    function markFieldInvalidByName(field) {
        if (
            field === "referral_source" ||
            field === "referral_social_platform" ||
            field === "referral_detail"
        ) {
            var picker = form.querySelector("[data-referral-picker]");
            if (picker && window.SafiranReferralSource) {
                window.SafiranReferralSource.validate(picker);
            }
            return;
        }
        if (field === "desired_countries") {
            markCountryGridInvalid();
            return;
        }
        if (field === "service_scope") {
            var scope = form.querySelector(".eval_service-scope");
            if (scope) {
                scope.classList.add("is-invalid", "eval_shake");
                setTimeout(function () {
                    scope.classList.remove("eval_shake");
                }, 450);
            }
            return;
        }
        var el = form.querySelector('[name="' + field + '"]');
        if (el) markInvalid(el);
    }

    function panelForField(field) {
        if (EVAL_FIELD_PANEL[field]) return EVAL_FIELD_PANEL[field];
        var el = form.querySelector('[name="' + field + '"]');
        if (!el) return total;
        var panel = el.closest(".eval_wizard-panel");
        if (!panel) return total;
        var pn = parseInt(panel.getAttribute("data-panel"), 10);
        return isNaN(pn) ? total : pn;
    }

    function requireTextField(name, label, n) {
        var el = qs(name);
        if (!el) return true;
        if (!String(el.value || "").trim()) {
            clearInvalidInStep(n);
            return validationFail(evalFieldMessage(name) || label + " را وارد کنید.", el);
        }
        el.classList.remove("is-invalid");
        if (el.closest(".major-combobox")) {
            el.closest(".major-combobox").classList.remove("is-invalid");
        }
        return true;
    }

    function requireSelectField(name, label, n) {
        var el = qs(name);
        if (!el) return true;
        if (!String(el.value || "").trim()) {
            clearInvalidInStep(n);
            return validationFail(evalFieldMessage(name) || label + " را انتخاب کنید.", el);
        }
        el.classList.remove("is-invalid");
        return true;
    }

    function validateStep(n) {
        clearInvalidInStep(n);

        if (n === 1) {
            if (!requireTextField("full_name", "نام و نام خانوادگی", n)) {
                updateWizardActions();
                return false;
            }
            var phoneEl = qs("phone");
            if (!phoneEl || !String(phoneEl.value || "").trim()) {
                updateWizardActions();
                return validationFail("شماره تماس را وارد کنید.", phoneEl);
            }
            var phoneResult = livePhone();
            if (isBlocking(phoneResult)) {
                updateWizardActions();
                return validationFail(
                    phoneResult.message || "شماره تماس معتبر نیست.",
                    phoneEl
                );
            }
            phoneEl.classList.remove("is-invalid");
        }

        if (n === 2) {
            if (!requireSelectField("current_degree", "آخرین مدرک", n)) {
                updateWizardActions();
                return false;
            }
            if (!requireTextField("field_of_study", "رشته تحصیلی", n)) {
                updateWizardActions();
                return false;
            }
            var gpaEl = qs("average_grade");
            if (!gpaEl || !String(gpaEl.value || "").trim()) {
                updateWizardActions();
                return validationFail("معدل را وارد کنید.", gpaEl);
            }
            var gpaResult = liveGpa();
            if (isBlocking(gpaResult)) {
                updateWizardActions();
                return validationFail(gpaResult.message || "معدل واردشده معتبر نیست.", gpaEl);
            }
            gpaEl.classList.remove("is-invalid");
        }

        if (n === 3) {
            /* زبان، نمره و دستاوردها اختیاری — فقط اگر نمره وارد شده باشد اعتبارسنجی می‌شود */
            if (langTestSelected()) {
                var langInp = qs("language_score");
                var scoreText = langInp ? String(langInp.value || "").trim() : "";
                if (scoreText) {
                    var langResult = liveLang();
                    if (isBlocking(langResult)) {
                        updateWizardActions();
                        return validationFail(
                            langResult.message || "نمره آزمون معتبر نیست.",
                            langInp
                        );
                    }
                    if (langInp) langInp.classList.remove("is-invalid");
                }
            }
        }

        if (n === total) {
            if (!hasSelectedDestinationCountry()) {
                markCountryGridInvalid();
                updateWizardActions();
                return validationFail("حداقل یک کشور مقصد را انتخاب کنید.", null);
            }
            hideCountrySelectionError();
            if (!requireTextField("desired_major", "رشته مورد نظر", n)) {
                updateWizardActions();
                return false;
            }
            var refPicker = form.querySelector("[data-referral-picker]");
            if (
                window.SafiranReferralSource &&
                refPicker &&
                !window.SafiranReferralSource.validate(refPicker)
            ) {
                updateWizardActions();
                return validationFail(
                    "لطفاً مشخص کنید از کجا با ما آشنا شدید.",
                    refPicker
                );
            }
            var captchaEl = qs("captcha_answer");
            if (!captchaEl || !String(captchaEl.value || "").trim()) {
                updateWizardActions();
                return validationFail("کد امنیتی (کپچا) را وارد کنید.", captchaEl);
            }
            captchaEl.classList.remove("is-invalid");
        }

        showValidationMessage("");
        updateWizardActions();
        return true;
    }

    function goNext() {
        if (!validateStep(current)) return;
        if (current < total) showPanel(current + 1, true);
    }

    function goPrev() {
        if (current > 1) showPanel(current - 1, true);
    }

    function toggleLangScore() {
        if (!langWrap || !langSelect) return;
        var hide = langSelect.value === "none" || langSelect.value === "";
        langWrap.classList.toggle("is-muted", hide);
        var inp = langWrap.querySelector("input");
        if (inp) {
            inp.disabled = hide;
            if (hide) {
                inp.value = "";
                setFeedback(langFeedback, inp, { status: "neutral", message: "" });
            }
        }
        syncHasIelts();
        if (!hide) liveLang();
        scheduleFieldProgressUpdate();
    }

    function initPickGroups() {
        form.querySelectorAll("[data-sync-select]").forEach(function (container) {
            var name = container.getAttribute("data-sync-select");
            if (name === "target_country") return;
            var select = qs(name);
            if (!select) return;
            syncPickGroup(container);

            container.addEventListener("click", function (e) {
                var btn = e.target.closest("[data-value]");
                if (!btn || !container.contains(btn)) return;
                var value = btn.getAttribute("data-value");
                if (value === undefined) return;
                select.value = value;
                select.dispatchEvent(new Event("change", { bubbles: true }));
                syncPickGroup(container);
                if (name === "language_test_type") toggleLangScore();
                if (name === "service_scope") {
                    var scope = form.querySelector(".eval_service-scope");
                    if (scope) scope.classList.remove("is-invalid");
                }
                scheduleFieldProgressUpdate();
            });
        });
    }

    function initYearPickers() {
        var sheet = document.getElementById("evalYearSheet");
        var wheel = document.getElementById("evalYearWheel");
        var titleEl = document.getElementById("evalYearSheetTitle");
        var previewVal = document.getElementById("evalYearSheetValue");
        var previewUnit = document.getElementById("evalYearSheetUnit");
        if (!sheet || !wheel) return;

        if (sheet.parentElement !== document.body) {
            document.body.appendChild(sheet);
        }

        var wheelWrap = wheel.closest(".eval_year-wheel-wrap");
        var activeSelect = null;
        var activeTrigger = null;
        var pendingValue = "";
        var scrollTimer = null;
        var wheelDragMoved = false;
        var drag = { active: false, pointerId: null, startY: 0, startScroll: 0 };
        var intakeTerms = pageConfig.evalIntakeTerms || ["پاییز", "بهار", "تابستان"];
        var intakeStartYear = pageConfig.evalJalaliYear || 1404;
        var intakeYearsAhead = pageConfig.evalIntakeYearsAhead || 40;
        var intakeExtendStep = pageConfig.evalIntakeExtendStep || 5;
        var intakeWheelState = { startYear: intakeStartYear, maxYear: null };

        function isIntakeSelect(select) {
            return select && select.name === "preferred_intake";
        }

        function itemHeight() {
            var wrap = wheel.closest(".eval_year-wheel-wrap");
            if (!wrap) return 48;
            var n = parseFloat(getComputedStyle(wrap).getPropertyValue("--eval-year-item-h"));
            return isNaN(n) ? 48 : n;
        }

        function wheelItems() {
            return wheel.querySelectorAll(".eval_year-wheel__item");
        }

        function updatePreview(label) {
            if (!previewVal) return;
            var text = label || "—";
            previewVal.textContent = text;
            previewVal.classList.toggle(
                "is-muted",
                !label || text === "—" || text.indexOf("انتخاب") >= 0
            );
        }

        function highlightActive() {
            var items = wheelItems();
            var h = itemHeight();
            var mid = wheel.scrollTop + wheel.clientHeight / 2;
            var best = null;
            var bestDist = Infinity;
            items.forEach(function (item) {
                var center = item.offsetTop + h / 2;
                var dist = Math.abs(center - mid);
                item.classList.remove("is-active", "is-near", "is-far");
                if (dist < bestDist) {
                    bestDist = dist;
                    best = item;
                }
            });
            if (best) {
                items.forEach(function (item) {
                    var center = item.offsetTop + h / 2;
                    var dist = Math.abs(center - mid);
                    if (item === best) {
                        item.classList.add("is-active");
                    } else if (dist < h * 1.45) {
                        item.classList.add("is-near");
                    } else if (dist < h * 2.45) {
                        item.classList.add("is-far");
                    }
                });
                pendingValue = best.getAttribute("data-value") || "";
                updatePreview(best.textContent.trim());
            }
            extendIntakeWheelIfNeeded();
        }

        function findWheelItem(value) {
            var items = wheelItems();
            var i;
            for (i = 0; i < items.length; i++) {
                if (items[i].getAttribute("data-value") === value) return items[i];
            }
            return null;
        }

        function scrollToValue(value, smooth) {
            var target = findWheelItem(value);
            if (!target) return;
            var h = itemHeight();
            var top = target.offsetTop - (wheel.clientHeight - h) / 2;
            wheel.scrollTo({ top: Math.max(0, top), behavior: smooth ? "smooth" : "auto" });
            if (!smooth) highlightActive();
        }

        function snapToNearest(smooth) {
            highlightActive();
            var active = wheel.querySelector(".eval_year-wheel__item.is-active");
            if (!active) return;
            var h = itemHeight();
            var top = active.offsetTop - (wheel.clientHeight - h) / 2;
            wheel.scrollTo({ top: Math.max(0, top), behavior: smooth ? "smooth" : "auto" });
            if (!smooth) highlightActive();
        }

        function bindWheelItemClick(item) {
            item.addEventListener("click", function () {
                if (wheelDragMoved) return;
                scrollToValue(item.getAttribute("data-value"), true);
            });
        }

        function createWheelItem(value, label, extraClass) {
            var item = document.createElement("div");
            item.className = "eval_year-wheel__item" + (extraClass ? " " + extraClass : "");
            item.setAttribute("role", "option");
            item.setAttribute("data-value", value);
            item.textContent = label;
            bindWheelItemClick(item);
            return item;
        }

        function syncIntakeSelectOptions(select, fromYear, toYear) {
            var current = select.value;
            select.innerHTML = "";
            var empty = document.createElement("option");
            empty.value = "";
            empty.textContent = "انتخاب ترم / سال";
            select.appendChild(empty);
            var y;
            var t;
            var label;
            var opt;
            for (y = fromYear; y <= toYear; y++) {
                for (t = 0; t < intakeTerms.length; t++) {
                    label = intakeTerms[t] + " " + y;
                    opt = document.createElement("option");
                    opt.value = label;
                    opt.textContent = label;
                    select.appendChild(opt);
                }
            }
            if (current) select.value = current;
        }

        function appendIntakeItemsToWheel(fromYear, toYear) {
            var padBottom = wheel.querySelector(".eval_year-wheel__pad:last-child");
            if (!padBottom) return;
            var y;
            var t;
            var label;
            for (y = fromYear; y <= toYear; y++) {
                for (t = 0; t < intakeTerms.length; t++) {
                    label = intakeTerms[t] + " " + y;
                    wheel.insertBefore(createWheelItem(label, label, ""), padBottom);
                }
            }
        }

        function appendIntakeOptionsToSelect(select, fromYear, toYear) {
            var y;
            var t;
            var label;
            var opt;
            for (y = fromYear; y <= toYear; y++) {
                for (t = 0; t < intakeTerms.length; t++) {
                    label = intakeTerms[t] + " " + y;
                    opt = document.createElement("option");
                    opt.value = label;
                    opt.textContent = label;
                    select.appendChild(opt);
                }
            }
        }

        function ensureIntakeWheelRange(select) {
            if (intakeWheelState.maxYear === null) {
                intakeWheelState.startYear = intakeStartYear;
                intakeWheelState.maxYear = intakeStartYear + intakeYearsAhead;
            }
            syncIntakeSelectOptions(
                select,
                intakeWheelState.startYear,
                intakeWheelState.maxYear
            );
        }

        function intakeDefaultValue() {
            if (!intakeTerms.length) return "";
            return intakeTerms[0] + " " + intakeStartYear;
        }

        function extendIntakeWheelIfNeeded() {
            if (!activeSelect || !isIntakeSelect(activeSelect)) return;
            var cap = intakeStartYear + intakeYearsAhead;
            if (intakeWheelState.maxYear >= cap) return;
            var nearBottom =
                wheel.scrollTop + wheel.clientHeight >=
                wheel.scrollHeight - itemHeight() * 3;
            if (!nearBottom) return;
            var fromYear = intakeWheelState.maxYear + 1;
            var toYear = Math.min(intakeWheelState.maxYear + intakeExtendStep, cap);
            if (fromYear > toYear) return;
            appendIntakeOptionsToSelect(activeSelect, fromYear, toYear);
            appendIntakeItemsToWheel(fromYear, toYear);
            intakeWheelState.maxYear = toYear;
        }

        function buildIntakeWheel(select) {
            ensureIntakeWheelRange(select);
            wheel.innerHTML = "";
            var padTop = document.createElement("div");
            padTop.className = "eval_year-wheel__pad";
            wheel.appendChild(padTop);
            wheel.appendChild(
                createWheelItem("", "انتخاب ترم / سال", "is-empty")
            );
            var padBottom = document.createElement("div");
            padBottom.className = "eval_year-wheel__pad";
            wheel.appendChild(padBottom);
            appendIntakeItemsToWheel(
                intakeWheelState.startYear,
                intakeWheelState.maxYear
            );
        }

        function buildWheel(select) {
            if (isIntakeSelect(select)) {
                buildIntakeWheel(select);
                return;
            }
            wheel.innerHTML = "";
            var padTop = document.createElement("div");
            padTop.className = "eval_year-wheel__pad";
            wheel.appendChild(padTop);
            var i;
            for (i = 0; i < select.options.length; i++) {
                var opt = select.options[i];
                if (opt.value === "" && opt.text) {
                    wheel.appendChild(
                        createWheelItem("", opt.text || "انتخاب نشده", "is-empty")
                    );
                    continue;
                }
                if (!opt.value && opt.value !== "0") continue;
                wheel.appendChild(createWheelItem(opt.value, opt.text, ""));
            }
            var padBottom = document.createElement("div");
            padBottom.className = "eval_year-wheel__pad";
            wheel.appendChild(padBottom);
        }

        function initYearWheelDrag() {
            if (!wheelWrap) return;

            function onPointerDown(e) {
                if (e.pointerType === "mouse" && e.button !== 0) return;
                drag.active = true;
                drag.pointerId = e.pointerId;
                drag.startY = e.clientY;
                drag.startScroll = wheel.scrollTop;
                wheelDragMoved = false;
                wheelWrap.classList.add("is-dragging");
                try {
                    wheelWrap.setPointerCapture(e.pointerId);
                } catch (err) {
                    /* ignore */
                }
            }

            function onPointerMove(e) {
                if (!drag.active || e.pointerId !== drag.pointerId) return;
                var dy = e.clientY - drag.startY;
                if (Math.abs(dy) > 3) wheelDragMoved = true;
                if (wheelDragMoved) {
                    e.preventDefault();
                    wheel.scrollTop = drag.startScroll - dy;
                    highlightActive();
                }
            }

            function endDrag(e) {
                if (!drag.active) return;
                if (e && e.pointerId !== drag.pointerId) return;
                drag.active = false;
                wheelWrap.classList.remove("is-dragging");
                try {
                    wheelWrap.releasePointerCapture(drag.pointerId);
                } catch (err) {
                    /* ignore */
                }
                if (wheelDragMoved) {
                    snapToNearest(true);
                    setTimeout(function () {
                        wheelDragMoved = false;
                    }, 0);
                }
            }

            wheelWrap.addEventListener("pointerdown", onPointerDown);
            wheelWrap.addEventListener("pointermove", onPointerMove);
            wheelWrap.addEventListener("pointerup", endDrag);
            wheelWrap.addEventListener("pointercancel", endDrag);

            wheelWrap.addEventListener(
                "wheel",
                function (e) {
                    if (!sheet.classList.contains("is-open")) return;
                    e.preventDefault();
                    wheel.scrollTop += e.deltaY;
                    highlightActive();
                    if (scrollTimer) clearTimeout(scrollTimer);
                    scrollTimer = setTimeout(function () {
                        snapToNearest(true);
                    }, 120);
                },
                { passive: false }
            );
        }

        function openSheet(select, trigger) {
            activeSelect = select;
            activeTrigger = trigger;
            if (isIntakeSelect(select)) {
                intakeWheelState.startYear = intakeStartYear;
                intakeWheelState.maxYear = null;
            }
            pendingValue = select.value || "";
            var fieldLabel = trigger.closest(".eval_field");
            var lbl = fieldLabel && fieldLabel.querySelector("label");
            var titleText = lbl ? lbl.textContent.replace(/\s*\(.*\)\s*/, "").trim() : "انتخاب سال";
            if (titleEl) titleEl.textContent = titleText;
            if (previewUnit) {
                if (select.name === "graduation_year") {
                    previewUnit.textContent = "سال یا وضعیت تحصیل";
                } else if (select.name === "preferred_intake") {
                    previewUnit.textContent = "ترم و سال شروع";
                } else {
                    previewUnit.textContent = "سال شمسی";
                }
            }
            buildWheel(select);
            sheet.hidden = false;
            sheet.setAttribute("aria-hidden", "false");
            document.body.classList.add("eval_year-sheet-open");
            requestAnimationFrame(function () {
                sheet.classList.add("is-open");
                requestAnimationFrame(function () {
                    if (pendingValue) {
                        scrollToValue(pendingValue, false);
                    } else if (isIntakeSelect(select)) {
                        var def = intakeDefaultValue();
                        if (def) scrollToValue(def, false);
                    } else {
                        var items = wheelItems();
                        if (items.length) {
                            var mid = Math.floor(items.length / 2);
                            scrollToValue(items[mid].getAttribute("data-value") || "", false);
                        }
                    }
                    highlightActive();
                });
            });
        }

        function closeSheet() {
            sheet.classList.remove("is-open");
            document.body.classList.remove("eval_year-sheet-open");
            setTimeout(function () {
                if (!sheet.classList.contains("is-open")) {
                    sheet.hidden = true;
                    sheet.setAttribute("aria-hidden", "true");
                }
            }, 280);
            activeSelect = null;
            activeTrigger = null;
        }

        function confirmYear() {
            if (!activeSelect) return;
            activeSelect.value = pendingValue;
            activeSelect.dispatchEvent(new Event("change", { bubbles: true }));
            if (activeTrigger) updateYearTrigger(activeTrigger, activeSelect);
            closeSheet();
        }

        wheel.addEventListener("scroll", function () {
            if (drag.active) {
                highlightActive();
                return;
            }
            if (scrollTimer) clearTimeout(scrollTimer);
            highlightActive();
            scrollTimer = setTimeout(function () {
                snapToNearest(true);
            }, 90);
        });

        initYearWheelDrag();

        form.querySelectorAll("[data-year-picker]").forEach(function (trigger) {
            var name = trigger.getAttribute("data-year-picker");
            var select = qs(name);
            if (!select) return;
            select.classList.add("eval_select-hidden");
            updateYearTrigger(trigger, select);
            trigger.addEventListener("click", function () {
                openSheet(select, trigger);
            });
        });

        sheet.querySelectorAll("[data-year-close]").forEach(function (btn) {
            btn.addEventListener("click", closeSheet);
        });
        var confirmBtn = sheet.querySelector("[data-year-confirm]");
        if (confirmBtn) confirmBtn.addEventListener("click", confirmYear);

        document.addEventListener("keydown", function (e) {
            if (sheet.hidden || !sheet.classList.contains("is-open")) return;
            if (e.key === "Escape") {
                e.preventDefault();
                closeSheet();
            }
        });
    }

    function initCountryCards() {
        var suggestPanel = document.getElementById("evalCountrySuggestPanel");
        var suggestList = document.getElementById("evalCountrySuggestList");
        var suggestHint = document.getElementById("evalCountrySuggestHint");
        var suggestTimer = null;

        function isOtherCountrySelected() {
            var other = form.querySelector('input[name="desired_countries"][value="other"]');
            return !!(other && other.checked);
        }

        function isNotSureCountrySelected() {
            var unsure = form.querySelector('input[name="desired_countries"][value="not_sure"]');
            return !!(unsure && unsure.checked);
        }

        function shouldShowCountrySuggestions() {
            /* «سایر کشورها» → پیشنهاد در گزارش نهایی؛ نه لیست ثابت زیر فرم */
            if (isOtherCountrySelected()) return false;
            if (!isNotSureCountrySelected()) return false;
            return hasProfileForCountrySuggest();
        }

        function hasProfileForCountrySuggest() {
            var fieldEl = qs("field_of_study");
            var gpaEl = qs("average_grade");
            var degreeEl = qs("current_degree");
            var field = fieldEl && fieldEl.value ? String(fieldEl.value).trim() : "";
            var gpaRaw = gpaEl && gpaEl.value ? String(gpaEl.value).trim() : "";
            var degree = degreeEl && degreeEl.value ? String(degreeEl.value).trim() : "";
            if (field.length < 2) return false;
            if (gpaRaw.length >= 1) return true;
            return degree.length >= 1;
        }

        function hideCountrySuggestPanel() {
            if (suggestPanel) suggestPanel.hidden = true;
            if (suggestList) suggestList.innerHTML = "";
            if (suggestHint) suggestHint.hidden = true;
        }

        function renderCountrySuggestions(items) {
            if (!suggestList) return;
            suggestList.innerHTML = "";
            if (!items || !items.length) {
                if (suggestHint) {
                    suggestHint.hidden = false;
                    suggestHint.textContent = "فعلاً پیشنهاد مشخصی نداریم — یکی از کشورهای بالا را انتخاب کنید یا با مشاور تماس بگیرید.";
                }
                return;
            }
            if (suggestHint) suggestHint.hidden = true;
            items.forEach(function (item) {
                var btn = document.createElement("button");
                btn.type = "button";
                btn.className = "eval_country-suggest__item";
                btn.setAttribute("data-country-code", item.code);
                var staticBase = pageConfig.staticUrl || "/static/";
                var flagHtml = item.flag
                    ? '<img src="' + staticBase + item.flag + '" alt="" width="28" height="18" loading="lazy">'
                    : '<span class="ti-world" aria-hidden="true"></span>';
                btn.innerHTML =
                    flagHtml +
                    '<span class="eval_country-suggest__body">' +
                    '<strong>' +
                    (item.label || item.code) +
                    "</strong>" +
                    "<span>" +
                    (item.reason || "") +
                    "</span></span>";
                btn.addEventListener("click", function () {
                    var input = form.querySelector(
                        'input[name="desired_countries"][value="' + item.code + '"]'
                    );
                    if (input) {
                        input.checked = true;
                        input.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                });
                suggestList.appendChild(btn);
            });
        }

        function fetchCountrySuggestions() {
            if (!shouldShowCountrySuggestions()) {
                hideCountrySuggestPanel();
                return;
            }
            if (suggestPanel) suggestPanel.hidden = false;
            if (suggestHint) {
                suggestHint.hidden = false;
                suggestHint.textContent = "در حال تحلیل پروفایل شما…";
            }
            var url = pageConfig.evalCountrySuggestUrl || "";
            if (!url) return;
            var params = new URLSearchParams();
            var fieldEl = qs("field_of_study");
            var degreeEl = qs("current_degree");
            var gpaEl = qs("average_grade");
            var langSel = qs("language_test");
            var langInp = qs("language_score");
            if (fieldEl && fieldEl.value) params.set("field", fieldEl.value);
            if (degreeEl && degreeEl.value) params.set("degree", degreeEl.value);
            if (gpaEl && gpaEl.value) params.set("gpa", gpaEl.value);
            if (langSel && langSel.value) params.set("lang_test", langSel.value);
            if (langInp && langInp.value) params.set("lang_score", langInp.value);
            if (isOtherCountrySelected()) params.set("selection", "other");
            else if (isNotSureCountrySelected()) params.set("selection", "not_sure");
            fetch(url + "?" + params.toString(), {
                credentials: "same-origin",
                headers: { Accept: "application/json" },
            })
                .then(readJsonResponse)
                .then(function (data) {
                    if (!data || !data.ok) return;
                    if (
                        data.profile_ready === false ||
                        !shouldShowCountrySuggestions()
                    ) {
                        hideCountrySuggestPanel();
                        return;
                    }
                    renderCountrySuggestions(data.suggestions || []);
                })
                .catch(function () {
                    if (suggestHint) {
                        suggestHint.hidden = false;
                        suggestHint.textContent = "خطا در دریافت پیشنهاد — دوباره تلاش کنید.";
                    }
                });
        }

        function scheduleCountrySuggest() {
            if (suggestTimer) clearTimeout(suggestTimer);
            suggestTimer = setTimeout(fetchCountrySuggestions, 350);
        }
        refreshCountrySuggest = scheduleCountrySuggest;

        ["field_of_study", "current_degree", "average_grade", "language_test", "language_score"].forEach(
            function (name) {
                var el = qs(name);
                if (!el) return;
                el.addEventListener("input", scheduleCountrySuggest);
                el.addEventListener("change", scheduleCountrySuggest);
            }
        );

        form.querySelectorAll(".eval_country-card").forEach(function (card) {
            var input = card.querySelector('input[type="checkbox"]');
            if (!input) return;
            card.classList.toggle("is-selected", input.checked);
            input.addEventListener("change", function () {
                card.classList.toggle("is-selected", input.checked);
                syncTargetCountry();
                if (hasSelectedDestinationCountry()) hideCountrySelectionError();
                updateWizardActions();
                scheduleFieldProgressUpdate();
                scheduleCountrySuggest();
            });
        });
        syncTargetCountry();
        updateWizardActions();
    }

    function initLiveValidation() {
        bindNumericInputNormalization("average_grade", true);
        bindNumericInputNormalization("language_score", false);
        var gpaEl = qs("average_grade");
        if (gpaEl) {
            gpaEl.addEventListener("input", liveGpa);
            gpaEl.addEventListener("blur", liveGpa);
        }
        var phoneEl = qs("phone");
        if (phoneEl) {
            phoneEl.addEventListener("input", livePhone);
            phoneEl.addEventListener("blur", livePhone);
        }
        var langInp = qs("language_score");
        if (langInp) {
            langInp.addEventListener("input", liveLang);
            langInp.addEventListener("blur", liveLang);
        }
    }

    if (btnNext) btnNext.addEventListener("click", goNext);
    if (btnPrev) btnPrev.addEventListener("click", goPrev);

    steps.forEach(function (li) {
        li.addEventListener("click", function () {
            var target = parseInt(li.getAttribute("data-step"), 10);
            if (target < current) {
                showPanel(target, true);
            } else if (target === current + 1 && validateStep(current)) {
                showPanel(target, true);
            }
        });
        li.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                li.click();
            }
        });
    });

    form.addEventListener("keydown", function (e) {
        if (e.key !== "Enter") return;
        var tag = (e.target.tagName || "").toLowerCase();
        if (
            tag === "textarea" ||
            e.target.closest(
                ".eval_chips, .eval_segment, .eval_lang-grid, .eval_option-grid, .eval_service-scope, .eval_year-sheet"
            )
        ) {
            return;
        }
        if (e.target.type === "submit") return;
        e.preventDefault();
        if (current < total) goNext();
    });

    var analyzeModal = document.getElementById("evalAnalyzeModal");
    var analyzeDialog = analyzeModal
        ? analyzeModal.querySelector(".eval-analyze__dialog")
        : null;
    var errorDialog = document.getElementById("evalErrorDialog");
    var errorDialogMessage = document.getElementById("evalErrorDialogMessage");
    var errorDialogClose = document.getElementById("evalErrorDialogClose");
    var analyzeTitle = document.getElementById("evalAnalyzeTitle");
    var analyzeDesc = document.getElementById("evalAnalyzeDesc");
    var analyzeQueue = document.getElementById("evalAnalyzeQueue");
    var analyzeQueueBadge = document.getElementById("evalAnalyzeQueueBadge");
    var analyzeQueueLock = document.getElementById("evalAnalyzeQueueLock");
    var analyzeBar = document.getElementById("evalAnalyzeBar");
    var analyzePercent = document.getElementById("evalAnalyzePercent");
    var analyzeStep = document.getElementById("evalAnalyzeStep");
    var analyzeReconnect = document.getElementById("evalAnalyzeReconnect");
    var analyzeChecklist = document.getElementById("evalAnalyzeChecklist");
    var analyzeSubmitting = false;
    var analyzePollCount = 0;
    var analyzeDisplayPct = 0;
    var analyzeTargetPct = 0;
    var analyzePageLocked = false;
    var analyzeRedirecting = false;
    var analyzeKeydownHandler = null;
    var analyzeBeforeUnloadHandler = null;

    var queueState = {
        active: false,
        ahead: -1,
        initialAhead: 0,
        startedAt: 0,
        submitDone: false,
        jobId: null,
        pollStarted: false,
        finishTimer: null,
        queueEnded: false,
    };
    var progressAnimTimer = null;

    var STEP_ORDER = [
        "validate",
        "profile",
        "countries",
        "scholarships",
        "blogs",
        "pricing",
        "match",
        "finalize",
        "done",
    ];

    var EVAL_AI_ANALYZE_DESC =
        "پرونده شما در حال بررسی توسط بهترین الگوریتم‌های هوش مصنوعی است.";

    function getCsrfToken() {
        var inp = form.querySelector("[name=csrfmiddlewaretoken]");
        if (inp && inp.value) return inp.value;
        var m = document.cookie.match(/csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : "";
    }

    var EVAL_JOB_STORAGE_KEY = "safiran_eval_active_job_v1";
    var evalReconnectAttempts = 0;

    function saveActiveJob(jobId) {
        if (!jobId) return;
        try {
            sessionStorage.setItem(
                EVAL_JOB_STORAGE_KEY,
                JSON.stringify({ jobId: String(jobId), savedAt: Date.now() })
            );
        } catch (e) {}
    }

    function loadActiveJob() {
        try {
            var raw = sessionStorage.getItem(EVAL_JOB_STORAGE_KEY);
            if (!raw) return null;
            var data = JSON.parse(raw);
            if (!data || !data.jobId) return null;
            if (Date.now() - (data.savedAt || 0) > 3 * 60 * 60 * 1000) {
                clearActiveJob();
                return null;
            }
            return String(data.jobId);
        } catch (e) {
            return null;
        }
    }

    function clearActiveJob() {
        try {
            sessionStorage.removeItem(EVAL_JOB_STORAGE_KEY);
        } catch (e) {}
    }

    function buildProcessUrl(jobId) {
        var processUrl = pageConfig.evalProcessUrl;
        if (!processUrl) return "";
        if (jobId) return processUrl + "?job=" + encodeURIComponent(jobId);
        return processUrl;
    }

    function readJsonResponse(r) {
        return r.text().then(function (body) {
            var trimmed = (body || "").trim();
            var lower = trimmed.slice(0, 32).toLowerCase();
            if (
                !trimmed ||
                lower.indexOf("<!doctype") === 0 ||
                lower.indexOf("<html") === 0 ||
                trimmed.charAt(0) === "<"
            ) {
                var htmlErr = new Error("در انتظار اینترنت…");
                htmlErr.retryable =
                    !r.status ||
                    r.status === 408 ||
                    r.status === 429 ||
                    r.status === 502 ||
                    r.status === 503 ||
                    r.status === 504 ||
                    r.status >= 500;
                if (!r.status || r.status >= 500) htmlErr.retryable = true;
                throw htmlErr;
            }
            try {
                return JSON.parse(trimmed);
            } catch (parseErr) {
                var parseError = new Error("در انتظار اینترنت…");
                parseError.retryable = true;
                throw parseError;
            }
        });
    }

    function isRetryableEvalError(err) {
        if (!err) return false;
        if (err.retryable) return true;
        if (err.name === "TypeError" || err.name === "SyntaxError") return true;
        var msg = String(err.message || "");
        if (/unexpected token|not valid json|failed to fetch|network|load failed/i.test(msg)) {
            return true;
        }
        return false;
    }

    function userFacingEvalError(err) {
        if (isRetryableEvalError(err)) {
            return "در انتظار اینترنت… تحلیل در سرور ادامه دارد.";
        }
        var msg = String((err && err.message) || "").trim();
        if (!msg || /unexpected token|not valid json|<!doctype/i.test(msg)) {
            return "ثبت انجام نشد. لطفاً چند لحظه بعد دوباره تلاش کنید.";
        }
        return msg;
    }

    function evalReconnectDelayMs() {
        evalReconnectAttempts += 1;
        return Math.min(10000, 500 + evalReconnectAttempts * 400);
    }

    function resetEvalReconnectAttempts() {
        evalReconnectAttempts = 0;
    }

    function showReconnectState(on) {
        if (analyzeDialog) {
            analyzeDialog.classList.toggle("eval-analyze__dialog--reconnect", !!on);
        }
        if (analyzeReconnect) {
            analyzeReconnect.hidden = !on;
        }
        if (on && analyzeStep) {
            analyzeStep.textContent = "در انتظار اینترنت…";
        }
    }

    function waitForInternetRetry(fn, delayMs) {
        showReconnectState(true);
        if (!analyzeModal || analyzeModal.hidden) {
            openAnalyzeModal(true);
        }
        analyzeSubmitting = true;
        lockAnalyzePage();
        return new Promise(function (resolve) {
            window.setTimeout(function () {
                resolve(fn());
            }, delayMs || evalReconnectDelayMs());
        });
    }

    function applyProcessPayload(data, jobId) {
        if (data && data.job_id) jobId = String(data.job_id);
        if (jobId) {
            queueState.jobId = jobId;
            saveActiveJob(jobId);
        }
        syncQueueFromServer(data.queue_ahead);
        var stepId = data.step_id || "validate";
        var pct = data.percent || 0;
        if (
            data.queue_active ||
            (typeof data.queue_ahead === "number" && data.queue_ahead > 0)
        ) {
            stepId = "validate";
            pct = Math.max(pct, 8);
        } else if (data.status === "queued") {
            stepId = "validate";
            pct = Math.max(pct, 8);
        }
        applyAnalyzeLayout(data);
        updateAnalyzeUI(pct, data.step_label || "", stepId);
        return jobId;
    }

    function tryRecoverActiveJobFromServer(jobId) {
        var url = buildProcessUrl(jobId || null);
        if (!url) return Promise.resolve(null);
        return fetch(url, {
            method: "GET",
            credentials: "same-origin",
            headers: { Accept: "application/json" },
        })
            .then(readJsonResponse)
            .then(function (data) {
                if (!data || data.error === "job_not_found") return null;
                if (
                    data.status === "running" ||
                    data.status === "queued" ||
                    (data.status === "done" && data.redirect_url)
                ) {
                    return data;
                }
                return null;
            })
            .catch(function () {
                return null;
            });
    }

    function resumeEvaluationFromPayload(data, jobId) {
        if (!data) return;
        analyzeSubmitting = true;
        if (btnSubmit) btnSubmit.disabled = true;
        openAnalyzeModal(true);
        queueState.submitDone = true;
        queueState.jobId = (data.job_id && String(data.job_id)) || jobId || loadActiveJob();
        queueState.pollStarted = false;
        if (typeof data.queue_ahead === "number" && data.queue_ahead > 0) {
            queueState.active = true;
            queueState.queueEnded = false;
        } else {
            queueState.queueEnded = true;
            queueState.active = false;
            setQueueVisible(false);
            if (analyzeDialog) {
                analyzeDialog.classList.remove("eval-analyze__dialog--queue");
            }
        }
        applyProcessPayload(data, queueState.jobId);
        beginJobPolling(queueState.jobId);
    }

    function tryResumeEvaluationOnLoad() {
        if (!pageConfig.evalProcessUrl || hasServerFormErrors()) return;
        var storedJob = loadActiveJob();
        var url = buildProcessUrl(storedJob);
        if (!url) return;
        fetch(url, {
            method: "GET",
            credentials: "same-origin",
            headers: { Accept: "application/json" },
        })
            .then(readJsonResponse)
            .then(function (data) {
                if (!data || data.error === "job_not_found") {
                    if (storedJob) clearActiveJob();
                    return;
                }
                if (data.status === "error") {
                    clearActiveJob();
                    return;
                }
                if (data.status === "done" && data.redirect_url) {
                    clearActiveJob();
                    redirectToEvaluationResult(data.redirect_url);
                    return;
                }
                if (
                    data.status === "running" ||
                    data.status === "queued" ||
                    data.queue_active
                ) {
                    resumeEvaluationFromPayload(data, storedJob);
                }
            })
            .catch(function () {});
    }

    function applyAnalyzeLayout(data) {
        if (!analyzeDialog) return;
        var compact = !!(
            data &&
            (data.ui_compact === true || data.report_has_data === false)
        );
        analyzeDialog.classList.toggle("eval-analyze__dialog--compact", compact);
        if (analyzeDesc) {
            analyzeDesc.textContent = compact
                ? "در حال بررسی اطلاعات شما؛ به‌زودی نتیجه آماده می‌شود."
                : EVAL_AI_ANALYZE_DESC;
        }
    }

    function clearQueueTimers() {
        if (queueState.finishTimer) {
            clearTimeout(queueState.finishTimer);
            queueState.finishTimer = null;
        }
    }

    function syncQueueFromServer(ahead) {
        if (typeof ahead !== "number" || Number.isNaN(ahead)) return;
        var next = Math.max(0, Math.floor(ahead));
        if (queueState.ahead < 0) {
            queueState.ahead = next;
            queueState.initialAhead = next;
        } else {
            queueState.ahead = next;
        }
        if (next > 0) {
            queueState.active = true;
        }
        updateQueuePresentation();
        if (next <= 0 && queueState.submitDone) {
            tryFinishQueuePhase();
        }
    }

    function stopProgressAnimation() {
        if (progressAnimTimer) {
            clearTimeout(progressAnimTimer);
            progressAnimTimer = null;
        }
    }

    function startProgressAnimation() {
        stopProgressAnimation();
        function tick() {
            if (!analyzeModal || analyzeModal.hidden || analyzeRedirecting) {
                stopProgressAnimation();
                return;
            }
            var moved = false;
            if (analyzeDisplayPct < analyzeTargetPct) {
                var gap = analyzeTargetPct - analyzeDisplayPct;
                analyzeDisplayPct = Math.min(
                    analyzeTargetPct,
                    analyzeDisplayPct + Math.max(0.55, gap * 0.24)
                );
                moved = true;
            } else if (queueState.active && queueState.ahead > 0) {
                var cap = 26;
                if (analyzeDisplayPct < cap) {
                    analyzeDisplayPct += 0.22 + Math.random() * 0.28;
                    moved = true;
                }
            } else if (analyzeTargetPct < 100 && analyzeDisplayPct < 97) {
                var idleCap = Math.min(96, analyzeTargetPct + 7);
                if (analyzeDisplayPct < idleCap) {
                    analyzeDisplayPct += 0.1 + Math.random() * 0.14;
                    moved = true;
                }
            }
            if (moved) {
                renderAnalyzePercent(analyzeDisplayPct);
            }
            progressAnimTimer = window.setTimeout(tick, 150);
        }
        tick();
    }

    function handleAnalyzePollError(err) {
        if (isRetryableEvalError(err)) {
            var jobId = queueState.jobId || loadActiveJob();
            if (jobId) {
                queueState.pollStarted = false;
                waitForInternetRetry(function () {
                    return pollEvaluationJob(jobId);
                }).catch(handleAnalyzePollError);
            }
            return;
        }
        closeAnalyzeModal();
        clearActiveJob();
        analyzeSubmitting = false;
        if (btnSubmit) btnSubmit.disabled = false;
        showValidationMessage(userFacingEvalError(err));
    }

    function beginJobPolling(jobId) {
        if (!jobId) return;
        if (queueState.pollStarted) return;
        queueState.pollStarted = true;
        saveActiveJob(jobId);
        pollEvaluationJob(jobId).catch(handleAnalyzePollError);
    }

    function lockAnalyzePage() {
        if (analyzePageLocked) return;
        analyzePageLocked = true;
        document.body.classList.add("eval-analyze-locked");
        analyzeBeforeUnloadHandler = function (e) {
            if (!analyzePageLocked || analyzeRedirecting) return;
            e.preventDefault();
            e.returnValue = "";
        };
        window.addEventListener("beforeunload", analyzeBeforeUnloadHandler);
        analyzeKeydownHandler = function (e) {
            if (!analyzePageLocked) return;
            if (e.key === "Escape") {
                e.preventDefault();
                e.stopPropagation();
            }
        };
        document.addEventListener("keydown", analyzeKeydownHandler, true);
    }

    function redirectToEvaluationResult(url) {
        if (!url) return;
        clearActiveJob();
        analyzeRedirecting = true;
        analyzeSubmitting = false;
        unlockAnalyzePage();
        clearDraft();
        window.location.replace(url);
    }

    function unlockAnalyzePage() {
        analyzePageLocked = false;
        document.body.classList.remove("eval-analyze-locked");
        if (analyzeBeforeUnloadHandler) {
            window.removeEventListener("beforeunload", analyzeBeforeUnloadHandler);
            analyzeBeforeUnloadHandler = null;
        }
        if (analyzeKeydownHandler) {
            document.removeEventListener("keydown", analyzeKeydownHandler, true);
            analyzeKeydownHandler = null;
        }
    }

    function setQueueVisible(visible) {
        if (analyzeQueue) analyzeQueue.hidden = !visible;
        if (analyzeDialog) {
            analyzeDialog.classList.toggle("eval-analyze__dialog--queue", !!visible);
        }
    }

    function updateQueuePresentation() {
        if (!queueState.active) return;

        var ahead = queueState.ahead;
        var waiting = ahead > 0;
        setQueueVisible(waiting);

        if (ahead < 0) {
            if (analyzeTitle) {
                analyzeTitle.textContent = "در حال ثبت پرونده شما";
            }
            if (analyzeDesc) {
                analyzeDesc.textContent = EVAL_AI_ANALYZE_DESC;
            }
            if (analyzeStep) {
                analyzeStep.textContent = "مرحله ۱ — ارسال اطلاعات";
            }
            updateAnalyzeChecklistSlide("validate");
            renderAnalyzePercent(analyzeDisplayPct);
            return;
        }

        if (!waiting) {
            if (analyzeTitle) {
                analyzeTitle.textContent = "تحلیل هوشمند پرونده شما";
            }
            if (analyzeDesc) {
                analyzeDesc.textContent = EVAL_AI_ANALYZE_DESC;
            }
            if (analyzeStep) {
                analyzeStep.textContent = queueState.submitDone
                    ? "مرحله ۱ — بررسی و اعتبارسنجی اطلاعات"
                    : "مرحله ۱ — دریافت و بررسی اطلاعات";
            }
            updateAnalyzeChecklistSlide("validate");
            renderAnalyzePercent(analyzeDisplayPct);
            return;
        }

        var position = ahead + 1;
        if (analyzeQueueBadge) {
            analyzeQueueBadge.textContent =
                toPersianDigits(ahead) + " نفر در صف انتظار هستند";
        }
        if (analyzeQueueLock) {
            analyzeQueueLock.textContent =
                "نوبت شما: " +
                toPersianDigits(position) +
                " — تحلیل هوشمند به‌زودی برای پرونده شما شروع می‌شود.";
        }
        if (analyzeTitle) {
            analyzeTitle.textContent = "در حال آماده‌سازی تحلیل هوشمند";
        }
        if (analyzeDesc) {
            analyzeDesc.textContent = EVAL_AI_ANALYZE_DESC;
        }
        if (analyzeStep) {
            analyzeStep.textContent = "مرحله ۱ — آماده‌سازی صف تحلیل";
        }
        updateAnalyzeChecklistSlide("validate");
        renderAnalyzePercent(analyzeDisplayPct);
    }

    function tryFinishQueuePhase() {
        if (!queueState.active || queueState.queueEnded) return;
        if (queueState.ahead > 0) return;
        if (!queueState.submitDone || !queueState.jobId) return;
        if (!queueState.finishTimer) {
            queueState.finishTimer = window.setTimeout(function () {
                queueState.finishTimer = null;
                endQueuePhaseAndPoll();
            }, queueState.initialAhead === 0 ? 0 : 160);
        }
    }

    function startQueuePhase() {
        clearQueueTimers();
        queueState.active = true;
        queueState.ahead = -1;
        queueState.initialAhead = 0;
        queueState.startedAt = Date.now();
        queueState.submitDone = false;
        queueState.jobId = null;
        queueState.pollStarted = false;
        queueState.queueEnded = false;
        analyzeDisplayPct = 4;
        analyzeTargetPct = 8;
        updateQueuePresentation();
        startProgressAnimation();
    }

    function endQueuePhaseAndPoll() {
        if (queueState.queueEnded) return;
        queueState.queueEnded = true;
        queueState.active = false;
        clearQueueTimers();
        setQueueVisible(false);
        if (analyzeDialog) {
            analyzeDialog.classList.remove("eval-analyze__dialog--queue");
        }
        if (analyzeTitle) {
            analyzeTitle.textContent = "تحلیل هوشمند پرونده شما";
        }
        if (analyzeDesc) {
            analyzeDesc.textContent = EVAL_AI_ANALYZE_DESC;
        }
        analyzeDisplayPct = Math.max(analyzeDisplayPct, analyzeTargetPct, 10);
        analyzeTargetPct = Math.max(analyzeTargetPct, 12);
        renderAnalyzePercent(analyzeDisplayPct);
        analyzePollCount = 0;
        if (queueState.jobId) {
            beginJobPolling(queueState.jobId);
        }
    }

    function openAnalyzeModal(skipQueueReset) {
        if (!analyzeModal) return;
        analyzePollCount = 0;
        if (!skipQueueReset) {
            analyzeDisplayPct = 0;
            analyzeTargetPct = 0;
            if (analyzeDialog) {
                analyzeDialog.classList.remove("eval-analyze__dialog--compact");
            }
        }
        analyzeModal.hidden = false;
        analyzeModal.removeAttribute("aria-hidden");
        analyzeModal.classList.add("is-open");
        document.body.style.overflow = "hidden";
        lockAnalyzePage();
        if (!skipQueueReset) {
            startQueuePhase();
        } else {
            startProgressAnimation();
        }
    }

    function closeAnalyzeModal() {
        if (!analyzeModal) return;
        showReconnectState(false);
        queueState.active = false;
        queueState.queueEnded = false;
        clearQueueTimers();
        stopProgressAnimation();
        setQueueVisible(false);
        if (analyzeDialog) {
            analyzeDialog.classList.remove("eval-analyze__dialog--queue");
        }
        analyzeModal.hidden = true;
        analyzeModal.setAttribute("aria-hidden", "true");
        analyzeModal.classList.remove("is-open");
        document.body.style.overflow = "";
        unlockAnalyzePage();
    }

    function openErrorDialog(message) {
        if (!errorDialog || !errorDialogMessage) {
            return;
        }
        errorDialogMessage.textContent = message || "لطفاً موارد فرم را بررسی کنید.";
        errorDialog.hidden = false;
        errorDialog.removeAttribute("aria-hidden");
        errorDialog.classList.add("is-open");
        document.body.style.overflow = "hidden";
        if (errorDialogClose) {
            setTimeout(function () {
                errorDialogClose.focus();
            }, 120);
        }
    }

    function closeErrorDialog() {
        if (!errorDialog) return;
        errorDialog.hidden = true;
        errorDialog.setAttribute("aria-hidden", "true");
        errorDialog.classList.remove("is-open");
        if (!analyzeModal || analyzeModal.hidden) {
            document.body.style.overflow = "";
        }
    }

    if (errorDialog) {
        errorDialog.querySelectorAll("[data-eval-error-close]").forEach(function (el) {
            el.addEventListener("click", closeErrorDialog);
        });
        errorDialog.addEventListener("keydown", function (e) {
            if (e.key === "Escape") {
                e.preventDefault();
                closeErrorDialog();
            }
        });
    }

    function analyzeStepIndex(stepId) {
        if (stepId === "done") return STEP_ORDER.length - 1;
        var idx = STEP_ORDER.indexOf(stepId);
        return idx >= 0 ? idx : 0;
    }

    function updateAnalyzeChecklistSlide(stepId) {
        if (!analyzeChecklist) return;
        var idx = analyzeStepIndex(stepId);
        var items = analyzeChecklist.querySelectorAll("li");
        items.forEach(function (li) {
            var sid = li.getAttribute("data-step");
            var si = STEP_ORDER.indexOf(sid);
            li.classList.remove("is-done", "is-active", "is-preview");
            if (stepId === "done") {
                li.classList.add("is-done");
                return;
            }
            if (si >= 0 && si < idx) li.classList.add("is-done");
            if (sid === stepId) li.classList.add("is-active");
            else if (si > idx && si <= idx + 3) li.classList.add("is-preview");
        });
        var first = items[0];
        var stepH =
            first && first.offsetHeight
                ? first.offsetHeight
                : parseFloat(
                      getComputedStyle(analyzeChecklist.parentElement || document.body)
                          .getPropertyValue("--eval-analyze-step-h")
                  ) || 38;
        analyzeChecklist.style.transform = "translate3d(0, -" + idx * stepH + "px, 0)";
    }

    function renderAnalyzePercent(pct) {
        var safe = Math.min(100, Math.max(0, Math.round(pct)));
        if (analyzeBar) analyzeBar.style.width = safe + "%";
        if (analyzePercent) analyzePercent.textContent = toPersianDigits(safe) + "٪";
    }

    function updateAnalyzeUI(percent, label, stepId) {
        var pct = Math.min(100, Math.max(0, parseInt(percent, 10) || 0));
        analyzeTargetPct = Math.max(analyzeTargetPct, pct);
        if (queueState.active) {
            if (pct > analyzeDisplayPct) {
                analyzeDisplayPct = Math.min(pct, analyzeDisplayPct + 3);
            }
            renderAnalyzePercent(analyzeDisplayPct);
            if (queueState.ahead <= 0) {
                if (label && analyzeStep) analyzeStep.textContent = label;
                updateAnalyzeChecklistSlide(stepId || "validate");
            } else {
                updateAnalyzeChecklistSlide("validate");
            }
            return;
        }
        if (analyzeTargetPct > analyzeDisplayPct) {
            analyzeDisplayPct = analyzeTargetPct;
        }
        renderAnalyzePercent(analyzeDisplayPct);
        if (analyzeStep) analyzeStep.textContent = label || "";
        updateAnalyzeChecklistSlide(stepId || "validate");
    }

    function pollDelayMs() {
        analyzePollCount += 1;
        if (analyzePollCount <= 20) return 90;
        if (analyzePollCount <= 45) return 150;
        return 240;
    }

    function pollEvaluationJob(jobId) {
        var url = buildProcessUrl(jobId);
        if (!url) return Promise.reject(new Error("no_process_url"));

        return fetch(url, {
            method: "GET",
            credentials: "same-origin",
            headers: { Accept: "application/json" },
        })
            .then(readJsonResponse)
            .then(function (data) {
                resetEvalReconnectAttempts();
                showReconnectState(false);

                if (data.error === "job_not_found") {
                    clearActiveJob();
                    throw new Error(data.error || "پرونده تحلیل یافت نشد.");
                }
                if (data.status === "error") {
                    clearActiveJob();
                    throw new Error(data.error || "خطا در تحلیل");
                }

                jobId = applyProcessPayload(data, jobId);

                if (data.status === "done" && data.redirect_url) {
                    updateAnalyzeUI(100, "در حال انتقال به گزارش…", "done");
                    window.setTimeout(function () {
                        redirectToEvaluationResult(data.redirect_url);
                    }, 350);
                    return data;
                }

                return new Promise(function (resolve) {
                    window.setTimeout(function () {
                        queueState.pollStarted = false;
                        resolve(pollEvaluationJob(jobId));
                    }, pollDelayMs());
                });
            })
            .catch(function (err) {
                if (!isRetryableEvalError(err)) throw err;
                showReconnectState(true);
                var retryJobId = jobId || queueState.jobId || loadActiveJob();
                return waitForInternetRetry(function () {
                    queueState.pollStarted = false;
                    return pollEvaluationJob(retryJobId);
                });
            });
    }

    function submitEvaluationAjax() {
        var submitUrl = pageConfig.evalSubmitUrl;
        if (!submitUrl) return Promise.reject(new Error("no_submit_url"));

        var fd = new FormData(form);
        return fetch(submitUrl, {
            method: "POST",
            body: fd,
            credentials: "same-origin",
            headers: {
                "X-CSRFToken": getCsrfToken(),
                Accept: "application/json",
            },
        })
            .then(readJsonResponse)
            .then(function (data) {
                if (!data.ok) {
                    var err = new Error("validation");
                    err.errors = data.errors || {};
                    err.captcha_question = data.captcha_question || "";
                    err.retryable = false;
                    throw err;
                }
                if (data.job_id) saveActiveJob(data.job_id);
                return data;
            })
            .catch(function (err) {
                if (err && (err.errors || err.retryable === false)) throw err;
                var netErr = new Error("در انتظار اینترنت…");
                netErr.retryable = true;
                throw netErr;
            });
    }

    function submitWithNetworkResilience() {
        return submitEvaluationAjax()
            .catch(function (err) {
                if (err && err.errors) throw err;
                if (!isRetryableEvalError(err)) throw err;
                return tryRecoverActiveJobFromServer(queueState.jobId || loadActiveJob()).then(
                    function (data) {
                        if (data) {
                            resetEvalReconnectAttempts();
                            showReconnectState(false);
                            if (data.status === "done" && data.redirect_url) {
                                redirectToEvaluationResult(data.redirect_url);
                                return { recovered: true };
                            }
                            queueState.submitDone = true;
                            queueState.jobId =
                                (data.job_id && String(data.job_id)) || loadActiveJob();
                            syncQueueFromServer(
                                typeof data.queue_ahead === "number" ? data.queue_ahead : 0
                            );
                            beginJobPolling(queueState.jobId);
                            tryFinishQueuePhase();
                            return { recovered: true };
                        }
                        return waitForInternetRetry(submitWithNetworkResilience);
                    }
                );
            });
    }

    function refreshCaptchaAfterError(question) {
        if (!window.SafiranCaptcha) return;
        var captchaEl = qs("captcha_answer");
        if (captchaEl) captchaEl.value = "";
        if (question) {
            window.SafiranCaptcha.applyQuestion("evaluation", question);
            return;
        }
        window.SafiranCaptcha.refresh("evaluation");
    }

    function showFormErrors(errors, captchaQuestion) {
        if (!errors || typeof errors !== "object") {
            var fallback = "لطفاً موارد الزامی فرم را تکمیل کنید.";
            showValidationMessage(fallback);
            openErrorDialog(fallback);
            return;
        }
        refreshCaptchaAfterError(captchaQuestion);
        var firstPanel = total;
        var messages = [];
        Object.keys(errors).forEach(function (field) {
            if (field === "__all__") {
                var allRaw = errors[field];
                var allMsg = Array.isArray(allRaw) ? allRaw[0] : allRaw;
                if (allMsg) messages.push(String(allMsg));
                return;
            }
            messages.push(evalFieldMessage(field, errors[field]));
            markFieldInvalidByName(field);
            var pn = panelForField(field);
            if (pn < firstPanel) firstPanel = pn;
        });
        var display =
            messages.length === 0
                ? "لطفاً موارد الزامی فرم را تکمیل کنید."
                : messages.length === 1
                  ? messages[0]
                  : messages.slice(0, 4).join(" • ");
        showValidationMessage(display);
        openErrorDialog(display);
        showPanel(firstPanel, true);
        if (errors.captcha_answer) {
            var captchaInput = qs("captcha_answer");
            if (captchaInput) {
                setTimeout(function () {
                    captchaInput.focus({ preventScroll: true });
                }, 280);
            }
        }
    }

    form.addEventListener("submit", function (e) {
        syncTargetCountry();
        syncHasIelts();
        for (var s = 1; s <= total; s++) {
            if (!validateStep(s)) {
                e.preventDefault();
                analyzeSubmitting = false;
                if (btnSubmit) btnSubmit.disabled = false;
                showPanel(s, true);
                return;
            }
        }

        if (!pageConfig.evalSubmitUrl || !pageConfig.evalProcessUrl) {
            return;
        }

        e.preventDefault();
        if (analyzeSubmitting) return;
        analyzeSubmitting = true;
        if (btnSubmit) btnSubmit.disabled = true;

        openAnalyzeModal();

        submitWithNetworkResilience()
            .then(function (data) {
                if (data && data.recovered) return;
                queueState.submitDone = true;
                queueState.jobId = data.job_id;
                syncQueueFromServer(
                    typeof data.queue_ahead === "number" ? data.queue_ahead : 0
                );
                beginJobPolling(data.job_id);
                tryFinishQueuePhase();
            })
            .catch(function (err) {
                if (isRetryableEvalError(err)) {
                    return waitForInternetRetry(function () {
                        return tryRecoverActiveJobFromServer(loadActiveJob()).then(function (
                            recovered
                        ) {
                            if (recovered) {
                                resumeEvaluationFromPayload(recovered, loadActiveJob());
                                return;
                            }
                            return submitWithNetworkResilience();
                        });
                    });
                }
                closeAnalyzeModal();
                clearActiveJob();
                analyzeSubmitting = false;
                if (btnSubmit) btnSubmit.disabled = false;
                if (err && err.errors && Object.keys(err.errors).length) {
                    showFormErrors(err.errors, err.captcha_question);
                    return;
                }
                var friendly = userFacingEvalError(err);
                showValidationMessage(friendly);
                openErrorDialog(friendly);
            });
    });

    form.querySelectorAll("input.eval-input").forEach(function (inp) {
        inp.addEventListener("input", function () {
            if (!inp.classList.contains("is-warn")) {
                inp.classList.remove("is-invalid");
            }
            var validationNode = document.querySelector("[data-eval-validation]:not([hidden])");
            if (validationNode) showValidationMessage("");
        });
    });

    var phone = qs("phone");
    if (phone) phone.classList.add("tel-ltr");

    if (langSelect) {
        langSelect.addEventListener("change", toggleLangScore);
        toggleLangScore();
    }

    function initContextPrefill() {
        var country = form.getAttribute("data-prefill-country");
        var majorText = form.getAttribute("data-prefill-major");
        var initialStep = parseInt(form.getAttribute("data-initial-step") || "1", 10);
        if (initialStep !== 1) return;

        if (country) {
            form.querySelectorAll('input[name="desired_countries"]').forEach(function (cb) {
                if (cb.value === country && !cb.checked) {
                    cb.checked = true;
                    cb.dispatchEvent(new Event("change", { bubbles: true }));
                }
            });
            var targetCountry = qs("target_country");
            if (targetCountry && !targetCountry.value) {
                targetCountry.value = country;
                targetCountry.dispatchEvent(new Event("change", { bubbles: true }));
            }
            form.querySelectorAll('[data-country-card="' + country + '"]').forEach(function (card) {
                card.classList.add("is-selected");
            });
        }

        if (majorText) {
            var majorField = qs("field_of_study");
            if (majorField && !majorField.value.trim()) {
                majorField.value = majorText;
                majorField.dispatchEvent(new Event("input", { bubbles: true }));
            }
        }
    }

    function initNavPrefill() {
        var prefill = form.getAttribute("data-prefill-degree");
        var initialStep = parseInt(form.getAttribute("data-initial-step") || "1", 10);
        if (!prefill || initialStep !== 1) return;
        var select = qs("current_degree");
        if (!select || (select.value && select.value !== "")) return;
        select.value = prefill;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        form.querySelectorAll('[data-sync-select="' + select.name + '"]').forEach(syncPickGroup);
        if (form.getAttribute("data-nav-intent") === "scholarship") {
            var intro = document.querySelector(".eval_intro p");
            if (intro) {
                intro.innerHTML =
                    "برای <strong>پیشنهاد بورسیه و مسیر پذیرش</strong> اطلاعات را وارد کنید. " +
                    "پس از ثبت، گزارش شخصی‌سازی‌شده نمایش داده می‌شود.";
            }
        }
    }

    function initMajorComboboxFields() {
        if (typeof global.initMajorComboboxes !== "function") return;
        var items = (pageConfig.evalMajorOptions || []).slice();
        global.initMajorComboboxes(form, {
            items: items,
            suggestUrl: pageConfig.evalMajorSuggestUrl || "",
        });

        form.querySelectorAll('input[name="desired_countries"]').forEach(function (cb) {
            cb.addEventListener("change", function () {
                form.querySelectorAll("[data-major-combobox]").forEach(function (root) {
                    var field = root.querySelector(".major-combobox__field");
                    if (field && document.activeElement === field) {
                        field.dispatchEvent(new Event("input", { bubbles: true }));
                    }
                });
            });
        });
    }

    initPickGroups();
    initYearPickers();
    initCountryCards();
    initLiveValidation();
    initNavPrefill();
    initContextPrefill();
    initMajorComboboxFields();
    initDraftPersistence();

    var draft = hasServerFormErrors() ? null : loadDraft();
    if (draft) {
        if (!restoreDraft(draft)) draft = null;
    }

    var initial = resolveInitialStep(draft);
    showPanel(initial, false);

    if (draftRestored) {
        var hintEl = firstHintEl();
        if (hintEl) {
            var restoredHint = hintEl.textContent;
            setTextAll("[data-eval-hint]", "اطلاعات قبلی بازیابی شد — می‌توانید ادامه دهید.");
            window.setTimeout(function () {
                var current = firstHintEl();
                if (current && current.textContent.indexOf("بازیابی شد") >= 0) {
                    setTextAll("[data-eval-hint]", restoredHint);
                }
            }, 4500);
        }
    }

    tryResumeEvaluationOnLoad();
})();
