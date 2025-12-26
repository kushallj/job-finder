import gspread
import json
from typing import List, Optional
from src.config import settings
from datetime import datetime


DEFAULT_SHEET_TITLE = "Job Automation Tracker"
DEFAULT_WORKSHEET = "Applications"
DEFAULT_HEADERS = [
    "timestamp",
    "title",
    "company",
    "location",
    "match_score",
    "matched_skills",
    "missing_skills",
    "recommendations",
    "url",
    "source",
]

SPREADSHEET_ID = "1TPW6yn1gaQaB6bD6VRfmUT7-pEpNSy6nRXxpDAf4n2A"  # unused default sample


class GoogleSheetsClient:
    def __init__(self, credentials_path: Optional[str] = None):
        creds_path = credentials_path or settings.google_credentials_path
        if not creds_path:
            raise ValueError("GOOGLE_CREDENTIALS_PATH is not set")
        self.gc = gspread.service_account(filename=creds_path)
        self.spreadsheet = None
        self.worksheet = None
        # Try to read service account email for helpful messages
        try:
            with open(creds_path, "r") as f:
                data = json.load(f)
                self.service_account_email = data.get("client_email")
        except Exception:
            self.service_account_email = None

    def get_or_create_spreadsheet(self, title: Optional[str] = None) -> None:
        """Open by title if exists, otherwise create a new spreadsheet with that title."""
        title = title or settings.google_sheet_title or DEFAULT_SHEET_TITLE
        try:
            self.spreadsheet = self.gc.open(title)
        except gspread.SpreadsheetNotFound:
            self.spreadsheet = self.gc.create(title)
            # Try sharing with the user's Gmail for visibility
            if settings.gmail_address:
                try:
                    self.spreadsheet.share(settings.gmail_address, perm_type="user", role="writer")
                except Exception:
                    pass

    def get_spreadsheet_by_id(self, spreadsheet_id: str) -> None:
        try:
            self.spreadsheet = self.gc.open_by_key(spreadsheet_id)
        except Exception as e:
            raise RuntimeError(f"Failed to open spreadsheet by ID: {e}")

    def get_spreadsheet_url(self) -> str:
        if not self.spreadsheet:
            raise RuntimeError("Spreadsheet not initialized")
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet.id}"

    def ensure_worksheet(self, name: str = DEFAULT_WORKSHEET, headers: List[str] = DEFAULT_HEADERS) -> None:
        if not self.spreadsheet:
            raise RuntimeError("Spreadsheet not initialized")
        try:
            self.worksheet = self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            self.worksheet = self.spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
            self.worksheet.append_row(headers)

        # Ensure headers are present in row 1
        try:
            existing = self.worksheet.row_values(1)
            if existing != headers:
                # Overwrite headers if mismatch
                self.worksheet.update(f"A1:{gspread.utils.rowcol_to_a1(1, len(headers))}", [headers])
        except Exception:
            pass

    def append_application_row(
        self,
        title: str,
        company: str,
        location: str,
        match_score: int,
        matched_skills: List[str],
        missing_skills: List[str],
        recommendations: str,
        url: str,
        source: str,
    ) -> None:
        if not self.worksheet:
            raise RuntimeError("Worksheet not initialized")

        row = [
            datetime.utcnow().isoformat(timespec="seconds"),
            title,
            company,
            location,
            match_score,
            ", ".join(matched_skills or []),
            ", ".join(missing_skills or []),
            recommendations or "",
            url,
            source,
        ]
        self.worksheet.append_row(row)
