"""
GovPulse — Analyzer
Adds sentiment, summary, and entity detection to each story.
Optimized: batched spaCy, skips already-analyzed stories.
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


# Make sure src/ is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ------------------------------------------------------------
# MODEL LOADING (once per process)
# ------------------------------------------------------------
print("Loading models...")
sentiment_analyzer = SentimentIntensityAnalyzer()
nlp = spacy.load("en_core_web_sm")
print("Models loaded.\n")


# ------------------------------------------------------------
# SENTIMENT
# ------------------------------------------------------------
def classify_sentiment(text):
    """Return Positive, Neutral, or Negative."""
    if not text:
        return "Neutral"

    scores = sentiment_analyzer.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.5:
        return "Positive"
    elif compound <= -0.5:
        return "Negative"
    else:
        return "Neutral"


def sentiment_confidence(text):
    """Return a 0.0-1.0 confidence score."""
    if not text:
        return 0.0
    scores = sentiment_analyzer.polarity_scores(text)
    return round(abs(scores["compound"]), 2)


# ------------------------------------------------------------
# SUMMARIZATION
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# ENTITY EXTRACTION (from a pre-computed doc)
# ------------------------------------------------------------
def _extract_entities_from_doc(doc):
    """Extract entities from an already-processed spaCy doc."""
    entities = {"organizations": [], "people": [], "locations": []}

    for ent in doc.ents:
        if ent.label_ == "ORG":
            entities["organizations"].append(ent.text)
        elif ent.label_ == "PERSON":
            entities["people"].append(ent.text)
        elif ent.label_ in ("GPE", "LOC"):
            entities["locations"].append(ent.text)

    # Deduplicate
    for key in entities:
        seen = set()
        unique = []
        for item in entities[key]:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        entities[key] = unique

    return entities


# ------------------------------------------------------------
# GOVERNMENT SOURCE
# ------------------------------------------------------------
def extract_government_source(text, entities):
    """Extract government source with strict attribution patterns."""
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

    for person in people[:5]:
        idx = text.find(person)
        if idx == -1:
            continue

        window = text[max(0, idx - 120): idx + 260]
        window_lower = window.lower()

        matched_role = None
        for role in role_keywords:
            if role in window_lower:
                matched_role = role
                break

        if not matched_role:
            continue

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
            return f"{person}, {matched_role.title()}"

    return ""


# ------------------------------------------------------------
# PAGE NUMBER
# ------------------------------------------------------------
def detect_page_number(source, url):
    """Web articles don't have page numbers."""
    return "Online"


# ------------------------------------------------------------
# MAIN ANALYSIS
# ------------------------------------------------------------
def analyze_all(input_file="data/raw/stories.json",
                output_file="data/processed/analyzed.json"):
    """Analyze all stories. Skips stories already in the DB."""

    # ---- Load stories ----
    print(f"Reading {input_file}...")
    with open(input_file, "r", encoding="utf-8-sig") as f:
        stories = json.load(f)

    print(f"Loaded {len(stories)} stories from file.")

    # ---- Load existing analyzed results (for merge) ----
    old_analyzed = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8-sig") as f:
                old_analyzed = json.load(f)
        except Exception:
            old_analyzed = []

    old_by_headline = {s["headline"]: s for s in old_analyzed if s.get("headline")}
    print(f"Found {len(old_by_headline)} previously analyzed stories.")

    # ---- Determine which stories need analysis ----
    try:
        from src import db
        existing_db = {s["headline"] for s in db.get_stories()}
    except Exception as e:
        print(f"[WARN] Could not check DB: {e}")
        existing_db = set()

    def _has_summary(story):
        s = story.get("ai_summary")
        return bool(s and str(s).strip())

    # Only skip stories that already have a summary — either in the incoming
    # batch, in previously analyzed output, or in the DB.
    new_stories = []
    for s in stories:
        h = s.get("headline")
        if not h:
            continue

        # If the story lacks a summary in the batch it came in with,
        # we must analyze it.
        if not _has_summary(s):
            new_stories.append(s)
            continue

        # If old_analyzed has a summary for this headline, keep it.
        old = old_by_headline.get(h)
        if old and _has_summary(old):
            continue

        # If the DB has a summary, keep it.
        if h in existing_db:
            try:
                db_story = db.get_story(h)
                if db_story and _has_summary(db_story):
                    continue
            except Exception:
                pass

        # Otherwise, this story needs (re-)analysis.
        new_stories.append(s)

    print(f"New stories requiring analysis: {len(new_stories)}")

    # If nothing new, just re-save the merged result
    if not new_stories:
        print("Nothing new to analyze.")
        merged = list(old_by_headline.values())
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8-sig") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        print(f"[OK] Saved {len(merged)} analyzed stories -> {output_file}")
        return

    # ---- Batch spaCy processing (optimization #2) ----
    print(f"\nBatched spaCy processing for {len(new_stories)} new stories...")
    texts = [
        (s.get("body") or s.get("headline") or "")[:100000]
        for s in new_stories
    ]
    docs = list(nlp.pipe(texts, batch_size=16))
    print("Batch processing complete.\n")

    # ---- Analyze each story ----
    analyzed_new = []
    for i, (story, doc) in enumerate(zip(new_stories, docs), 1):
        print(f"  [{i}/{len(new_stories)}] {story['headline'][:60]}...")

        text = story.get("body", "") or story.get("headline", "")

        story["sentiment"] = classify_sentiment(text)
        story["sentiment_confidence"] = sentiment_confidence(text)
        story["ai_summary"] = summarize(text)
        story["entities"] = _extract_entities_from_doc(doc)
        story["government_source"] = extract_government_source(text, story["entities"])
        story["page"] = detect_page_number(story.get("source", ""), story.get("url", ""))

        analyzed_new.append(story)

    # ---- Merge new + existing ----
    merged_by_headline = dict(old_by_headline)
    for s in analyzed_new:
        merged_by_headline[s["headline"]] = s

    # Also include any DB stories that aren't in either set (safety)
    for s in stories:
        if s["headline"] not in merged_by_headline:
            merged_by_headline[s["headline"]] = s

    merged = list(merged_by_headline.values())

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8-sig") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    # ---- Summary ----
    counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for s in merged:
        counts[s.get("sentiment", "Neutral")] = counts.get(s.get("sentiment", "Neutral"), 0) + 1

    print(f"\n[OK] Saved {len(merged)} analyzed stories -> {output_file}")
    print(f"     ({len(analyzed_new)} newly analyzed, {len(merged) - len(analyzed_new)} carried over)")
    print(f"\nSentiment breakdown:")
    print(f"  Positive: {counts['Positive']}")
    print(f"  Neutral:  {counts['Neutral']}")
    print(f"  Negative: {counts['Negative']}")


if __name__ == "__main__":
    analyze_all()