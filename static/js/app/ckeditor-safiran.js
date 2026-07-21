/**
 * تنظیمات مشترک CKEditor — اندازه و چیدمان تصاویر
 */
(function () {
    "use strict";

    if (typeof CKEDITOR === "undefined") {
        return;
    }

    CKEDITOR.stylesSet.add("safiran", [
        {
            name: "تصویر — کوچک (۲۵۰px) وسط",
            element: "img",
            attributes: { class: "ck-img ck-img--xs ck-img--center" },
        },
        {
            name: "تصویر — متوسط (۴۰۰px) وسط",
            element: "img",
            attributes: { class: "ck-img ck-img--sm ck-img--center" },
        },
        {
            name: "تصویر — بزرگ (۶۰۰px) وسط",
            element: "img",
            attributes: { class: "ck-img ck-img--md ck-img--center" },
        },
        {
            name: "تصویر — عریض (۸۰۰px) وسط",
            element: "img",
            attributes: { class: "ck-img ck-img--lg ck-img--center" },
        },
        {
            name: "تصویر — تمام‌عرض",
            element: "img",
            attributes: { class: "ck-img ck-img--full ck-img--center" },
        },
        {
            name: "تصویر — چپ (شناور)",
            element: "img",
            attributes: { class: "ck-img ck-img--sm ck-img--float-start" },
        },
        {
            name: "تصویر — راست (شناور)",
            element: "img",
            attributes: { class: "ck-img ck-img--sm ck-img--float-end" },
        },
        {
            name: "تصویر — وسط (بدون شناور)",
            element: "img",
            attributes: { class: "ck-img ck-img--md ck-img--center" },
        },
    ]);

    if (window.__safiranCkEditorHooks) {
        return;
    }
    window.__safiranCkEditorHooks = true;

    CKEDITOR.on("instanceReady", function (evt) {
        var editor = evt.editor;

        editor.on("doubleclick", function (ev) {
            var element = ev.data.element;
            if (element && element.is("img")) {
                ev.data.dialog = "image";
            }
        });

        editor.on("insertElement", function (ev) {
            var el = ev.data;
            if (!el || !el.is || !el.is("img")) {
                return;
            }
            if (!el.hasClass("ck-img")) {
                el.addClass("ck-img ck-img--md ck-img--center");
            }
        });

        var editable = editor.editable();
        if (editable && editable.setAttribute) {
            editable.setAttribute("class", "ck-content cke_editable");
        }
    });
})();
