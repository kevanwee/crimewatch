"""Shared location and rule catalogs for CrimeWatch."""

from __future__ import annotations

SINGAPORE_LOCATION_COORDS = {
    "Admiralty": (1.4406, 103.8010),
    "Ang Mo Kio": (1.3691, 103.8454),
    "Bedok": (1.3236, 103.9273),
    "Bishan": (1.3526, 103.8352),
    "Boon Lay": (1.3386, 103.7057),
    "Bukit Batok": (1.3590, 103.7637),
    "Bukit Merah": (1.2819, 103.8239),
    "Bukit Panjang": (1.3774, 103.7719),
    "Bukit Timah": (1.3294, 103.8021),
    "Changi": (1.3644, 103.9915),
    "Choa Chu Kang": (1.3840, 103.7470),
    "Chinatown": (1.2808, 103.8442),
    "Clementi": (1.3162, 103.7649),
    "Downtown Core": (1.2867, 103.8538),
    "Geylang": (1.3201, 103.8918),
    "Hougang": (1.3612, 103.8863),
    "Jurong": (1.3329, 103.7436),
    "Jurong East": (1.3331, 103.7430),
    "Jurong West": (1.3404, 103.7070),
    "Kallang": (1.3100, 103.8714),
    "Little India": (1.3060, 103.8495),
    "Mandai": (1.4069, 103.7575),
    "Marina Bay": (1.2815, 103.8636),
    "Newton": (1.3126, 103.8391),
    "Novena": (1.3203, 103.8438),
    "Orchard": (1.3036, 103.8318),
    "Pasir Ris": (1.3721, 103.9474),
    "Paya Lebar": (1.3181, 103.8929),
    "Punggol": (1.3984, 103.9072),
    "Queenstown": (1.2942, 103.7861),
    "Rochor": (1.3039, 103.8520),
    "Sembawang": (1.4491, 103.8185),
    "Sengkang": (1.3868, 103.8914),
    "Sentosa": (1.2494, 103.8303),
    "Serangoon": (1.3554, 103.8679),
    "Tampines": (1.3496, 103.9568),
    "Toa Payoh": (1.3340, 103.8471),
    "Woodlands": (1.4382, 103.7891),
    "Yishun": (1.4304, 103.8354),
}

# Additional text forms mapped to canonical location keys above.
LOCATION_ALIASES = {
    "amk": "Ang Mo Kio",
    "bukit merah estate": "Bukit Merah",
    "cbd": "Downtown Core",
    "central business district": "Downtown Core",
    "city area": "Downtown Core",
    "city hall": "Downtown Core",
    "joo chiat": "Geylang",
    "jurong east": "Jurong East",
    "jurong west": "Jurong West",
    "tekka": "Little India",
}

# If these are near a location mention, the mention is likely not the incident location.
INSTITUTION_TERMS = {
    "academy",
    "camp",
    "checkpoint",
    "correctional",
    "court",
    "detention",
    "hospital",
    "imprisonment",
    "institution",
    "jail",
    "prison",
    "remand",
}

LEGAL_PROCESS_TERMS = {
    "appeal",
    "convicted",
    "hearing",
    "judge",
    "judgment",
    "mitigation",
    "pleaded guilty",
    "prosecution",
    "sentence",
    "sentenced",
    "trial",
}

RESIDENTIAL_TERMS = {
    "address",
    "flat",
    "home",
    "lived",
    "resided",
    "stayed",
}

# Strong evidence that a location mention is the scene of offence activity.
INCIDENT_TERMS = {
    "abduct",
    "abuse",
    "assault",
    "attack",
    "burglar",
    "cheat",
    "fight",
    "fraud",
    "harass",
    "kidnap",
    "murder",
    "offence",
    "offense",
    "rape",
    "rioting",
    "rob",
    "scam",
    "stab",
    "theft",
    "traffic",
    "traffick",
    "violence",
}

LOCATION_SPECIFIC_EXCLUSIONS = {
    "Changi": {
        "changi prison",
        "changi prison complex",
        "changi general hospital",
        "changi women's prison",
    },
}
