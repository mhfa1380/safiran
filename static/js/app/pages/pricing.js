/**
 * ماشین‌حساب تعرفه — ویزارد چندمرحله‌ای با API بکند
 */
(function () {
    "use strict";

    var cfg = window.PAGE_CONFIG || {};
    var calcUrl = cfg.pricingCalculateUrl;
    var appointmentUrl = cfg.pricingAppointmentUrl || "/رزرو-مشاوره/";

    var countriesEl = document.getElementById("pricing-countries-data");
    var studyEl = document.getElementById("pricing-study-countries-data");
    var countries = [];
    var studyPricing = { countries: [], default_code: "", compare_rows: [] };
    if (countriesEl && countriesEl.textContent) {
        try {
            countries = JSON.parse(countriesEl.textContent);
        } catch (e) {
            countries = [];
        }
    }
    if (studyEl && studyEl.textContent) {
        try {
            studyPricing = JSON.parse(studyEl.textContent);
        } catch (e) {
            studyPricing = { countries: [], default_code: "", compare_rows: [] };
        }
    }

    var selectedCountryCode = studyPricing.default_code || (studyPricing.countries[0] && studyPricing.countries[0].code) || "";

    var bodyEl = document.getElementById("calc-body");
    var liveInner = document.getElementById("calc-live-inner");
    var livePanel = document.getElementById("calc-live");
    var progressBar = document.getElementById("calc-progress-bar");
    var progressWrap = document.getElementById("calc-progress-wrap");
    var btnNext = document.getElementById("calc-btn-next");
    var btnBack = document.getElementById("calc-btn-back");

    if (!bodyEl || !btnNext) return;

    var GOAL_OPTIONS = [
        { value: "study", label: "مهاجرت تحصیلی", icon: "ti-book" },
        { value: "language", label: "دوره زبان", icon: "ti-world" },
        { value: "visa_only", label: "فقط ویزا", icon: "ti-id-badge" },
        { value: "docs_only", label: "مدارک و مقرری", icon: "ti-files" },
    ];

    var SITUATION_BY_GOAL = {
        study: [
            { value: "starting", label: "تازه شروع کرده‌ام", icon: "ti-flag-alt" },
            { value: "has_admission", label: "پذیرش دانشگاه دارم", icon: "ti-check-box" },
            { value: "in_progress", label: "وسط کار اپلای هستم", icon: "ti-reload" },
            { value: "visa_stage", label: "مرحله ویزا و سفارت", icon: "ti-id-badge" },
        ],
        language: [
            { value: "starting", label: "هنوز اپلای نکرده‌ام", icon: "ti-flag-alt" },
            { value: "in_progress", label: "در حال اپلای هستم", icon: "ti-reload" },
            { value: "has_admission", label: "پذیرش دارم", icon: "ti-check-box" },
        ],
        visa_only: [
            { value: "visa_stage", label: "آماده ویزا هستم", icon: "ti-id-badge" },
            { value: "in_progress", label: "مدارک را آماده می‌کنم", icon: "ti-files" },
        ],
        docs_only: [{ value: "starting", label: "نیاز به راهنمایی دارم", icon: "ti-help-alt" }],
    };

    var state = {
        stepIndex: 0,
        goal: "",
        countrySlug: "",
        countryName: "",
        situation: "",
        extraKeys: [],
        optionalExtras: [],
        result: null,
        previewResult: null,
        prevServiceKeys: {},
        previewTimer: null,
        previewRequestId: 0,
    };

    function getSteps() {
        var steps = [{ id: "goal", type: "choice", title: "هدف شما چیست؟", subtitle: "یک گزینه انتخاب کنید" }];
        if (state.goal && state.goal !== "") {
            steps.push({
                id: "country",
                type: "country",
                title: "کشور مقصد",
                subtitle: "برای محاسبه مقرری و پیشنهاد دقیق‌تر",
            });
            var sitOpts = SITUATION_BY_GOAL[state.goal] || [];
            if (sitOpts.length) {
                steps.push({
                    id: "situation",
                    type: "choice",
                    title: "در چه مرحله‌ای هستید؟",
                    subtitle: "پیشنهاد بر اساس وضعیت فعلی تنظیم می‌شود",
                    options: sitOpts,
                });
            }
            steps.push({
                id: "extras",
                type: "extras",
                title: "خدمات تکمیلی (اختیاری)",
                subtitle: "در صورت نیاز اضافه کنید — می‌توانید رد کنید",
                skippable: true,
            });
        }
        steps.push({ id: "result", type: "result", title: "پیشنهاد تعرفه شما" });
        return steps;
    }

    function getCsrfToken() {
        var match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    function getStudyCountryByCode(code) {
        return (
            studyPricing.countries.find(function (c) {
                return c.code === code;
            }) || null
        );
    }

    function resolveCountrySlug() {
        if (state.countrySlug) return state.countrySlug;
        var sc = getStudyCountryByCode(selectedCountryCode);
        return sc && sc.allowance_slug ? sc.allowance_slug : "";
    }

    function resolveSituationForPreview() {
        if (state.situation) return state.situation;
        var opts = SITUATION_BY_GOAL[state.goal] || [];
        return opts.length ? opts[0].value : "";
    }

    function isOnResultStep() {
        var steps = getSteps();
        var step = steps[state.stepIndex];
        return step && step.id === "result";
    }

    function setLivePanelVisible(show) {
        if (livePanel) livePanel.hidden = !show;
    }

    function renderLivePlaceholder(message) {
        if (!liveInner) return;
        liveInner.innerHTML =
            '<p class="pricing-calc__live-placeholder">' +
            escapeHtml(message || "گزینه‌ها را انتخاب کنید تا جمع لحظه‌ای نمایش داده شود.") +
            "</p>";
    }

    function renderLiveSummary(data, meta) {
        if (!liveInner) return;
        meta = meta || {};

        if (!data || !data.ok) {
            renderLivePlaceholder(
                (data && data.error) || "برای برآورد، هدف و کشور مقصد را انتخاب کنید."
            );
            return;
        }

        var services = data.services || [];
        var newKeys = {};
        services.forEach(function (s) {
            newKeys[s.key] = true;
        });

        var added = [];
        var removed = [];
        Object.keys(newKeys).forEach(function (k) {
            if (!state.prevServiceKeys[k]) added.push(k);
        });
        Object.keys(state.prevServiceKeys).forEach(function (k) {
            if (!newKeys[k]) removed.push(k);
        });

        var addedLines = [];
        var removedLines = [];
        services.forEach(function (s) {
            if (added.indexOf(s.key) >= 0) addedLines.push(s);
        });
        if (state.previewResult && state.previewResult.services) {
            state.previewResult.services.forEach(function (s) {
                if (removed.indexOf(s.key) >= 0) removedLines.push(s);
            });
        }

        state.prevServiceKeys = newKeys;
        state.previewResult = data;

        var countryLabel = state.countryName || "";
        if (!countryLabel && selectedCountryCode) {
            var sc = getStudyCountryByCode(selectedCountryCode);
            if (sc) countryLabel = sc.name;
        }

        var html =
            '<div class="pricing-calc__live-head">' +
            '<p class="pricing-calc__live-label">جمع لحظه‌ای حق‌الزحمه</p>' +
            '<p class="pricing-calc__live-total">' +
            escapeHtml(data.total_display || "—") +
            "</p>";
        if (countryLabel) {
            html +=
                '<p class="pricing-calc__live-country">کشور: ' +
                escapeHtml(countryLabel) +
                (meta.previewSituation ? " · برآورد موقت" : "") +
                "</p>";
        }
        html += "</div>";

        if (addedLines.length && meta.showDelta !== false) {
            addedLines.forEach(function (s) {
                html +=
                    '<p class="pricing-calc__live-delta">افزوده شد: ' +
                    escapeHtml(s.title) +
                    " — " +
                    escapeHtml(s.price_display) +
                    "</p>";
            });
        }
        if (removedLines.length && meta.showDelta !== false) {
            removedLines.forEach(function (s) {
                html +=
                    '<p class="pricing-calc__live-delta is-remove">حذف شد: ' +
                    escapeHtml(s.title) +
                    "</p>";
            });
        }

        html += '<ul class="pricing-calc__live-list">';
        services.forEach(function (s) {
            var isNew = added.indexOf(s.key) >= 0 ? " is-new" : "";
            html +=
                '<li class="pricing-calc__live-item' +
                isNew +
                '">' +
                '<span class="pricing-calc__live-item-name">' +
                escapeHtml(s.title) +
                "</span>" +
                '<span class="pricing-calc__live-item-price">' +
                escapeHtml(s.price_display) +
                "</span></li>";
        });
        html += "</ul>";

        if (data.upfront_display) {
            html +=
                '<p class="pricing-calc__live-hint">پیش‌پرداخت ۴۰٪: ' +
                escapeHtml(data.upfront_display) +
                "</p>";
        }

        liveInner.innerHTML = html;
    }

    function scheduleLivePreview() {
        if (!calcUrl || !liveInner || isOnResultStep()) {
            setLivePanelVisible(false);
            return;
        }
        setLivePanelVisible(true);
        clearTimeout(state.previewTimer);
        state.previewTimer = setTimeout(fetchLivePreview, 300);
    }

    function fetchLivePreview() {
        if (!state.goal) {
            renderLivePlaceholder();
            return;
        }

        var countrySlug = resolveCountrySlug();
        var situation = resolveSituationForPreview();
        if (!countrySlug) {
            renderLivePlaceholder("کشور مقصد را انتخاب کنید تا مبلغ دقیق محاسبه شود.");
            return;
        }
        if (!situation) {
            renderLivePlaceholder("مرحله پرونده را مشخص کنید.");
            return;
        }

        var requestId = ++state.previewRequestId;
        liveInner.innerHTML = '<p class="pricing-calc__live-loading">در حال محاسبه…</p>';

        fetch(calcUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            credentials: "same-origin",
            body: JSON.stringify({
                goal: state.goal,
                situation: situation,
                country_slug: countrySlug,
                extra_keys: state.extraKeys,
            }),
        })
            .then(function (r) {
                if (!r.ok) {
                    return r.json().catch(function () {
                        return { ok: false, error: "خطا در محاسبه (" + r.status + ")" };
                    });
                }
                return r.json();
            })
            .then(function (data) {
                if (requestId !== state.previewRequestId || isOnResultStep()) return;
                var previewSituation = !state.situation;
                renderLiveSummary(data, {
                    previewSituation: previewSituation,
                    showDelta: !previewSituation,
                });
            })
            .catch(function () {
                if (requestId !== state.previewRequestId) return;
                renderLivePlaceholder("خطا در محاسبه لحظه‌ای.");
            });
    }

    function setProgress() {
        var steps = getSteps();
        var pct = steps.length > 1 ? Math.round((state.stepIndex / (steps.length - 1)) * 100) : 0;
        if (progressBar) progressBar.style.width = pct + "%";
        if (progressWrap) progressWrap.setAttribute("aria-valuenow", String(pct));
    }

    function canProceed() {
        var steps = getSteps();
        var step = steps[state.stepIndex];
        if (!step) return false;
        if (step.id === "goal") return !!state.goal;
        if (step.id === "country") return !!state.countrySlug;
        if (step.id === "situation") return !!state.situation;
        if (step.id === "extras") return true;
        return true;
    }

    function updateNav() {
        var steps = getSteps();
        var step = steps[state.stepIndex];
        btnBack.hidden = state.stepIndex === 0;
        if (step && step.id === "result") {
            btnNext.textContent = "محاسبه مجدد";
            btnNext.disabled = false;
        } else if (step && step.id === "extras") {
            btnNext.textContent = "مشاهده پیشنهاد";
            btnNext.disabled = false;
        } else {
            btnNext.textContent = "ادامه";
            btnNext.disabled = !canProceed();
        }
    }

    function renderChoiceStep(step) {
        var opts = step.options || GOAL_OPTIONS;
        var html =
            '<div class="pricing-calc__step" data-step="' +
            step.id +
            '">' +
            '<h3 class="pricing-calc__step-title">' +
            escapeHtml(step.title) +
            "</h3>" +
            '<p class="pricing-calc__step-sub">' +
            escapeHtml(step.subtitle || "") +
            "</p>" +
            '<div class="pricing-calc__choices">';
        opts.forEach(function (opt) {
            var selected = "";
            if (step.id === "goal" && state.goal === opt.value) selected = " is-selected";
            if (step.id === "situation" && state.situation === opt.value) selected = " is-selected";
            html +=
                '<button type="button" class="pricing-calc__choice' +
                selected +
                '" data-value="' +
                escapeAttr(opt.value) +
                '">' +
                '<span class="' +
                escapeAttr(opt.icon || "ti-angle-left") +
                '" aria-hidden="true"></span>' +
                "<span>" +
                escapeHtml(opt.label) +
                "</span></button>";
        });
        html += "</div></div>";
        return html;
    }

    function renderCountryStep(step) {
        if (studyPricing.countries.length) {
            var chips = studyPricing.countries
                .map(function (sc) {
                    var active = resolveCountrySlug() === sc.allowance_slug ? " is-selected" : "";
                    return (
                        '<button type="button" class="pricing-calc__choice' +
                        active +
                        '" data-country-code="' +
                        escapeAttr(sc.code) +
                        '">' +
                        '<span class="ti-flag-alt" aria-hidden="true"></span>' +
                        "<span>" +
                        escapeHtml(sc.name) +
                        "</span></button>"
                    );
                })
                .join("");
            return (
                '<div class="pricing-calc__step" data-step="country">' +
                '<h3 class="pricing-calc__step-title">' +
                escapeHtml(step.title) +
                "</h3>" +
                '<p class="pricing-calc__step-sub">' +
                escapeHtml(step.subtitle || "") +
                "</p>" +
                '<div class="pricing-calc__choices pricing-calc__choices--country">' +
                chips +
                "</div></div>"
            );
        }
        return (
            '<div class="pricing-calc__step" data-step="country">' +
            '<h3 class="pricing-calc__step-title">' +
            escapeHtml(step.title) +
            "</h3>" +
            '<p class="pricing-calc__step-sub">' +
            escapeHtml(step.subtitle || "") +
            "</p>" +
            '<div class="pricing-calc__country-wrap">' +
            '<div class="faq-page__search-field">' +
            '<span class="faq-page__search-icon ti-search" aria-hidden="true"></span>' +
            '<input type="text" class="pricing-calc__country-input" id="calc-country-input" ' +
            'placeholder="نام کشور را بنویسید…" value="' +
            escapeAttr(state.countryName) +
            '" autocomplete="off">' +
            "</div>" +
            '<ul class="pricing-calc__country-list" id="calc-country-list"></ul>' +
            "</div>" +
            "</div>"
        );
    }

    function renderExtrasStep(step) {
        var html =
            '<div class="pricing-calc__step" data-step="extras">' +
            '<h3 class="pricing-calc__step-title">' +
            escapeHtml(step.title) +
            "</h3>" +
            '<p class="pricing-calc__step-sub">' +
            escapeHtml(step.subtitle || "") +
            '</p><div class="pricing-calc__extras" id="calc-extras-wrap">';
        if (!state.optionalExtras.length) {
            html += '<p class="text-muted">در حال آماده‌سازی…</p>';
        } else {
            state.optionalExtras.forEach(function (ex) {
                var on = state.extraKeys.indexOf(ex.key) >= 0 ? " is-on" : "";
                html +=
                    '<button type="button" class="pricing-calc__extra' +
                    on +
                    '" data-key="' +
                    escapeAttr(ex.key) +
                    '">' +
                    escapeHtml(ex.title) +
                    " — " +
                    escapeHtml(ex.price_display) +
                    "</button>";
            });
        }
        html += "</div></div>";
        return html;
    }

    function renderResult(data) {
        if (!data || !data.ok) {
            return (
                '<div class="pricing-result"><p class="text-danger">' +
                escapeHtml((data && data.error) || "خطا در محاسبه") +
                "</p></div>"
            );
        }

        var html = '<div class="pricing-result">';
        html +=
            '<div class="pricing-result__total">' +
            '<p class="pricing-result__total-label">برآورد حق‌الزحمه خدمات موسسه</p>' +
            '<p class="pricing-result__total-value">' +
            escapeHtml(data.total_display) +
            "</p></div>";

        if (data.upfront_display) {
            html +=
                '<p class="pricing-result__payment"><strong>پیش‌پرداخت (۴۰٪):</strong> ' +
                escapeHtml(data.upfront_display) +
                " — <strong>مابقی:</strong> " +
                escapeHtml(data.remainder_display || "") +
                "</p>";
        }

        if (data.living_allowance) {
            html +=
                '<div class="pricing-result__living"><strong>مقرری بانکی ' +
                escapeHtml(data.living_allowance.name) +
                ":</strong> " +
                escapeHtml(data.living_allowance.display) +
                " <span>(جدا از حق‌الزحمه)</span></div>";
        }

        html += '<ul class="pricing-result__list">';
        (data.services || []).forEach(function (s) {
            html +=
                '<li class="pricing-result__item">' +
                "<div><p class=\"pricing-result__item-title\">" +
                escapeHtml(s.title) +
                "</p>";
            if (s.reason) {
                html += '<p class="pricing-result__item-reason">' + escapeHtml(s.reason) + "</p>";
            }
            html +=
                "</div><span class=\"pricing-result__item-price\">" +
                escapeHtml(s.price_display) +
                "</span></li>";
        });
        html += "</ul>";

        if (data.notes && data.notes.length) {
            html += '<ul class="pricing-result__notes">';
            data.notes.forEach(function (n) {
                html += "<li>" + escapeHtml(n) + "</li>";
            });
            html += "</ul>";
        }

        html +=
            '<div class="pricing-result__actions">' +
            '<a href="' +
            escapeAttr(appointmentUrl) +
            '" class="faq-page__btn faq-page__btn--primary">رزرو مشاوره</a>' +
            '<button type="button" class="faq-page__btn faq-page__btn--ghost" id="calc-restart">شروع دوباره</button>' +
            "</div></div>";

        highlightTariffCards(data.services || []);
        return html;
    }

    function highlightTariffCards(services) {
        document.querySelectorAll(".faq-page__item").forEach(function (item) {
            item.classList.remove("is-highlight");
            item.removeAttribute("open");
        });
        var first = null;
        services.forEach(function (s) {
            var item = document.querySelector('.faq-page__item[data-tariff-key="' + s.key + '"]');
            if (item) {
                item.classList.add("is-highlight");
                item.setAttribute("open", "");
                if (!first) first = item;
            }
        });
        if (first) {
            setTimeout(function () {
                first.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }, 400);
        }
    }

    function escapeHtml(str) {
        if (!str) return "";
        var d = document.createElement("div");
        d.textContent = str;
        return d.innerHTML;
    }

    function escapeAttr(str) {
        return escapeHtml(str).replace(/"/g, "&quot;");
    }

    function bindCountrySearch() {
        var input = document.getElementById("calc-country-input");
        var list = document.getElementById("calc-country-list");
        if (!input || !list) return;

        function showList(filter) {
            var q = (filter || "").trim().toLowerCase();
            var items = countries.filter(function (c) {
                return !q || (c.search && c.search.indexOf(q) >= 0) || (c.name && c.name.toLowerCase().indexOf(q) >= 0);
            });
            list.innerHTML = "";
            items.slice(0, 12).forEach(function (c) {
                var li = document.createElement("li");
                li.className = "pricing-calc__country-item";
                li.setAttribute("role", "option");
                li.dataset.slug = c.slug;
                li.innerHTML =
                    escapeHtml(c.name) + "<small>" + escapeHtml(c.display) + "</small>";
                li.addEventListener("click", function () {
                    state.countrySlug = c.slug;
                    state.countryName = c.name;
                    input.value = c.name;
                    list.classList.remove("is-open");
                    updateNav();
                    scheduleLivePreview();
                });
                list.appendChild(li);
            });
            list.classList.toggle("is-open", items.length > 0);
        }

        input.addEventListener("input", function () {
            state.countrySlug = "";
            state.countryName = input.value;
            showList(input.value);
            updateNav();
        });
        input.addEventListener("focus", function () {
            showList(input.value);
        });
        document.addEventListener("click", function (e) {
            if (!list.contains(e.target) && e.target !== input) {
                list.classList.remove("is-open");
            }
        });
    }

    function bindStepEvents() {
        bodyEl.querySelectorAll(".pricing-calc__choice").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var stepEl = btn.closest("[data-step]");
                var stepId = stepEl ? stepEl.getAttribute("data-step") : "";
                var val = btn.getAttribute("data-value");
                bodyEl.querySelectorAll(".pricing-calc__choice").forEach(function (b) {
                    b.classList.remove("is-selected");
                });
                btn.classList.add("is-selected");
                if (stepId === "goal") {
                    state.goal = val;
                    state.situation = "";
                    state.extraKeys = [];
                    state.optionalExtras = [];
                    state.prevServiceKeys = {};
                } else if (stepId === "situation") {
                    state.situation = val;
                }
                updateNav();
                scheduleLivePreview();
            });
        });

        bodyEl.querySelectorAll('[data-step="country"] .pricing-calc__choice[data-country-code]').forEach(
            function (btn) {
                btn.addEventListener("click", function () {
                    var code = btn.getAttribute("data-country-code");
                    var sc = getStudyCountryByCode(code);
                    if (!sc) return;
                    bodyEl.querySelectorAll('[data-step="country"] .pricing-calc__choice').forEach(function (b) {
                        b.classList.remove("is-selected");
                    });
                    btn.classList.add("is-selected");
                    state.countrySlug = sc.allowance_slug || "";
                    state.countryName = sc.name || "";
                    selectedCountryCode = sc.code;
                    applyCountryPrices(sc.code);
                    updateNav();
                    scheduleLivePreview();
                });
            }
        );

        bodyEl.querySelectorAll(".pricing-calc__extra").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var key = btn.getAttribute("data-key");
                var idx = state.extraKeys.indexOf(key);
                if (idx >= 0) {
                    state.extraKeys.splice(idx, 1);
                    btn.classList.remove("is-on");
                } else {
                    state.extraKeys.push(key);
                    btn.classList.add("is-on");
                }
                scheduleLivePreview();
            });
        });

        bindCountrySearch();

        var restart = document.getElementById("calc-restart");
        if (restart) {
            restart.addEventListener("click", function () {
                state.stepIndex = 0;
                state.goal = "";
                state.countrySlug = "";
                state.countryName = "";
                state.situation = "";
                state.extraKeys = [];
                state.result = null;
                state.previewResult = null;
                state.prevServiceKeys = {};
                renderStep();
            });
        }
    }

    function prefetchExtras() {
        if (!calcUrl || !state.goal || !state.situation) return Promise.resolve();
        return fetch(calcUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({
                goal: state.goal,
                situation: state.situation,
                country_slug: state.countrySlug,
                extra_keys: [],
            }),
        })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                if (data.ok && data.optional_extras) {
                    state.optionalExtras = data.optional_extras;
                }
            })
            .catch(function () {});
    }

    function fetchResult() {
        bodyEl.innerHTML = '<div class="pricing-calc__loading">در حال محاسبه…</div>';
        return fetch(calcUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({
                goal: state.goal,
                situation: state.situation,
                country_slug: state.countrySlug,
                extra_keys: state.extraKeys,
            }),
        })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                state.result = data;
                if (data.ok && data.optional_extras && !state.optionalExtras.length) {
                    state.optionalExtras = data.optional_extras;
                }
                bodyEl.innerHTML = renderResult(data);
                bindStepEvents();
                updateNav();
            })
            .catch(function () {
                bodyEl.innerHTML = renderResult({ ok: false, error: "ارتباط با سرور برقرار نشد." });
                updateNav();
            });
    }

    function renderStep() {
        var steps = getSteps();
        if (state.stepIndex >= steps.length) state.stepIndex = steps.length - 1;
        var step = steps[state.stepIndex];
        setProgress();

        if (step.type === "result") {
            setLivePanelVisible(false);
            fetchResult();
            return;
        }

        setLivePanelVisible(true);

        var html = "";
        if (step.type === "choice") html = renderChoiceStep(step);
        else if (step.type === "country") html = renderCountryStep(step);
        else if (step.type === "extras") {
            html = renderExtrasStep(step);
            prefetchExtras().then(function () {
                if (steps[state.stepIndex] && steps[state.stepIndex].id === "extras") {
                    bodyEl.innerHTML = renderExtrasStep(step);
                    bindStepEvents();
                }
            });
        }

        bodyEl.innerHTML = html;
        bindStepEvents();

        if (step.id === "situation") {
            var sitOpts = SITUATION_BY_GOAL[state.goal] || [];
            if (sitOpts.length === 1 && !state.situation) {
                state.situation = sitOpts[0].value;
                var lone = bodyEl.querySelector(".pricing-calc__choice");
                if (lone) lone.classList.add("is-selected");
            }
        }

        updateNav();
        scheduleLivePreview();
    }

    btnNext.addEventListener("click", function () {
        var steps = getSteps();
        var step = steps[state.stepIndex];
        if (step && step.id === "result") {
            state.stepIndex = 0;
            state.result = null;
            renderStep();
            return;
        }
        if (state.stepIndex < steps.length - 1) {
            state.stepIndex += 1;
            renderStep();
        }
    });

    btnBack.addEventListener("click", function () {
        if (state.stepIndex > 0) {
            state.stepIndex -= 1;
            renderStep();
        }
    });

    renderStep();

    function getSelectedCountry() {
        return studyPricing.countries.find(function (c) {
            return c.code === selectedCountryCode;
        });
    }

    function applyCountryPrices(code) {
        var country = studyPricing.countries.find(function (c) {
            return c.code === code;
        });
        if (!country) return;
        selectedCountryCode = code;

        document.querySelectorAll(".pricing-page__country-chip").forEach(function (btn) {
            var active = btn.getAttribute("data-country-code") === code;
            btn.classList.toggle("is-active", active);
            btn.setAttribute("aria-selected", active ? "true" : "false");
        });

        document.querySelectorAll(".faq-page__item[data-tariff-key]").forEach(function (item) {
            var key = item.getAttribute("data-tariff-key");
            var tag = item.querySelector(".pricing-page__price-tag");
            var line = country.tariffs && country.tariffs[key];
            if (tag && line && line.price_display) {
                tag.textContent = line.price_display;
            }
        });

        document.querySelectorAll("#pricing-consult-compare tbody tr").forEach(function (row) {
            row.classList.toggle(
                "is-active",
                row.getAttribute("data-country-code") === code
            );
        });

        document.querySelectorAll("#allowance-tbody tr").forEach(function (row) {
            var slug = row.getAttribute("data-allowance-slug");
            row.classList.toggle("is-highlight", slug === country.allowance_slug);
        });

        state.countrySlug = country.allowance_slug || "";
        state.countryName = country.name || "";
        scheduleLivePreview();
    }

    if (studyPricing.countries.length) {
        applyCountryPrices(selectedCountryCode);
        document.querySelectorAll(".pricing-page__country-chip").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var code = btn.getAttribute("data-country-code");
                if (code) applyCountryPrices(code);
            });
        });
    } else {
        renderLivePlaceholder();
    }

    /* ناوبری بخش‌ها — سایدبار و چیپ موبایل */
    function setActiveSection(id) {
        document.querySelectorAll("[data-pricing-section]").forEach(function (el) {
            el.classList.toggle("is-active", el.getAttribute("data-pricing-section") === id);
        });
    }

    document.querySelectorAll(".faq-page__nav-link, .faq-page__chip").forEach(function (link) {
        link.addEventListener("click", function (e) {
            var id = link.getAttribute("data-pricing-section");
            if (!id) return;
            var target = document.getElementById(id);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: "smooth", block: "start" });
                setActiveSection(id);
            }
        });
    });

    var sectionIds = [];
    document.querySelectorAll("[data-pricing-section]").forEach(function (el) {
        var id = el.getAttribute("data-pricing-section");
        if (id) sectionIds.push(id);
    });
    var sectionEls = sectionIds
        .map(function (id) {
            return document.getElementById(id);
        })
        .filter(Boolean);

    if (sectionEls.length && "IntersectionObserver" in window) {
        var observer = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        setActiveSection(entry.target.id);
                    }
                });
            },
            { rootMargin: "-30% 0px -55% 0px", threshold: 0 }
        );
        sectionEls.forEach(function (el) {
            observer.observe(el);
        });
    }

    /* فیلتر جدول مقرری */
    var allowanceFilter = document.getElementById("allowance-filter");
    var allowanceTbody = document.getElementById("allowance-tbody");
    if (allowanceFilter && allowanceTbody) {
        allowanceFilter.addEventListener("input", function () {
            var q = allowanceFilter.value.trim().toLowerCase();
            allowanceTbody.querySelectorAll("tr").forEach(function (row) {
                var text = (row.getAttribute("data-search") || row.textContent || "").toLowerCase();
                row.classList.toggle("is-hidden", q && text.indexOf(q) < 0);
            });
        });
    }
})();
