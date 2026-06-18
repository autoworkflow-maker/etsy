import os
import json
import cloudinary
import cloudinary.uploader
from anthropic import Anthropic
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from openpyxl import Workbook
from openpyxl.styles import Font
from product_file_builder import ProductFileBuilder

from docx import Document

import csv
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    HRFlowable, PageBreak, Table, TableStyle
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import math
BLOCKED_TERMS = [
    "disney","marvel","pokemon","harry potter",
    "taylor swift","nfl","nba",
    "cure","heal","diagnose","treat",
    "prompt pack","ai prompt",
    "guaranteed income","get rich"
]
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Cloudinary config
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
)

BRAND_BLUE  = colors.HexColor("#185FA5")
BRAND_DARK  = colors.HexColor("#1a1a2e")
BRAND_GREEN = colors.HexColor("#1D9E75")
BRAND_GRAY  = colors.HexColor("#888780")


# ── 1. Generate content with Claude Sonnet ────────────────────
def is_etsy_safe(product):
    text = (
        product.get("keyword", "") + " " +
        product.get("niche_angle", "") + " " +
        product.get("product_type", "")
    ).lower()

    return not any(term in text for term in BLOCKED_TERMS)

def generate_product_content(pick):
    prompt = f"""
Create complete content for a digital product on Etsy.

Product type: {pick.get('product_type', 'PDF guide')}
Keyword: {pick['keyword']}
Niche angle: {pick.get('niche_angle', pick['keyword'])}
Price: ${pick.get('suggested_price', 4.99)}

Return ONLY a JSON object, no explanation:
{{
  "etsy_title": "SEO-optimised Etsy title max 140 chars, keyword first",
  "etsy_description": "Full product description 200 words, benefits-led, FAQ at end",
  "etsy_tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10","tag11","tag12","tag13"],
  "pdf_guide_title": "catchy PDF cover title",
  "pdf_subtitle": "one line subtitle",
  "introduction": "2 paragraph intro",
  "worksheets": [{{"title":"worksheet title","purpose":"what it helps with","instructions":"how to use it"}}],
  "checklists": ["checklist item 1","checklist item 2","checklist item 3","checklist item 4","checklist item 5"],
  "workflow": [{{"step":1,"title":"step title","description":"what to do"}}],
  "tips": ["tip1","tip2","tip3","tip4","tip5"],
  "tools": [{{"name":"tool","what_it_does":"description","free":true}}],
  "keywords": ["kw1","kw2","kw3","kw4","kw5"],
  "conclusion": "1-2 paragraph conclusion",
  "pin_headline": "bold Pinterest pin headline max 8 words",
  "social_post": "Twitter/X post max 240 chars with hashtags"
}}

Include 3 worksheets, 4 workflow steps, 5 checklist items, 3 tools.
Keep all values short. Return valid JSON only.
Do not create AI prompt packs, medical claims, financial guarantees, celebrity/brand/copyrighted content.
Etsy tags must be exactly 13. Each tag max 20 chars.
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",  # Quality matters for product content
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ── 2. Build PDF with ReportLab ───────────────────────────────

def build_pdf(content, pick, filepath):
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)

    styles   = getSampleStyleSheet()
    cover_title = ParagraphStyle("CT", fontSize=26, fontName="Helvetica-Bold",
                                 textColor=BRAND_BLUE, alignment=TA_CENTER, spaceAfter=10, leading=32)
    cover_sub   = ParagraphStyle("CS", fontSize=13, fontName="Helvetica",
                                 textColor=BRAND_GRAY, alignment=TA_CENTER, spaceAfter=6)
    cover_brand = ParagraphStyle("CB", fontSize=11, fontName="Helvetica-Bold",
                                 textColor=BRAND_GREEN, alignment=TA_CENTER)
    sec_head    = ParagraphStyle("SH", fontSize=15, fontName="Helvetica-Bold",
                                 textColor=BRAND_BLUE, spaceBefore=18, spaceAfter=6)
    sub_head    = ParagraphStyle("SH2", fontSize=11, fontName="Helvetica-Bold",
                                 textColor=BRAND_DARK, spaceBefore=10, spaceAfter=4)
    body        = ParagraphStyle("B", fontSize=10, fontName="Helvetica",
                                 textColor=BRAND_DARK, spaceAfter=5, leading=14)
    prompt_s    = ParagraphStyle("P", fontSize=9, fontName="Helvetica-Oblique",
                                 textColor=colors.HexColor("#2c3e50"),
                                 backColor=colors.HexColor("#eef2ff"),
                                 leftIndent=8, rightIndent=8, spaceBefore=3,
                                 spaceAfter=7, leading=13)
    tip_s       = ParagraphStyle("T", fontSize=10, fontName="Helvetica",
                                 textColor=BRAND_DARK, leftIndent=14, spaceAfter=4, leading=13)
    kw_s        = ParagraphStyle("K", fontSize=9, fontName="Helvetica-Bold",
                                 textColor=BRAND_GREEN, leftIndent=10, spaceAfter=3)
    footer_s    = ParagraphStyle("F", fontSize=8, fontName="Helvetica",
                                 textColor=BRAND_GRAY, alignment=TA_CENTER)

    story = []

    # Cover
    story += [Spacer(1, 1*inch),
              Paragraph("AI TOOLS DAILY", cover_brand),
              Spacer(1, 0.2*inch),
              HRFlowable(width="100%", thickness=2, color=BRAND_BLUE),
              Spacer(1, 0.2*inch),
              Paragraph(content["pdf_guide_title"], cover_title),
              Paragraph(content["pdf_subtitle"], cover_sub),
              Spacer(1, 0.2*inch),
              HRFlowable(width="100%", thickness=1, color=BRAND_GRAY),
              Spacer(1, 0.3*inch)]

    info = [["Published:", datetime.now().strftime("%B %Y")],
            ["Topic:", pick["keyword"].title()],
            ["Price:", f"${pick.get('suggested_price', 4.99)}"]]
    t = Table(info, colWidths=[1.4*inch, 5*inch])
    t.setStyle(TableStyle([
        ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("TEXTCOLOR",     (0,0), (0,-1), BRAND_GRAY),
        ("TEXTCOLOR",     (1,0), (1,-1), BRAND_DARK),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story += [t, PageBreak()]

    # Intro
    story += [Paragraph("Introduction", sec_head),
              HRFlowable(width="100%", thickness=0.5, color=BRAND_BLUE),
              Spacer(1,6),
              Paragraph(content["introduction"], body)]

    # Prompts
    story += [PageBreak(), Paragraph("Worksheets", sec_head),
              HRFlowable(width="100%", thickness=0.5, color=BRAND_BLUE), Spacer(1,6)]
    for i, p in enumerate(content.get("worksheets", []), 1):
        story += [Paragraph(f"{i}. {p['title']}", sub_head),
                  Paragraph(f"<b>Purpose:</b> {p['purpose']}", body),
                  Paragraph(p["instructions"], prompt_s)]

    # Workflow table
    story += [PageBreak(), Paragraph("Step-by-Step Workflow", sec_head),
              HRFlowable(width="100%", thickness=0.5, color=BRAND_BLUE), Spacer(1,6)]
    wf_data = [["#", "Step", "What to do"]]
    for s in content.get("workflow", []):
        wf_data.append([str(s["step"]), s["title"], s["description"]])
    wt = Table(wf_data, colWidths=[0.4*inch, 1.7*inch, 4.4*inch])
    wt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), BRAND_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f7f9ff")]),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
    ]))
    story.append(wt)

    # Tips, tools, keywords, conclusion
    story += [Spacer(1,16), Paragraph("Pro Tips", sec_head),
              HRFlowable(width="100%", thickness=0.5, color=BRAND_BLUE), Spacer(1,6)]
    for i, tip in enumerate(content.get("tips", []), 1):
        story.append(Paragraph(f"  {i}.  {tip}", tip_s))

    story += [PageBreak(), Paragraph("Recommended Tools", sec_head),
              HRFlowable(width="100%", thickness=0.5, color=BRAND_BLUE), Spacer(1,6)]
    tl_data = [["Tool", "What it does", "Free?"]]
    for t in content.get("tools", []):
        tl_data.append([t["name"], t["what_it_does"], "Yes" if t["free"] else "Paid"])
    tt = Table(tl_data, colWidths=[1.5*inch, 4*inch, 1*inch])
    tt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), BRAND_BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f7f9ff")]),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("TEXTCOLOR",     (2,1), (2,-1), BRAND_GREEN),
    ]))
    story.append(tt)

    story += [Spacer(1,16), Paragraph("SEO Keyword Cheat Sheet", sec_head),
              HRFlowable(width="100%", thickness=0.5, color=BRAND_BLUE), Spacer(1,6)]
    for kw in content.get("keywords", []):
        story.append(Paragraph(f"  •  {kw}", kw_s))

    story += [Spacer(1,14), Paragraph("Conclusion", sec_head),
              HRFlowable(width="100%", thickness=0.5, color=BRAND_BLUE), Spacer(1,6),
              Paragraph(content["conclusion"], body),
              Spacer(1, 0.3*inch),
              HRFlowable(width="100%", thickness=0.5, color=BRAND_GRAY),
              Spacer(1,6),
              Paragraph(f"AI Tools Daily  •  {datetime.now().year}  •  Educational content  •  May contain affiliate links.", footer_s)]

    doc.build(story)
    return filepath


# ── 3. Generate Pinterest pin image ──────────────────────────

def get_daily_theme():
    day = datetime.now().timetuple().tm_yday
    cycle = (math.sin(2 * math.pi * day / 365) + 1) / 2
    themes = [
        {"bg_top":(12,20,42),"bg_bot":(32,50,112),"border":(95,135,210),"card_l":(245,248,255),"card_d":(22,43,86),"accent":(65,210,125),"txt_l":(190,210,255),"txt_d":(150,175,220),"title":(10,25,50)},
        {"bg_top":(42,18,10),"bg_bot":(112,55,20),"border":(210,140,80),"card_l":(255,248,240),"card_d":(86,35,15),"accent":(255,180,50),"txt_l":(255,220,180),"txt_d":(220,180,140),"title":(50,20,5)},
        {"bg_top":(20,10,40),"bg_bot":(60,20,100),"border":(160,90,220),"card_l":(248,242,255),"card_d":(45,15,80),"accent":(200,80,255),"txt_l":(220,190,255),"txt_d":(180,150,220),"title":(25,5,50)},
        {"bg_top":(8,30,15),"bg_bot":(20,70,40),"border":(80,190,120),"card_l":(240,255,245),"card_d":(15,55,30),"accent":(50,220,100),"txt_l":(180,240,200),"txt_d":(140,200,160),"title":(5,30,15)},
        {"bg_top":(30,25,5),"bg_bot":(75,60,10),"border":(210,175,50),"card_l":(255,252,235),"card_d":(60,48,8),"accent":(230,190,40),"txt_l":(245,220,130),"txt_d":(210,185,100),"title":(35,28,3)},
    ]
    idx   = (day // 7) % len(themes)
    base  = themes[idx]
    nxt   = themes[(idx+1) % len(themes)]
    blend = cycle * 0.25
    def bc(c1,c2,t): return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))
    return {k: bc(base[k], nxt[k], blend) for k in base}


def build_pin_image(headline, keyword, filepath):
    w, h   = 1000, 1500
    theme  = get_daily_theme()
    img    = Image.new("RGB", (w, h), theme["bg_top"])
    draw   = ImageDraw.Draw(img)

    for y in range(h):
        t = y/h
        r = int(theme["bg_top"][0]+(theme["bg_bot"][0]-theme["bg_top"][0])*t)
        g = int(theme["bg_top"][1]+(theme["bg_bot"][1]-theme["bg_top"][1])*t)
        b = int(theme["bg_top"][2]+(theme["bg_bot"][2]-theme["bg_top"][2])*t)
        draw.line([(0,y),(w,y)], fill=(r,g,b))

    draw.rounded_rectangle([55,55,945,1445], radius=36, outline=theme["border"], width=4)

    try:
        f_big  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 54)
        f_med  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        f_sm   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        f_foot = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except:
        f_big = f_med = f_sm = f_foot = ImageFont.load_default()

    draw.text((80,90),  "AI TOOLS DAILY",                     font=f_sm,   fill=theme["txt_l"])
    draw.text((80,130), datetime.now().strftime("%B %d, %Y"), font=f_foot, fill=theme["txt_d"])

    draw.rounded_rectangle([80,230,920,560], radius=30, fill=theme["card_l"])

    words, lines, line = headline.split(), [], ""
    for word in words:
        if len(line+" "+word) <= 20:
            line = line+" "+word if line else word
        else:
            lines.append(line)
            line = word
    if line: lines.append(line)
    y_pos = 275
    for ln in lines[:4]:
        draw.text((115, y_pos), ln, font=f_big, fill=theme["title"])
        y_pos += 65

    draw.rounded_rectangle([80,640,920,990], radius=30, fill=theme["card_d"])
    draw.text((115,690), "Today's Digital Product",           font=f_med, fill="white")
    words2, lines2, line2 = keyword.split(), [], ""
    for word in words2:
        if len(line2+" "+word) <= 30: line2 = line2+" "+word if line2 else word
        else: lines2.append(line2); line2 = word
    if line2: lines2.append(line2)
    y2 = 760
    for ln in lines2[:3]:
        draw.text((115,y2), ln, font=f_sm, fill=theme["txt_l"])
        y2 += 36

    draw.rounded_rectangle([80,1070,920,1270], radius=30, fill=theme["accent"])
    draw.text((115,1120), "Download instantly",              font=f_med,  fill=theme["title"])
    draw.text((115,1180), "Templates • Planners • Trackers",     font=f_sm,   fill=theme["title"])
    draw.text((80,1375),  "Affiliate disclosure included",   font=f_foot, fill=theme["txt_d"])

    img.save(filepath)
    return filepath




# ── 4. Upload to Cloudinary ───────────────────────────────────

def upload_to_cloudinary(filepath, folder, resource_type="raw"):
    result = cloudinary.uploader.upload(
        filepath,
        folder        = folder,
        resource_type = resource_type,
        use_filename  = True,
        unique_filename = True
    )
    return result.get("secure_url")


# ── 5. Main ───────────────────────────────────────────────────

def run():
    print(f"Product creation started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    with open("data/todays_picks.json", "r") as f:
        picks = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    created = []

    for i, pick in enumerate(picks):
        if not is_etsy_safe(pick):
            print(f"Skipped policy-risk product: {pick['keyword']}")
            continue

        keyword = pick["keyword"]
        ptype = pick.get("product_type", "").lower()

        if "planner" in ptype:
            pick["suggested_price"] = min(pick.get("suggested_price", 9.99), 9.99)

        if "tracker" in ptype:
            pick["suggested_price"] = min(pick.get("suggested_price", 7.99), 7.99)

        if "template" in ptype:
            pick["suggested_price"] = min(pick.get("suggested_price", 24.99), 24.99)

        slug = keyword.replace(" ", "_")[:40]
        folder = f"products/{today}/{slug}"
        builder = ProductFileBuilder(folder)
        file_path = builder.build_for_product(keyword, ptype)
        os.makedirs(folder, exist_ok=True)

        print(f"\nCreating product {i+1}/{len(picks)}: {keyword}")

        print("  Generating content with Claude Sonnet...")
        content = generate_product_content(pick)

        pdf_path = f"{folder}/product.pdf"
        print("  Building PDF...")
        build_pdf(content, pick, pdf_path)
        file_url = None

       builder = ProductFileBuilder(folder)
       file_path = builder.build_for_product(keyword, ptype)

        file_url = None

        if file_path:
            file_url = upload_to_cloudinary(
                file_path,
                f"digital-products/{today}",
                resource_type="raw"
            )
            )

        pin_path = f"{folder}/pin.png"
        print("  Building Pinterest image...")
        build_pin_image(content["pin_headline"], keyword, pin_path)

        print("  Uploading to Cloudinary...")
        pdf_url = upload_to_cloudinary(pdf_path, f"digital-products/{today}", resource_type="raw")
        pin_url = upload_to_cloudinary(pin_path, f"pins/{today}", resource_type="image")

        metadata = {
            "keyword": keyword,
            "product_type": pick.get("product_type"),
            "suggested_price": pick.get("suggested_price", 9.00),
            "etsy_title": content["etsy_title"],
            "etsy_description": content["etsy_description"],
            "etsy_tags": content["etsy_tags"],
            "social_post": content["social_post"],
            "pdf_url": pdf_url,
            "pin_url": pin_url,
            "created_at": today,
            "product_file_url": file_url,
        }

        meta_path = f"{folder}/metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        created.append(metadata)
        print(f"  Done — PDF: {pdf_url}")

    with open("data/created_today.json", "w") as f:
        json.dump(created, f, indent=2)

    print(f"\nCreated {len(created)} products. Saved to data/created_today.json")


if __name__ == "__main__":
    run()
