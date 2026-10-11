"""
GovPulse — Government Entity Mapper
Matches detected entities to Namibian government institutions.

Includes:
- 14 official ministries
- 3 offices (President, PM, Judiciary)
- 9 agencies / constitutional bodies
- 89 state-owned enterprises
- 14 regional councils
- 13 municipalities
- 26 town councils
- 18 village councils
- 63 principals (EDs, Ministers, Heads) mapped to their institution

Precision over recall: when in doubt, leave a story Unmapped.
"""

import json
import os
import sys
import io


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# ============================================================
# OFFICES
# ============================================================
OFFICES = {
    "Office of the President": [
        "Office of the President",
        "Office of the President of Namibia",
        "State House",
        "The Presidency",
    ],
    "Office of the Prime Minister": [
        "Office of the Prime Minister",
        "Prime Minister's Office",
    ],
    "Office of the Judiciary": [
        "Office of the Judiciary",
        "Supreme Court of Namibia",
        "High Court of Namibia",
        "Magistrates Commission",
    ],
}


# ============================================================
# MINISTRIES (14 official, March 2025 structure)
# ============================================================
MINISTRIES = {
    "Ministry of Defence and Veterans Affairs": [
        "Ministry of Defence and Veterans Affairs", "MODVA",
        "Ministry of Defence",
        "Namibian Defence Force", "NDF",
    ],
    "Ministry of Home Affairs, Immigration, Safety and Security": [
        "Ministry of Home Affairs, Immigration, Safety and Security", "MHAISS",
        "Ministry of Home Affairs",
        "Ministry of Safety and Security",
        "Namibian Police Force", "NamPol",
        "Namibian Correctional Service",
    ],
    "Ministry of International Relations and Trade": [
        "Ministry of International Relations and Trade", "MIRT",
        "Ministry of International Relations and Cooperation", "MIRCO",
        "Ministry of International Relations",
    ],
    "Ministry of Finance": [
        "Ministry of Finance", "MoF",
        "Ministry of Finance and Public Enterprises",
    ],
    "Ministry of Agriculture, Fisheries, Water and Land Reform": [
        "Ministry of Agriculture, Fisheries, Water and Land Reform", "MAWLR",
        "Ministry of Agriculture, Water and Land Reform",
        "Ministry of Agriculture, Water and Forestry",
        "Ministry of Agriculture",
        "Department of Water Affairs",
        "Directorate of Veterinary Services",
    ],
    "Ministry of Education, Innovation, Youth, Sports, Arts and Culture": [
        "Ministry of Education, Innovation, Youth, Sports, Arts and Culture",
        "MoEIYSC",
        "Ministry of Education, Arts and Culture",
        "Ministry of Education, Arts, Sports and Culture",
        "Ministry of Education",
        "Ministry of Higher Education, Technology and Innovation",
        "Ministry of Sports, Youth and National Service",
        "Ministry of Sports and Youth",
    ],
    "Ministry of Health and Social Services": [
        "Ministry of Health and Social Services", "MoHSS",
        "Ministry of Health",
        "National Directorate of Primary Health Care Services",
    ],
    "Ministry of Industries, Mines and Energy": [
        "Ministry of Industries, Mines and Energy",
        "Ministry of Industrialisation and Trade",
        "Ministry of Industrialization and Trade",
        "Ministry of Mines and Energy",
        "Ministry of Mines",
        "Ministry of Trade and Industry",
        "Ministry of Industries and Trade",
        "Mines and Energy",
    ],
    "Ministry of Environment, Forestry and Tourism": [
        "Ministry of Environment, Forestry and Tourism", "MEFT",
        "Ministry of Environment and Tourism",
        "Ministry of Environment",
        "Department of Environmental Affairs",
    ],
    "Ministry of Information and Communication Technology": [
        "Ministry of Information and Communication Technology", "MICT",
        "Ministry of Information and Communications Technology",
    ],
    "Ministry of Gender Equality and Child Welfare": [
        "Ministry of Gender Equality and Child Welfare", "MGECW",
        "Ministry of Gender Equality, Poverty Eradication and Social Welfare",
        "Ministry of Gender Equality",
    ],
    "Ministry of Works and Transport": [
        "Ministry of Works and Transport", "MWT",
        "Ministry of Works",
        "Department of Transport",
    ],
    "Ministry of Urban and Rural Development": [
        "Ministry of Urban and Rural Development", "MURD",
        "Ministry of Regional and Local Government and Housing",
        "Ministry of Regional and Local Government",
    ],
    "Ministry of Justice and Labour Relations": [
        "Ministry of Justice and Labour Relations", "MJLR",
        "Ministry of Justice",
        "Ministry of Labour, Industrial Relations and Employment Creation",
        "Ministry of Labour",
        "Master of the High Court", "Legal Aid", "Labour Commissioner",
    ],
}


