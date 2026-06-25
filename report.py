"""
Scoring Engine + PDF Report Generator
Reads analysis.json, computes A–F grade, outputs a styled PDF report.
"""
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


JSON_IN  = "output/analysis.json"
PDF_OUT  = "output/driver_report.pdf"

# ── Scoring weights ────────────────────────────────────────────────────────────
WEIGHT_OFFSET  = 0.50   # lane centering
WEIGHT_SWERVE  = 0.35   # swerve event count
WEIGHT_DETECT  = 0.15   # lane detection coverage (proxy for visibility/speed)

GRADE_TABLE = [
    (90, "A", "Excellent — very disciplined lane keeping"),
    (78, "B", "Good — minor deviations, overall stable"),
    (62, "C", "Average — noticeable swerves, room to improve"),
    (50, "D", "Below average — frequent lane departures"),
    (0,  "F", "Poor — dangerous driving pattern detected"),
]


def score_offset(std_px):
    """
    Maps offset STD DEVIATION (wobble/variability) to 0-100, NOT raw
    average offset. Raw average offset is dominated by constant camera
    mount bias (the dashcam is rarely perfectly centered) and penalizing
    it punishes mount position, not driving quality. Std deviation
    captures how much the car's lane position actually fluctuates,
    which is the real signal for lane discipline.
    Below 8px std = rock steady. Above ~40px = weaving.
    """
    if std_px <= 8:    return 100
    if std_px <= 15:   return 95 - (std_px - 8) * 1.5
    if std_px <= 25:   return 84 - (std_px - 15) * 1.4
    if std_px <= 40:   return 70 - (std_px - 25) * 1.5
    if std_px <= 60:   return 47 - (std_px - 40) * 1.0
    return max(0, 27 - (std_px - 60) * 0.4)


def score_swerve(swerve_count, duration_s):
    """Maps swerves-per-minute to 0–100."""
    if duration_s < 1:
        return 100
    spm = swerve_count / (duration_s / 60)
    if spm == 0:    return 100
    if spm <= 3:    return 95
    if spm <= 8:    return 85
    if spm <= 15:   return 72
    if spm <= 22:   return 60
    if spm <= 32:   return 45
    return max(0, 30 - (spm - 32) * 1.0)


def score_detection(detected, total):
    """Lane detection coverage ratio → 0–100."""
    if total == 0:
        return 50
    ratio = detected / total
    return min(100, int(ratio * 105))   # slight bonus for clean detection


def compute_grade(score):
    for threshold, grade, desc in GRADE_TABLE:
        if score >= threshold:
            return grade, desc
    return "F", GRADE_TABLE[-1][2]


def grade_color(grade):
    return {
        "A": colors.HexColor("#27AE60"),
        "B": colors.HexColor("#2ECC71"),
        "C": colors.HexColor("#F39C12"),
        "D": colors.HexColor("#E67E22"),
        "F": colors.HexColor("#E74C3C"),
    }.get(grade, colors.grey)


