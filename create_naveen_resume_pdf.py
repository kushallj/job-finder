import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors

# ── Page geometry ─────────────────────────────────────────────────────────────
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
BULLET_SIZE     = 8.0
SKILL_SIZE      = 8.0

SECTION_COLOR   = colors.HexColor("#1a1a2e")
RULE_COLOR      = colors.HexColor("#1a1a2e")


def styles():
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "name": s("name",
            fontName="Helvetica-Bold", fontSize=NAME_SIZE,
            leading=NAME_SIZE + 2, alignment=TA_CENTER,
            spaceAfter=1, textColor=SECTION_COLOR),

        "tagline": s("tagline",
            fontName="Helvetica-Bold", fontSize=TAGLINE_SIZE,
            leading=TAGLINE_SIZE + 2, alignment=TA_CENTER,
            spaceAfter=1, textColor=colors.HexColor("#333333")),

        "contact": s("contact",
            fontName="Helvetica", fontSize=CONTACT_SIZE,
            leading=CONTACT_SIZE + 2, alignment=TA_CENTER,
            spaceAfter=4, textColor=colors.HexColor("#444444")),

        "section": s("section",
            fontName="Helvetica-Bold", fontSize=SECTION_SIZE,
            leading=SECTION_SIZE + 1, spaceBefore=5, spaceAfter=1,
            textColor=SECTION_COLOR, alignment=TA_LEFT),

        "job_title": s("job_title",
            fontName="Helvetica-Bold", fontSize=JOB_TITLE_SIZE,
            leading=JOB_TITLE_SIZE + 1, spaceBefore=4, spaceAfter=0),

        "company": s("company",
            fontName="Helvetica-Oblique", fontSize=COMPANY_SIZE,
            leading=COMPANY_SIZE + 1, spaceAfter=2,
            textColor=colors.HexColor("#444444")),

        "body": s("body",
            fontName="Helvetica", fontSize=BODY_SIZE,
            leading=BODY_SIZE + 2.5, spaceAfter=3),

        "bullet": s("bullet",
            fontName="Helvetica", fontSize=BULLET_SIZE,
            leading=BULLET_SIZE + 2.0, leftIndent=9, firstLineIndent=-9,
            spaceAfter=1.5),

        "skill_line": s("skill_line",
            fontName="Helvetica", fontSize=SKILL_SIZE,
            leading=SKILL_SIZE + 2.2, spaceAfter=1.5),
    }


def rule(story):
    story.append(HRFlowable(
        width="100%", thickness=0.6,
        color=RULE_COLOR, spaceBefore=1, spaceAfter=3))


def section_header(story, title, st):
    story.append(Paragraph(title.upper(), st["section"]))
    rule(story)


def bullet_para(text, st):
    clean = text.lstrip("•-– ").strip()
    return Paragraph(f"• {clean}", st["bullet"])