# ============================================================
# AGENCIES / CONSTITUTIONAL BODIES
# ============================================================
AGENCIES = {
    "Anti-Corruption Commission": [
        "Anti-Corruption Commission", "ACC",
    ],
    "Electoral Commission of Namibia": [
        "Electoral Commission of Namibia", "ECN",
    ],
    "Namibia Central Intelligence Service": [
        "Namibia Central Intelligence Service", "NCIS",
        "Central Intelligence Service",
    ],
    "National Planning Commission": [
        "National Planning Commission", "NPC",
    ],
    "Office of the Attorney-General": [
        "Office of the Attorney-General", "Attorney-General",
    ],
    "Office of the Auditor-General": [
        "Office of the Auditor-General", "Auditor-General",
    ],
    "Office of the Ombudsman": [
        "Office of the Ombudsman", "Ombudsman",
    ],
    "Public Service Commission of Namibia": [
        "Public Service Commission of Namibia",
        "Public Service Commission",
    ],
    "Parliament of Namibia": [
        "Parliament of Namibia",
        "National Assembly", "National Council",
        "Speaker of the National Assembly",
    ],
}


# ============================================================
# STATE-OWNED ENTERPRISES
# ============================================================
SOES = {
    "Agribank": ["Agribank", "Agricultural Bank of Namibia"],
    "Air Namibia": ["Air Namibia"],
    "August 26 Group": ["August 26 Group", "August 26 Holdings"],
    "Bank of Namibia": ["Bank of Namibia", "BoN"],
    "Central Procurement Board of Namibia": [
        "Central Procurement Board of Namibia", "Central Procurement Board", "CPBN",
    ],
    "Communications Regulatory Authority of Namibia": [
        "Communications Regulatory Authority of Namibia", "CRAN",
    ],
    "Development Bank of Namibia": [
        "Development Bank of Namibia", "DBN",
    ],
    "Diamond Board of Namibia": ["Diamond Board of Namibia"],
    "Electricity Control Board": ["Electricity Control Board", "ECB"],
    "Environmental Investment Fund of Namibia": [
        "Environmental Investment Fund of Namibia",
        "Environmental Investment Fund", "EIF",
    ],
    "Epangelo Mining": ["Epangelo Mining", "Epangelo"],
    "Film Commission of Namibia": [
        "Film Commission of Namibia", "Namibia Film Commission",
    ],
    "Financial Intelligence Centre": [
        "Financial Intelligence Centre", "FIC",
    ],
    "Government Institutions Pensions Fund Namibia": [
        "Government Institutions Pensions Fund Namibia",
        "Government Institutions Pensions Fund", "GIPF",
    ],
    "National Fishing Corporation of Namibia": [
        "National Fishing Corporation of Namibia", "FISHCOR",
    ],
    "National Petroleum Corporation of Namibia": [
        "National Petroleum Corporation of Namibia", "NAMCOR",
    ],
    "Fisheries Observer Agency": ["Fisheries Observer Agency"],
    "Henties Bay Waterfront (Pty) Ltd": ["Henties Bay Waterfront"],
    "Karakul Board of South West Africa": ["Karakul Board"],
    "Land Acquisition and Development Fund": ["Land Acquisition and Development Fund"],
    "Lüderitz Waterfront Limited": ["Lüderitz Waterfront"],
    "Meat Board of Namibia": ["Meat Board of Namibia"],
    "Meat Corporation of Namibia": ["Meat Corporation of Namibia", "MeatCo"],
    "Minerals Development Fund of Namibia": ["Minerals Development Fund"],
    "Mobile Telecommunications Limited": [
        "Mobile Telecommunications Limited", "MTC",
        "Mobile Telecommunications Company",
    ],
    "Motor Vehicle Accident Fund": [
        "Motor Vehicle Accident Fund", "MVA Fund",
    ],
    "NamDeb": ["NamDeb", "Namdeb Diamond Corporation"],
    "Namibia Airports Company": ["Namibia Airports Company", "NAC"],
    "Namibia Bricks Enterprises": ["Namibia Bricks Enterprises"],
    "Namibian Broadcasting Corporation": [
        "Namibian Broadcasting Corporation", "NBC",
    ],
    "Namib Desert Diamonds": ["Namib Desert Diamonds", "NAMDIA"],
    "Namibia Diamond Trading Company": [
        "Namibia Diamond Trading Company", "NDTC",
    ],
    "Namibia Development Corporation": [
        "Namibia Development Corporation", "NDC",
    ],
    "Namibia Financial Institutions Supervisory Authority": [
        "Namibia Financial Institutions Supervisory Authority", "NAMFISA",
    ],
    "Namibian Agronomic Board": ["Namibian Agronomic Board", "NAB"],
    "Namibia National Reinsurance Corporation": [
        "Namibia National Reinsurance Corporation", "NamibRe",
    ],
    "Namibian College of Open Learning": [
        "Namibian College of Open Learning", "Namcol", "NAMCOL",
    ],
    "Namibian Communications Commission": ["Namibian Communications Commission"],
    "Namibian Competition Commission": [
        "Namibian Competition Commission", "NaCC",
    ],
    "Namibia Institute of Public Administration and Management": [
        "Namibia Institute of Public Administration and Management", "NIPAM",
    ],
    "Namibia Institute of Pathology": [
        "Namibia Institute of Pathology", "NIP",
    ],
    "Namibia Industrial Development Agency": [
        "Namibia Industrial Development Agency", "NIDA",
    ],
    "Namibian Maritime and Fisheries Institute": [
        "Namibian Maritime and Fisheries Institute", "NAMFI",
    ],
    "Namibian Ports Authority": ["Namibian Ports Authority", "Namport"],
    "Namibia Revenue Agency": [
        "Namibia Revenue Agency", "NamRA",
        "Namibia Revenue Authority",
    ],
    "Namibian Standards Institution": [
        "Namibian Standards Institution", "NSI",
    ],
    "Namibia Post and Telecommunications": [
        "Namibia Post and Telecommunications", "NamPost", "Namibia Post",
    ],
    "Namibia Power Corporation": [
        "Namibia Power Corporation", "NamPower",
    ],
    "Namibia Press Agency": ["Namibia Press Agency", "NAMPA"],
    "Namibia Qualifications Authority": [
        "Namibia Qualifications Authority", "NQA",
    ],
    "Namibia Sports Commission": ["Namibia Sports Commission"],
    "Namibia Statistics Agency": [
        "Namibia Statistics Agency", "NSA",
    ],
    "Namibia Students Financial Assistance Fund": [
        "Namibia Students Financial Assistance Fund",
        "Namibia Students' Financial Assistance Fund", "NSFAF",
    ],
    "Namibia Tourism Board": ["Namibia Tourism Board"],
    "Namibia Training Authority": [
        "Namibia Training Authority", "NTA",
    ],
    "Namibia Water Corporation": [
        "Namibia Water Corporation", "NamWater",
    ],
    "Namibia Wildlife Resorts": ["Namibia Wildlife Resorts", "NWR"],
    "Namibia University of Science and Technology": [
        "Namibia University of Science and Technology", "NUST",
    ],
    "NamZim": ["NamZim"],
    "National Art Gallery of Namibia": [
        "National Art Gallery of Namibia", "NAGN",
    ],
    "National Council for Higher Education": [
        "National Council for Higher Education", "NCHE",
    ],
    "National Disability Council": [
        "National Disability Council", "NDC Disability",
    ],
    "National Emergency and Disaster Management Fund": [
        "National Emergency and Disaster Management Fund",
    ],
    "National Heritage Council": [
        "National Heritage Council", "NHC",
    ],
    "National Housing Enterprise": [
        "National Housing Enterprise", "NHE",
    ],
    "National Theatre of Namibia": [
        "National Theatre of Namibia", "NTN",
    ],
    "National Special Risks Association": [
        "National Special Risks Association", "NASRIA",
    ],
    "National Youth Council": [
        "National Youth Council", "NYC",
    ],
    "Namibia Investment Promotion and Development Board": [
        "Namibia Investment Promotion and Development Board", "NIPDB",
        "NIPDBN",
    ],
    "National Youth Service": [
        "National Youth Service", "NYS",
    ],
    "New Era Publication Corporation": [
        "New Era Publication Corporation", "New Era",
    ],
    "Offshore Development Company": ["Offshore Development Company"],
    "Regional Equity and Development Fund": ["Regional Equity and Development Fund"],
    "Road Fund Administration": ["Road Fund Administration", "RFA"],
    "Roads Authority": ["Roads Authority", "RA Roads"],
    "Roads Contractor Company": ["Roads Contractor Company", "RCC"],
    "Security Enterprises and Security Officers Regulation Board": [
        "Security Enterprises and Security Officers Regulation Board",
        "SESORB",
    ],
    "SME Bank of Namibia": ["SME Bank of Namibia", "SME Bank"],
    "Star Protection Service": ["Star Protection Service"],
    "Social Security Commission": [
        "Social Security Commission", "SSC",
    ],
    "TransNamib Holdings": ["TransNamib Holdings", "TransNamib"],
    "University of Namibia": ["University of Namibia", "UNAM"],
    "Veterans Subversion Fund": ["Veterans Subversion Fund"],
    "Windhoek Country Club and Casino": [
        "Windhoek Country Club and Casino", "Windhoek Country Club",
    ],
    "Windhoeker Maschinenfabrik": ["Windhoeker Maschinenfabrik"],
    "Youth Credit Scheme": ["Youth Credit Scheme"],
    "Zambezi Waterfront Limited": ["Zambezi Waterfront"],
}


