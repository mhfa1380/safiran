"""Curated top universities for countries where Wikipedia fetch returns sparse results."""
from __future__ import annotations

WORLD_CURATED_TOP: dict[str, list[dict]] = {
    "france": [
        {"name_en": "Sorbonne University", "qs_rank": 25},
        {"name_en": "Université Paris-Saclay", "qs_rank": 71},
        {"name_en": "École Polytechnique", "qs_rank": 38},
        {"name_en": "Sciences Po", "qs_rank": 319},
        {"name_en": "Université PSL", "qs_rank": 24},
        {"name_en": "Université Grenoble Alpes", "qs_rank": 334},
        {"name_en": "Aix-Marseille University", "qs_rank": 387},
        {"name_en": "University of Strasbourg", "qs_rank": 421},
        {"name_en": "Université de Montpellier", "qs_rank": 511},
        {"name_en": "Université de Bordeaux", "qs_rank": 465},
    ],
    "ireland": [
        {"name_en": "Trinity College Dublin", "qs_rank": 81},
        {"name_en": "University College Dublin", "qs_rank": 171},
        {"name_en": "University of Galway", "qs_rank": 273},
        {"name_en": "University College Cork", "qs_rank": 292},
        {"name_en": "Dublin City University", "qs_rank": 436},
        {"name_en": "University of Limerick", "qs_rank": 426},
    ],
    "denmark": [
        {"name_en": "University of Copenhagen", "qs_rank": 100},
        {"name_en": "Technical University of Denmark", "qs_rank": 104},
        {"name_en": "Aarhus University", "qs_rank": 143},
        {"name_en": "University of Southern Denmark", "qs_rank": 347},
    ],
    "portugal": [
        {"name_en": "University of Lisbon", "qs_rank": 266},
        {"name_en": "University of Porto", "qs_rank": 295},
        {"name_en": "NOVA University Lisbon", "qs_rank": 358},
        {"name_en": "University of Coimbra", "qs_rank": 431},
    ],
    "hungary": [
        {"name_en": "Eötvös Loránd University", "qs_rank": 564},
        {"name_en": "University of Szeged", "qs_rank": 601},
        {"name_en": "Budapest University of Technology and Economics", "qs_rank": 721},
    ],
    "thailand": [
        {"name_en": "Chulalongkorn University", "qs_rank": 211},
        {"name_en": "Mahidol University", "qs_rank": 382},
        {"name_en": "Chiang Mai University", "qs_rank": 571},
    ],
    "israel": [
        {"name_en": "Hebrew University of Jerusalem", "qs_rank": 215},
        {"name_en": "Tel Aviv University", "qs_rank": 220},
        {"name_en": "Technion – Israel Institute of Technology", "qs_rank": 392},
        {"name_en": "Ben-Gurion University of the Negev", "qs_rank": 471},
    ],
    "russia": [
        {"name_en": "Lomonosov Moscow State University", "qs_rank": 87},
        {"name_en": "Saint Petersburg State University", "qs_rank": 315},
        {"name_en": "Novosibirsk State University", "qs_rank": 442},
    ],
    "taiwan": [
        {"name_en": "National Taiwan University", "qs_rank": 68},
        {"name_en": "National Tsing Hua University", "qs_rank": 191},
        {"name_en": "National Cheng Kung University", "qs_rank": 228},
        {"name_en": "National Yang Ming Chiao Tung University", "qs_rank": 217},
    ],
    "south_korea": [
        {"name_en": "Seoul National University", "qs_rank": 31},
        {"name_en": "KAIST", "qs_rank": 53},
        {"name_en": "Yonsei University", "qs_rank": 76},
        {"name_en": "Korea University", "qs_rank": 79},
        {"name_en": "Pohang University of Science and Technology", "qs_rank": 98},
        {"name_en": "Sungkyunkwan University", "qs_rank": 145},
        {"name_en": "Hanyang University", "qs_rank": 164},
    ],
    "hong_kong": [
        {"name_en": "University of Hong Kong", "qs_rank": 17},
        {"name_en": "Chinese University of Hong Kong", "qs_rank": 36},
        {"name_en": "Hong Kong University of Science and Technology", "qs_rank": 47},
        {"name_en": "City University of Hong Kong", "qs_rank": 62},
        {"name_en": "Hong Kong Polytechnic University", "qs_rank": 65},
    ],
    "uae": [
        {"name_en": "United Arab Emirates University", "qs_rank": 290},
        {"name_en": "Khalifa University", "qs_rank": 202},
        {"name_en": "American University of Sharjah", "qs_rank": 364},
    ],
    "india": [
        {"name_en": "Indian Institute of Technology Bombay", "qs_rank": 149},
        {"name_en": "Indian Institute of Technology Delhi", "qs_rank": 150},
        {"name_en": "Indian Institute of Science", "qs_rank": 211},
        {"name_en": "Indian Institute of Technology Madras", "qs_rank": 285},
        {"name_en": "University of Delhi", "qs_rank": 407},
    ],
}
