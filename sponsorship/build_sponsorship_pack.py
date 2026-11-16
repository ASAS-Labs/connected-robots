#!/usr/bin/env python3
"""Build the EARS-CONN 2027 sponsorship information pack PDF."""

from pathlib import Path

from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "EARS-CONN_2027_Sponsorship_Information_Pack.pdf"
LOGO = ROOT / "images" / "logos" / "ears-conn.png"
CCNY = ROOT / "images" / "logos" / "CNNY.png"

NAVY = HexColor("#0B1F3A")
TEAL = HexColor("#0E7490")
SLATE = HexColor("#334155")
MUTED = HexColor("#64748B")
LIGHT = HexColor("#F1F5F9")
LINE = HexColor("#CBD5E1")
ACCENT = HexColor("#B45309")


def draw_header_bar(c, width, height, title_right="SPONSORSHIP INFORMATION PACK"):
    c.setFillColor(NAVY)
    c.rect(0, height - 0.95 * inch, width, 0.95 * inch, fill=1, stroke=0)
    if LOGO.exists():
        c.drawImage(
            str(LOGO),
            0.55 * inch,
            height - 0.82 * inch,
            width=0.55 * inch,
            height=0.55 * inch,
            mask="auto",
            preserveAspectRatio=True,
            anchor="c",
        )
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1.25 * inch, height - 0.42 * inch, "EARS-CONN 2027")
    c.setFont("Helvetica", 9)
    c.drawString(1.25 * inch, height - 0.62 * inch, "January 19–22, 2027  ·  New York City")
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 0.55 * inch, height - 0.48 * inch, title_right)


def draw_footer(c, width, page_num, total=5):
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    y = 0.55 * inch
    c.line(0.55 * inch, y + 0.18 * inch, width - 0.55 * inch, y + 0.18 * inch)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(0.55 * inch, y - 0.05 * inch, "https://ears-conn.com")
    c.drawRightString(width - 0.55 * inch, y - 0.05 * inch, f"{page_num} of {total}")


def bullet(c, x, y, text, max_width, font="Helvetica", size=10, leading=13, color=SLATE):
    c.setFillColor(TEAL)
    c.circle(x + 3, y + 3, 2.2, fill=1, stroke=0)
    c.setFillColor(color)
    c.setFont(font, size)
    # simple wrap
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if c.stringWidth(trial, font, size) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    for i, line in enumerate(lines):
        c.drawString(x + 12, y - i * leading, line)
    return y - max(len(lines), 1) * leading - 4


def section_title(c, x, y, text):
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, text)
    c.setStrokeColor(TEAL)
    c.setLineWidth(2)
    c.line(x, y - 6, x + 1.6 * inch, y - 6)
    return y - 22


def tier_box(c, x, y, w, h, name, price, exclusivity, items, featured=False):
    c.setFillColor(LIGHT if not featured else HexColor("#ECFEFF"))
    c.setStrokeColor(TEAL if featured else LINE)
    c.setLineWidth(1.4 if featured else 0.8)
    c.roundRect(x, y - h, w, h, 8, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x + 12, y - 18, name)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(x + w - 12, y - 18, price)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(x + 12, y - 32, exclusivity)
    yy = y - 48
    for item in items:
        yy = bullet(c, x + 8, yy, item, w - 28, size=8.5, leading=11)
    return yy