# ============================================================
# REGIONAL COUNCILS
# ============================================================
REGIONAL_COUNCILS = {
    "Erongo Regional Council": ["Erongo Regional Council", "Erongo Region"],
    "Hardap Regional Council": ["Hardap Regional Council", "Hardap Region"],
    "//Kharas Regional Council": [
        "//Kharas Regional Council", "Karas Regional Council",
        "//Kharas Region", "Karas Region",
    ],
    "Kavango East Regional Council": [
        "Kavango East Regional Council", "Kavango East Region",
    ],
    "Kavango West Regional Council": [
        "Kavango West Regional Council", "Kavango West Region",
    ],
    "Khomas Regional Council": ["Khomas Regional Council", "Khomas Region"],
    "Kunene Regional Council": ["Kunene Regional Council", "Kunene Region"],
    "Ohangwena Regional Council": [
        "Ohangwena Regional Council", "Ohangwena Region",
    ],
    "Omaheke Regional Council": ["Omaheke Regional Council", "Omaheke Region"],
    "Omusati Regional Council": ["Omusati Regional Council", "Omusati Region"],
    "Oshana Regional Council": ["Oshana Regional Council", "Oshana Region"],
    "Oshikoto Regional Council": ["Oshikoto Regional Council", "Oshikoto Region"],
    "Otjozondjupa Regional Council": [
        "Otjozondjupa Regional Council", "Otjozondjupa Region",
    ],
    "Zambezi Regional Council": ["Zambezi Regional Council", "Zambezi Region"],
}


