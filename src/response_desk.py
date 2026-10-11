"""
GovPulse — Response Desk
Drafts government responses to negative coverage using historical precedent.
"""

import json
import os
import re
import time
import sys
import io
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "qwen/qwen3.8-27b"
STATEMENTS_DIR = "sample_statements"


def load_statements_for_ministry(ministry_name):
    """Find all sample statements that match the given ministry."""
    if not os.path.isdir(STATEMENTS_DIR):
        return []

    matches = []
    ministry_lower = ministry_name.lower()

    keywords = []
    if "home affairs" in ministry_lower:
        keywords = ["home_affairs"]
    elif "health" in ministry_lower:
        keywords = ["health"]
    elif "agriculture" in ministry_lower:
        keywords = ["agriculture"]
    elif "finance" in ministry_lower:
        keywords = ["finance"]
    elif "urban" in ministry_lower or "windhoek" in ministry_lower:
        keywords = ["urban", "windhoek"]
    elif "works" in ministry_lower or "transport" in ministry_lower:
        keywords = ["works", "transport"]
    elif "mines" in ministry_lower or "energy" in ministry_lower:
        keywords = ["mines", "energy"]
    elif "education" in ministry_lower:
        keywords = ["education"]
    elif "environment" in ministry_lower:
        keywords = ["environment"]
    elif "information" in ministry_lower or "communication" in ministry_lower:
        keywords = ["ict", "mict", "communication"]
    elif "parliament" in ministry_lower:
        keywords = ["parliament"]

    for filename in os.listdir(STATEMENTS_DIR):
        if not filename.endswith(".txt"):
            continue
        for kw in keywords:
            if kw in filename.lower():
                with open(os.path.join(STATEMENTS_DIR, filename),
                          "r", encoding="utf-8") as f:
                    matches.append((filename, f.read()))
                break

    return matches


def build_prompt(story, precedents):
    """Build the prompt for the LLM."""
    precedents_text = "\n\n---\n\n".join(
        f"[Source: {name}]\n{content}" for name, content in precedents
    ) if precedents else "(No prior statements available for this ministry.)"

    prompt = f"""You are a Communication Officer for the Namibian government.

A negative news story has been published about a ministry. You need to draft a brief official response statement for the ministry.

NEGATIVE STORY:
- Headline: {story.get('headline', '')}
- Summary: {story.get('ai_summary', '')}
- Institution: {", ".join(story.get('oma', []))}

PRIOR STATEMENTS FROM THIS MINISTRY:
{precedents_text}

TASK:
Write a very short official response (2-3 sentences, no more than 50 words) 
in the tone and style of the prior statements. The response should:
1. Acknowledge the issue
2. State what the ministry is doing
3. Reassure the public

Do NOT invent specific facts, dates, or names that aren't in the source material.

Return ONLY the statement text. No preamble, no explanation. Maximum 50 words."""
    return prompt


def clean_draft(draft):
    """Fix common LLM spacing and punctuation artifacts."""
    if not draft:
        return draft
    draft = re.sub(r"([a-z])([A-Z])", r"\1 \2", draft)
    draft = re.sub(r"\s+", " ", draft)
    draft = re.sub(r"\s([.,;:!?])", r"\1", draft)
    draft = re.sub(r"([.!?])([A-Z])", r"\1 \2", draft)
    return draft.strip()


def draft_response(story):
    """Generate a draft response for a negative story."""
    oma_list = story.get("oma", [])
    if not oma_list or oma_list == ["Unmapped"]:
        return {
            "draft": None,
            "status": "skipped",
            "reason": "Story has no mapped institution"
        }

    ministry = oma_list[0]
    precedents = load_statements_for_ministry(ministry)
    prompt = build_prompt(story, precedents)

    last_error = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=150,
            )
            draft = (response.choices[0].message.content or "").strip()

            if draft:
                draft = clean_draft(draft)
                return {
                    "draft": draft,
                    "status": "ok",
                    "ministry": ministry,
                    "precedents_used": [name for name, _ in precedents],
                    "precedents": [
                        {"filename": name, "content": content}
                        for name, content in precedents
                    ],
                    "attempts": attempt + 1,
                    "generated_at": datetime.now().isoformat(),
                }

            print(f"      [RETRY {attempt + 1}/3] Empty response, retrying...")
            time.sleep(2)

        except Exception as e:
            last_error = str(e)
            print(f"      [RETRY {attempt + 1}/3] {e}")
            time.sleep(2)

    return {
        "draft": None,
        "status": "failed",
        "reason": last_error or "Empty response after 3 attempts",
        "ministry": ministry,
        "precedents_used": [name for name, _ in precedents],
        "precedents": [
            {"filename": name, "content": content}
            for name, content in precedents
        ],
    }


def process_negative_stories(input_file="data/processed/mapped.json",
                             output_file="data/processed/responses.json"):
    """Generate draft responses for all negative stories."""
    print(f"Reading {input_file}...")
    with open(input_file, "r", encoding="utf-8-sig") as f:
        stories = json.load(f)

    negatives = [s for s in stories if s.get("sentiment") == "Negative"]
    print(f"Found {len(negatives)} negative stories.\n")

    results = []
    for i, story in enumerate(negatives, 1):
        print(f"  [{i}/{len(negatives)}] {story['headline'][:60]}...")
        response = draft_response(story)

        results.append({
            "headline": story["headline"],
            "oma": story.get("oma", []),
            "sentiment": story["sentiment"],
            "response": response,
        })

        if response["status"] == "ok":
            print(f"      [OK] Draft generated ({len(response['draft'])} chars)")
        else:
            print(f"      [SKIP] {response.get('reason', 'unknown')}")

        time.sleep(1.5)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8-sig") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    success = sum(1 for r in results if r["response"]["status"] == "ok")
    print(f"\n[OK] Saved {len(results)} response drafts -> {output_file}")
    print(f"     Successful drafts: {success}/{len(results)}")


if __name__ == "__main__":
    process_negative_stories()