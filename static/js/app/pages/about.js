(function () {
    "use strict";

    var tabs = document.querySelectorAll(".about-team__tab[data-team-group], .faq-page__filter[data-team-group]");
    var panels = document.querySelectorAll(".about-team__panel[data-team-panel]");
    var navLinks = document.querySelectorAll(".about-page .faq-page__nav-link[href^='#']");

    function activateTeam(groupCode) {
        if (!tabs.length) return;

        tabs.forEach(function (tab) {
            var isActive = tab.getAttribute("data-team-group") === groupCode;
            tab.classList.toggle("is-active", isActive);
            tab.setAttribute("aria-selected", isActive ? "true" : "false");
        });

        panels.forEach(function (panel) {
            var isActive = panel.getAttribute("data-team-panel") === groupCode;
            panel.classList.toggle("is-active", isActive);
            if (isActive) {
                panel.removeAttribute("hidden");
            } else {
                panel.setAttribute("hidden", "");
            }
        });
    }

    tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
            activateTeam(tab.getAttribute("data-team-group"));
        });
    });

    function setActiveNav(id) {
        if (!id || !navLinks.length) return;
        navLinks.forEach(function (link) {
            var href = link.getAttribute("href") || "";
            link.classList.toggle("is-active", href === "#" + id);
        });
    }

    if (navLinks.length && "IntersectionObserver" in window) {
        var sections = [];
        navLinks.forEach(function (link) {
            var id = (link.getAttribute("href") || "").replace("#", "");
            var el = document.getElementById(id);
            if (el) sections.push({ id: id, el: el });
        });

        var observer = new IntersectionObserver(
            function (entries) {
                var visible = entries
                    .filter(function (e) { return e.isIntersecting; })
                    .sort(function (a, b) { return b.intersectionRatio - a.intersectionRatio; });
                if (visible[0]) {
                    setActiveNav(visible[0].target.id);
                }
            },
            { rootMargin: "-30% 0px -55% 0px", threshold: [0, 0.2, 0.5] }
        );

        sections.forEach(function (s) { observer.observe(s.el); });
    }

    navLinks.forEach(function (link) {
        link.addEventListener("click", function (e) {
            var id = (this.getAttribute("href") || "").replace("#", "");
            var target = document.getElementById(id);
            if (!target) return;
            e.preventDefault();
            target.scrollIntoView({ behavior: "smooth", block: "start" });
            setActiveNav(id);
        });
    });
})();