# ============================================================
# MUNICIPALITIES
# ============================================================
MUNICIPALITIES = {
    "Gobabis Municipality": ["Gobabis Municipality"],
    "Grootfontein Municipality": ["Grootfontein Municipality"],
    "Keetmanshoop Municipality": ["Keetmanshoop Municipality"],
    "Mariental Municipality": ["Mariental Municipality"],
    "Okahandja Municipality": ["Okahandja Municipality"],
    "Omaruru Municipality": ["Omaruru Municipality"],
    "Otjiwarongo Municipality": ["Otjiwarongo Municipality"],
    "Outjo Municipality": ["Outjo Municipality"],
    "Henties Bay Municipality": ["Henties Bay Municipality"],
    "Swakopmund Municipality": ["Swakopmund Municipality"],
    "Tsumeb Municipality": ["Tsumeb Municipality"],
    "Walvis Bay Municipality": ["Walvis Bay Municipality"],
    "Windhoek Municipality": [
        "Windhoek Municipality", "City of Windhoek",
        "Municipality of Windhoek", "CoW",
    ],
}


# ============================================================
# TOWN COUNCILS
# ============================================================
TOWN_COUNCILS = {
    "Arandis Town Council": ["Arandis Town Council"],
    "Aranos Town Council": ["Aranos Town Council"],
    "Eenhana Town Council": ["Eenhana Town Council"],
    "Helao Nafidi Town Council": ["Helao Nafidi Town Council"],
    "Katima Mulilo Town Council": ["Katima Mulilo Town Council"],
    "Karibib Town Council": ["Karibib Town Council"],
    "Khorixas Town Council": ["Khorixas Town Council"],
    "Lüderitz Town Council": ["Lüderitz Town Council"],
    "Nkurenkuru Town Council": ["Nkurenkuru Town Council"],
    "Okahao Town Council": ["Okahao Town Council"],
    "Oranjemund Town Council": ["Oranjemund Town Council"],
    "Okakarara Town Council": ["Okakarara Town Council"],
    "Omuthiya Town Council": ["Omuthiya Town Council"],
    "Ondangwa Town Council": ["Ondangwa Town Council"],
    "Ongwediva Town Council": ["Ongwediva Town Council"],
    "Oniipa Town Council": ["Oniipa Town Council"],
    "Opuwo Town Council": ["Opuwo Town Council"],
    "Oshakati Town Council": ["Oshakati Town Council"],
    "Outapi Town Council": ["Outapi Town Council"],
    "Oshikuku Town Council": ["Oshikuku Town Council"],
    "Otavi Town Council": ["Otavi Town Council"],
    "Rehoboth Town Council": ["Rehoboth Town Council"],
    "Rundu Town Council": ["Rundu Town Council"],
    "Ruacana Town Council": ["Ruacana Town Council"],
    "Karasburg Town Council": ["Karasburg Town Council"],
    "Usakos Town Council": ["Usakos Town Council"],
}