def page_cover(c, width, height):
    draw_header_bar(c, width, height)
    y = height - 1.35 * inch

    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.7 * inch, y, "SPONSORSHIP")
    y -= 28
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(0.7 * inch, y, "Information Pack")
    y -= 18
    c.setStrokeColor(TEAL)
    c.setLineWidth(2.5)
    c.line(0.7 * inch, y, 3.2 * inch, y)
    y -= 28

    c.setFillColor(SLATE)
    c.setFont("Helvetica", 11)
    for line in [
        "Embodied AI and Remote Sensing for",
        "Sustainable, Safe Connected Cities",
    ]:
        c.drawString(0.7 * inch, y, line)
        y -= 16

    y -= 10
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 10)
    facts = [
        "Conference · January 19–20, 2027",
        "Hands-on Workshop · January 21–22, 2027",
        "Venue · Grove School of Engineering, The City College of New York",
        "Host partners · CCNY · CUNY · UNU Hub R-SIRUS",
    ]
    for f in facts:
        y = bullet(c, 0.7 * inch, y, f, 4.6 * inch, size=10, leading=14)

    # Contact panel
    panel_x = 5.3 * inch
    panel_y = height - 1.5 * inch
    panel_w = 2.5 * inch
    panel_h = 3.35 * inch
    c.setFillColor(NAVY)
    c.roundRect(panel_x, panel_y - panel_h, panel_w, panel_h, 10, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(panel_x + 14, panel_y - 28, "Sponsorship contact")
    c.setFont("Helvetica", 8.5)
    lines = [
        "Dr. Aliasghar Arab",
        "Research Professor",
        "CCNY and NYU",
        "",
        "aarab@ccny.cuny.edu",
        "",
        "With organizers:",
        "Fred Moshary · CCNY",
        "Reza Khanbilvardi · CCNY",
        "Karin Sjöstrand · UNU Hub",
        "",
        "Website",
        "https://ears-conn.com",
    ]
    yy = panel_y - 48
    for line in lines:
        c.drawString(panel_x + 14, yy, line)
        yy -= 13

    # Bottom strip
    c.setFillColor(LIGHT)
    c.rect(0, 0.85 * inch, width, 1.35 * inch, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.7 * inch, 1.85 * inch, "Why sponsor EARS-CONN?")
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 9)
    why = (
        "Reach researchers, city agencies, insurers, and industry building the stack from "
        "edge chips and robots to satellites — for safer, more sustainable connected urban communities."
    )
    # wrap
    words = why.split()
    cur = ""
    yy = 1.6 * inch
    for w in words:
        trial = (cur + " " + w).strip()
        if c.stringWidth(trial, "Helvetica", 9) < width - 1.4 * inch:
            cur = trial
        else:
            c.drawString(0.7 * inch, yy, cur)
            yy -= 12
            cur = w
    if cur:
        c.drawString(0.7 * inch, yy, cur)

    if CCNY.exists():
        c.drawImage(
            str(CCNY),
            width - 1.7 * inch,
            0.95 * inch,
            width=1.0 * inch,
            height=0.42 * inch,
            mask="auto",
            preserveAspectRatio=True,
            anchor="c",
        )
    draw_footer(c, width, 1)


def page_about(c, width, height):
    draw_header_bar(c, width, height, "ABOUT THE EVENT")
    y = height - 1.35 * inch
    y = section_title(c, 0.7 * inch, y, "About EARS-CONN 2027")

    paras = [
        "EARS-CONN 2027 brings researchers, industry, and city leaders to New York for a four-day forum on Embodied AI and Remote Sensing for Sustainable, Safe Connected Cities.",
        "A chip in a car, a phone in a pocket, even a streetlight can communicate with satellites. EARS-CONN focuses on how onboard and street-level intelligence connects in realtime to remote sensing — closing the loop from sensors to decisions for resilient urban communities.",
        "The scientific and practical programme spans remote sensing, robotics and autonomy, edge/cloud AI, digital twins, urban resilience, insurance intelligence, and governance of connected systems.",
        "Days 1–2 are a plenary conference (keynotes, panels, posters, Innovation Stage). Days 3–4 are a hands-on Autoware / ROS 2 workshop and hackathon, with certificates co-issued by UNU Hub R-SIRUS and CCNY.",
        "EARS-CONN is hosted at The City College of New York with the United Nations University Hub R-SIRUS — the first UNU research and training hub in the United States — building on the Hub’s Digital Earth and AI for Sustainability professional development workshop.",
    ]
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 10)
    for p in paras:
        words = p.split()
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if c.stringWidth(trial, "Helvetica", 10) < width - 1.4 * inch:
                cur = trial
            else:
                c.drawString(0.7 * inch, y, cur)
                y -= 13
                cur = w
        if cur:
            c.drawString(0.7 * inch, y, cur)
            y -= 13
        y -= 8

    y -= 4
    y = section_title(c, 0.7 * inch, y, "Who attends")
    audience = [
        "Researchers in remote sensing, robotics, AI, civil/environmental engineering, urban science",
        "Industry & startups in AV, drones, geospatial, telecom, edge AI, and sensing products",
        "City agencies, first responders, and infrastructure operators",
        "Insurers and risk professionals focused on hyper-local urban risk",
        "Policymakers, NGOs, and students / early-career engineers",
    ]
    for a in audience:
        y = bullet(c, 0.7 * inch, y, a, width - 1.5 * inch, size=10, leading=13)

    y -= 8
    y = section_title(c, 0.7 * inch, y, "Audience & brand alignment")
    for a in [
        "Position your brand at the intersection of embodied AI, connectivity, and Earth observation",
        "Meet hiring pipelines and research partners across CUNY, NYU, NOAA-linked networks, and startups",
        "Support student skills via the workshop/hackathon and visible community impact in NYC",
    ]:
        y = bullet(c, 0.7 * inch, y, a, width - 1.5 * inch, size=10, leading=13)

    draw_footer(c, width, 2)


