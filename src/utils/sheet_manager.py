import gspread
from google.oauth2.service_account import Credentials
from src.config import settings

class SheetsManager:
    """Manage Google Sheets operations"""
    
    def __init__(self):
        creds = Credentials.from_service_account_file(
            settings.google_credentials_path,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        self.client = gspread.authorize(creds)
    
    def create_tracking_sheet(self, sheet_name: str = "Job Applications"):
        """Create new tracking spreadsheet"""
        sheet = self.client.create(sheet_name)
        worksheet = sheet.sheet1
        
        # Setup headers
        headers = [
            "Job Title", "Company", "Location", "Match Score",
            "Status", "Applied Date", "URL", "Notes"
        ]
        worksheet.update('A1:H1', [headers])
        
        return sheet.url
    
    def add_application(self, sheet_url: str, application_data: dict):
        """Add application to tracking sheet"""
        sheet = self.client.open_by_url(sheet_url)
        worksheet = sheet.sheet1
        
        row = [
            application_data['title'],
            application_data['company'],
            application_data['location'],
            application_data['match_score'],
            application_data['status'],
            application_data['applied_date'],
            application_data['url'],
            application_data['notes']
        ]
        
        worksheet.append_row(row)