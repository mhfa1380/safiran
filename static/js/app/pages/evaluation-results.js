(function () {
    "use strict";

    var shareBtn = document.getElementById("evalrShareBtn");
    var printBtn = document.getElementById("evalrPrintBtn");
    var toast = document.getElementById("evalrShareToast");
    var shareUrl =
        (shareBtn && shareBtn.getAttribute("data-share-url")) ||
        (window.PAGE_CONFIG && window.PAGE_CONFIG.evalShareUrl) ||
        window.location.href;

    function showToast() {
        if (!toast) return;
        toast.hidden = false;
        setTimeout(function () {
            toast.hidden = true;
        }, 2500);
    }

    if (shareBtn) {
        shareBtn.addEventListener("click", function () {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(shareUrl).then(showToast).catch(fallbackCopy);
            } else {
                fallbackCopy();
            }
        });
    }

    function fallbackCopy() {
        var input = document.createElement("input");
        input.value = shareUrl;
        document.body.appendChild(input);
        input.select();
        try {
            document.execCommand("copy");
            showToast();
        } catch (e) {
            prompt("لینک را کپی کنید:", shareUrl);
        }
        document.body.removeChild(input);
    }

    if (printBtn) {
        printBtn.addEventListener("click", function () {
            window.print();
        });
    }
})();
