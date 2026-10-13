"""
GovPulse — Daily Brief Generator
Generates the MICT daily brief in Excel and PDF format.
Only includes stories scraped on the brief's date.
"""

import json
import os
import sys
import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


SENTIMENT_COLORS = {
    "Positive": "C6EFCE",
    "Neutral":  "FFFFFF",
    "Negative": "FFC7CE",
}

SENTIMENT_TEXT_COLORS = {
    "Positive": "006100",
    "Neutral":  "000000",
    "Negative": "9C0006",
}


def load_stories(input_file="data/processed/mapped.json",
                 approvals_file="data/processed/approvals.json",
                 exclude_unmapped=True):
    """
    Load mapped stories, filter to today's scrape date only, and enrich
    each with its approved response.

    Filtering logic:
      1. Keep only stories whose scraped_at date == today.
      2. If today has no stories (scraper not yet run), fall back to the
         most recent date with data — the brief is never empty.
      3. Optionally exclude unmapped stories.
      4. Approvals only appear if they were made on or after the brief date.
    """
    with open(input_file, "r", encoding="utf-8-sig") as f:
        all_stories = json.load(f)

    # Determine the brief date and filter stories
    today = datetime.now().date().isoformat()

    stories_today = [
        s for s in all_stories
        if (s.get("scraped_at") or "")[:10] == today
    ]

    if stories_today:
        brief_date = today
    else:
        # Fallback: use the most recent date that has stories
        dates = sorted(
            set(
                (s.get("scraped_at") or "")[:10]
                for s in all_stories
                if s.get("scraped_at")
            ),
            reverse=True,
        )
        if dates:
            brief_date = dates[0]
            stories_today = [
                s for s in all_stories
                if (s.get("scraped_at") or "")[:10] == brief_date
            ]
            print(f"[WARN] No stories scraped today ({today}). "
                  f"Falling back to {brief_date}")
        else:
            brief_date = today
            stories_today = all_stories

    print(f"Brief date: {brief_date} — {len(stories_today)} stories "
          f"(out of {len(all_stories)} total)")

    # Exclude unmapped stories from the brief
    if exclude_unmapped:
        stories_today = [
            s for s in stories_today
            if s.get("oma") and s["oma"] != ["Unmapped"]
        ]
        print(f"After excluding unmapped: {len(stories_today)} stories")

    # Load approvals
    approvals = {}
    if os.path.exists(approvals_file):
        try:
            with open(approvals_file, "r", encoding="utf-8-sig") as f:
                approvals = json.load(f)
        except Exception as e:
            print(f"[WARN] Could not load approvals: {e}")

    # Attach approval markers ONLY to stories in today's brief,
    # and ONLY if the approval was made on/after the brief date.
    for story in stories_today:
        headline = story.get("headline", "")
        if headline in approvals:
            approval = approvals[headline]
            approved_at = (approval.get("approved_at") or "")[:10]
            ministry = approval.get("ministry", "")
            final_text = approval.get("final_text", "")

            if approved_at and approved_at >= brief_date:
                story["comment"] = (
                    f"✓ {approved_at} — {ministry}:\n\"{final_text}\""
                )
            else:
                story["comment"] = "None"
        else:
            story["comment"] = story.get("comment", "None") or "None"

    return stories_today, brief_date


def format_oma(oma_list):
    if not oma_list or oma_list == ["Unmapped"]:
        return "Unmapped"
    return "; ".join(oma_list)


