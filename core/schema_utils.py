"""ISO 3166-1 alpha-2 برای schema.org و سئو ساختاریافته."""

from __future__ import annotations

COUNTRY_ISO_ALPHA2: dict[str, str] = {
    "canada": "CA",
    "china": "CN",
    "spain": "ES",
    "uk": "GB",
    "usa": "US",
    "australia": "AU",
    "germany": "DE",
    "italy": "IT",
    "france": "FR",
    "netherlands": "NL",
    "switzerland": "CH",
    "japan": "JP",
    "south_korea": "KR",
    "singapore": "SG",
    "hong_kong": "HK",
    "ireland": "IE",
    "sweden": "SE",
    "belgium": "BE",
    "austria": "AT",
    "new_zealand": "NZ",
    "denmark": "DK",
    "finland": "FI",
    "norway": "NO",
    "portugal": "PT",
    "poland": "PL",
    "czech": "CZ",
    "hungary": "HU",
    "greece": "GR",
    "turkey": "TR",
    "malaysia": "MY",
    "uae": "AE",
    "saudi_arabia": "SA",
    "qatar": "QA",
    "india": "IN",
    "thailand": "TH",
    "israel": "IL",
    "brazil": "BR",
    "mexico": "MX",
    "argentina": "AR",
    "chile": "CL",
    "south_africa": "ZA",
    "egypt": "EG",
    "russia": "RU",
    "taiwan": "TW",
}


def country_iso_alpha2(code: str) -> str:
    return COUNTRY_ISO_ALPHA2.get((code or "").strip().lower(), "")