# ============================================================
# VILLAGE COUNCILS
# ============================================================
VILLAGE_COUNCILS = {
    "Aroab Village Council": ["Aroab Village Council"],
    "Berseba Village Council": ["Berseba Village Council"],
    "Bethanie Village Council": ["Bethanie Village Council"],
    "Bukalo Village Council": ["Bukalo Village Council"],
    "Divundu Village Council": ["Divundu Village Council"],
    "Gibeon Village Council": ["Gibeon Village Council"],
    "Gochas Village Council": ["Gochas Village Council"],
    "Kalkrand Village Council": ["Kalkrand Village Council"],
    "Kamanjab Village Council": ["Kamanjab Village Council"],
    "Koes Village Council": ["Koes Village Council"],
    "Leonardville Village Council": ["Leonardville Village Council"],
    "Maltahohe Village Council": ["Maltahohe Village Council"],
    "Okongo Village Council": ["Okongo Village Council"],
    "Otjinene Village Council": ["Otjinene Village Council"],
    "Stampriet Village Council": ["Stampriet Village Council"],
    "Tsandi Village Council": ["Tsandi Village Council"],
    "Tses Village Council": ["Tses Village Council"],
    "Witvlei Village Council": ["Witvlei Village Council"],
}


# ============================================================
# PRINCIPALS — names → institution
# ============================================================
PRINCIPALS = {
    "Elijah Ngurare": "Office of the Prime Minister",
    "Frans Kapofi": "Ministry of Defence and Veterans Affairs",
    "Lucia Iipumbu": "Ministry of Industrialisation and Trade",
    "Selma Ashipala-Musavyi": "Ministry of International Relations and Trade",
    "Selma Ashipala Musaviy": "Ministry of International Relations and Trade",
    "Ericah Shafudah": "Ministry of Finance",
    "Sanet Steenkamp": "Ministry of Education, Innovation, Youth, Sports, Arts and Culture",
    "Esperance Luvindao": "Ministry of Health and Social Services",
    "Natangwe Ithete": "Ministry of Finance",
    "Indileni Daniel": "Ministry of Environment, Forestry and Tourism",
    "Emma Theofelus": "Ministry of Information and Communication Technology",
    "Emma Kantema": "Ministry of Gender Equality and Child Welfare",
    "Veikko Nekundi": "Ministry of Works and Transport",
    "James Sankwasa": "Ministry of Works and Transport",
    "Fillemon Wise Emmanuel": "Ministry of Urban and Rural Development",
    "Charles Mubita": "Ministry of International Relations and Trade",
    "Jenelly Matundu": "Ministry of International Relations and Trade",
    "Dino Ballotti": "Ministry of Industrialisation and Trade",
    "Gaudentia Kröhne": "Ministry of Gender Equality and Child Welfare",
    "Linda Bayoli": "Ministry of Gender Equality and Child Welfare",
    "Evelyn !Nawases Taeyele": "Ministry of Environment, Forestry and Tourism",
    "Kaire Mbuende": "National Planning Commission",
    "Festus Mbandeka": "Office of the Attorney-General",
    "Benedict Likando": "Ministry of Justice and Labour Relations",
    "Annely Haiphene": "Ministry of Health and Social Services",
    "Nghidina Daniel": "Ministry of Home Affairs, Immigration, Safety and Security",
    "Ndiiath Nghipondoka-Robiati": "Ministry of Education, Innovation, Youth, Sports, Arts and Culture",
    "Michael Humavindu": "Ministry of Finance",
    "Ndiyakupi Nghituwamata": "Ministry of Agriculture, Fisheries, Water and Land Reform",
    "Teofilus Nghitila": "Ministry of Environment, Forestry and Tourism",
    "Erastus Heitengela": "Ministry of Health and Social Services",
    "Gerard Vries": "Ministry of Finance",
    "Penda Ithindi": "Ministry of Industrialisation and Trade",
    "Moses Pakote": "Ministry of Urban and Rural Development",
    "Sikongo Haihambo": "Ministry of Finance",
    "Lydia Indombo": "Ministry of Information and Communication Technology",
    "Titus Ndove": "Ministry of Works and Transport",
    "Wilhemina Shivute": "Ministry of Gender Equality and Child Welfare",
    "Audrin Mathe": "Ministry of Education, Innovation, Youth, Sports, Arts and Culture",
    "Gladice Pickering": "Ministry of International Relations and Trade",
    "Tuyakula Haipinge": "Ministry of Health and Social Services",
    "Shivute Indongo": "Ministry of Mines and Energy",
    "Ben Nangombe": "Ministry of Justice and Labour Relations",
    "I-Ben Nashandi": "Ministry of Urban and Rural Development",
    "Mateus Kaholongo": "Ministry of Home Affairs, Immigration, Safety and Security",
    "Nevile Gertze": "Ministry of Industrialisation and Trade",
    "Pijoo Nganate": "Ministry of Urban and Rural Development",
    "Vipuakuje Muharukua": "Ministry of Industrialisation and Trade",
    "Verna Sinimbo": "Ministry of Industrialisation and Trade",
    "John Khamuseb": "Ministry of Works and Transport",
    "Sam Nujoma": "Office of the President",
    "Sacky Kathindi": "Ministry of Urban and Rural Development",
    "Natalia /Goagoses": "Ministry of Urban and Rural Development",
    "Kadiva Hamutumwa": "Ministry of Industrialisation and Trade",
    "Hamunyera Hambyuka": "Ministry of Home Affairs, Immigration, Safety and Security",
    "Immanuel Shikongo": "Ministry of Home Affairs, Immigration, Safety and Security",
    "Hofni Iipinge": "Ministry of Health and Social Services",
    "Dorthy Kabula": "Ministry of Works and Transport",
    "Dawid Gertze": "Ministry of Home Affairs, Immigration, Safety and Security",
    "Riaan McNab": "Ministry of Urban and Rural Development",
    "Corné Mélissen": "Ministry of Industrialisation and Trade",
    "Emilia Nghikembua": "Ministry of Information and Communication Technology",
    "Titus Nampala": "Ministry of Industrialisation and Trade",
    "Bryan Eiseb": "Ministry of Finance",
    "Theo Uusiku": "Ministry of Industrialisation and Trade",
    "Shiwana Ndeunyema": "Ministry of Agriculture, Fisheries, Water and Land Reform",
    "Werner Embvula": "Ministry of Home Affairs, Immigration, Safety and Security",
}


