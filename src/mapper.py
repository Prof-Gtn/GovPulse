"""
GovPulse — Government Entity Mapper
Matches detected entities to Namibian government institutions.
"""

import json
import os


GOVERNMENT_TAXONOMY = {
    "Office of the President": ["Office of the President", "Presidency", "State House"],
    "Office of the Prime Minister": ["Office of the Prime Minister", "OPM"],
    "Office of the Vice President": ["Office of the Vice President", "OVP"],

    "Ministry of Agriculture, Fisheries, Water and Land Reform": [
        "Ministry of Agriculture, Fisheries, Water and Land Reform",
        "Ministry of Agriculture, Water and Land Reform",
        "Ministry of Agriculture", "MAWLR", "Agribank",
        "Meat Board of Namibia", "Namibian Agronomic Board",
        "Directorate of Veterinary Services", "NamWater",
        "Namibia Water Corporation"
    ],
    "Ministry of Defence and Veterans Affairs": [
        "Ministry of Defence and Veterans Affairs", "MODVA",
        "Ministry of Defence", "Namibian Defence Force", "NDF"
    ],
    "Ministry of Education, Innovation, Youth, Sports, Arts and Culture": [
        "Ministry of Education, Innovation, Youth, Sports, Arts and Culture",
        "Ministry of Education, Arts and Culture", "Ministry of Education",
        "Ministry of Higher Education, Technology and Innovation",
        "National Youth Service", "NSFAF",
        "University of Namibia", "UNAM",
        "Namibia University of Science and Technology", "NUST",
        "Namibian College of Open Learning", "NAMCOL"
    ],
    "Ministry of Environment, Forestry and Tourism": [
        "Ministry of Environment, Forestry and Tourism",
        "Ministry of Environment and Tourism", "MEFT",
        "Namibia Wildlife Resorts", "NWR", "Namibia Tourism Board"
    ],
    "Ministry of Finance": [
        "Ministry of Finance", "Namibia Revenue Agency", "NamRA",
        "Bank of Namibia", "Development Bank of Namibia",
        "Government Institutions Pensions Fund", "GIPF"
    ],
    "Ministry of Gender Equality and Child Welfare": [
        "Ministry of Gender Equality and Child Welfare",
        "Ministry of Gender Equality, Poverty Eradication and Social Welfare"
    ],
    "Ministry of Health and Social Services": [
        "Ministry of Health and Social Services", "Ministry of Health",
        "MoHSS", "Social Security Commission"
    ],
    "Ministry of Home Affairs, Immigration, Safety and Security": [
        "Ministry of Home Affairs, Immigration, Safety and Security",
        "Ministry of Home Affairs", "Namibian Police Force", "NamPol",
        "Namibian Correctional Service"
    ],
    "Ministry of Industrialisation and Trade": [
        "Ministry of Industrialisation and Trade",
        "Ministry of Trade and Industry", "NIPDB",
        "Namibian Standards Institution", "BIPA"
    ],
    # NOTE: MTC, NBC, NAMPA removed — they were causing false matches
    "Ministry of Information and Communication Technology": [
        "Ministry of Information and Communication Technology", "MICT",
        "Communications Regulatory Authority of Namibia", "CRAN",
        "Telecom Namibia", "Namibia Post", "NamPost"
    ],
    "Ministry of International Relations and Trade": [
        "Ministry of International Relations and Trade",
        "Ministry of International Relations and Cooperation", "MIRCO"
    ],
    "Ministry of Justice and Labour Relations": [
        "Ministry of Justice and Labour Relations", "Ministry of Justice",
        "Ministry of Labour, Industrial Relations and Employment Creation",
        "Office of the Judiciary"
    ],
    "Ministry of Mines and Energy": [
        "Ministry of Mines and Energy", "Ministry of Mines",
        "Epangelo Mining Company", "NAMDIA", "NAMCOR",
        "NamPower", "Electricity Control Board"
    ],
    "Ministry of Urban and Rural Development": [
        "Ministry of Urban and Rural Development",
        "City of Windhoek", "Municipality of Windhoek",
        "National Housing Enterprise", "NHE"
    ],
    "Ministry of Works and Transport": [
        "Ministry of Works and Transport", "Ministry of Works",
        "Roads Authority", "TransNamib", "Namibia Airports Company",
        "Namibian Ports Authority", "Namport"
    ],

    "Parliament of Namibia": [
        "Parliament of Namibia", "National Assembly", "National Council"
    ],
    "Anti-Corruption Commission": ["Anti-Corruption Commission"],
    "Electoral Commission of Namibia": ["Electoral Commission of Namibia"],
    "Office of the Auditor-General": ["Office of the Auditor-General", "Auditor-General"],
    "National Planning Commission": ["National Planning Commission"],

    "Zambezi Regional Council": ["Zambezi Regional Council", "Zambezi Region"],
    "Erongo Regional Council": ["Erongo Regional Council", "Erongo Region"],
    "Hardap Regional Council": ["Hardap Regional Council", "Hardap Region"],
    "Karas Regional Council": ["Karas Regional Council", "Karas Region"],
    "Khomas Regional Council": ["Khomas Regional Council", "Khomas Region"],
    "Kunene Regional Council": ["Kunene Regional Council", "Kunene Region"],
    "Ohangwena Regional Council": ["Ohangwena Regional Council", "Ohangwena Region"],
    "Kavango East Regional Council": ["Kavango East Regional Council", "Kavango East Region"],
    "Kavango West Regional Council": ["Kavango West Regional Council", "Kavango West Region"],
    "Omaheke Regional Council": ["Omaheke Regional Council", "Omaheke Region"],
    "Omusati Regional Council": ["Omusati Regional Council", "Omusati Region"],
    "Oshana Regional Council": ["Oshana Regional Council", "Oshana Region"],
    "Oshikoto Regional Council": ["Oshikoto Regional Council", "Oshikoto Region"],
    "Otjozondjupa Regional Council": ["Otjozondjupa Regional Council", "Otjozondjupa Region"],

    "Other State-Owned Enterprises": [
        "Meatco", "NIDA", "AMTA", "NAMFISA", "NIPAM",
        "Namibia Statistics Agency", "Environmental Investment Fund", "EIF",
        "Mobile Telecommunications Limited", "MTC",
        "Namibian Broadcasting Corporation", "NBC",
        "Namibia Press Agency", "NAMPA",
        "New Era Publication Corporation"
    ],
}


