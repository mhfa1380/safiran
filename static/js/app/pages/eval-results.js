/**
 * بازخورد لایک/دیسلایک بخش‌های گزارش ارزیابی
 */
(function () {
    'use strict';

    function readConfig() {
        var el = document.getElementById('eval-feedback-config');
        if (!el || !el.textContent) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            return null;
        }
    }

    function getCsrfToken() {
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function voteKey(section, itemKey) {
        return itemKey ? section + ':' + itemKey : section;
    }

    function setHintState(hint, vote) {
        var up = hint.querySelector('.evalr-hint__btn--up');
        var down = hint.querySelector('.evalr-hint__btn--down');
        var thanks = hint.querySelector('.evalr-hint__thanks');
        var label = hint.querySelector('.evalr-hint__label');
        if (!up || !down) return;

        up.classList.toggle('is-active', vote === 1);
        down.classList.toggle('is-active', vote === -1);
        up.setAttribute('aria-pressed', vote === 1 ? 'true' : 'false');
        down.setAttribute('aria-pressed', vote === -1 ? 'true' : 'false');
        hint.classList.toggle('is-voted', vote === 1 || vote === -1);

        if (thanks) {
            thanks.hidden = !(vote === 1 || vote === -1);
        }
        if (label && (vote === 1 || vote === -1)) {
            label.textContent = vote === 1 ? 'ممنون از بازخورد مثبت' : 'بازخورد شما ثبت شد';
        }
    }

    function init() {
        var config = readConfig();
        if (!config || !config.url) return;

        var votes = config.votes || {};
        var hints = document.querySelectorAll('[data-eval-hint]');

        hints.forEach(function (hint) {
            var section = hint.getAttribute('data-section') || '';
            var itemKey = hint.getAttribute('data-item-key') || '';
            var key = voteKey(section, itemKey);
            if (Object.prototype.hasOwnProperty.call(votes, key)) {
                setHintState(hint, votes[key]);
            }

            hint.addEventListener('click', function (event) {
                var btn = event.target.closest('[data-vote]');
                if (!btn || btn.disabled) return;
                event.preventDefault();
                event.stopPropagation();

                var vote = parseInt(btn.getAttribute('data-vote'), 10);
                if (vote !== 1 && vote !== -1) return;

                var buttons = hint.querySelectorAll('[data-vote]');
                buttons.forEach(function (b) { b.disabled = true; });

                fetch(config.url, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({
                        section: section,
                        item_key: itemKey,
                        vote: vote,
                    }),
                })
                    .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
                    .then(function (result) {
                        if (!result.ok || !result.data.ok) {
                            throw new Error((result.data && result.data.error) || 'failed');
                        }
                        votes[key] = result.data.vote;
                        setHintState(hint, result.data.vote);
                    })
                    .catch(function () {
                        var errLabel = hint.querySelector('.evalr-hint__label');
                        if (errLabel) errLabel.textContent = 'خطا در ثبت — دوباره تلاش کنید';
                    })
                    .finally(function () {
                        buttons.forEach(function (b) { b.disabled = false; });
                    });
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
