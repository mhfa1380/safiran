/**
 * Searchable major combobox — evaluation form (DB-backed + smart fuzzy suggest API)
 */
(function (global) {
    "use strict";

    var MAX_RESULTS = 10;
    var SUGGEST_DEBOUNCE_MS = 120;

    function toEnDigits(s) {
        return String(s || "").replace(/[۰-۹]/g, function (c) {
            return String(c.charCodeAt(0) - 1728);
        });
    }

    function normalize(s) {
        return toEnDigits(s)
            .toLowerCase()
            .replace(/\u200c/g, "")
            .replace(/\s+/g, " ")
            .trim();
    }

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function MajorCombobox(root, options) {
        this.root = root;
        this.options = options || {};
        this.allItems = Array.isArray(options.items) ? options.items : [];
        this.suggestUrl = options.suggestUrl || "";
        this.required = !!options.required;
        this.input = root.querySelector(".major-combobox__field");
        this.panel = null;
        this.list = null;
        this.status = null;
        this.customBtn = null;
        this.activeIndex = -1;
        this.filtered = [];
        this.open = false;
        this._debounce = null;
        this._suggestAbort = null;
        this._loading = false;
        this._lastQuery = "";

        if (!this.input) return;
        this._build();
        this._bind();
        this._syncInvalid();
    }

    MajorCombobox.prototype._build = function () {
        var self = this;
        this.root.classList.add("major-combobox");

        var control = document.createElement("div");
        control.className = "major-combobox__control";

        var icon = document.createElement("span");
        icon.className = "major-combobox__icon";
        icon.setAttribute("aria-hidden", "true");
        icon.innerHTML =
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3-3"/></svg>';

        var actions = document.createElement("div");
        actions.className = "major-combobox__actions";

        var clearBtn = document.createElement("button");
        clearBtn.type = "button";
        clearBtn.className = "major-combobox__btn major-combobox__clear";
        clearBtn.setAttribute("aria-label", "پاک کردن");
        clearBtn.innerHTML = "×";
        clearBtn.hidden = !this.input.value;

        var toggleBtn = document.createElement("button");
        toggleBtn.type = "button";
        toggleBtn.className = "major-combobox__btn major-combobox__toggle";
        toggleBtn.setAttribute("aria-label", "باز کردن لیست");
        toggleBtn.innerHTML =
            '<span class="major-combobox__chevron" aria-hidden="true">▾</span>';

        actions.appendChild(clearBtn);
        actions.appendChild(toggleBtn);

        this.input.parentNode.insertBefore(control, this.input);
        control.appendChild(icon);
        control.appendChild(this.input);
        control.appendChild(actions);

        var panelId =
            "major-combobox-panel-" + (this.input.name || "field") + "-" + Math.random().toString(36).slice(2, 8);
        this.panel = document.createElement("div");
        this.panel.className = "major-combobox__panel";
        this.panel.id = panelId;
        this.panel.hidden = true;
        this.input.setAttribute("aria-controls", panelId);

        this.status = document.createElement("div");
        this.status.className = "major-combobox__status";

        this.list = document.createElement("ul");
        this.list.className = "major-combobox__list";
        this.list.setAttribute("role", "listbox");

        var footer = document.createElement("div");
        footer.className = "major-combobox__footer";
        this.customBtn = document.createElement("button");
        this.customBtn.type = "button";
        this.customBtn.className = "major-combobox__custom";
        footer.appendChild(this.customBtn);

        this.panel.appendChild(this.status);
        this.panel.appendChild(this.list);
        this.panel.appendChild(footer);
        this.root.appendChild(this.panel);

        this.clearBtn = clearBtn;
        this.toggleBtn = toggleBtn;

        clearBtn.addEventListener("click", function (e) {
            e.preventDefault();
            self.input.value = "";
            self.input.focus();
            self._applyFilter("");
            self.openPanel();
            clearBtn.hidden = true;
            self.input.classList.remove("is-invalid");
            self.root.classList.remove("is-invalid");
        });

        toggleBtn.addEventListener("click", function (e) {
            e.preventDefault();
            if (self.open) self.closePanel();
            else {
                self.input.focus();
                self.openPanel();
                self._applyFilter(self.input.value);
            }
        });
    };

    MajorCombobox.prototype._bind = function () {
        var self = this;

        this.input.addEventListener("input", function () {
            clearTimeout(self._debounce);
            self._debounce = setTimeout(function () {
                self.clearBtn.hidden = !self.input.value;
                self._applyFilter(self.input.value);
                self.openPanel();
            }, SUGGEST_DEBOUNCE_MS);
        });

        this.input.addEventListener("focus", function () {
            self._applyFilter(self.input.value);
            self.openPanel();
        });

        this.input.addEventListener("keydown", function (e) {
            if (e.key === "ArrowDown") {
                e.preventDefault();
                self.openPanel();
                self._moveActive(1);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                self._moveActive(-1);
            } else if (e.key === "Enter") {
                if (self.open && self.activeIndex >= 0) {
                    e.preventDefault();
                    self._selectIndex(self.activeIndex);
                } else if (self.open) {
                    e.preventDefault();
                    self._useCustom();
                }
            } else if (e.key === "Escape") {
                self.closePanel();
            }
        });

        this.customBtn.addEventListener("click", function () {
            self._useCustom();
        });

        document.addEventListener("click", function (e) {
            if (!self.root.contains(e.target)) self.closePanel();
        });
    };

    MajorCombobox.prototype._selectedCountries = function () {
        var form = this.root.closest("form");
        if (!form) return [];
        var checked = form.querySelectorAll('input[name="desired_countries"]:checked');
        var codes = [];
        checked.forEach(function (el) {
            if (el.value && el.value !== "undecided" && el.value !== "other") codes.push(el.value);
        });
        return codes;
    };

    MajorCombobox.prototype._buildSuggestUrl = function (query) {
        if (!this.suggestUrl) return "";
        var url = this.suggestUrl;
        var sep = url.indexOf("?") >= 0 ? "&" : "?";
        var params = ["q=" + encodeURIComponent(query || "")];
        var countries = this._selectedCountries();
        if (countries.length) {
            params.push("countries=" + encodeURIComponent(countries.join(",")));
        }
        return url + sep + params.join("&");
    };

    MajorCombobox.prototype._scoreItemLocal = function (item, qNorm, countries) {
        var titleNorm = normalize(item.title);
        var score = 0;
        if (!qNorm) score += 1;
        else if (titleNorm === qNorm) score += 100;
        else if (titleNorm.indexOf(qNorm) === 0) score += 60;
        else if (titleNorm.indexOf(qNorm) >= 0) score += 35;
        else {
            var parts = qNorm.split(" ");
            var hits = 0;
            parts.forEach(function (p) {
                if (p && titleNorm.indexOf(p) >= 0) hits += 1;
            });
            if (hits) score += hits * 12;
        }
        if (countries.length && item.countries && item.countries.length) {
            countries.forEach(function (c) {
                if (item.countries.indexOf(c) >= 0) score += 8;
            });
        }
        return score;
    };

    MajorCombobox.prototype._filterLocal = function (query) {
        var qNorm = normalize(query);
        var countries = this._selectedCountries();
        var scored = [];

        this.allItems.forEach(function (item) {
            var score = this._scoreItemLocal(item, qNorm, countries);
            if (qNorm && score <= 0) return;
            scored.push({ item: item, score: score });
        }, this);

        scored.sort(function (a, b) {
            if (b.score !== a.score) return b.score - a.score;
            return a.item.title.localeCompare(b.item.title, "fa");
        });

        this.filtered = scored.slice(0, MAX_RESULTS).map(function (s) {
            return s.item;
        });
        this.activeIndex = this.filtered.length ? 0 : -1;
        this._render(qNorm, false);
    };

    MajorCombobox.prototype._fetchSuggestions = function (query) {
        var self = this;
        var qNorm = normalize(query);

        if (!this.suggestUrl) {
            this._filterLocal(query);
            return;
        }

        if (this._suggestAbort) {
            this._suggestAbort.abort();
            this._suggestAbort = null;
        }

        this._loading = true;
        this._lastQuery = query;
        this._render(qNorm, true);

        this._suggestAbort =
            typeof AbortController !== "undefined" ? new AbortController() : null;
        var fetchOpts = {
            headers: { "X-Requested-With": "XMLHttpRequest" },
        };
        if (this._suggestAbort) fetchOpts.signal = this._suggestAbort.signal;

        fetch(this._buildSuggestUrl(query), fetchOpts)
            .then(function (res) {
                return res.json();
            })
            .then(function (data) {
                if (normalize(self.input.value) !== normalize(self._lastQuery)) return;
                if (!data || !data.ok || !Array.isArray(data.suggestions)) {
                    self._filterLocal(query);
                    return;
                }
                self.filtered = data.suggestions.slice(0, MAX_RESULTS);
                self.activeIndex = self.filtered.length ? 0 : -1;
                self._loading = false;
                self._render(qNorm, false, data.smart);
            })
            .catch(function (err) {
                if (err && err.name === "AbortError") return;
                if (normalize(self.input.value) !== normalize(self._lastQuery)) return;
                self._loading = false;
                self._filterLocal(query);
            });
    };

    MajorCombobox.prototype._applyFilter = function (query) {
        this._loading = false;
        this._fetchSuggestions(query);
    };

    MajorCombobox.prototype._render = function (qNorm, loading, smart) {
        var self = this;
        this.list.innerHTML = "";

        if (loading) {
            this.status.textContent = "در حال جستجوی هوشمند…";
        } else if (!this.filtered.length) {
            this.status.textContent = qNorm
                ? "رشته‌ای در لیست پیدا نشد — می‌توانید همان متن را ثبت کنید."
                : "نام رشته را تایپ کنید یا از لیست انتخاب کنید.";
        } else {
            var hint = this.filtered.length + " پیشنهاد";
            if (qNorm) hint += " برای «" + this.input.value.trim() + "»";
            if (smart) hint += " · جستجوی هوشمند";
            this.status.textContent = hint;
        }

        this.filtered.forEach(function (item, idx) {
            var li = document.createElement("li");
            var btn = document.createElement("button");
            btn.type = "button";
            btn.className =
                "major-combobox__option" +
                (idx === self.activeIndex ? " is-active" : "") +
                (item.smart_match ? " is-smart" : "");
            btn.setAttribute("role", "option");
            btn.setAttribute("aria-selected", idx === self.activeIndex ? "true" : "false");
            var meta =
                item.country_labels && item.country_labels.length
                    ? item.country_labels.join(" · ")
                    : "";
            btn.innerHTML =
                '<span class="major-combobox__option-title">' +
                escapeHtml(item.title) +
                "</span>" +
                (meta
                    ? '<span class="major-combobox__option-meta">' + escapeHtml(meta) + "</span>"
                    : "") +
                (item.smart_match
                    ? '<span class="major-combobox__option-tag">پیشنهاد هوشمند</span>'
                    : "");
            btn.addEventListener("click", function () {
                self._selectItem(item.title);
            });
            li.appendChild(btn);
            self.list.appendChild(li);
        });

        var typed = this.input.value.trim();
        if (typed) {
            this.customBtn.innerHTML =
                'ثبت دستی: <strong>«' + escapeHtml(typed) + "»</strong>";
            this.customBtn.hidden = false;
            var exact = this.allItems.some(function (it) {
                return normalize(it.title) === normalize(typed);
            });
            if (exact) this.customBtn.hidden = true;
        } else {
            this.customBtn.innerHTML = "نام رشته را تایپ کنید";
            this.customBtn.hidden = !this.required;
        }
    };

    MajorCombobox.prototype._moveActive = function (delta) {
        var total = this.filtered.length + (this.customBtn.hidden ? 0 : 1);
        if (!total) return;
        this.activeIndex += delta;
        if (this.activeIndex >= this.filtered.length) this.activeIndex = this.filtered.length;
        if (this.activeIndex < -1) this.activeIndex = -1;
        this._highlightActive();
    };

    MajorCombobox.prototype._highlightActive = function () {
        var buttons = this.list.querySelectorAll(".major-combobox__option");
        buttons.forEach(function (btn, i) {
            btn.classList.toggle("is-active", i === this.activeIndex);
            btn.setAttribute("aria-selected", i === this.activeIndex ? "true" : "false");
        }, this);
        this.customBtn.classList.toggle("is-active", this.activeIndex === this.filtered.length);
    };

    MajorCombobox.prototype._selectIndex = function (idx) {
        if (idx >= 0 && idx < this.filtered.length) {
            this._selectItem(this.filtered[idx].title);
        } else {
            this._useCustom();
        }
    };

    MajorCombobox.prototype._selectItem = function (title) {
        this.input.value = title;
        this.clearBtn.hidden = false;
        this.input.classList.remove("is-invalid");
        this.root.classList.remove("is-invalid");
        this.closePanel();
        this.input.dispatchEvent(new Event("change", { bubbles: true }));
    };

    MajorCombobox.prototype._useCustom = function () {
        var v = this.input.value.trim();
        if (!v && this.required) return;
        this.clearBtn.hidden = !v;
        this.closePanel();
        this.input.dispatchEvent(new Event("change", { bubbles: true }));
    };

    MajorCombobox.prototype.openPanel = function () {
        this.open = true;
        this.root.classList.add("is-open");
        this.panel.hidden = false;
        this.input.setAttribute("aria-expanded", "true");
    };

    MajorCombobox.prototype.closePanel = function () {
        this.open = false;
        this.root.classList.remove("is-open");
        this.panel.hidden = true;
        this.input.setAttribute("aria-expanded", "false");
        this.activeIndex = -1;
        if (this._suggestAbort) {
            this._suggestAbort.abort();
            this._suggestAbort = null;
        }
    };

    MajorCombobox.prototype._syncInvalid = function () {
        var self = this;
        this.input.addEventListener("invalid", function () {
            self.root.classList.add("is-invalid");
        });
    };

    function initMajorComboboxes(container, config) {
        if (!container) return [];
        var items = (config && config.items) || [];
        var suggestUrl = (config && config.suggestUrl) || "";
        var instances = [];
        container.querySelectorAll("[data-major-combobox]").forEach(function (el) {
            var required = el.getAttribute("data-required") === "true";
            instances.push(
                new MajorCombobox(el, {
                    items: items,
                    suggestUrl: suggestUrl,
                    required: required,
                })
            );
        });
        return instances;
    }

    global.MajorCombobox = MajorCombobox;
    global.initMajorComboboxes = initMajorComboboxes;
})(typeof window !== "undefined" ? window : this);