def build_pdf(data, scores, total_score, grade, grade_desc):
    doc = SimpleDocTemplate(
        PDF_OUT, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    story  = []

    # ── Header ────────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "title", parent=styles["Title"],
        fontSize=22, textColor=colors.HexColor("#1A1A2E"),
        spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#555566"),
        alignment=TA_CENTER, spaceAfter=2
    )

    story.append(Paragraph("🚗  Driver Skill Rating Report", title_style))
    story.append(Paragraph("Dashcam CV Analysis Pipeline — OpenCV + Python", sub_style))
    story.append(Paragraph(f"Video: {data['video']}  |  Duration: {data['duration_s']}s  |  FPS: {data['fps']}", sub_style))
    story.append(HRFlowable(width="100%", thickness=1.5,
                             color=colors.HexColor("#1A1A2E"), spaceAfter=10))

    # ── Grade badge ───────────────────────────────────────────────────────────
    gc = grade_color(grade)
    badge_data = [[
        Paragraph(
            f'<font size="48" color="{gc.hexval() if hasattr(gc,"hexval") else "#333"}">'
            f'<b>{grade}</b></font>',
            ParagraphStyle("badge", alignment=TA_CENTER)
        ),
        Paragraph(
            f'<b>Overall Score: {total_score}/100</b><br/>'
            f'<font size="11">{grade_desc}</font>',
            ParagraphStyle("badgetext", fontSize=13,
                           leading=20, leftIndent=10)
        )
    ]]
    badge_table = Table(badge_data, colWidths=[3.5*cm, 13*cm])
    badge_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F8F8FC")),
        ("ROUNDEDCORNERS", [6]),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 14))

    # ── Score breakdown ───────────────────────────────────────────────────────
    story.append(Paragraph("<b>Score Breakdown</b>",
                           ParagraphStyle("h2", fontSize=13,
                                          textColor=colors.HexColor("#1A1A2E"),
                                          spaceAfter=6)))

    breakdown = [
        ["Category", "Raw Value", "Component Score", "Weight", "Weighted"],
        [
            "Lane Centering",
            f"{data['std_offset_px']} px offset std-dev",
            f"{scores['offset']:.1f}",
            "50%",
            f"{scores['offset'] * 0.50:.1f}"
        ],
        [
            "Swerve Control",
            f"{scores['swerve_count']} events in {data['duration_s']}s",
            f"{scores['swerve']:.1f}",
            "35%",
            f"{scores['swerve'] * 0.35:.1f}"
        ],
        [
            "Detection Coverage",
            f"{data['lane_detected_frames']}/{data['total_frames']} frames",
            f"{scores['detect']:.1f}",
            "15%",
            f"{scores['detect'] * 0.15:.1f}"
        ],
        ["", "", "", "<b>Total</b>", f"<b>{total_score}</b>"],
    ]

    col_widths = [4.5*cm, 5*cm, 3.5*cm, 2*cm, 2.5*cm]
    t = Table(breakdown, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A1A2E")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2),
         [colors.HexColor("#F5F5FA"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCDD")),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("FONTNAME", (-2, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    # ── Event log ─────────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Event Log</b>",
                           ParagraphStyle("h2", fontSize=13,
                                          textColor=colors.HexColor("#1A1A2E"),
                                          spaceAfter=6)))

    events = data.get("events", [])
    if events:
        event_data = [["#", "Time (s)", "Type", "Detail"]]
        for i, ev in enumerate(events, 1):
            event_data.append([
                str(i),
                str(ev["time_s"]),
                ev["type"].upper(),
                ev.get("detail", "—")
            ])
        et = Table(event_data, colWidths=[1*cm, 2.5*cm, 3.5*cm, 10.5*cm])
        et.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#FEF9EC"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCDD")),
            ("ALIGN", (0, 0), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ]))
        story.append(et)
    else:
        story.append(Paragraph("No events detected. Clean drive! ✅",
                                styles["Normal"]))

    story.append(Spacer(1, 14))

    # ── Stats summary ─────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Raw Statistics</b>",
                           ParagraphStyle("h2", fontSize=13,
                                          textColor=colors.HexColor("#1A1A2E"),
                                          spaceAfter=6)))

    stats = [
        ["Metric", "Value"],
        ["Total frames",          str(data["total_frames"])],
        ["Lane detected frames",  str(data["lane_detected_frames"])],
        ["Average offset (abs)",  f"{data['avg_abs_offset_px']} px"],
        ["Max offset (abs)",      f"{data['max_abs_offset_px']} px"],
        ["Offset std-dev",        f"{data['std_offset_px']} px"],
        ["Swerve events",         str(scores['swerve_count'])],
        ["Duration",              f"{data['duration_s']} s"],
    ]
    st = Table(stats, colWidths=[7*cm, 10.5*cm])
    st.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A1A2E")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#F5F5FA"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCDD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(st)
    story.append(Spacer(1, 20))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.8,
                             color=colors.HexColor("#AAAACC"), spaceBefore=4))
    story.append(Paragraph(
        "Generated by Driver Skill Rating System · OpenCV + Python Pipeline",
        ParagraphStyle("footer", fontSize=8, textColor=colors.HexColor("#999999"),
                       alignment=TA_CENTER, spaceAfter=0)
    ))

    doc.build(story)
    print(f"Report saved → {PDF_OUT}")


def run():
    with open(JSON_IN) as f:
        data = json.load(f)

    swerve_count = sum(1 for e in data["events"] if e["type"] == "swerve")

    s_offset = score_offset(data["std_offset_px"])
    s_swerve = score_swerve(swerve_count, data["duration_s"])
    s_detect = score_detection(data["lane_detected_frames"], data["total_frames"])

    total = int(
        s_offset * WEIGHT_OFFSET +
        s_swerve * WEIGHT_SWERVE +
        s_detect * WEIGHT_DETECT
    )

    grade, grade_desc = compute_grade(total)

    scores = {
        "offset":       round(s_offset, 1),
        "swerve":       round(s_swerve, 1),
        "detect":       round(s_detect, 1),
        "swerve_count": swerve_count,
    }

    print(f"\nScoring complete:")
    print(f"  Offset score  : {s_offset:.1f}")
    print(f"  Swerve score  : {s_swerve:.1f}")
    print(f"  Detect score  : {s_detect:.1f}")
    print(f"  Total         : {total}/100  → Grade {grade}")
    print(f"  {grade_desc}")

    build_pdf(data, scores, total, grade, grade_desc)


if __name__ == "__main__":
    run()