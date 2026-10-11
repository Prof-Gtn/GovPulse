"""
Quick check: how many stories have full body text?
"""
import json

with open("data/raw/stories.json", encoding="utf-8-sig") as f:
    stories = json.load(f)

print(f"Total stories: {len(stories)}")
print()

# Count by source
from collections import Counter
sources = Counter(s["source"] for s in stories)
print("By source:")
for src, count in sources.items():
    print(f"  {src}: {count}")
print()

# Find stories with empty or short bodies
short = [s for s in stories if len(s.get("body", "")) < 100]
print(f"Stories with short/empty body: {len(short)}")

if short:
    print()
    print("Short-body stories:")
    for s in short:
        print(f"  [{s['source']}] {s['headline'][:60]}")
        print(f"      Body length: {len(s.get('body', ''))}")
        print(f"      URL: {s['url']}")