def page_tiers_high(c, width, height):
    draw_header_bar(c, width, height, "SPONSORSHIP TIERS")
    y = height - 1.3 * inch
    y = section_title(c, 0.7 * inch, y, "Sponsorships")
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 10)
    c.drawString(
        0.7 * inch,
        y,
        "EARS-CONN 2027 offers sponsorship levels to match a range of budgets and goals.",
    )
    y -= 18

    left_items = [
        "Logo on ears-conn.com with link to homepage (largest size)",
        "Logo on advertising and promotional material",
        "Prime exhibition / demo table (approx. 6 m² footprint)",
        "10-minute company/product presentation",
        "Promotional material in digital goodie bag",
        "Full-page advertisement in event programme",
        "6 complimentary conference registrations",
        "Mention in press releases",
        "Mention at opening and closing of the event",
        "Named recognition as Presenting Sponsor on selected materials",
    ]
    right_items = [
        "Logo on ears-conn.com with link to homepage",
        "Logo on advertising and promotional material",
        "Exhibition / demo table (approx. 4 m² footprint)",
        "5-minute company/product spotlight",
        "Promotional material in digital goodie bag",
        "Half-page advertisement in event programme",
        "4 complimentary conference registrations",
        "Mention at opening and closing of the event",
    ]

    box_h = 4.55 * inch
    tier_box(
        c,
        0.55 * inch,
        y,
        3.55 * inch,
        box_h,
        "PLATINUM Sponsor",
        "$8,000",
        "Exclusivity (one)",
        left_items,
        featured=True,
    )
    tier_box(
        c,
        4.25 * inch,
        y,
        3.55 * inch,
        box_h,
        "GOLD Sponsor",
        "$5,000",
        "Exclusivity (two)",
        right_items,
        featured=False,
    )

    c.setFillColor(MUTED)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(
        0.7 * inch,
        0.85 * inch,
        "* Platinum and Gold logos appear larger than Silver/Bronze across website and materials.",
    )
    draw_footer(c, width, 3)


def page_tiers_low(c, width, height):
    draw_header_bar(c, width, height, "SPONSORSHIP TIERS")
    y = height - 1.3 * inch
    y = section_title(c, 0.7 * inch, y, "Sponsorships (continued)")

    silver = [
        "Logo on ears-conn.com with link to homepage",
        "Logo on advertising and promotional material",
        "Exhibition / demo table (approx. 4 m² footprint)",
        "2 complimentary conference registrations",
    ]
    bronze = [
        "Logo on ears-conn.com with link to homepage",
        "Listing of sponsor in event advertising material",
    ]

    tier_box(
        c,
        0.55 * inch,
        y,
        3.55 * inch,
        2.6 * inch,
        "SILVER Sponsor",
        "$3,000",
        "Exclusivity (six)",
        silver,
    )
    tier_box(
        c,
        4.25 * inch,
        y,
        3.55 * inch,
        2.6 * inch,
        "BRONZE Sponsor",
        "$1,000",
        "Open",
        bronze,
    )

    y = y - 2.85 * inch
    y = section_title(c, 0.7 * inch, y, "Additional sponsorship opportunities")
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 10)
    add = [
        "Welcome reception or networking evening — exclusive naming",
        "Lunch / coffee-break sponsorship with on-site and programme credit",
        "Innovation Challenge / EARS-CONN Prize sponsor",
        "Workshop hackathon prize sponsor (Days 3–4)",
        "Student scholarship or travel support package",
        "Banner / digital display placement in main session rooms",
    ]
    for a in add:
        y = bullet(c, 0.7 * inch, y, a, width - 1.5 * inch, size=10, leading=13)

    y -= 6
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawString(
        0.7 * inch,
        y,
        "Interested parties may combine tiers with add-ons. Contact us for a tailored package.",
    )

    draw_footer(c, width, 4)


