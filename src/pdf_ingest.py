"""
GovPulse — PDF Newspaper Ingest
Extracts text from uploaded newspaper PDFs and adds them as stories.
"""

import sys
import os
import json
import io
from datetime import datetime
import pdfplumber

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def ingest_pdf(pdf_path, source_name="Uploaded Newspaper"):
    stories = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if not lines:
                continue

            headline = lines[0][:140]
            body = " ".join(lines[1:]) if len(lines) > 1 else text

            stories.append({
                "source": source_name,
                "headline": headline,
                "url": f"upload://{os.path.basename(pdf_path)}#page{i}",
                "scraped_at": datetime.now().isoformat(),
                "body": body,
                "page": str(i),
            })

    raw_path = "data/raw/stories.json"
    existing = []
    if os.path.exists(raw_path):
        with open(raw_path, encoding="utf-8-sig") as f:
            existing = json.load(f)

    seen = {s.get("url") for s in existing}
    added = [s for s in stories if s["url"] not in seen]
    existing.extend(added)

    os.makedirs(os.path.dirname(raw_path), exist_ok=True)
    with open(raw_path, "w", encoding="utf-8-sig") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"[OK] Ingested {len(added)} pages from {pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python src/pdf_ingest.py <pdf_path> <source_name>")
        sys.exit(1)
    ingest_pdf(sys.argv[1], sys.argv[2])