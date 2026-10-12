"""
GovPulse — Seed Demo Data
Adds realistic sample stories across all ministries so the demo
has coverage for every user type.

These are clearly labeled with source="Sample Data" so they can be
distinguished from live pipeline output.
"""

import os
import sys
from datetime import datetime, timedelta


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src import db


# ------------------------------------------------------------
# SAMPLE STORIES
# ------------------------------------------------------------
SAMPLE_STORIES = [
    # ---------- HEALTH ----------
    {
        "source": "Sample Data",
        "headline": "Health Ministry launches nationwide vaccination drive",
        "ai_summary": "The Ministry of Health and Social Services has launched a nationwide vaccination campaign targeting children under five. The programme aims to reach over 200,000 children across all 14 regions.",
        "sentiment": "Positive",
        "sentiment_confidence": 0.72,
        "oma": ["Ministry of Health and Social Services"],
        "government_source": "Executive Director, Ministry of Health and Social Services",
        "url": "",
        "body": "The Ministry of Health and Social Services has launched a nationwide vaccination campaign targeting children under five years of age. The programme aims to reach over 200,000 children across all 14 regions over the next six months. Speaking at the launch event, the Executive Director emphasised the Ministry's commitment to ensuring every child has access to essential vaccines. The campaign is supported by UNICEF and the World Health Organization.",
        "government_source_quote": True,
    },
    {
        "source": "Sample Data",
        "headline": "Medicine shortages reported at Katutura Intermediate Hospital",
        "ai_summary": "Patients at Katutura Intermediate Hospital have reported that essential medicines have been unavailable for two weeks. The Ministry of Health has not yet commented on the situation.",
        "sentiment": "Negative",
        "sentiment_confidence": 0.85,
        "oma": ["Ministry of Health and Social Services"],
        "government_source": "",
        "url": "",
        "body": "Patients at Katutura Intermediate Hospital have reported that essential medicines have been unavailable for two weeks. Hospital staff, speaking on condition of anonymity, said the shortage affects chronic medications for hypertension, diabetes, and HIV treatment. The Ministry of Health and Social Services has not yet commented. This is the second such incident in three months.",
        "government_source_quote": False,
    },
    {
        "source": "Sample Data",
        "headline": "Mental health funding increases by 40 percent for 2026",
        "ai_summary": "The government has increased mental health funding by 40 percent in the 2026 budget. The Ministry of Health will use the funds to establish five new mental health units.",
        "sentiment": "Positive",
        "sentiment_confidence": 0.78,
        "oma": ["Ministry of Health and Social Services"],
        "government_source": "Minister of Health and Social Services",
        "url": "",
        "body": "The government has allocated an additional 40 percent to mental health services in the 2026 national budget. The Ministry of Health and Social Services will use the funds to establish five new mental health units across the country by 2027. The Minister said this reflects the government's commitment to addressing the growing mental health crisis.",
        "government_source_quote": True,
    },
    {
        "source": "Sample Data",
        "headline": "Hospital capacity strained as patient numbers rise",
        "ai_summary": "Windhoek Central Hospital is operating above capacity following an increase in patient admissions. Staff have called for urgent intervention from the Ministry of Health.",
        "sentiment": "Negative",
        "sentiment_confidence": 0.82,
        "oma": ["Ministry of Health and Social Services"],
        "government_source": "Spokesperson, Ministry of Health and Social Services",
        "url": "",
        "body": "Windhoek Central Hospital is currently operating above capacity, with patient admissions exceeding the facility's designed limits. Hospital staff have called on the Ministry of Health and Social Services to intervene urgently. A spokesperson for the Ministry said additional resources would be deployed in the coming weeks.",
        "government_source_quote": True,
    },

    # ---------- FINANCE ----------
    {
        "source": "Sample Data",
        "headline": "Finance Ministry announces tax relief for small businesses",
        "ai_summary": "The Ministry of Finance has announced tax relief measures for small and medium enterprises. The measures take effect in the next fiscal year.",
        "sentiment": "Positive",
        "sentiment_confidence": 0.75,
        "oma": ["Ministry of Finance"],
        "government_source": "Minister of Finance",
        "url": "",
        "body": "The Ministry of Finance has announced a package of tax relief measures aimed at supporting small and medium enterprises. The measures include reduced corporate tax rates for businesses below a certain revenue threshold, and simplified VAT compliance. The Minister said the changes would take effect in the next fiscal year.",
        "government_source_quote": True,
    },
    {
        "source": "Sample Data",
        "headline": "NamRA targets informal traders in new compliance drive",
        "ai_summary": "The Namibia Revenue Agency has launched a compliance drive targeting informal traders. Traders have raised concerns about the impact on their livelihoods.",
        "sentiment": "Negative",
        "sentiment_confidence": 0.68,
        "oma": ["Ministry of Finance", "Namibia Revenue Agency"],
        "government_source": "Spokesperson, NamRA",
        "url": "",
        "body": "The Namibia Revenue Agency (NamRA) has launched a compliance drive aimed at informal traders operating in Windhoek, Oshakati, and Walvis Bay. Traders have raised concerns about the impact on their livelihoods. A spokesperson for NamRA said the drive was intended to help traders understand their tax obligations, not to penalise them.",
        "government_source_quote": True,
    },
    {
        "source": "Sample Data",
        "headline": "Budget allocation for 2027 prioritises infrastructure",
        "ai_summary": "The Ministry of Finance has outlined the 2027 budget priorities, with infrastructure receiving the largest allocation. Details will be tabled in Parliament next month.",
        "sentiment": "Neutral",
        "sentiment_confidence": 0.55,
        "oma": ["Ministry of Finance"],
        "government_source": "Minister of Finance",
        "url": "",
        "body": "The Ministry of Finance has outlined the strategic priorities for the 2027 national budget, with infrastructure development receiving the largest allocation. The budget includes increased spending on roads, water infrastructure, and energy projects. The full budget will be tabled in Parliament next month.",
        "government_source_quote": True,
    },

    # ---------- EDUCATION ----------
    {
        "source": "Sample Data",
        "headline": "Ministry of Education launches digital literacy programme",
        "ai_summary": "A national digital literacy programme has been launched to equip learners with computer skills. The initiative targets rural schools first.",
        "sentiment": "Positive",
        "sentiment_confidence": 0.80,
        "oma": ["Ministry of Education, Innovation, Youth, Sports, Arts and Culture"],
        "government_source": "Minister of Education",
        "url": "",
        "body": "The Ministry of Education, Innovation, Youth, Sports, Arts and Culture has launched a national digital literacy programme aimed at equipping learners with essential computer skills. The initiative will begin with rural schools, where access to technology has historically been limited. The Minister said the programme would reach 500 schools within the first year.",
        "government_source_quote": True,
    },
    {
        "source": "Sample Data",
        "headline": "Teacher shortages affect rural schools across the country",
        "ai_summary": "Schools in rural Namibia are facing severe teacher shortages, with some subjects having no qualified instructors. The Ministry acknowledges the challenge.",
        "sentiment": "Negative",
        "sentiment_confidence": 0.78,
        "oma": ["Ministry of Education, Innovation, Youth, Sports, Arts and Culture"],
        "government_source": "Spokesperson, Ministry of Education",
        "url": "",
        "body": "Schools across rural Namibia are facing severe teacher shortages, with mathematics, science, and English most affected. Some schools report having no qualified instructors for certain subjects. A spokesperson for the Ministry of Education said the government is working on incentives to attract teachers to rural areas.",
        "government_source_quote": True,
    },
    {
        "source": "Sample Data",
        "headline": "NUST researchers win international innovation award",
        "ai_summary": "A team from the Namibia University of Science and Technology has won an international award for a solar-powered water purification system.",
        "sentiment": "Positive",
        "sentiment_confidence": 0.88,
        "oma": ["Ministry of Education, Innovation, Youth, Sports, Arts and Culture", "Namibia University of Science and Technology"],
        "government_source": "",
        "url": "",
        "body": "A research team from the Namibia University of Science and Technology (NUST) has won an international innovation award for developing a solar-powered water purification system designed for rural communities. The award was presented at a ceremony in Nairobi. The Ministry of Education congratulated the team.",
        "government_source_quote": False,
    },

    # ---------- INTERNATIONAL RELATIONS ----------
    {
        "source": "Sample Data",
        "headline": "Namibia and Germany sign N$103 million energy partnership",
        "ai_summary": "The two countries have signed a N$103 million agreement to develop green hydrogen production in Namibia. The partnership is expected to create local jobs.",
        "sentiment": "Positive",
        "sentiment_confidence": 0.82,
        "oma": ["Ministry of International Relations and Trade"],
        "government_source": "Minister of International Relations and Trade",
        "url": "",
        "body": "Namibia and Germany have signed a N$103 million partnership agreement to develop green hydrogen production capacity. The agreement was signed during a state visit to Berlin. The Minister of International Relations and Trade said the partnership would create thousands of local jobs and position Namibia as a leader in renewable energy on the African continent.",
        "government_source_quote": True,
    },
    {
        "source": "Sample Data",
        "headline": "Namibia and Zimbabwe strengthen agriculture and trade ties",
        "ai_summary": "Bilateral trade discussions between Namibia and Zimbabwe focused on agricultural exports and investment opportunities.",
        "sentiment": "Positive",
        "sentiment_confidence": 0.72,
        "oma": ["Ministry of International Relations and Trade"],
        "government_source": "Minister of International Relations and Trade",
        "url": "",
        "body": "Namibia and Zimbabwe have agreed to strengthen bilateral trade in agriculture and related industries. The agreement was reached during the Zimbabwe-Namibia Trade Mission, which brought together business leaders from both countries. The Minister of International Relations and Trade highlighted opportunities for Namibian exporters in Zimbabwe's growing market.",
        "government_source_quote": True,
    },
]


