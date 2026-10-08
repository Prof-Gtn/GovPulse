"""
GovPulse — Analyzer
Adds sentiment, summary, and entity detection to each story.
"""

import json
import os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import spacy


# Load once (slow to load, fast to use)
print("Loading models...")
sentiment_analyzer = SentimentIntensityAnalyzer()
nlp = spacy.load("en_core_web_sm")
print("Models loaded.\n")


def classify_sentiment(text):
    """Return Positive, Neutral, or Negative."""
    if not text:
        return "Neutral"

    scores = sentiment_analyzer.polarity_scores(text)
    compound = scores["compound"]

    # Wider neutral band for news content (VADER defaults are
    # tuned for social media; news articles need a wider neutral zone)
    if compound >= 0.3:
        return "Positive"
    elif compound <= -0.3:
        return "Negative"
    else:
        return "Neutral"


def summarize(text, sentences=2):
    """Return a short summary. Falls back to first 200 chars if too short."""
    if not text:
        return ""

    words = text.split()
    if len(words) < 40:
        return text[:200]

    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary_sentences = summarizer(parser.document, sentences)
        result = " ".join(str(s) for s in summary_sentences)

        # Cleanup: strip leading punctuation and whitespace
        result = result.lstrip(",. ;:'\"")
        result = result.strip()

        # Strip leading fragments until we hit a capital letter
        while result and not result[0].isupper():
            result = result[1:].lstrip()

        # Capitalize the first letter
        if result:
            result = result[0].upper() + result[1:]

        # Fallback if sumy returned nothing usable
        if not result.strip():
            return text[:200]

        return result

    except Exception as e:
        print(f"    [WARN] Summarization failed: {e}")
        return text[:200]


def extract_entities(text):
    """Extract organizations, people, and locations."""
    if not text:
        return {"organizations": [], "people": [], "locations": []}

    # spaCy has a max length — truncate very long texts
    doc = nlp(text[:100000])

    entities = {
        "organizations": [],
        "people": [],
        "locations": [],
    }

    for ent in doc.ents:
        if ent.label_ == "ORG":
            entities["organizations"].append(ent.text)
        elif ent.label_ == "PERSON":
            entities["people"].append(ent.text)
        elif ent.label_ in ("GPE", "LOC"):
            entities["locations"].append(ent.text)

    # Deduplicate while preserving order
    for key in entities:
        seen = set()
        unique = []
        for item in entities[key]:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        entities[key] = unique

    return entities

def extract_government_source(text, entities):
    """
    Try to identify the government official or source quoted in the story.
    Uses keyword patterns and detected person names.
    Returns a string like 'Hon. Emma Theofelus, Minister of ICT' or ''.
    """
    if not text:
        return ""

    text_lower = text.lower()

    # Government role keywords — if we see these, we look for a nearby name
    role_keywords = [
        "minister", "deputy minister", "president", "vice president",
        "prime minister", "executive director", "spokesperson",
        "spokesman", "spokeswoman", "ceo", "chief executive",
        "governor", "councillor", "mayor", "chairperson",
        "permanent secretary", "director", "commissioner",
        "ombudsman", "auditor-general", "attorney-general"
    ]

    # Find sentences that mention a government role
    sentences = text.split(". ")
    candidate_sources = []

    for sentence in sentences:
        sentence_lower = sentence.lower()
        for role in role_keywords:
            if role in sentence_lower:
                candidate_sources.append((sentence, role))
                break

    if not candidate_sources:
        return ""

    # Take the first candidate and try to find a person name inside it
    for sentence, role in candidate_sources:
        # Look for a detected person in this sentence
        for person in entities.get("people", []):
            if person in sentence:
                # Try to find the role title near the person
                role_start = sentence.lower().find(role)
                return f"{person}, {role.title()}"

    # If no person matched, return the first role keyword found
    first_sentence, first_role = candidate_sources[0]
    return f"Source quoted: {first_role.title()} (unnamed)"

    return ""


def detect_page_number(source, url):
    """
    Web articles don't have page numbers. Return 'Online' for web sources.
    For print sources, return the page number if we knew it.
    """
    if source and "Online" in source:
        return "Online"
    return "Online"  # Default for all web sources

def analyze_story(story):
    """Enrich one story with sentiment, summary, entities."""
    text = story.get("body", "") or story.get("headline", "")

    story["sentiment"] = classify_sentiment(text)
    story["ai_summary"] = summarize(text)
    story["entities"] = extract_entities(text)

    # NEW: extract government source
    story["government_source"] = extract_government_source(text, story["entities"])

    # NEW: set page number (Online for web sources)
    story["page"] = detect_page_number(story.get("source", ""), story.get("url", ""))

    return story


def analyze_all(input_file="data/raw/stories.json",
                output_file="data/processed/analyzed.json"):
    """Analyze all stories."""
    print(f"Reading {input_file}...")
    with open(input_file, "r", encoding="utf-8-sig") as f:
        stories = json.load(f)

    print(f"Analyzing {len(stories)} stories...\n")

    analyzed = []
    for i, story in enumerate(stories, 1):
        print(f"  [{i}/{len(stories)}] {story['headline'][:60]}...")
        analyzed.append(analyze_story(story))

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8-sig") as f:
        json.dump(analyzed, f, indent=2, ensure_ascii=False)

    # Summary
    counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for s in analyzed:
        counts[s["sentiment"]] += 1

    print(f"\n[OK] Saved {len(analyzed)} analyzed stories → {output_file}")
    print(f"\nSentiment breakdown:")
    print(f"  Positive: {counts['Positive']}")
    print(f"  Neutral:  {counts['Neutral']}")
    print(f"  Negative: {counts['Negative']}")

    # Show sample
    print(f"\nSample analysis:")
    for s in analyzed[:2]:
        print(f"\n  Headline:  {s['headline']}")
        print(f"  Sentiment: {s['sentiment']}")
        print(f"  Summary:   {s['ai_summary'][:150]}...")
        print(f"  People:    {s['entities']['people'][:5]}")
        print(f"  Orgs:      {s['entities']['organizations'][:5]}")


if __name__ == "__main__":
    analyze_all()