def build_story(st):
    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    story.append(Paragraph("NAVEEN SINGH", st["name"]))
    story.append(Paragraph(
        "Data Analyst &nbsp;|&nbsp; Financial Analytics &nbsp;|&nbsp; Machine Learning",
        st["tagline"]))
    story.append(Paragraph(
        "Faridabad, 121003 &nbsp;|&nbsp; +91 7053562057 &nbsp;|&nbsp; "
        "singh.naveen000007@gmail.com &nbsp;|&nbsp; "
        "linkedin.com/in/singh-naveen-pjn/",
        st["contact"]))

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    section_header(story, "Summary", st)
    story.append(Paragraph(
        "Results-driven <b>Data Analyst with 2+ years of experience</b> in data analytics, SQL, financial analytics, "
        "machine learning, and business intelligence dashboard development. Skilled in ETL pipeline optimization, "
        "financial risk detection through <b>Suspicious Transaction Monitoring (STR)</b>, fraud detection, and data visualization. "
        "Proven track record of delivering data-driven insights that improve operational efficiency, strengthen financial "
        "risk management, and reduce losses through data analysis and reporting automation.",
        st["body"]))

    # ── EXPERIENCE ────────────────────────────────────────────────────────────
    section_header(story, "Experience", st)

    # --- Progfin ---
    story.append(Paragraph("Analyst &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; December 2023 – Present", st["job_title"]))
    story.append(Paragraph(
        "Progfin Pvt Ltd &nbsp;·&nbsp; Delhi, India",
        st["company"]))

    progfin_bullets = [
        "Optimized complex SQL queries and automated ETL reporting processes, <b>reducing manual reporting time by 40%</b>.",
        "Led ledger analysis initiatives, identifying financial discrepancies and <b>reducing reconciliation errors by 30%</b>.",
        "Executed <b>Suspicious Transaction Monitoring (STR)</b> project, detecting high-risk transactions and <b>improving fraud detection efficiency by 35%</b>.",
        "Analyzed distributor onboarding data, <b>minimizing potential financial risk exposure by 25%</b>.",
        "Developed real-time dashboards using <b>Metabase</b>, <b>improving decision-making speed by 50%</b> across teams.",
        "Conducted employee attrition analysis, identifying churn drivers and supporting HR strategies that <b>reduced turnover risk by 20%</b>.",
    ]
    for b in progfin_bullets:
        story.append(bullet_para(b, st))

    story.append(Spacer(1, 3))

    # --- Bugendaitech ---
    story.append(Paragraph("Data Scientist Intern &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; June 2023 – August 2023", st["job_title"]))
    story.append(Paragraph(
        "Bugendaitech &nbsp;·&nbsp; Pune, India",
        st["company"]))

    intern_bullets = [
        "Built supervised machine learning models (regression & classification) achieving <b>85% prediction accuracy</b>.",
        "Performed data preprocessing and feature engineering using Python (Pandas), <b>improving model performance by 20%</b>.",
        "Delivered analytical presentations to stakeholders, improving reporting clarity and insight adoption.",
    ]
    for b in intern_bullets:
        story.append(bullet_para(b, st))

    # ── SKILLS ────────────────────────────────────────────────────────────────
    section_header(story, "Skills", st)

    skill_rows = [
        ("Languages & Querying", "SQL, Python (Pandas), Data Analytics, Data Analysis"),
        ("Data Engineering", "DBT, AWS DMS, ETL Pipelines, Data Preprocessing, Feature Engineering"),
        ("Machine Learning", "Regression, Classification, Supervised Learning, Model Evaluation"),
        ("Visualization & BI", "Metabase, Tableau, Business Intelligence, Dashboard Development, Data Visualization"),
        ("Domain Expertise", "STR Monitoring, Financial Data Analysis, Financial Risk Management, Fraud Detection, Ledger Reconciliation, Reporting Automation"),
        ("Tools & Technologies", "Chitthi, Metabase, Infobip, DBeaver, SharePoint, Jupyter Notebook"),
    ]
    for label, val in skill_rows:
        story.append(Paragraph(f"<b>{label}:</b> {val}", st["skill_line"]))

    # ── EDUCATION & CERTIFICATIONS ─────────────────────────────────────────────
    section_header(story, "Education & Certifications", st)

    story.append(Paragraph("<b>MSc Computer Science</b> &nbsp;·&nbsp; PTJLN College, Faridabad (MDU University) &nbsp;·&nbsp; 2022", st["skill_line"]))
    story.append(Paragraph("<b>BCA</b> &nbsp;·&nbsp; PTJLN College, Faridabad (MDU University) &nbsp;·&nbsp; 2020", st["skill_line"]))
    story.append(Paragraph("<b>PGP Advanced in Data Science and Machine Learning</b> &nbsp;·&nbsp; NIIT, Pune", st["skill_line"]))
    story.append(Paragraph("<b>Data Analytics</b> &nbsp;·&nbsp; Dreamer Infotech &nbsp;·&nbsp; 2022", st["skill_line"]))

    return story


def generate_pdf(output_path="data/resume.pdf"):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )
    doc.build(build_story(styles()))
    print(f"Generated {output_path} successfully.")


if __name__ == "__main__":
    generate_pdf()
