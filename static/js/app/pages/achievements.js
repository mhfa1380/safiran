(function () {
    "use strict";

    var config = window.PAGE_CONFIG || {};
    var wrapper = document.getElementById("achievements-content-wrapper");
    var searchInput = document.getElementById("achievement-search-input");
    var suggestPanel = document.getElementById("achievement-suggest-panel");
    var modal = document.getElementById("achievements-video-modal");
    var player = document.getElementById("achievements-modal-player");
    var modalTitle = document.getElementById("achievements-modal-title");

    if (!wrapper) {
        return;
    }

    var searchUrl = config.achievementSearchUrl || "";
    var suggestUrl = config.achievementSuggestUrl || "";
    var activeMonth = "all";
    var suggestTimer;
    var searchTimer;

    var monthSelectors =
        ".faq-page__nav-link[data-month], .faq-page__filter[data-month]";

    function escapeHtml(str) {
        var el = document.createElement("div");
        el.textContent = str || "";
        return el.innerHTML;
    }

    function getActiveMonth() {
        var active = document.querySelector(monthSelectors + ".is-active");
        if (active) {
            return active.getAttribute("data-month") || "all";
        }
        return activeMonth;
    }

    function buildUrl(base, q, month) {
        var params = [];
        if (q) {
            params.push("q=" + encodeURIComponent(q));
        }
        if (month && month !== "all") {
            params.push("month=" + encodeURIComponent(month));
        }
        return base + (params.length ? "?" + params.join("&") : "");
    }

    function setMonthFilters(month) {
        activeMonth = month || "all";
        document.querySelectorAll(monthSelectors).forEach(function (btn) {
            var isActive = btn.getAttribute("data-month") === activeMonth;
            btn.classList.toggle("is-active", isActive);
            if (btn.getAttribute("role") === "tab") {
                btn.setAttribute("aria-selected", isActive ? "true" : "false");
            }
        });
    }

    function bindMonthFilters() {
        document.querySelectorAll(monthSelectors).forEach(function (btn) {
            btn.addEventListener("click", function () {
                setMonthFilters(btn.getAttribute("data-month") || "all");
                doSearch(false);
            });
        });
    }

    function bindQuickTags() {
        document.querySelectorAll(".ach-quick-tag[data-ach-quick]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var term = btn.getAttribute("data-ach-quick") || "";
                if (searchInput) {
                    searchInput.value = term;
                    searchInput.focus();
                }
                document.querySelectorAll(".ach-quick-tag").forEach(function (el) {
                    el.classList.toggle("is-active", el === btn);
                });
                doSearch(true);
            });
        });
    }

    function bindVideoButtons() {
        wrapper.querySelectorAll(".achievements-card__play").forEach(function (btn) {
            btn.addEventListener("click", function (e) {
                e.preventDefault();
                e.stopPropagation();
                openModal(
                    btn.getAttribute("data-video-type"),
                    btn.getAttribute("data-video-src"),
                    btn.getAttribute("data-video-title")
                );
            });
        });
    }

    function closeModal() {
        if (!modal) {
            return;
        }
        modal.hidden = true;
        document.body.style.overflow = "";
        if (player) {
            player.innerHTML = "";
        }
    }

    function openModal(type, src, title) {
        if (!modal || !player) {
            return;
        }
        player.innerHTML = "";
        if (modalTitle) {
            modalTitle.textContent = title || "";
        }
        if (type === "file") {
            var video = document.createElement("video");
            video.src = src;
            video.controls = true;
            video.playsInline = true;
            player.appendChild(video);
        } else {
            var iframe = document.createElement("iframe");
            iframe.src = src;
            iframe.title = title || "ویدیو";
            iframe.allow =
                "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
            iframe.allowFullscreen = true;
            player.appendChild(iframe);
        }
        modal.hidden = false;
        document.body.style.overflow = "hidden";
    }

    function scrollToBest(slug) {
        if (!slug) {
            return;
        }
        var card = wrapper.querySelector('[data-achievement-slug="' + slug + '"]');
        if (card) {
            card.classList.add("is-highlight");
            card.scrollIntoView({ behavior: "smooth", block: "center" });
            window.setTimeout(function () {
                card.classList.remove("is-highlight");
            }, 1400);
        }
    }

    function doSearch(scrollToBestMatch) {
        if (!searchUrl) {
            return;
        }
        var q = searchInput ? (searchInput.value || "").trim() : "";
        var month = getActiveMonth();
        if (q.length > 0 && q.length < 2) {
            return;
        }
        wrapper.classList.add("is-loading");
        fetch(buildUrl(searchUrl, q, month), { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                if (!data.ok || !data.html) {
                    return;
                }
                wrapper.innerHTML = data.html;
                bindVideoButtons();
                if (scrollToBestMatch && data.best_slug) {
                    scrollToBest(data.best_slug);
                }
            })
            .finally(function () {
                wrapper.classList.remove("is-loading");
            });
    }

    function hideSuggest() {
        if (suggestPanel) {
            suggestPanel.hidden = true;
            suggestPanel.innerHTML = "";
        }
    }

    function renderSuggest(items) {
        if (!suggestPanel) {
            return;
        }
        if (!items || !items.length) {
            hideSuggest();
            return;
        }
        suggestPanel.innerHTML = items
            .map(function (item, idx) {
                var label = item.person_name + " — " + (item.person_role || item.title);
                return (
                    '<button type="button" class="faq-page__suggest-item" role="option" data-index="' +
                    idx +
                    '" data-slug="' +
                    escapeHtml(item.slug) +
                    '" data-label="' +
                    escapeHtml(label) +
                    '">' +
                    '<span class="faq-page__suggest-q">' +
                    escapeHtml(label) +
                    "</span>" +
                    (item.month_label
                        ? '<span class="faq-page__suggest-cat">' + escapeHtml(item.month_label) + "</span>"
                        : "") +
                    (item.smart_match ? '<span class="faq-page__suggest-tag">پیشنهاد هوشمند</span>' : "") +
                    "</button>"
                );
            })
            .join("");
        suggestPanel.hidden = false;
        suggestPanel.querySelectorAll(".faq-page__suggest-item").forEach(function (el) {
            el.addEventListener("click", function () {
                if (searchInput) {
                    searchInput.value = this.getAttribute("data-label") || "";
                }
                hideSuggest();
                doSearch(true);
            });
        });
    }

    function doSuggest() {
        if (!suggestUrl) {
            return;
        }
        var q = searchInput ? (searchInput.value || "").trim() : "";
        fetch(buildUrl(suggestUrl, q, getActiveMonth()), { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                if (data.ok) {
                    renderSuggest(data.suggestions);
                }
            });
    }

    if (searchInput) {
        searchInput.addEventListener("input", function () {
            clearTimeout(suggestTimer);
            clearTimeout(searchTimer);
            var q = (searchInput.value || "").trim();
            document.querySelectorAll(".ach-quick-tag").forEach(function (el) {
                el.classList.remove("is-active");
            });
            if (q.length === 0) {
                hideSuggest();
                searchTimer = window.setTimeout(function () {
                    doSearch(false);
                }, 200);
                return;
            }
            if (q.length < 2) {
                hideSuggest();
                return;
            }
            suggestTimer = window.setTimeout(doSuggest, 150);
            searchTimer = window.setTimeout(function () {
                doSearch(false);
            }, 320);
        });

        searchInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                hideSuggest();
                doSearch(true);
            }
            if (e.key === "Escape") {
                hideSuggest();
            }
        });
    }

    bindMonthFilters();
    bindQuickTags();
    bindVideoButtons();

    if (modal) {
        modal.querySelectorAll("[data-modal-close]").forEach(function (el) {
            el.addEventListener("click", closeModal);
        });
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && !modal.hidden) {
                closeModal();
            }
        });
    }

    document.addEventListener("click", function (e) {
        if (!suggestPanel || suggestPanel.hidden) {
            return;
        }
        if (e.target.closest(".faq-page__search-field")) {
            return;
        }
        hideSuggest();
    });
})();
