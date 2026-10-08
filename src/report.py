"""
GovPulse — Daily Brief Generator
Generates the MICT daily brief in Excel format.
"""

import json
import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# Colour codes matching MICT's convention
SENTIMENT_COLORS = {
    "Positive": "C6EFCE",  # green background
    "Neutral":  "FFFFFF",  # white
    "Negative": "FFC7CE",  # red background
}

SENTIMENT_TEXT_COLORS = {
    "Positive": "006100",
    "Neutral":  "000000",
    "Negative": "9C0006",
}


def load_stories(input_file="data/processed/mapped.json"):
    """Load the mapped stories."""
    with open(input_file, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def format_oma(oma_list):
    """Turn ['Ministry X', 'Ministry Y'] into 'Ministry X; Ministry Y'."""
    if not oma_list:
        return "Unmapped"
    if oma_list == ["Unmapped"]:
        return "Unmapped"
    return "; ".join(oma_list)


def build_workbook(stories):
    """Build the Excel workbook in MICT's format."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Brief"

    # ---------- Title block ----------
    ws.merge_cells("A1:H1")
    title_cell = ws["A1"]
    title_cell.value = "GOVERNMENT MEDIA MONITORING AND ANALYSIS DAILY BRIEF"
    title_cell.font = Font(bold=True, size=14, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor="1F3864")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:H2")
    date_cell = ws["A2"]
    date_cell.value = f"DATE: {datetime.now().strftime('%A, %d %B %Y').upper()}"
    date_cell.font = Font(bold=True, size=11)
    date_cell.alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 20

    # ---------- Header row ----------
    headers = [
        "Newspaper",
        "Page",
        "Headline",
        "Brief Summary",
        "Government Source Quoted",
        "Sentiment",
        "O/M/A",
        "Comment / Recommendation",
    ]

    header_row = 4
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_num, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

    # ---------- Data rows ----------
    row = header_row + 1
    for story in stories:
        sentiment = story.get("sentiment", "Neutral")
        bg_color = SENTIMENT_COLORS.get(sentiment, "FFFFFF")
        text_color = SENTIMENT_TEXT_COLORS.get(sentiment, "000000")

        values = [
            story.get("source", ""),
            story.get("page", "Online"),
            story.get("headline", ""),
            story.get("ai_summary", ""),
            story.get("government_source", "") or "None",
            sentiment,
            format_oma(story.get("oma", [])),
            story.get("comment", "None"),
        ]

        for col_num, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=col_num, value=value)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            # Apply sentiment colour to the sentiment column
            if col_num == 6:
                cell.fill = PatternFill("solid", fgColor=bg_color)
                cell.font = Font(bold=True, color=text_color)

        row += 1

    # ---------- Column widths ----------
    widths = {
        "A": 15,  # Newspaper
        "B": 8,   # Page
        "C": 35,  # Headline
        "D": 50,  # Summary
        "E": 30,  # Source quoted
        "F": 12,  # Sentiment
        "G": 35,  # O/M/A
        "H": 25,  # Comment
    }
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    # ---------- Footer ----------
    footer_row = row + 1
    ws.merge_cells(f"A{footer_row}:H{footer_row}")
    footer = ws.cell(row=footer_row, column=1)
    footer.value = (
        "Kindly review the communication recommendations above and inform "
        "the MICT of any responses or actions taken by the institution to "
        "counter negative coverage."
    )
    footer.font = Font(italic=True, size=10)
    footer.alignment = Alignment(wrap_text=True)

    footer_row += 2
    ws.merge_cells(f"A{footer_row}:H{footer_row}")
    notes = ws.cell(row=footer_row, column=1)
    notes.value = (
        "NOTES:  "
        "Highlight in red: Story is negative  |  "
        "Highlight in green: Story is positive  |  "
        "Highlight in black: Story is neutral"
    )
    notes.font = Font(italic=True, size=10)

    return wb


def generate_report(input_file="data/processed/mapped.json",
                    output_file="data/processed/daily_brief.xlsx"):
    """Generate the daily brief."""
    print(f"Loading stories from {input_file}...")
    stories = load_stories(input_file)
    print(f"Generating daily brief for {len(stories)} stories...")

    wb = build_workbook(stories)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    wb.save(output_file)

    print(f"\n[OK] Daily brief saved → {output_file}")

    # Summary
    counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for s in stories:
        counts[s.get("sentiment", "Neutral")] += 1

    print(f"\nSentiment breakdown:")
    print(f"  Positive: {counts['Positive']}")
    print(f"  Neutral:  {counts['Neutral']}")
    print(f"  Negative: {counts['Negative']}")

    mapped = sum(1 for s in stories if s.get("oma") and s["oma"] != ["Unmapped"])
    print(f"\nMapped stories: {mapped}/{len(stories)}")


if __name__ == "__main__":
    generate_report()