"""Download flag SVGs for world countries into static/img/flags/."""
from __future__ import annotations

import urllib.request
from pathlib import Path

FLAGS = {
    "gb": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/gb.svg",
    "us": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/us.svg",
    "au": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/au.svg",
    "fr": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/fr.svg",
    "nl": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/nl.svg",
    "ch": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/ch.svg",
    "jp": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/jp.svg",
    "kr": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/kr.svg",
    "sg": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/sg.svg",
    "hk": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/hk.svg",
    "ie": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/ie.svg",
    "se": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/se.svg",
    "be": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/be.svg",
    "at": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/at.svg",
    "nz": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/nz.svg",
    "dk": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/dk.svg",
    "fi": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/fi.svg",
    "no": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/no.svg",
    "pt": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/pt.svg",
    "pl": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/pl.svg",
    "cz": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/cz.svg",
    "hu": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/hu.svg",
    "gr": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/gr.svg",
    "tr": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/tr.svg",
    "my": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/my.svg",
    "ae": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/ae.svg",
    "sa": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/sa.svg",
    "qa": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/qa.svg",
    "in": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/in.svg",
    "th": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/th.svg",
    "il": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/il.svg",
    "br": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/br.svg",
    "mx": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/mx.svg",
    "ar": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/ar.svg",
    "cl": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/cl.svg",
    "za": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/za.svg",
    "eg": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/eg.svg",
    "ru": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/ru.svg",
    "tw": "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/tw.svg",
}

OUT = Path(__file__).resolve().parent.parent / "static" / "img" / "flags"
UA = "SafiranFlagDownloader/1.0"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for code, url in FLAGS.items():
        dest = OUT / f"{code}.svg"
        if dest.is_file() and dest.stat().st_size > 100:
            continue
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.write_bytes(resp.read())
        print("saved", dest.name)


if __name__ == "__main__":
    main()