def page_matrix(c, width, height):
    draw_header_bar(c, width, height, "COMPARISON & EXHIBITION")
    y = height - 1.3 * inch
    y = section_title(c, 0.7 * inch, y, "Benefits at a glance")

    headers = ["Benefit", "Platinum", "Gold", "Silver", "Bronze"]
    rows = [
        ["Exclusivity", "1", "2", "6", "—"],
        ["Logo + link on website", "✓", "✓", "✓", "✓"],
        ["Logo on promo materials", "✓", "✓", "✓", "listing"],
        ["Exhibition / demo space", "6 m²", "4 m²", "4 m²", "—"],
        ["On-stage presentation", "10 min", "5 min", "—", "—"],
        ["Digital goodie bag insert", "✓", "✓", "—", "—"],
        ["Programme advertisement", "Full page", "Half page", "—", "—"],
        ["Complimentary registrations", "6", "4", "2", "—"],
        ["Press-release mention", "✓", "—", "—", "—"],
        ["Opening / closing mention", "✓", "✓", "—", "—"],
    ]

    col_w = [2.7 * inch, 1.05 * inch, 1.05 * inch, 1.05 * inch, 1.05 * inch]
    x0 = 0.55 * inch
    row_h = 18
    # header
    c.setFillColor(NAVY)
    c.rect(x0, y - row_h, sum(col_w), row_h, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    x = x0 + 4
    for i, h in enumerate(headers):
        c.drawString(x, y - 12, h)
        x += col_w[i]
    y -= row_h

    c.setFont("Helvetica", 8)
    for ri, row in enumerate(rows):
        if ri % 2 == 0:
            c.setFillColor(LIGHT)
            c.rect(x0, y - row_h, sum(col_w), row_h, fill=1, stroke=0)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.4)
        c.rect(x0, y - row_h, sum(col_w), row_h, fill=0, stroke=1)
        x = x0 + 4
        for i, cell in enumerate(row):
            c.setFillColor(NAVY if i == 0 else SLATE)
            c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", 8)
            c.drawString(x, y - 12, cell)
            x += col_w[i]
        y -= row_h

    y -= 22
    y = section_title(c, 0.7 * inch, y, "Exhibition space (à la carte)")
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 10)
    c.drawString(0.7 * inch, y, "Exhibition Space — $1,000")
    y -= 16
    for a in [
        "Approx. 4 m² footprint (e.g. 2 m × 2 m)",
        "One table and two chairs",
        "One power connection",
        "Available to non-tier exhibitors or as an add-on",
    ]:
        y = bullet(c, 0.7 * inch, y, a, width - 1.5 * inch, size=10, leading=13)

    y -= 8
    y = section_title(c, 0.7 * inch, y, "Made to measure")
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 9.5)
    text = (
        "Organizations that need a custom booth build, non-standard equipment, recruiting lounge, "
        "or a named programme element are welcome to contact us. We will design a package that "
        "fits your goals and the venue constraints at CCNY."
    )
    words = text.split()
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if c.stringWidth(trial, "Helvetica", 9.5) < width - 1.4 * inch:
            cur = trial
        else:
            c.drawString(0.7 * inch, y, cur)
            y -= 12
            cur = w
    if cur:
        c.drawString(0.7 * inch, y, cur)
        y -= 16

    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.7 * inch, y, "Next step")
    y -= 14
    c.setFillColor(SLATE)
    c.setFont("Helvetica", 10)
    c.drawString(0.7 * inch, y, "Email aarab@ccny.cuny.edu with preferred tier (or ask for a tailored option).")
    y -= 13
    c.drawString(0.7 * inch, y, "Website: https://ears-conn.com")

    draw_footer(c, width, 5)


def main():
    width, height = letter
    c = canvas.Canvas(str(OUT), pagesize=letter)
    c.setTitle("EARS-CONN 2027 Sponsorship Information Pack")
    c.setAuthor("EARS-CONN Organizing Team")
    page_cover(c, width, height)
    c.showPage()
    page_about(c, width, height)
    c.showPage()
    page_tiers_high(c, width, height)
    c.showPage()
    page_tiers_low(c, width, height)
    c.showPage()
    page_matrix(c, width, height)
    c.save()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
