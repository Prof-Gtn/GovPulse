"""
GovPulse — Daily Brief Generator
=================================

Generates the MICT "Government Media Monitoring and Analysis Daily Brief"
in Excel (.xlsx) and PDF (.pdf) format.
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import shutil
import sys
from datetime import date, datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

# Excel
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# PDF
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate, Frame, NextPageTemplate, PageTemplate,
    Paragraph, Table, TableStyle,
)


# ======================================================================
# STDIO ENCODING
# ======================================================================
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# ======================================================================
# PATHS
# ======================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BRIEFS_DIR = os.path.join(PROJECT_ROOT, "data", "processed", "briefs")


# ======================================================================
# COLOURS (Excel — sentiment row text)
# ======================================================================
XLSX_TEXT_COLOR = {
    "Positive": "00A650",
    "Neutral":  "000000",
    "Negative": "D3202F",
}
XLSX_BORDER_BLUE = "4472C4"
XLSX_HEADER_BLUE = "1F3864"


# ======================================================================
# COLOURS (PDF — manual brief palette)
# ======================================================================
BANNER_BLUE = colors.HexColor("#8FC4E6")
LETTER_FILL = colors.HexColor("#B4DAF2")
OUTLINE_NAVY = colors.HexColor("#1F3864")
DATE_BAR_BLUE = colors.HexColor("#4472C4")
TABLE_HEADER_BLUE = colors.HexColor("#1F3864")
GRID_BLUE = colors.HexColor("#4472C4")
TEXT_BLACK = colors.black
WHITE = colors.white

POSITIVE_TEXT = colors.HexColor("#00A650")
NEGATIVE_TEXT = colors.HexColor("#D3202F")
NEUTRAL_TEXT = colors.black


# ======================================================================
# PAGE GEOMETRY
# ======================================================================
PAGE_W, PAGE_H = landscape(A4)

COL_WIDTHS_CM = [2.0, 1.4, 4.3, 6.2, 4.0, 2.0, 4.0, 3.7]
COL_WIDTHS = [w * cm for w in COL_WIDTHS_CM]
CONTENT_W = sum(COL_WIDTHS)
MARGIN_X = (PAGE_W - CONTENT_W) / 2

BANNER_H = PAGE_H * 0.33
DATE_BAR_H = 26.0
SMALL_HEADER_H = 34.0
FOOTER_H = 90.0
FOOTER_BOTTOM = 14.0


# ======================================================================
# TYPOGRAPHY
# ======================================================================
FONT_BOLD = "Times-Bold"
FONT_BOLD_ITALIC = "Times-BoldItalic"
FONT_REGULAR = "Times-Roman"
FONT_ITALIC = "Times-Italic"

SIZE_GOVERNMENT = 54
SIZE_SUBTITLE = 24
SIZE_REPUBLIC = 11
SIZE_MINISTRY = 13
SIZE_TABLE_HEADER = 8.5
SIZE_TABLE_BODY = 8
SIZE_DATE_BAR = 14

CAP_HEIGHT = 0.70
OUTLINE_THICKNESS = 3.0
OUTLINE_STEP_DEG = 6
COAT_MAX_H = 78.0
COAT_TOP_GAP = 10.0
SUBTITLE_SIDE_MARGIN = 22.0


COLUMN_HEADERS = [
    "Newspaper",
    '<font size="7.5">Page<br/>Number</font>',
    "Headline",
    "Brief Summary",
    'Government source quoted<br/><font size="7">(official interviewed, media '
    "statement, report, event speech)</font>",
    "Sentiment",
    "O/M/A, Institution(s)",
    "Comment / Recommendation",
]

FOOTER_REVIEW_TEXT = (
    "Kindly review the communication recommendations above and inform the MICT "
    "of any responses or actions taken by the institution to counter negative "
    "coverage."
)

_MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
           "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
_DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


# ======================================================================
# TEXT HELPERS
# ======================================================================
def _clean(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\u2713", "Approved:").replace("\u2714", "Approved:")
    text = re.sub(r"[\u2000-\u200b\u202f\u205f\u3000]", " ", text)
    return text.encode("cp1252", "ignore").decode("cp1252")


def _para_text(value: Any) -> str:
    return escape(_clean(value)).replace("\r\n", "\n").replace("\n", "<br/>")


def _normalise_sentiment(value: Any) -> str:
    label = _clean(value).strip().title()
    return label if label in ("Positive", "Negative", "Neutral") else "Neutral"


def _format_orgs(story: Dict[str, Any]) -> str:
    orgs = story.get("mapped_org") or story.get("oma") or []
    if isinstance(orgs, str):
        orgs = [orgs]
    orgs = [str(o) for o in orgs if o]
    return "; ".join(orgs) if orgs else "Unmapped"


def _format_page(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return "Online"
    return str(value)


def format_brief_date(brief_date: Any) -> str:
    parsed: Optional[date] = None
    if isinstance(brief_date, datetime):
        parsed = brief_date.date()
    elif isinstance(brief_date, date):
        parsed = brief_date
    else:
        try:
            parsed = datetime.fromisoformat(str(brief_date)[:10]).date()
        except ValueError:
            parsed = None
    if parsed is None:
        return f"DATE: {_clean(brief_date).upper()}"
    return (f"DATE: {_DAYS[parsed.weekday()]}, {parsed.day:02d} "
            f"{_MONTHS[parsed.month - 1]} {parsed.year}")


def _fit_font_size(text: str, font: str, size: float, max_width: float) -> float:
    width = stringWidth(text, font, size)
    return size if width <= max_width else size * max_width / width


# ======================================================================
# COAT OF ARMS
# ======================================================================
def _candidate_coat_paths() -> List[str]:
    paths: List[str] = []
    override = os.environ.get("GOVPULSE_COAT_OF_ARMS")
    if override:
        paths.append(override)
    for base in (PROJECT_ROOT, SCRIPT_DIR, os.getcwd()):
        paths.append(os.path.join(base, "web", "assets", "coat_of_arms.png"))
    return paths


@lru_cache(maxsize=1)
def _load_coat_of_arms() -> Optional[Tuple[str, Tuple[int, int]]]:
    for path in _candidate_coat_paths():
        if os.path.isfile(path):
            try:
                return path, ImageReader(path).getSize()
            except Exception:
                continue
    return None


def _coat_size(max_h: float) -> Tuple[float, float]:
    loaded = _load_coat_of_arms()
    if loaded is None:
        return max_h * 0.85, max_h
    iw, ih = loaded[1]
    scale = max_h / ih
    return iw * scale, max_h


def draw_coat_of_arms(c, x: float, y: float, w: float, h: float) -> None:
    loaded = _load_coat_of_arms()
    if loaded is not None:
        try:
            c.drawImage(loaded[0], x, y, width=w, height=h, mask="auto",
                        preserveAspectRatio=True)
            return
        except Exception:
            pass
    c.saveState()
    c.setStrokeColor(WHITE)
    c.setFillColor(WHITE)
    c.setStrokeAlpha(0.45)
    c.setFillAlpha(0.45)
    c.setLineWidth(1.0)
    c.setDash(3, 3)
    c.roundRect(x, y, w, h, 4, stroke=1, fill=0)
    c.restoreState()


# ======================================================================
# OUTLINED LETTERING
# ======================================================================
def draw_outlined_text(c, text: str, cx: float, baseline: float, font: str,
                       size: float, fill, outline,
                       thickness: float = OUTLINE_THICKNESS,
                       step_deg: int = OUTLINE_STEP_DEG) -> None:
    x = cx - stringWidth(text, font, size) / 2
    c.saveState()
    c.setFont(font, size)
    c.setFillColor(outline)
    for radius in (thickness, thickness * 0.55):
        for angle in range(0, 360, step_deg):
            rad = math.radians(angle)
            c.drawString(x + math.cos(rad) * radius,
                         baseline + math.sin(rad) * radius, text)
    c.setFillColor(fill)
    c.drawString(x, baseline, text)
    c.restoreState()


# ======================================================================
# BANNER + DATE BAR + SMALL HEADER
# ======================================================================
def draw_banner(c, x: float, y: float, w: float, h: float) -> None:
    cx, top = x + w / 2, y + h

    coat_w, coat_h = _coat_size(COAT_MAX_H)
    coat_x = cx - coat_w / 2
    coat_y = top - COAT_TOP_GAP - coat_h

    republic_y = coat_y - 11
    ministry_y = republic_y - 14
    gov_y = ministry_y - (6 + OUTLINE_THICKNESS + CAP_HEIGHT * SIZE_GOVERNMENT)

    subtitle = "MEDIA MONITORING AND ANALYSIS DAILY BRIEF"
    sub_size = _fit_font_size(subtitle, FONT_BOLD, SIZE_SUBTITLE,
                              w - 2 * SUBTITLE_SIDE_MARGIN - 2 * OUTLINE_THICKNESS)
    sub_y = gov_y - (OUTLINE_THICKNESS * 2 + 6 + CAP_HEIGHT * sub_size)

    ministry = "Ministry of Information and Communication Technology"

    c.saveState()
    c.setFillColor(BANNER_BLUE)
    c.rect(x, y, w, h, stroke=0, fill=1)
    c.restoreState()

    draw_coat_of_arms(c, coat_x, coat_y, coat_w, coat_h)

    c.saveState()
    c.setFillColor(TEXT_BLACK)
    c.setFont(FONT_BOLD, SIZE_REPUBLIC)
    c.drawCentredString(cx, republic_y, "Republic of Namibia")
    c.setFont(FONT_BOLD, SIZE_MINISTRY)
    c.drawCentredString(cx, ministry_y, ministry)
    c.restoreState()

    draw_outlined_text(c, "Government", cx, gov_y, FONT_BOLD, SIZE_GOVERNMENT,
                       LETTER_FILL, OUTLINE_NAVY)
    draw_outlined_text(c, subtitle, cx, sub_y, FONT_BOLD, sub_size,
                       LETTER_FILL, OUTLINE_NAVY)


def draw_date_bar(c, y_top: float, text: str) -> None:
    y = y_top - DATE_BAR_H
    c.saveState()
    c.setFillColor(DATE_BAR_BLUE)
    c.rect(0, y, PAGE_W, DATE_BAR_H, stroke=0, fill=1)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, SIZE_DATE_BAR)
    c.drawCentredString(PAGE_W / 2,
                        y + (DATE_BAR_H - SIZE_DATE_BAR * CAP_HEIGHT) / 2,
                        text)
    c.restoreState()


def draw_small_header(c, date_text: str) -> None:
    y = PAGE_H - SMALL_HEADER_H
    c.saveState()
    c.setFillColor(BANNER_BLUE)
    c.rect(0, y, PAGE_W, SMALL_HEADER_H, stroke=0, fill=1)
    c.setFillColor(DATE_BAR_BLUE)
    c.rect(0, y, PAGE_W, 2.0, stroke=0, fill=1)

    text_x = MARGIN_X
    loaded = _load_coat_of_arms()
    if loaded is not None:
        iw, ih = loaded[1]
        h = SMALL_HEADER_H - 10
        w = iw * h / ih
        try:
            c.drawImage(loaded[0], MARGIN_X, y + 5, width=w, height=h, mask="auto")
            text_x = MARGIN_X + w + 8
        except Exception:
            pass

    c.setFillColor(OUTLINE_NAVY)
    c.setFont(FONT_BOLD, 11)
    c.drawString(text_x, y + SMALL_HEADER_H / 2 - 3,
                 "Government Media Monitoring and Analysis Daily Brief")
    c.setFont(FONT_BOLD, 9)
    c.drawRightString(PAGE_W - MARGIN_X, y + SMALL_HEADER_H / 2 - 3, date_text)
    c.restoreState()


# ======================================================================
# FOOTER — for the LAST PAGE only
# ======================================================================
def draw_footer(c, timestamp: str, page_number: int) -> None:
    c.saveState()

    review_lines = [
        "Kindly review the communication recommendations above and inform",
        "the MICT of any responses or actions taken by the institution to",
        "counter negative coverage.",
    ]

    cx = PAGE_W / 2
    y = FOOTER_BOTTOM + 60

    c.setFillColor(TEXT_BLACK)
    c.setFont(FONT_REGULAR, 9)
    bullet_x = MARGIN_X + 30
    c.drawString(bullet_x, y, "\u2022")
    c.drawString(bullet_x + 12, y, review_lines[0])
    c.drawString(bullet_x + 12, y - 11, review_lines[1])
    c.drawString(bullet_x + 12, y - 22, review_lines[2])

    y -= 42
    c.setFont(FONT_BOLD, 10)
    c.drawCentredString(cx, y, "NOTES:")

    y -= 16
    line_h = 12
    label_x = cx - 90
    dot_x = label_x - 12

    c.setFillColor(colors.HexColor("#FF0000"))
    c.circle(dot_x, y + 3, 2.2, stroke=0, fill=1)
    c.setFont(FONT_REGULAR, 9)
    c.drawString(label_x, y, "Highlight in red: Story is negative")

    y -= line_h
    c.setFillColor(colors.HexColor("#00A650"))
    c.circle(dot_x, y + 3, 2.2, stroke=0, fill=1)
    c.drawString(label_x, y, "Highlight in green: Story is positive")

    y -= line_h
    c.setFillColor(TEXT_BLACK)
    c.circle(dot_x, y + 3, 2.2, stroke=0, fill=1)
    c.drawString(label_x, y, "Highlight in black: Story is neutral")

    c.setFillColor(colors.HexColor("#555B66"))
    c.setFont(FONT_ITALIC, 7)
    c.drawString(MARGIN_X, FOOTER_BOTTOM,
                 f"Generated by GovPulse \u2014 Government Media Intelligence "
                 f"Platform | {timestamp}")
    c.drawRightString(MARGIN_X + CONTENT_W, FOOTER_BOTTOM, f"Page {page_number}")

    c.restoreState()


# ======================================================================
# STYLES + TABLE (PDF)
# ======================================================================
def build_styles() -> Dict[str, ParagraphStyle]:
    styles = {
        "th": ParagraphStyle("th", fontName=FONT_BOLD, fontSize=SIZE_TABLE_HEADER,
                             leading=10, textColor=TABLE_HEADER_BLUE, alignment=TA_LEFT),
        "cell": ParagraphStyle("cell", fontName=FONT_REGULAR, fontSize=SIZE_TABLE_BODY,
                               leading=10, textColor=TEXT_BLACK, alignment=TA_LEFT),
        "empty": ParagraphStyle("empty", fontName=FONT_ITALIC, fontSize=SIZE_TABLE_BODY + 1,
                                leading=11, textColor=colors.HexColor("#555B66"),
                                alignment=TA_CENTER),
    }
    for sentiment, colour in (("Positive", POSITIVE_TEXT),
                              ("Negative", NEGATIVE_TEXT),
                              ("Neutral",  NEUTRAL_TEXT)):
        styles[f"row_{sentiment}"] = ParagraphStyle(
            f"row_{sentiment}", fontName=FONT_REGULAR,
            fontSize=SIZE_TABLE_BODY, leading=10,
            textColor=colour, alignment=TA_LEFT,
        )
        styles[f"row_{sentiment}_bold"] = ParagraphStyle(
            f"row_{sentiment}_bold", fontName=FONT_BOLD,
            fontSize=SIZE_TABLE_BODY, leading=10,
            textColor=colour, alignment=TA_LEFT,
        )
    return styles


def build_story_table(stories: Sequence[Dict[str, Any]],
                      styles: Dict[str, ParagraphStyle]) -> Table:
    header_row = [Paragraph(h, styles["th"]) for h in COLUMN_HEADERS]
    rows: List[List[Any]] = [header_row]

    commands: List[Tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), WHITE),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("VALIGN", (0, 1), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.6, GRID_BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    if not stories:
        rows.append([Paragraph("No stories available for this date.",
                               styles["empty"])] + [""] * 7)
        commands += [("SPAN", (0, 1), (-1, 1)),
                     ("TOPPADDING", (0, 1), (-1, 1), 14),
                     ("BOTTOMPADDING", (0, 1), (-1, 1), 14)]
    else:
        for i, story in enumerate(stories, start=1):
            sentiment = _normalise_sentiment(story.get("sentiment"))
            cell = styles[f"row_{sentiment}"]
            bold = styles[f"row_{sentiment}_bold"]

            rows.append([
                Paragraph(_para_text(story.get("source")), bold),
                Paragraph(_para_text(_format_page(story.get("page"))), cell),
                Paragraph(_para_text(story.get("headline")), bold),
                Paragraph(_para_text(story.get("ai_summary")), cell),
                Paragraph(_para_text(story.get("government_source") or "None"), cell),
                Paragraph(sentiment, cell),
                Paragraph(_para_text(_format_orgs(story)), cell),
                Paragraph(_para_text(story.get("comment") or "None"), cell),
            ])

            bg = {"Positive": colors.HexColor("#E8F5EC"),
                  "Negative": colors.HexColor("#FCE9EA"),
                  "Neutral":  colors.HexColor("#F5F5F5")}.get(sentiment)
            if bg:
                commands.append(("BACKGROUND", (0, i), (-1, i), bg))

    table = Table(rows, colWidths=COL_WIDTHS, repeatRows=1, splitInRow=1,
                  hAlign="CENTER")
    table.setStyle(TableStyle(commands))
    return table


# ======================================================================
# DOCUMENT ASSEMBLY (two-pass: footer only on last page)
# ======================================================================
def _build_document(output_path: str, date_text: str, timestamp: str,
                    total_pages: Optional[int] = None) -> BaseDocTemplate:
    """If total_pages is None, footer draws on every page (used in pass 1).
    If total_pages is set, footer draws only on that page (used in pass 2)."""

    def on_first_page(canvas, doc):
        draw_banner(canvas, 0, PAGE_H - BANNER_H, PAGE_W, BANNER_H)
        draw_date_bar(canvas, PAGE_H - BANNER_H, date_text)
        page_num = canvas.getPageNumber()
        if total_pages is None or page_num == total_pages:
            draw_footer(canvas, timestamp, page_num)

    def on_later_pages(canvas, doc):
        draw_small_header(canvas, date_text)
        page_num = canvas.getPageNumber()
        if total_pages is None or page_num == total_pages:
            draw_footer(canvas, timestamp, page_num)

    doc = BaseDocTemplate(
        output_path, pagesize=(PAGE_W, PAGE_H),
        leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=0, bottomMargin=FOOTER_H,
        title="Government Media Monitoring and Analysis Daily Brief",
        author="GovPulse — Government Media Intelligence Platform",
        creator="GovPulse",
    )

    frame_kwargs = dict(x1=MARGIN_X, y1=FOOTER_H, width=CONTENT_W,
                        leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0)
    first_frame = Frame(height=PAGE_H - BANNER_H - DATE_BAR_H - FOOTER_H,
                        id="first_frame", **frame_kwargs)
    later_frame = Frame(height=PAGE_H - SMALL_HEADER_H - 6 - FOOTER_H,
                        id="later_frame", **frame_kwargs)

    doc.addPageTemplates([
        PageTemplate(id="first", frames=[first_frame],
                     onPage=on_first_page, pagesize=(PAGE_W, PAGE_H)),
        PageTemplate(id="later", frames=[later_frame],
                     onPage=on_later_pages, pagesize=(PAGE_W, PAGE_H)),
    ])
    return doc


# ======================================================================
# ARCHIVE
# ======================================================================
def _archive_brief(source_path: str, brief_date: str, ext: str) -> bool:
    os.makedirs(BRIEFS_DIR, exist_ok=True)
    dest_path = os.path.join(BRIEFS_DIR, f"{brief_date}.{ext}")
    try:
        shutil.copy2(source_path, dest_path)
        print(f"    [OK] Archived -> {dest_path}")
        return True
    except Exception as e:
        print(f"    [WARN] Could not archive {ext}: {e}")
        return False


# ======================================================================
# STORY LOADING
# ======================================================================
def load_stories(input_file: str = "data/processed/mapped.json",
                 approvals_file: str = "data/processed/approvals.json",
                 exclude_unmapped: bool = True):
    with open(input_file, "r", encoding="utf-8-sig") as f:
        all_stories = json.load(f)

    today = datetime.now().date().isoformat()
    stories_today = [s for s in all_stories
                     if (s.get("scraped_at") or "")[:10] == today]

    if stories_today:
        brief_date = today
    else:
        dates = sorted(set((s.get("scraped_at") or "")[:10]
                           for s in all_stories if s.get("scraped_at")),
                       reverse=True)
        if dates:
            brief_date = dates[0]
            stories_today = [s for s in all_stories
                             if (s.get("scraped_at") or "")[:10] == brief_date]
            print(f"[WARN] No stories scraped today ({today}). "
                  f"Falling back to {brief_date}")
        else:
            brief_date = today
            stories_today = all_stories

    print(f"Brief date: {brief_date} — {len(stories_today)} stories "
          f"(out of {len(all_stories)} total)")

    if exclude_unmapped:
        stories_today = [s for s in stories_today
                         if s.get("oma") and s["oma"] != ["Unmapped"]]
        print(f"After excluding unmapped: {len(stories_today)} stories")

    approvals: Dict[str, Any] = {}
    if os.path.exists(approvals_file):
        try:
            with open(approvals_file, "r", encoding="utf-8-sig") as f:
                approvals = json.load(f)
        except Exception as e:
            print(f"[WARN] Could not load approvals: {e}")

    for story in stories_today:
        headline = story.get("headline", "")
        if headline in approvals:
            approval = approvals[headline]
            approved_at = (approval.get("approved_at") or "")[:10]
            ministry = approval.get("ministry", "")
            final_text = approval.get("final_text", "")
            if approved_at and approved_at >= brief_date:
                story["comment"] = (f"✓ {approved_at} — {ministry}:\n\"{final_text}\"")
            else:
                story["comment"] = "None"
        else:
            story["comment"] = story.get("comment", "None") or "None"

    return stories_today, brief_date


# ======================================================================
# EXCEL — matches PDF style (Times, blue borders, coloured row text, bulleted footer)
# ======================================================================
def build_workbook(stories: List[Dict[str, Any]], brief_date: str) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Brief"

    # ---- Title block ----
    ws.merge_cells("A1:H1")
    title_cell = ws["A1"]
    title_cell.value = "GOVERNMENT MEDIA MONITORING AND ANALYSIS DAILY BRIEF"
    title_cell.font = Font(bold=True, size=14, color="FFFFFF",
                           name="Times New Roman")
    title_cell.fill = PatternFill("solid", fgColor=XLSX_HEADER_BLUE)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:H2")
    date_cell = ws["A2"]
    formatted_date = datetime.fromisoformat(brief_date).strftime("%A, %d %B %Y").upper()
    date_cell.value = f"DATE: {formatted_date}"
    date_cell.font = Font(bold=True, size=11, name="Times New Roman")
    date_cell.alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 20

    # ---- Headers: blue text on white, thin blue border ----
    headers = [
        "Newspaper", "Page Number", "Headline", "Brief Summary",
        "Government source quoted",
        "Sentiment", "O/M/A, Institution(s)", "Comment / Recommendation",
    ]
    header_row = 4
    thin_blue = Side(style="thin", color=XLSX_BORDER_BLUE)
    border_all = Border(left=thin_blue, right=thin_blue, top=thin_blue, bottom=thin_blue)

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_num, value=header)
        cell.font = Font(bold=True, color=XLSX_HEADER_BLUE,
                         name="Times New Roman", size=10)
        cell.fill = PatternFill("solid", fgColor="FFFFFF")
        cell.alignment = Alignment(horizontal="left", vertical="center",
                                   wrap_text=True)
        cell.border = border_all

    ws.row_dimensions[header_row].height = 36
    ws.freeze_panes = f"A{header_row + 1}"

    # ---- Data rows: entire row's text coloured by sentiment ----
    row = header_row + 1
    for story in stories:
        sentiment = _normalise_sentiment(story.get("sentiment"))
        text_color = XLSX_TEXT_COLOR.get(sentiment, "000000")

        values = [
            story.get("source", ""),
            _format_page(story.get("page")),
            story.get("headline", ""),
            story.get("ai_summary", ""),
            story.get("government_source", "") or "None",
            sentiment,
            _format_orgs(story),
            story.get("comment", "None"),
        ]

        for col_num, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=col_num, value=value)
            is_bold = col_num in (1, 3)  # Source + Headline bolded
            cell.font = Font(color=text_color, name="Times New Roman",
                             size=10, bold=is_bold)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border_all
            cell.fill = PatternFill("solid", fgColor="FFFFFF")

        summary_text = str(story.get("ai_summary", "") or "")
        estimated_lines = max(2, len(summary_text) // 55)
        ws.row_dimensions[row].height = 15 * estimated_lines
        row += 1

    # ---- Column widths ----
    widths = {"A": 14, "B": 10, "C": 32, "D": 60,
              "E": 28, "F": 11, "G": 32, "H": 22}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    # ---- Bulleted review note (centered) ----
    footer_row = row + 2
    ws.merge_cells(f"A{footer_row}:H{footer_row}")
    review = ws.cell(row=footer_row, column=1)
    review.value = "• " + FOOTER_REVIEW_TEXT
    review.font = Font(italic=True, size=10, name="Times New Roman")
    review.alignment = Alignment(wrap_text=True, horizontal="center")
    ws.row_dimensions[footer_row].height = 40

    # ---- NOTES: header (centered) ----
    notes_row = footer_row + 1
    ws.merge_cells(f"A{notes_row}:H{notes_row}")
    notes_hdr = ws.cell(row=notes_row, column=1)
    notes_hdr.value = "NOTES:"
    notes_hdr.font = Font(bold=True, size=11, name="Times New Roman")
    notes_hdr.alignment = Alignment(horizontal="center")

    # ---- Colour-key bullets ----
    bullet_defs = [
        ("FF0000", "   •  Highlight in red: Story is negative"),
        ("00A650", "   •  Highlight in green: Story is positive"),
        ("000000", "   •  Highlight in black: Story is neutral"),
    ]
    bullet_row = notes_row
    for color, text in bullet_defs:
        bullet_row += 1
        ws.merge_cells(f"A{bullet_row}:H{bullet_row}")
        cell = ws.cell(row=bullet_row, column=1)
        cell.value = text
        cell.font = Font(color=color, size=10, name="Times New Roman")
        cell.alignment = Alignment(horizontal="center")

    # ---- Credit line ----
    credit_row = bullet_row + 2
    ws.merge_cells(f"A{credit_row}:H{credit_row}")
    credit = ws.cell(row=credit_row, column=1)
    credit.value = (f"Generated by GovPulse — Government Media Intelligence "
                    f"Platform | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    credit.font = Font(italic=True, size=9, color="555B66", name="Times New Roman")
    credit.alignment = Alignment(horizontal="right")

    return wb


def generate_report(input_file: str = "data/processed/mapped.json",
                    output_file: str = "data/processed/daily_brief.xlsx"):
    print(f"Loading stories from {input_file}...")
    stories, brief_date = load_stories(input_file)
    print(f"Generating daily brief for {len(stories)} stories...")

    wb = build_workbook(stories, brief_date)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    wb.save(output_file)

    print(f"\n[OK] Daily brief saved -> {output_file}")

    counts = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for s in stories:
        counts[_normalise_sentiment(s.get("sentiment"))] += 1

    print(f"\nSentiment breakdown:")
    print(f"  Positive: {counts['Positive']}")
    print(f"  Neutral:  {counts['Neutral']}")
    print(f"  Negative: {counts['Negative']}")

    mapped = sum(1 for s in stories if s.get("oma") and s["oma"] != ["Unmapped"])
    print(f"\nMapped stories: {mapped}/{len(stories)}")

    _archive_brief(output_file, brief_date, "xlsx")


# ======================================================================
# PDF — two-pass render so footer appears only on the last page
# ======================================================================
def _render_pdf(stories: List[Dict[str, Any]], brief_date: str,
                output_path: str) -> str:
    folder = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(folder, exist_ok=True)

    styles = build_styles()
    date_text = format_brief_date(brief_date)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Pass 1 — write to temp file to count pages
    temp_path = output_path + ".tmp"
    table_pass1 = build_story_table(stories or [], styles)
    doc1 = _build_document(temp_path, date_text, timestamp, total_pages=None)
    doc1.build([NextPageTemplate("later"), table_pass1])

    # Count pages
    total_pages = 1
    try:
        from PyPDF2 import PdfReader
        total_pages = len(PdfReader(temp_path).pages)
    except Exception as e:
        print(f"    [WARN] Could not count pages: {e} — assuming 1")

    # Pass 2 — final render with footer only on last page
    table_pass2 = build_story_table(stories or [], styles)
    doc2 = _build_document(output_path, date_text, timestamp,
                           total_pages=total_pages)
    doc2.build([NextPageTemplate("later"), table_pass2])

    # Clean up temp file
    try:
        os.remove(temp_path)
    except Exception:
        pass

    print(f"    [OK] {total_pages} pages rendered")
    return output_path


def generate_pdf(input_file: str = "data/processed/mapped.json",
                 output_file: str = "data/processed/daily_brief.pdf"):
    print(f"Loading stories from {input_file}...")
    stories, brief_date = load_stories(input_file)
    print(f"Generating PDF brief for {len(stories)} stories...")

    _render_pdf(stories, brief_date, output_file)
    _archive_brief(output_file, brief_date, "pdf")

    print(f"\n[OK] PDF daily brief saved -> {output_file}")


def generate_all(input_file: str = "data/processed/mapped.json"):
    generate_report(input_file, "data/processed/daily_brief.xlsx")
    generate_pdf(input_file, "data/processed/daily_brief.pdf")


if __name__ == "__main__":
    generate_all()