# ------------------------------------------------------------
# INSERT INTO DATABASE
# ------------------------------------------------------------
def insert_stories():
    inserted = 0
    skipped = 0

    for s in SAMPLE_STORIES:
        # Check if it already exists
        existing = db.get_story(s["headline"])
        if existing:
            skipped += 1
            continue

        # Add metadata
        s["scraped_at"] = datetime.now().isoformat()
        s["created_at"] = datetime.now().isoformat()
        s["page"] = "Sample"
        s["entities"] = {"organizations": [], "people": [], "locations": []}

        # Clean the internal-only field
        s.pop("government_source_quote", None)

        try:
            db.upsert_story(s)
            inserted += 1
            print(f"  [OK] {s['headline'][:70]}")
        except Exception as e:
            print(f"  [ERR] {s['headline'][:70]}: {e}")

    return inserted, skipped


def run():
    print("=" * 60)
    print("  GovPulse — Seed Demo Data")
    print("=" * 60)
    print()

    print(f"Inserting {len(SAMPLE_STORIES)} sample stories...")
    inserted, skipped = insert_stories()

    print()
    print("=" * 60)
    print(f"  Inserted: {inserted}")
    print(f"  Skipped:  {skipped} (already existed)")
    print("=" * 60)

    # Show new ministry coverage
    print("\nCurrent coverage by ministry:")
    from collections import Counter
    stories = db.get_stories()
    c = Counter()
    for s in stories:
        for oma in (s.get("oma") or []):
            c[oma] += 1

    for name, count in c.most_common(20):
        print(f"  {count:3d}  {name}")


if __name__ == "__main__":
    run()