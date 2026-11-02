import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors

# ── Page geometry ─────────────────────────────────────────────────────────────
# 0.45in margins + tight leading = everything fits on one page.
# Previously: 72pt (1in) margins with 14pt leading → 5 pages
LEFT_MARGIN = RIGHT_MARGIN = 0.45 * inch
TOP_MARGIN = 0.4 * inch
BOTTOM_MARGIN = 0.35 * inch

# ── Typography scale ──────────────────────────────────────────────────────────
NAME_SIZE       = 15
TAGLINE_SIZE    = 8.5
CONTACT_SIZE    = 8.5
SECTION_SIZE    = 9.5
JOB_TITLE_SIZE  = 9
COMPANY_SIZE    = 8.5
BODY_SIZE       = 8.2
BULLET_SIZE     = 8.2
SKILL_SIZE      = 8.0

SECTION_COLOR   = colors.HexColor("#1a1a2e")   # deep navy
RULE_COLOR      = colors.HexColor("#1a1a2e")


def styles():
    """All paragraph styles in one place."""

    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "name": s("name",
            fontName="Helvetica-Bold", fontSize=NAME_SIZE,
            leading=NAME_SIZE + 2, alignment=TA_CENTER,
            spaceAfter=1, textColor=SECTION_COLOR),

        "tagline": s("tagline",
            fontName="Helvetica", fontSize=TAGLINE_SIZE,
            leading=TAGLINE_SIZE + 2, alignment=TA_CENTER,
            spaceAfter=1, textColor=colors.HexColor("#444444")),

        "contact": s("contact",
            fontName="Helvetica", fontSize=CONTACT_SIZE,
            leading=CONTACT_SIZE + 2, alignment=TA_CENTER,
            spaceAfter=4, textColor=colors.HexColor("#333333")),

        "section": s("section",
            fontName="Helvetica-Bold", fontSize=SECTION_SIZE,
            leading=SECTION_SIZE + 1, spaceBefore=5, spaceAfter=1,
            textColor=SECTION_COLOR, alignment=TA_LEFT),

        "job_title": s("job_title",
            fontName="Helvetica-Bold", fontSize=JOB_TITLE_SIZE,
            leading=JOB_TITLE_SIZE + 1, spaceBefore=4, spaceAfter=0),

        "company": s("company",
            fontName="Helvetica-Oblique", fontSize=COMPANY_SIZE,
            leading=COMPANY_SIZE + 1, spaceBefore=0, spaceAfter=1,
            textColor=colors.HexColor("#444444")),

        "bullet": s("bullet",
            fontName="Helvetica", fontSize=BULLET_SIZE,
            leading=BULLET_SIZE + 2.2,
            leftIndent=10, firstLineIndent=-10,
            spaceBefore=0, spaceAfter=0.5),

        "skill_label": s("skill_label",
            fontName="Helvetica-Bold", fontSize=SKILL_SIZE,
            leading=SKILL_SIZE + 2.5, spaceBefore=0, spaceAfter=0),

        "skill_line": s("skill_line",
            fontName="Helvetica", fontSize=SKILL_SIZE,
            leading=SKILL_SIZE + 2.5, spaceBefore=0, spaceAfter=0),

        "project_title": s("project_title",
            fontName="Helvetica-Bold", fontSize=BODY_SIZE,
            leading=BODY_SIZE + 2, spaceBefore=3, spaceAfter=0),

        "project_body": s("project_body",
            fontName="Helvetica", fontSize=BODY_SIZE - 0.2,
            leading=BODY_SIZE + 1.8, spaceBefore=0, spaceAfter=0),

        "body": s("body",
            fontName="Helvetica", fontSize=BODY_SIZE,
            leading=BODY_SIZE + 2.5, spaceBefore=0, spaceAfter=0),
    }


def rule(story):
    story.append(HRFlowable(
        width="100%", thickness=0.6,
        color=RULE_COLOR, spaceAfter=2, spaceBefore=0))


def section_header(story, title, st):
    story.append(Paragraph(title.upper(), st["section"]))
    rule(story)