def match_entity_to_oma(entity_text, taxonomy):
    """Exact match only."""
    entity_lower = entity_text.lower().strip()

    for oma_name, aliases in taxonomy.items():
        for alias in aliases:
            if entity_lower == alias.lower().strip():
                return oma_name

    return None


def map_story(story, taxonomy):
    """Add O/M/A field to a story based on detected entities."""
    matched = []

    # ---------- STEP 1: Detect crime indicators FIRST ----------
    body_lower = (
        (story.get("body", "") or "") + " " +
        (story.get("headline", "") or "")
    ).lower()

    crime_keywords = [
        "arrested", "police", "nampol", "murder", "homicide",
        "suspect", "crime", "convicted", "sentenced",
        "robbery", "corruption", "fraud", "court case",
        "high court", "magistrate", "prosecutor"
    ]
    is_crime_story = any(kw in body_lower for kw in crime_keywords)

    # ---------- STEP 2: Detected organizations (exact match) ----------
    for org in story.get("entities", {}).get("organizations", []):
        oma = match_entity_to_oma(org, taxonomy)
        if oma and oma not in matched:
            matched.append(oma)

    # ---------- STEP 3: Detected people (exact match) ----------
    if not matched:
        for person in story.get("entities", {}).get("people", []):
            oma = match_entity_to_oma(person, taxonomy)
            if oma and oma not in matched:
                matched.append(oma)

    # ---------- STEP 4: If it's a crime story, tag Home Affairs ----------
    # If the only matches are weak (SOEs, regional councils),
    # clear them and use Home Affairs instead.
    if is_crime_story:
        strong_matches = [
            m for m in matched
            if m != "Other State-Owned Enterprises"
            and "Regional Council" not in m
        ]

        if not strong_matches:
            matched = [
                "Ministry of Home Affairs, Immigration, Safety and Security"
            ]

    # ---------- STEP 5: Body scan for full official ministry names ----------
    if not matched:
        high_confidence_phrases = {
            "Ministry of Agriculture, Fisheries, Water and Land Reform":
                "ministry of agriculture",
            "Ministry of Health and Social Services":
                "ministry of health",
            "Ministry of Education, Innovation, Youth, Sports, Arts and Culture":
                "ministry of education",
            "Ministry of Urban and Rural Development":
                "ministry of urban and rural development",
            "Ministry of Works and Transport":
                "ministry of works and transport",
            "Ministry of Finance":
                "ministry of finance",
            "Ministry of Home Affairs, Immigration, Safety and Security":
                "ministry of home affairs",
            "Ministry of International Relations and Trade":
                "ministry of international relations",
            "Ministry of Justice and Labour Relations":
                "ministry of justice",
            "Ministry of Mines and Energy":
                "ministry of mines and energy",
            "Ministry of Industrialisation and Trade":
                "ministry of industrialisation",
            "Ministry of Environment, Forestry and Tourism":
                "ministry of environment",
            "Ministry of Information and Communication Technology":
                "ministry of information and communication",
            "Parliament of Namibia":
                "parliament of namibia",
        }

        for oma_name, phrase in high_confidence_phrases.items():
            if phrase in body_lower:
                matched.append(oma_name)

    story["oma"] = matched if matched else ["Unmapped"]
    return story


def map_all(input_file="data/processed/analyzed.json",
            output_file="data/processed/mapped.json"):
    print(f"Reading {input_file}...")
    with open(input_file, "r", encoding="utf-8-sig") as f:
        stories = json.load(f)

    print(f"Mapping {len(stories)} stories to government entities...\n")

    mapped = []
    for i, story in enumerate(stories, 1):
        mapped.append(map_story(story, GOVERNMENT_TAXONOMY))
        print(f"  [{i}/{len(stories)}] {story['headline'][:50]}... → {mapped[-1]['oma']}")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8-sig") as f:
        json.dump(mapped, f, indent=2, ensure_ascii=False)

    mapped_count = sum(1 for s in mapped if s["oma"] != ["Unmapped"])
    unmapped_count = len(mapped) - mapped_count

    print(f"\n[OK] Saved {len(mapped)} mapped stories → {output_file}")
    print(f"\nMapping results:")
    print(f"  Mapped:   {mapped_count}")
    print(f"  Unmapped: {unmapped_count}")


if __name__ == "__main__":
    map_all()