# ============================================================
# COMBINED TAXONOMY
# ============================================================
def build_taxonomy():
    """Combine all taxonomy sections into one dict."""
    taxonomy = {}
    for section in (OFFICES, MINISTRIES, AGENCIES, SOES,
                    REGIONAL_COUNCILS, MUNICIPALITIES,
                    TOWN_COUNCILS, VILLAGE_COUNCILS):
        taxonomy.update(section)
    return taxonomy


GOVERNMENT_TAXONOMY = build_taxonomy()


# ============================================================
# MATCHING LOGIC
# ============================================================
def match_entity_to_oma(entity_text, taxonomy):
    """
    Exact match (case-insensitive), stripping leading 'the'.
    This handles spaCy's habit of keeping 'the' in front of
    organisation names (e.g. 'the National Assembly').
    """
    entity_lower = entity_text.lower().strip()

    # Strip a leading "the "
    if entity_lower.startswith("the "):
        entity_lower = entity_lower[4:].strip()

    for oma_name, aliases in taxonomy.items():
        for alias in aliases:
            alias_lower = alias.lower().strip()
            if alias_lower.startswith("the "):
                alias_lower = alias_lower[4:].strip()
            if entity_lower == alias_lower:
                return oma_name

    return None


# ============================================================
# NON-ENGLISH FILTER
# ============================================================
NON_ENGLISH_MARKERS = [
    "ovanhu", "otai", "otau", "ombaanga", "omukithi",
    "omauliko", "okutondoka", "omahangu", "ongha",
    "ovakwashiwana", "omukanda", "ovakwetu",
    "ovandu", "otjike", "ovature",
    "mense", "regering", "namibie", "volgende",
]


