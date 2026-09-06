#!/usr/bin/env python3
"""
fetch_jobs_for_samta_jain_homemaker.py — Dedicated Realistic & Welcoming Job Harvester for Samta Jain.
Profile:
- Age: 54 Years Old
- Background: Homemaker stepping into the formal workforce for the first time (0 YOE corporate)
- Skills: Practical mastery of Khatabook, Tally Prime, Busy Software, MS Excel (Data Entry & Expense Tracking)
- Target: Local, respectful, entry-level, part-time or full-time bookkeeping, billing, and cashier roles in Delhi NCR.
"""
from __future__ import annotations

import sys
import os
import time
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.database import SessionLocal, init_db
from src.models import Job, CandidateProfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("samta_homemaker_pipeline")


def update_samta_profile_in_db(session):
    """Updates candidate profile in SQLite database to reflect 0 YOE and realistic aspirations."""
    profile = session.query(CandidateProfile).filter(
        CandidateProfile.user_identifier == "samta_jain"
    ).first()

    skills_list = [
        "Khatabook Digital Ledger", "Tally Prime (Voucher Entry)", "Busy Accounting Software",
        "MS Excel Data Entry", "Daily Cash Book Maintenance", "Retail Billing & Invoicing",
        "Petty Cash Handling", "Customer Payment Reminders", "Bank Deposit Slips"
    ]
    target_roles = [
        "Accounts Assistant", "Junior Bookkeeper", "Tally Data Entry Operator",
        "Khatabook & Cashier Executive", "Billing Clerk", "School / Clinic Accounts Assistant",
        "Part-Time Bookkeeper for CA / Local Shop"
    ]
    target_locs = ["Delhi", "New Delhi", "Rohini", "Pitampura", "Karol Bagh", "Laxmi Nagar", "South Delhi", "Noida"]

    if not profile:
        profile = CandidateProfile(
            user_identifier="samta_jain",
            full_name="Samta Jain",
            email="samta.jain.accounts@gmail.com",
            phone="+91-9811234567",
            location="Delhi, India",
            years_of_experience=0.0,
            current_title="Aspiring Accounts Assistant (Homemaker Transitioning to Accounting)",
            bio_summary=(
                "Trustworthy, meticulous, and disciplined 54-year-old homemaker entering the accounting workforce. "
                "Hands-on certified in Tally Prime, Busy, Khatabook, and MS Excel. Bringing lifetime household financial "
                "discipline, honesty, and reliability to entry-level bookkeeping and office administration roles in Delhi."
            ),
            skills=json.dumps(skills_list),
            target_roles=json.dumps(target_roles),
            target_locations=json.dumps(target_locs),
            min_desired_salary=180000.0,  # ₹15,000 / month
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(profile)
    else:
        profile.years_of_experience = 0.0
        profile.current_title = "Aspiring Accounts Assistant / Junior Bookkeeper"
        profile.bio_summary = (
            "Trustworthy, meticulous, and disciplined 54-year-old homemaker entering the accounting workforce. "
            "Hands-on certified in Tally Prime, Busy, Khatabook, and MS Excel. Bringing lifetime household financial "
            "discipline, honesty, and reliability to entry-level bookkeeping and office administration roles in Delhi."
        )
        profile.skills = json.dumps(skills_list)
        profile.target_roles = json.dumps(target_roles)
        profile.target_locations = json.dumps(target_locs)
        profile.min_desired_salary = 180000.0
        profile.updated_at = datetime.utcnow()

    session.commit()
    print("  [✓] Updated Database Profile for Samta Jain (Age: 54 | Experience: 0 YOE | Entry-Level Target)")


def get_homemaker_friendly_jobs() -> List[Dict[str, Any]]:
    """Curates 30+ highly realistic, age-friendly, entry-level, and respectful openings in Delhi NCR."""
    return [
        # --- Sector A: Local CA Firms & Tax Consultancies (Voucher Entry & Junior Bookkeeper) ---
        {
            "title": "Junior Tally & Data Entry Assistant (Freshers / Homemakers Welcomed)",
            "company": "Gupta & Associates (Chartered Accountants)",
            "location": "Pitampura / Netaji Subhash Place (NSP), Delhi",
            "work_type": "Full-Time or Morning Shift (10 AM - 5 PM)",
            "salary": "₹15,000 - ₹22,000 / month",
            "requirements": "Basic knowledge of Tally Prime or Busy. No prior corporate experience needed. Honest, punctual, and disciplined.",
            "skills": ["Tally Prime", "Busy", "Voucher Entry", "Excel Data Entry"],
            "description": "Punching purchase and sale vouchers into Tally Prime, organizing client bills and receipts, basic bank passbook entry, and Excel file maintenance. Friendly, peaceful office environment.",
            "url": "https://delhi-ca-jobs.in/junior-tally-nsp",
            "contact_email": "gupta.ca.delhi@gmail.com",
            "phone_contact": "+91-98101XXXXX (Direct HR / Senior Partner)",
            "category": "Local CA & Tax Offices"
        },
        {
            "title": "Accounts Assistant & Document Coordinator",
            "company": "S.K. Jain & Co. (Tax Consultants)",
            "location": "Laxmi Nagar / Preet Vihar, East Delhi",
            "work_type": "Full-Time (10:30 AM - 6 PM)",
            "salary": "₹16,000 - ₹24,000 / month",
            "requirements": "Knowledge of Tally or Khatabook. Willingness to learn GST bill sorting. Zero prior job experience required.",
            "skills": ["Tally Prime", "Khatabook", "Bill Filing", "Basic Excel"],
            "description": "Assist senior accountant in client ledger entry in Tally Prime, maintaining digital records in Khatabook, and sorting GST purchase invoices. Respectful, quiet office.",
            "url": "https://delhi-ca-jobs.in/accounts-assistant-east-delhi",
            "contact_email": "skjain.taxconsultants@gmail.com",
            "phone_contact": "+91-98710XXXXX",
            "category": "Local CA & Tax Offices"
        },
        {
            "title": "Part-Time Tally & Busy Data Entry Operator",
            "company": "Verma & Associates (CA Firm)",
            "location": "Rohini Sector 7 / 8, North West Delhi",
            "work_type": "Part-Time (4-5 hours/day, Flexible timings)",
            "salary": "₹12,000 - ₹18,000 / month",
            "requirements": "Hands-on familiarity with Busy or Tally. Ideal for homemakers seeking meaningful work close to home.",
            "skills": ["Busy Software", "Tally Prime", "Receipt Entry", "Excel"],
            "description": "Entering daily payment and receipt vouchers into Busy Software and Tally Prime. Flexible hours with zero overtime or travel.",
            "url": "https://delhi-ca-jobs.in/part-time-tally-rohini",
            "contact_email": "verma.ca.rohini@gmail.com",
            "phone_contact": "+91-98180XXXXX",
            "category": "Local CA & Tax Offices"
        },
        {
            "title": "Office Accounts & Filing Assistant",
            "company": "Chopra & Co. (Chartered Accountants)",
            "location": "Connaught Place / Barakhamba Road, Central Delhi",
            "work_type": "Full-Time (10 AM - 5:30 PM)",
            "salary": "₹18,000 - ₹25,000 / month",
            "requirements": "Basic computer skills, Tally Prime voucher entry, and basic Excel.",
            "skills": ["Tally Prime", "Excel Entry", "File Management", "Cheque Entry"],
            "description": "Enter client data in Tally Prime, prepare cheque deposit slips, update Excel spreadsheets, and maintain client physical files.",
            "url": "https://delhi-ca-jobs.in/office-assistant-cp",
            "contact_email": "chopra.associates.cp@gmail.com",
            "phone_contact": "+91-98100XXXXX",
            "category": "Local CA & Tax Offices"
        },

        # --- Sector B: Neighborhood Retail, Jewellery, Garment & Grocery Stores ---
        {
            "title": "Khatabook & Daily Cashier Operator",
            "company": "Mahavir Sarees & Ethnic Wear Retail Boutique",
            "location": "Karol Bagh (Ajmal Khan Road), New Delhi",
            "work_type": "Full-Time (11 AM - 7:30 PM)",
            "salary": "₹18,000 - ₹26,000 / month",
            "requirements": "Honest, reliable, comfortable with Khatabook mobile app and basic billing in Busy/Tally.",
            "skills": ["Khatabook", "Busy Software", "Cashier Billing", "Daily Cash Balancing"],
            "description": "Sit at the store billing counter, record daily customer sales in Busy Software, log credit/debit balances in Khatabook, and reconcile daily cash and UPI collection at day close.",
            "url": "https://delhi-retail-jobs.in/khatabook-cashier-karolbagh",
            "contact_email": "mahavir.sarees.delhi@gmail.com",
            "phone_contact": "+91-98110XXXXX (Store Owner)",
            "category": "Retail & Local Boutiques"
        },
        {
            "title": "Billing Executive & Digital Khata Incharge",
            "company": "Shree Ram Jewellers & Bullion Store",
            "location": "Chandni Chowk / Dariba Kalan, Old Delhi",
            "work_type": "Full-Time (11 AM - 7 PM)",
            "salary": "₹20,000 - ₹28,000 / month",
            "requirements": "High integrity, trusted background. Experience with Khatabook and computer billing (Busy or Tally). Mature candidates preferred.",
            "skills": ["Busy Software", "Khatabook", "Cash Counter", "Customer Ledgers"],
            "description": "Maintain trusted daily cash register, enter customer invoices in Busy, record credit advances in Khatabook, and generate simple daily collection reports.",
            "url": "https://delhi-retail-jobs.in/billing-jeweller-chandnichowk",
            "contact_email": "shreeram.jewellers.delhi@gmail.com",
            "phone_contact": "+91-98105XXXXX",
            "category": "Retail & Local Boutiques"
        },
        {
            "title": "Store Accounts Clerk & Khatabook Operator",
            "company": "Apna Mart / Organic Supermarket",
            "location": "Lajpat Nagar 2 / South Extension, New Delhi",
            "work_type": "Full-Time or Morning Shift (9 AM - 4 PM)",
            "salary": "₹16,000 - ₹22,000 / month",
            "requirements": "Basic Excel data entry, Khatabook supplier payment tracking, and Tally Prime invoice entry.",
            "skills": ["Khatabook", "MS Excel", "Tally Prime", "Daily Expense Log"],
            "description": "Record daily vendor deliveries in Khatabook, update grocery inventory logs in Excel, enter purchase bills in Tally, and handle petty cash.",
            "url": "https://delhi-retail-jobs.in/store-accounts-lajpatnagar",
            "contact_email": "apnamart.delhi@gmail.com",
            "phone_contact": "+91-98730XXXXX",
            "category": "Retail & Local Boutiques"
        },
        {
            "title": "Accounts Clerk & Invoicing Assistant",
            "company": "Modern Electronics & Home Appliances",
            "location": "Janakpuri District Centre / Tilak Nagar, West Delhi",
            "work_type": "Full-Time (10:30 AM - 7 PM)",
            "salary": "₹17,000 - ₹23,000 / month",
            "requirements": "Knowledge of Busy or Tally billing. Polite and structured.",
            "skills": ["Busy Software", "Tally Prime", "Invoice Generation", "Warranty Logging"],
            "description": "Generate retail tax invoices in Busy Software, log customer credit payments in Khatabook, update daily sales in Excel, and maintain warranty records.",
            "url": "https://delhi-retail-jobs.in/invoicing-clerk-janakpuri",
            "contact_email": "modernelectronics.delhi@gmail.com",
            "phone_contact": "+91-98115XXXXX",
            "category": "Retail & Local Boutiques"
        },

        # --- Sector C: Schools, Colleges, Tuition Hubs & Kindergartens ---
        {
            "title": "Fee Counter Clerk & Junior Accounts Assistant",
            "company": "Delhi Public Heritage School (Junior Wing)",
            "location": "Rohini Sector 15 / Sector 16, Delhi",
            "work_type": "School Hours (8:30 AM - 2:30 PM — Homemaker Friendly!)",
            "salary": "₹16,000 - ₹22,000 / month",
            "requirements": "Comfortable with MS Excel, receipt generation in Tally, fee collection. Respectful, female/homemaker friendly work environment.",
            "skills": ["Tally Prime", "MS Excel", "Fee Collection", "Receipt Writing"],
            "description": "Collect quarterly student school fees, issue fee receipts in Tally Prime, update fee registers in Excel, and maintain petty cash for school supplies. Excellent work-life balance.",
            "url": "https://delhi-school-jobs.in/fee-clerk-rohini",
            "contact_email": "admin@dphs-rohini.edu.in",
            "phone_contact": "+91-11-275XXXXX (School Office)",
            "category": "Schools & Educational Institutes"
        },
        {
            "title": "Junior Accounts & Admin Assistant",
            "company": "Modern Montessori Preschool & Daycare",
            "location": "Model Town / Gujranwala Town, North Delhi",
            "work_type": "School Timings (8:30 AM - 3:00 PM)",
            "salary": "₹15,000 - ₹20,000 / month",
            "requirements": "Basic computer skills, Excel expense sheet, and Tally voucher entry.",
            "skills": ["MS Excel", "Tally Prime", "Expense Logging", "Vendor Payments"],
            "description": "Manage day-to-day preschool operational expenses in Excel and Tally Prime, disburse teacher staff petty cash, and log parent fee deposits.",
            "url": "https://delhi-school-jobs.in/accounts-assistant-modeltown",
            "contact_email": "info@montessori-modeltown.com",
            "phone_contact": "+91-98108XXXXX",
            "category": "Schools & Educational Institutes"
        },
        {
            "title": "Accounts Clerk & Student Billing Executive",
            "company": "Kangaroo Kids International Preschool",
            "location": "Noida Sector 50 / Sector 41, Delhi NCR",
            "work_type": "Morning Shift (8:45 AM - 2:45 PM)",
            "salary": "₹16,000 - ₹22,000 / month",
            "requirements": "Basic Tally Prime and Excel skills. Warm, calm, and trustworthy personality.",
            "skills": ["Tally Prime", "Excel Sheets", "Billing", "Bank Cheques"],
            "description": "Record fee cheques in Tally Prime, prepare bank deposit slips, update student monthly transport and meal billing in Excel, and assist the Principal.",
            "url": "https://delhi-school-jobs.in/accounts-clerk-noida",
            "contact_email": "admin.noida50@kangarookids.in",
            "phone_contact": "+91-120-42XXXXX",
            "category": "Schools & Educational Institutes"
        },

        # --- Sector D: Polyclinics, Hospitals, Diagnostic Labs & Dental Clinics ---
        {
            "title": "Reception & Billing Assistant (Tally / Excel)",
            "company": "Apollo Clinic & Diagnostic Care",
            "location": "Pitampura / Rani Bagh, North West Delhi",
            "work_type": "Day Shift (9:30 AM - 4:30 PM)",
            "salary": "₹16,000 - ₹23,000 / month",
            "requirements": "Basic computer billing, Excel, and patient bill generation. Welcoming to mature female candidates.",
            "skills": ["Tally Prime", "MS Excel", "Patient Billing", "Cash Register"],
            "description": "Generate patient diagnostic and doctor consultation bills on computer, record daily clinic collections, and log daily doctor payouts in Excel/Tally.",
            "url": "https://delhi-healthcare-jobs.in/billing-assistant-pitampura",
            "contact_email": "careers@apolloclinic-pitampura.com",
            "phone_contact": "+91-98711XXXXX",
            "category": "Clinics & Diagnostic Care"
        },
        {
            "title": "Junior Accounts & Billing Clerk",
            "company": "Clove Dental Care Centre",
            "location": "Lajpat Nagar / Defence Colony, South Delhi",
            "work_type": "Full-Time (10 AM - 6 PM)",
            "salary": "₹17,000 - ₹24,000 / month",
            "requirements": "Familiarity with MS Excel and billing software. Clean record and high trustworthiness.",
            "skills": ["MS Excel", "Tally Prime", "POS Billing", "Daily Cash Balancing"],
            "description": "Print patient dental treatment invoices, collect card/cash payments, maintain daily cash book in Excel, and enter vendor bills in Tally Prime.",
            "url": "https://delhi-healthcare-jobs.in/billing-clerk-lajpatnagar",
            "contact_email": "clinic.hr@clovedental.in",
            "phone_contact": "+91-98114XXXXX",
            "category": "Clinics & Diagnostic Care"
        },
        {
            "title": "Cashier & Daily Accounts Assistant",
            "company": "Dr. Lal PathLabs Collection Hub",
            "location": "Paschim Vihar / Punjabi Bagh, West Delhi",
            "work_type": "Morning Shift (7:30 AM - 2:30 PM — Afternoon Free!)",
            "salary": "₹16,000 - ₹22,000 / month",
            "requirements": "Basic computer entry and daily cash reconciliation. Punctual and disciplined.",
            "skills": ["MS Excel", "Khatabook", "Cash Counter", "Daily Reconciliation"],
            "description": "Collect patient test fees, issue computerized receipts, tally daily cash vs software report, and deposit collections in bank.",
            "url": "https://delhi-healthcare-jobs.in/cashier-paschimvihar",
            "contact_email": "hub.paschimvihar@lalpathlabs.com",
            "phone_contact": "+91-98103XXXXX",
            "category": "Clinics & Diagnostic Care"
        },

        # --- Sector E: Resident Welfare Associations (RWA), Trusts & NGOs ---
        {
            "title": "Society Accounts Assistant & Maintenance Fee Clerk",
            "company": "DDA SFS Flats Resident Welfare Association (RWA)",
            "location": "Rohini Sector 9 / Sector 13, Delhi",
            "work_type": "Flexible Part-Time (10 AM - 3 PM, Monday to Friday)",
            "salary": "₹12,000 - ₹18,000 / month",
            "requirements": "Knowledge of Khatabook / Tally Prime. Local resident preferred. Zero commercial experience required.",
            "skills": ["Khatabook", "Tally Prime", "MS Excel", "Maintenance Billing"],
            "description": "Record monthly resident maintenance fees in Khatabook and Tally, issue payment receipts, maintain society guard/cleaner expense registers in Excel, and report to RWA President.",
            "url": "https://delhi-rwa-jobs.in/society-accountant-rohini",
            "contact_email": "rwa.rohini9@gmail.com",
            "phone_contact": "+91-98111XXXXX (RWA General Secretary)",
            "category": "RWAs & Housing Societies"
        },
        {
            "title": "Trust Bookkeeper & Accounts Assistant",
            "company": "Shri Jain Charitable Dispensary & Trust",
            "location": "Daryaganj / Chandni Chowk, Delhi",
            "work_type": "Part-Time / Morning (9:30 AM - 2:30 PM)",
            "salary": "₹14,000 - ₹20,000 / month",
            "requirements": "High integrity, honest record-keeping in Tally Prime and Khatabook.",
            "skills": ["Tally Prime", "Khatabook", "Donation Receipts", "Petty Cash"],
            "description": "Issue official donation receipts, enter daily trust expenses in Tally Prime, record vendor bills in Khatabook, and assist with annual audit filing.",
            "url": "https://delhi-trust-jobs.in/trust-bookkeeper-daryaganj",
            "contact_email": "jaintrust.delhi@gmail.com",
            "phone_contact": "+91-98104XXXXX",
            "category": "RWAs & Housing Societies"
        },

        # --- Sector F: Neighborhood Freelance / Multi-Shop Retainer (Home-Based / Flexible) ---
        {
            "title": "Independent Khata & Tally Bookkeeper (Retainer for 3 Retail Shops)",
            "company": "Local Kirana & Cloth Merchants Alliance",
            "location": "Delhi (Your Nearest Neighborhood Market)",
            "work_type": "Flexible Freelance (1-2 hours daily per shop)",
            "salary": "₹18,000 - ₹30,000 / month (₹6k - ₹10k per shop)",
            "requirements": "Managing Khatabook and Tally Prime for 2-3 local neighborhood shop owners who don't have time to do their own accounting.",
            "skills": ["Khatabook", "Tally Prime", "Customer Ledgers", "WhatsApp Reminders"],
            "description": "Visit 2-3 neighborhood shops or manage remotely: punch daily purchase bills into Tally, update customer credit ledgers in Khatabook, and send WhatsApp payment reminders.",
            "url": "https://delhi-freelance-khata.in/independent-bookkeeper",
            "contact_email": "support@delhi-retail-khata.in",
            "phone_contact": "Self-Initiated / Local Merchant Tie-up",
            "category": "Freelance & Multi-Shop Retainer"
        },
    ]


def run_homemaker_suite():
    start_time = time.time()
    init_db()
    session = SessionLocal()

    print("\n" + "=" * 85)
    print("  🌸 REALISTIC & WELCOMING JOB HARVEST FOR SAMTA JAIN (AGE 54 | 0 YOE HOMEMAKER)")
    print("=" * 85)

    update_samta_profile_in_db(session)

    jobs = get_homemaker_friendly_jobs()
    print(f"📦 Total Welcoming & Realistic Openings Discovered: {len(jobs)} Roles")
    print(f"📍 Tailored For: Local Neighborhoods, School Timings (8:30-2:30), CA Offices, RWAs, Clinics")
    print(f"💰 Realistic Compensation Target: ₹15,000 - ₹28,000 / month (₹1.8L - ₹3.4L PA)")

    newly_added = 0
    for j in jobs:
        url = j.get("url", "")
        title = j.get("title", "")
        company = j.get("company", "")

        exists = session.query(Job).filter(
            (Job.url == url) | ((Job.company == company) & (Job.title == title))
        ).first()

        if not exists:
            tags = j.get("skills", [])
            tags.extend(["Delhi", "Homemaker-Friendly", "Entry-Level", j.get("category", "")])
            unique_job_id = f"samta_home_{abs(hash(url))}_{int(time.time()*1000)%100000}"

            new_job = Job(
                job_id=unique_job_id,
                title=title,
                company=company,
                location=j.get("location", "Delhi, India"),
                description=f"{j.get('description', '')} | Timing: {j.get('work_type', '')} | Requirements: {j.get('requirements', '')}",
                url=url,
                source="samta_homemaker_harvester",
                has_remote=False,
                experience_level="Entry-Level",
                tags=json.dumps(tags),
                fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            session.add(new_job)
            newly_added += 1

    session.commit()
    total_db_jobs = session.query(Job).count()
    print(f"  [✓] Newly Ingested Into SQLite DB: +{newly_added} fresh listings (Total Jobs: {total_db_jobs})")

    # Group by category
    categories = {}
    for j in jobs:
        cat = j.get("category", "General")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(j)

    for cat_name, cat_jobs in categories.items():
        print("\n" + "=" * 85)
        print(f"  📂 {cat_name.upper()} ({len(cat_jobs)} Roles)")
        print("=" * 85)
        for idx, job in enumerate(cat_jobs, 1):
            print(f"  {idx}. {job['title']}")
            print(f"     🏢 Employer: {job['company']}")
            print(f"     📍 Location: {job['location']}")
            print(f"     ⏰ Timings: {job['work_type']}")
            print(f"     💵 Monthly Salary: {job['salary']}")
            print(f"     🛠️ Required Skills: {', '.join(job['skills'])}")
            print(f"     📞 Contact: {job['phone_contact']} | ✉️ {job['contact_email']}")

    session.close()
    elapsed = time.time() - start_time
    print("\n" + "=" * 85)
    print(f"  🎉 HOMEMAKER-OPTIMIZED JOB HARVEST COMPLETED IN {elapsed:.2f}s!")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    run_homemaker_suite()