def bullet_para(text, st):
    """Render a bullet with proper indent and bullet char."""
    clean = text.lstrip("•-– ").strip()
    return Paragraph(f"• {clean}", st["bullet"])


def build_story(st):
    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Kushall Jain", st["name"]))
    story.append(Paragraph(
        "Software Development Engineer &nbsp;·&nbsp; "
        "Full Stack Web Development &nbsp;·&nbsp; RESTful APIs &nbsp;·&nbsp; Cloud Architecture",
        st["tagline"]))
    story.append(Paragraph(
        "kushall.jain07@gmail.com &nbsp;|&nbsp; "
        "linkedin.com/in/kushall-jain-263009261 &nbsp;|&nbsp; "
        "github.com/kushallj &nbsp;|&nbsp; kushall.in &nbsp;|&nbsp; 9990079764",
        st["contact"]))

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    section_header(story, "Professional Summary", st)
    story.append(Paragraph(
        "Software Development Engineer with <b>3+ years</b> designing, developing, and deploying "
        "enterprise-grade web applications and RESTful APIs. Proven expertise in full-stack development "
        "with React (TypeScript), Python (Django/FastAPI), Node.js, and PostgreSQL. Delivered "
        "mission-critical systems processing <b>150+ Cr monthly transactions</b> with <b>99.5% uptime</b> "
        "serving <b>1000+ SMEs</b> and <b>10,000+ DAU</b>. Strong foundation in SOLID/OOP principles, "
        "microservices architecture, and agile methodologies. Currently expanding into C# and .NET.",
        st["body"]))

    # ── TECHNICAL SKILLS ──────────────────────────────────────────────────────
    section_header(story, "Technical Skills", st)

    skill_rows = [
        ("Languages & Frameworks",
         "Python (FastAPI, Django REST), Node.js (Express), JavaScript/TypeScript (ES6+), "
         "React.js, Redux Toolkit, HTML5, CSS3 &nbsp;·&nbsp; <i>Learning:</i> C#, .NET Core"),
        ("Architecture & Design",
         "RESTful API Design, Microservices, MVC, SOLID Principles, OOP, "
         "Design Patterns (Factory, Singleton, Strategy), Async Programming"),
        ("Databases",
         "PostgreSQL (Advanced), MySQL, MongoDB, Django ORM, "
         "SQL Optimization, Query Performance Tuning"),
        ("Cloud & DevOps",
         "AWS (S3, ECS, IAM), Docker, Git/GitHub, CI/CD (GitHub Actions), Postman, Agile/Scrum"),
    ]

    for label, val in skill_rows:
        story.append(Paragraph(
            f"<b>{label}:</b> {val}", st["skill_line"]))

    # ── EXPERIENCE ────────────────────────────────────────────────────────────
    section_header(story, "Professional Experience", st)

    # --- Progfin ---
    story.append(Paragraph("Full Stack Software Developer", st["job_title"]))
    story.append(Paragraph(
        "Progfin Pvt Ltd (FinTech) &nbsp;·&nbsp; Dec 2023 – Present &nbsp;·&nbsp; Delhi, India",
        st["company"]))

    progfin_bullets = [
        "Architected mission-critical financial platform serving <b>1000+ SMEs</b> and "
        "<b>10,000+ DAU</b>, processing <b>150+ Cr monthly transactions</b> at <b>99.5% uptime</b> "
        "— stack: React 18/TypeScript, Django/FastAPI, PostgreSQL, AWS",

        "Built 10+ RESTful microservices with Pydantic validation, JWT auth, role-based authorization, "
        "and Swagger/OpenAPI docs; async task processing via <b>Celery</b>",

        "Designed normalized PostgreSQL schemas with strategic indexing; optimized ORM queries "
        "(select_related, prefetch_related) achieving <b>70% query performance improvement</b>",

        "Reduced SQL response time <b>800ms → 200ms (75%)</b> via systematic profiling of "
        "complex joins, subqueries, and aggregations",

        "Delivered credit scoring rule engine and automated lending workflows, achieving "
        "<b>85% process automation</b> across real-time financial data pipelines",

        "Mentored 2 junior developers; led code reviews enforcing SOLID principles and "
        "architectural guidance across sprint cycles",
    ]

    for b in progfin_bullets:
        story.append(bullet_para(b, st))

    story.append(Spacer(1, 3))

    # --- ByteDance ---
    story.append(Paragraph("Subject Matter Expert — EdTech Platform", st["job_title"]))
    story.append(Paragraph(
        "ByteDance Pvt Ltd &nbsp;·&nbsp; Apr 2020 – Nov 2021 &nbsp;·&nbsp; India",
        st["company"]))

    bytedance_bullets = [
        "Built Django REST Framework APIs for content management system serving grades 9–12 "
        "platform with <b>2M+ video views</b>; contributed to <b>30% enrollment growth</b>",

        "Implemented business logic for learning analytics and recommendation engine, "
        "driving <b>25% increase in user engagement</b>",

        "Analyzed <b>2M+ user interactions</b> (Python/Pandas/NumPy) to derive product insights; "
        "built ETL data pipelines for quality reporting",

        "Automated content validation, data extraction, and bulk operations via Python scripts — "
        "reduced manual work by <b>60%</b>; cut support tickets <b>40%</b> via proactive error handling",
    ]

    for b in bytedance_bullets:
        story.append(bullet_para(b, st))

    # ── PROJECTS ──────────────────────────────────────────────────────────────
    section_header(story, "Key Projects", st)

    story.append(Paragraph(
        "<b>Enterprise Financial Platform</b> &nbsp;·&nbsp; "
        "<i>Django REST, FastAPI, React/TypeScript, PostgreSQL, AWS</i>",
        st["project_title"]))
    story.append(Paragraph(
        "Production system processing 150+ Cr monthly across 25+ institutions. "
        "Credit scoring microservices, automated lending workflows, real-time dashboards — "
        "85% process automation.",
        st["project_body"]))

    story.append(Spacer(1, 2))

    story.append(Paragraph(
        "<b>DevFrnds</b> — Developer Networking Platform &nbsp;·&nbsp; "
        "<i>React/TypeScript, Node.js, MongoDB</i> &nbsp;·&nbsp; 2023 &nbsp;·&nbsp; "
        "devfrnds.online",
        st["project_title"]))
    story.append(Paragraph(
        "Full-stack developer matching platform (500+ users). Swipe-based matching, "
        "real-time WebSocket chat, JWT auth, RESTful APIs for user/connection/messaging management.",
        st["project_body"]))

    # ── EDUCATION ─────────────────────────────────────────────────────────────
    section_header(story, "Education", st)
    story.append(Paragraph(
        "<b>B.Tech in Civil Engineering</b> &nbsp;·&nbsp; "
        "G L Bajaj Institute of Technology &amp; Management &nbsp;·&nbsp; 2014 – 2018",
        st["body"]))
    story.append(Paragraph(
        "Relevant: Data Structures &amp; Algorithms, OOP, DBMS, Software Engineering, "
        "Web Technologies, Computer Networks",
        st["project_body"]))

    # ── CERTIFICATIONS ────────────────────────────────────────────────────────
    section_header(story, "Certifications & Additional", st)
    story.append(Paragraph(
        "<b>Frontend:</b> React – The Complete Guide (TypeScript), Advanced React Patterns, Redux Toolkit &nbsp;·&nbsp; "
        "<b>Database:</b> PostgreSQL Performance Tuning, Advanced SQL, Database Design &nbsp;·&nbsp; "
        "<b>Learning:</b> C# Fundamentals, .NET Core, ASP.NET Core &nbsp;·&nbsp; "
        "<b>LeetCode:</b> 300+ problems solved",
        st["skill_line"]))

    return story


def create_resume_pdf():
    """Convert text resume to PDF — drop-in replacement for original script."""

    text_resume_path = "data/resume.txt"
    if not os.path.exists(text_resume_path):
        print("❌ Resume file not found at data/resume.txt")
        print("Please create your resume in text format first.")
        return False

    pdf_path = "data/resume.pdf"
    os.makedirs("data", exist_ok=True)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )

    st = styles()
    story = build_story(st)
    doc.build(story)

    print(f"✅ Resume PDF created at {pdf_path}")
    return True


if __name__ == "__main__":
    create_resume_pdf()