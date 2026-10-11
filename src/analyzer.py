"""
GovPulse — Analyzer
Adds sentiment, summary, and entity detection to each story.
"""

import json
import os
import re
import sys
import io
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import spacy


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


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

    # Wider neutral band for news content.
    # 0.6 is stricter than VADER's default 0.05, which helps avoid
    # misclassifying factual political stories as positive/negative.
    if compound >= 0.6:
        return "Positive"
    elif compound <= -0.6:
        return "Negative"
    else:
        return "Neutral"


def sentiment_confidence(text):
    """Return a 0.0-1.0 confidence score based on how strong the sentiment is."""
    if not text:
        return 0.0
    scores = sentiment_analyzer.polarity_scores(text)
    return round(abs(scores["compound"]), 2)


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

        result = result.lstrip(",. ;:'\"")
        result = result.strip()

        while result and not result[0].isupper():
            result = result[1:].lstrip()

        if result:
            result = result[0].upper() + result[1:]

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

    doc = nlp(text[:100000])

    entities = {"organizations": [], "people": [], "locations": []}

    for ent in doc.ents:
        if ent.label_ == "ORG":
            entities["organizations"].append(ent.text)
        elif ent.label_ == "PERSON":
            entities["people"].append(ent.text)
        elif ent.label_ in ("GPE", "LOC"):
            entities["locations"].append(ent.text)

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
    Extract the government source quoted — ONLY when a strong
    attribution pattern is present.

    Returns 'Name, Role' or '' if uncertain.
    """
    if not text:
        return ""

    people = entities.get("people", []) if entities else []
    if not people:
        return ""

    role_keywords = [
        "minister", "deputy minister", "president", "vice president",
        "prime minister", "executive director", "spokesperson",
        "spokesman", "spokeswoman", "chief executive",
        "governor", "mayor", "chairperson", "permanent secretary",
        "commissioner", "ombudsman", "auditor-general", "attorney-general",
    ]

    # Only the first 5 detected people
    for person in people[:5]:
        # Find where this person is mentioned
        idx = text.find(person)
        if idx == -1:
            continue

        # Examine a window around the mention
        window = text[max(0, idx - 120): idx + 260]
        window_lower = window.lower()

        # Require a government-role keyword near the name
        matched_role = None
        for role in role_keywords:
            if role in window_lower:
                matched_role = role
                break

        if not matched_role:
            continue

        # Require an attribution pattern
        attribution_patterns = [
            r"said\s+" + re.escape(person),
            re.escape(person) + r"\s+said",
            r"according to\s+" + re.escape(person),
            re.escape(person) + r"\s+told",
            re.escape(person) + r"\s+explained",
            re.escape(person) + r"\s+noted",
            re.escape(person) + r",\s+(?:the\s+)?(?:minister|president|director|spokesperson|governor|mayor|commissioner|chief executive|deputy minister|executive director)",
        ]

        if any(re.search(p, window, re.IGNORECASE) for p in attribution_patterns):
            # Use clean title case
            return f"{person}, {matched_role.title()}"

    return ""


def detect_page_number(source, url):
    """Web articles don't have page numbers."""
    return "Online"


def analyze_story(story):
    """Enrich one story with sentiment, summary, entities, confidence, source."""
    text = story.get("body", "") or story.get("headline", "")

    story["sentiment"] = classify_sentiment(text)
    story["sentiment_confidence"] = sentiment_confidence(text)
    story["ai_summary"] = summarize(text)
    story["entities"] = extract_entities(text)
    story["government_source"] = extract_government_source(text, story["entities"])
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

    counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for s in analyzed:
        counts[s["sentiment"]] += 1

    print(f"\n[OK] Saved {len(analyzed)} analyzed stories -> {output_file}")
    print(f"\nSentiment breakdown:")
    print(f"  Positive: {counts['Positive']}")
    print(f"  Neutral:  {counts['Neutral']}")
    print(f"  Negative: {counts['Negative']}")

    print(f"\nSample analysis:")
    for s in analyzed[:2]:
        print(f"\n  Headline:  {s['headline']}")
        print(f"  Sentiment: {s['sentiment']} (confidence: {s['sentiment_confidence']})")
        print(f"  Summary:   {s['ai_summary'][:150]}...")
        print(f"  Source:    {s['government_source']}")
        print(f"  People:    {s['entities']['people'][:5]}")
        print(f"  Orgs:      {s['entities']['organizations'][:5]}")


if __name__ == "__main__":
    analyze_all()