#!/usr/bin/env python3
"""
Convert resume.txt to resume.pdf for email attachments
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def create_resume_pdf():
    """Convert text resume to PDF"""
    
    # Check if text resume exists
    text_resume_path = "data/resume.txt"
    if not os.path.exists(text_resume_path):
        print("❌ Resume file not found at data/resume.txt")
        print("Please create your resume in text format first.")
        return False
    
    # Read the text resume
    with open(text_resume_path, 'r', encoding='utf-8') as f:
        resume_text = f.read()
    
    # Create PDF
    pdf_path = "data/resume.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, 
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1,  # Center alignment
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        leading=14,
    )
    
    # Build the PDF content
    story = []
    
    # Add title
    story.append(Paragraph("Kushall Jain", title_style))
    story.append(Spacer(1, 12))
    
    # Split resume into paragraphs and add to PDF
    paragraphs = resume_text.split('\n\n')
    
    for para in paragraphs:
        if para.strip():
            # Clean up the text for PDF
            clean_para = para.strip().replace('\n', '<br/>')
            story.append(Paragraph(clean_para, normal_style))
            story.append(Spacer(1, 6))
    
    # Build PDF
    doc.build(story)
    
    print(f"✅ Resume PDF created at {pdf_path}")
    return True

if __name__ == "__main__":
    create_resume_pdf()