def is_mostly_english(text):
    """
    Return True if the story is mostly English.
    Returns False if it contains strong non-English markers or
    a large fraction of non-ASCII letters.
    """
    if not text:
        return True

    sample = text[:500]
    if not sample:
        return True

    sample_lower = sample.lower()

    if any(marker in sample_lower for marker in NON_ENGLISH_MARKERS):
        return False

    ascii_letters = sum(1 for c in sample if c.isalpha() and c.isascii())
    total_letters = sum(1 for c in sample if c.isalpha())

    if total_letters == 0:
        return True

    return (ascii_letters / total_letters) >= 0.95


# ============================================================
# SPORTS FILTER
# ============================================================
SPORTS_KEYWORDS = [
    "football", "netball", "boxing", "karate", "rugby",
    "cricket", "olympic", "olympian", "wbo", "ibf",
    "fifa", "caf", "premier league", "championship",
    "tournament", "kudus", "wanderers", "desert jewels",
    "world cup", "netball premier",
]


def is_sports_story(text):
    """Check if a story is mainly about sports."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in SPORTS_KEYWORDS)


# ============================================================
# MINISTRY PREFERENCE
# ============================================================
def prefer_ministries(matched):
    """
    If multiple matches, prefer ministries over SOEs/agencies.
    Returns at most 2 tags.
    """
    if len(matched) <= 2:
        return matched

    ministries = [m for m in matched if m.startswith("Ministry of")]
    others = [m for m in matched if not m.startswith("Ministry of")]

    if ministries:
        final = [ministries[0]]
        if others:
            final.append(others[0])
        return final

    return matched[:2]


# ============================================================
# BILATERAL / TRADE FALLBACK
# ============================================================
BILATERAL_PARTNERS = [
    "zimbabwe", "china", "philippines", "kyrgyz", "zambia",
    "botswana", "angola", "ghana", "kenya", "south africa",
    "japan", "india", "brazil", "russia", "germany", "france",
    "united states", "united kingdom", "eu", "european union",
    "cuba", "nigeria", "tanzania", "mozambique", "malawi",
]


def is_bilateral_story(text_lower):
    """Check if the story is about bilateral cooperation."""
    if "namibia" not in text_lower:
        return False

    has_partner = any(partner in text_lower for partner in BILATERAL_PARTNERS)
    if not has_partner:
        return False

    trade_markers = [
        "bilateral", "cooperation", "trade and investment",
        "trade ties", "diplomatic", "memorandum of understanding",
        "bilateral relations", "bilateral cooperation",
    ]
    return any(marker in text_lower for marker in trade_markers)


# ============================================================
# MAIN MAPPER
# ============================================================
def map_story(story, taxonomy):
    """Add O/M/A field to a story based on detected entities."""
    matched = []

    body_lower = (
        (story.get("body", "") or "") + " " +
        (story.get("headline", "") or "")
    ).lower()

    # ---------- STEP -1: Skip non-English stories ----------
    full_text = (story.get("headline", "") or "") + " " + (story.get("body", "") or "")
    if not is_mostly_english(full_text):
        story["oma"] = ["Unmapped"]
        return story

    # ---------- STEP 0: Sports filter ----------
    if is_sports_story(body_lower):
        sports_ministry = None
        for org in story.get("entities", {}).get("organizations", []):
            o = org.lower()
            if "sport" in o or "namibia sports commission" in o:
                sports_ministry = (
                    "Ministry of Education, Innovation, Youth, Sports, Arts and Culture"
                )
                break
        story["oma"] = [sports_ministry] if sports_ministry else ["Unmapped"]
        return story

    # ---------- STEP 1: Crime indicators ----------
    crime_keywords = [
        "arrested", "nampol", "murder", "homicide",
        "convicted", "sentenced",
        "robbery", "high court", "magistrate", "prosecutor",
    ]
    is_crime_story = any(kw in body_lower for kw in crime_keywords)

    # ---------- STEP 2: Detected organizations (exact match) ----------
    for org in story.get("entities", {}).get("organizations", []):
        oma = match_entity_to_oma(org, taxonomy)
        if oma and oma not in matched:
            matched.append(oma)

    # ---------- STEP 3: Detected people → principals (weaker) ----------
    # Only run if no organization match yet.
    if not matched:
        people = story.get("entities", {}).get("people", [])[:3]
        for person in people:
            oma = match_entity_to_oma(person, taxonomy)
            if oma and oma not in matched:
                matched.append(oma)
                continue
            if person in PRINCIPALS:
                principal_match = PRINCIPALS[person]
                if principal_match not in matched:
                    matched.append(principal_match)

    # ---------- STEP 4: Crime override (weak matches only) ----------
    if is_crime_story:
        strong_matches = [
            m for m in matched
            if m != "Other State-Owned Enterprises"
            and "Regional Council" not in m
            and "Village Council" not in m
            and "Town Council" not in m
            and "Municipality" not in m
        ]
        if not strong_matches:
            matched = ["Ministry of Home Affairs, Immigration, Safety and Security"]

    # ---------- STEP 5: Strict body scan (full names only) ----------
    if not matched:
        full_names = {
            "Ministry of Agriculture, Fisheries, Water and Land Reform":
                "ministry of agriculture, fisheries, water and land reform",
            "Ministry of Health and Social Services":
                "ministry of health and social services",
            "Ministry of Education, Innovation, Youth, Sports, Arts and Culture":
                "ministry of education, innovation, youth, sports, arts and culture",
            "Ministry of Urban and Rural Development":
                "ministry of urban and rural development",
            "Ministry of Works and Transport":
                "ministry of works and transport",
            "Ministry of Home Affairs, Immigration, Safety and Security":
                "ministry of home affairs, immigration, safety and security",
            "Ministry of International Relations and Trade":
                "ministry of international relations and trade",
            "Ministry of Justice and Labour Relations":
                "ministry of justice and labour relations",
            "Ministry of Industrialisation and Trade":
                "ministry of industrialisation and trade",
            "Ministry of Environment, Forestry and Tourism":
                "ministry of environment, forestry and tourism",
            "Ministry of Information and Communication Technology":
                "ministry of information and communication technology",
            "Ministry of Gender Equality and Child Welfare":
                "ministry of gender equality and child welfare",
            "Ministry of Defence and Veterans Affairs":
                "ministry of defence and veterans affairs",
            "Ministry of Finance":
                "ministry of finance",
        }

        for oma_name, phrase in full_names.items():
            if phrase in body_lower:
                matched.append(oma_name)

    # ---------- STEP 6: Bilateral / trade fallback ----------
    if not matched and is_bilateral_story(body_lower):
        matched.append("Ministry of International Relations and Trade")

    # ---------- STEP 7: Prefer ministries, cap at 2 tags ----------
    matched = prefer_ministries(matched)

    story["oma"] = matched if matched else ["Unmapped"]
    return story


# ============================================================
# MAIN
# ============================================================
def map_all(input_file="data/processed/analyzed.json",
            output_file="data/processed/mapped.json"):
    print(f"Reading {input_file}...")
    with open(input_file, "r", encoding="utf-8-sig") as f:
        stories = json.load(f)

    print(f"Mapping {len(stories)} stories to government entities...\n")

    mapped = []
    for i, story in enumerate(stories, 1):
        mapped.append(map_story(story, GOVERNMENT_TAXONOMY))
        print(f"  [{i}/{len(stories)}] {story['headline'][:50]}... -> {mapped[-1]['oma']}")

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8-sig") as f:
        json.dump(mapped, f, indent=2, ensure_ascii=False)

    mapped_count = sum(1 for s in mapped if s["oma"] != ["Unmapped"])
    unmapped_count = len(mapped) - mapped_count

    print(f"\n[OK] Saved {len(mapped)} mapped stories -> {output_file}")
    print(f"\nMapping results:")
    print(f"  Mapped:   {mapped_count}")
    print(f"  Unmapped: {unmapped_count}")

    oma_counts = {}
    for s in mapped:
        for oma in s["oma"]:
            oma_counts[oma] = oma_counts.get(oma, 0) + 1

    print(f"\nTop institutions:")
    for oma, count in sorted(oma_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {oma}: {count}")


if __name__ == "__main__":
    map_all()