# ------------------------------------------------------------------
# EXCEL
# ------------------------------------------------------------------
def build_workbook(stories, brief_date):
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Brief"

    # Title block
    ws.merge_cells("A1:H1")
    title_cell = ws["A1"]
    title_cell.value = "GOVERNMENT MEDIA MONITORING AND ANALYSIS DAILY BRIEF"
    title_cell.font = Font(bold=True, size=14, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor="1F3864")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:H2")
    date_cell = ws["A2"]
    formatted_date = datetime.fromisoformat(brief_date).strftime("%A, %d %B %Y").upper()
    date_cell.value = f"DATE: {formatted_date}"
    date_cell.font = Font(bold=True, size=11)
    date_cell.alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 20

    # Header row
    headers = [
        "Newspaper", "Page", "Headline", "Brief Summary",
        "Government Source Quoted", "Sentiment", "O/M/A",
        "Comment / Recommendation",
    ]

    header_row = 4
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_num, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin"),
        )

    ws.row_dimensions[header_row].height = 30
    ws.freeze_panes = f"A{header_row + 1}"

    # Data rows
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
                left=Side(style="thin"), right=Side(style="thin"),
                top=Side(style="thin"), bottom=Side(style="thin"),
            )

            if col_num == 6:
                cell.fill = PatternFill("solid", fgColor=bg_color)
                cell.font = Font(bold=True, color=text_color)

        summary_text = str(story.get("ai_summary", "") or "")
        estimated_lines = max(2, len(summary_text) // 55)
        ws.row_dimensions[row].height = 15 * estimated_lines

        row += 1

    widths = {
        "A": 14, "B": 8, "C": 32, "D": 60,
        "E": 28, "F": 11, "G": 32, "H": 22,
    }
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    # Footer
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
        "NOTES:  Highlight in red: Story is negative  |  "
        "Highlight in green: Story is positive  |  "
        "Highlight in black: Story is neutral"
    )
    notes.font = Font(italic=True, size=10)

    footer_row += 2
    ws.merge_cells(f"A{footer_row}:H{footer_row}")
    credit = ws.cell(row=footer_row, column=1)
    credit.value = (
        f"Generated by GovPulse — Government Media Intelligence Platform "
        f"| {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    credit.font = Font(italic=True, size=9, color="888888")
    credit.alignment = Alignment(horizontal="right")

    return wb


def generate_report(input_file="data/processed/mapped.json",
                    output_file="data/processed/daily_brief.xlsx"):
    print(f"Loading stories from {input_file}...")
    stories, brief_date = load_stories(input_file)
    print(f"Generating daily brief for {len(stories)} stories...")

    wb = build_workbook(stories, brief_date)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    wb.save(output_file)

    print(f"\n[OK] Daily brief saved -> {output_file}")

    counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for s in stories:
        counts[s.get("sentiment", "Neutral")] += 1

    print(f"\nSentiment breakdown:")
    print(f"  Positive: {counts['Positive']}")
    print(f"  Neutral:  {counts['Neutral']}")
    print(f"  Negative: {counts['Negative']}")

    mapped = sum(1 for s in stories if s.get("oma") and s["oma"] != ["Unmapped"])
    print(f"\nMapped stories: {mapped}/{len(stories)}")


# ------------------------------------------------------------------
# PDF
# ------------------------------------------------------------------
def generate_pdf(input_file="data/processed/mapped.json",
                 output_file="data/processed/daily_brief.pdf"):
    """Generate the daily brief as a PDF."""
    print(f"Loading stories from {input_file}...")
    stories, brief_date = load_stories(input_file)
    print(f"Generating PDF brief for {len(stories)} stories...")

    doc = SimpleDocTemplate(
        output_file,
        pagesize=landscape(A4),
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title="Government Media Monitoring and Analysis Daily Brief",
        author="GovPulse — Team Binary",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "GpTitle", parent=styles["Heading1"], fontSize=14,
        textColor=colors.HexColor("#FFFFFF"), alignment=TA_CENTER, spaceAfter=0,
    )
    date_style = ParagraphStyle(
        "GpDate", parent=styles["Normal"], fontSize=11,
        alignment=TA_CENTER, spaceAfter=8,
    )
    header_style = ParagraphStyle(
        "GpHeader", parent=styles["Normal"], fontSize=8,
        textColor=colors.HexColor("#FFFFFF"), alignment=TA_CENTER, leading=10,
    )
    cell_style = ParagraphStyle(
        "GpCell", parent=styles["Normal"], fontSize=7.5, leading=9,
    )
    footer_style = ParagraphStyle(
        "GpFooter", parent=styles["Normal"], fontSize=9,
        alignment=TA_LEFT, leading=11,
    )
    notes_style = ParagraphStyle(
        "GpNotes", parent=styles["Normal"], fontSize=8,
        alignment=TA_LEFT, leading=10, textColor=colors.HexColor("#555555"),
    )

    elements = []

    # Title bar
    title_table = Table(
        [[Paragraph("GOVERNMENT MEDIA MONITORING AND ANALYSIS DAILY BRIEF", title_style)]],
        colWidths=[doc.width],
    )
    title_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1F3864")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(title_table)

    formatted_date = datetime.fromisoformat(brief_date).strftime("%A, %d %B %Y").upper()
    date_text = f"DATE: {formatted_date}"
    elements.append(Paragraph(date_text, date_style))
    elements.append(Spacer(1, 0.3 * cm))

    # Data table
    headers = [
        "Newspaper", "Page", "Headline", "Brief Summary",
        "Government Source Quoted", "Sentiment", "O/M/A", "Comment"
    ]
    header_row = [Paragraph(h, header_style) for h in headers]
    rows = [header_row]

    for story in stories:
        sentiment = story.get("sentiment", "Neutral")
        row = [
            Paragraph(story.get("source", ""), cell_style),
            Paragraph(story.get("page", "Online"), cell_style),
            Paragraph(story.get("headline", ""), cell_style),
            Paragraph(story.get("ai_summary", ""), cell_style),
            Paragraph(story.get("government_source", "None") or "None", cell_style),
            Paragraph(sentiment, cell_style),
            Paragraph(format_oma(story.get("oma", [])), cell_style),
            Paragraph(story.get("comment", "None") or "None", cell_style),
        ]
        rows.append(row)

    col_widths = [
        2.0 * cm,  # Newspaper
        1.2 * cm,  # Page
        4.5 * cm,  # Headline
        6.0 * cm,  # Summary
        3.5 * cm,  # Source
        1.8 * cm,  # Sentiment
        4.0 * cm,  # O/M/A
        4.5 * cm,  # Comment
    ]

    table = Table(rows, colWidths=col_widths, repeatRows=1)

    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0B7C3")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])

    # Colour-code sentiment cells (column 5)
    for i, story in enumerate(stories, start=1):
        sentiment = story.get("sentiment", "Neutral")
        if sentiment == "Positive":
            style.add("BACKGROUND", (5, i), (5, i), colors.HexColor("#C6EFCE"))
            style.add("TEXTCOLOR", (5, i), (5, i), colors.HexColor("#006100"))
        elif sentiment == "Negative":
            style.add("BACKGROUND", (5, i), (5, i), colors.HexColor("#FFC7CE"))
            style.add("TEXTCOLOR", (5, i), (5, i), colors.HexColor("#9C0006"))
        else:
            style.add("BACKGROUND", (5, i), (5, i), colors.HexColor("#F3F4F6"))

    table.setStyle(style)
    elements.append(table)
    elements.append(Spacer(1, 0.5 * cm))

    # Footer
    footer_text = (
        "Kindly review the communication recommendations above and inform "
        "the MICT of any responses or actions taken by the institution to "
        "counter negative coverage."
    )
    elements.append(Paragraph(footer_text, footer_style))
    elements.append(Spacer(1, 0.3 * cm))

    notes_text = (
        "<b>NOTES:</b> Highlight in red: Story is negative | "
        "Highlight in green: Story is positive | "
        "Highlight in black: Story is neutral"
    )
    elements.append(Paragraph(notes_text, notes_style))
    elements.append(Spacer(1, 0.3 * cm))

    credit_text = (
        f"Generated by GovPulse — Government Media Intelligence Platform "
        f"| {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    elements.append(Paragraph(credit_text, notes_style))

    doc.build(elements)

    print(f"\n[OK] PDF daily brief saved -> {output_file}")


def generate_all(input_file="data/processed/mapped.json"):
    """Generate both Excel and PDF daily briefs."""
    generate_report(input_file, "data/processed/daily_brief.xlsx")
    generate_pdf(input_file, "data/processed/daily_brief.pdf")


if __name__ == "__main__":
    generate_all()