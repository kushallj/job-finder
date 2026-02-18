import httpx
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

@dataclass
class Contact:
    name: str
    title: str
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    company: str = ""
    department: str = ""
    confidence_score: int = 0  # 0-100

class ContactFinder:
    """Find HR and Engineering Manager contacts for companies"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        
    async def find_company_contacts(self, company_name: str, job_title: str = "") -> List[Contact]:
        """Find contacts for a company using multiple methods"""
        contacts = []
        
        # Method 1: LinkedIn search (requires LinkedIn API or scraping)
        linkedin_contacts = await self._search_linkedin(company_name)
        contacts.extend(linkedin_contacts)
        
        # Method 2: Company website search
        website_contacts = await self._search_company_website(company_name)
        contacts.extend(website_contacts)
        
        # Method 3: Apollo.io style email pattern matching
        email_contacts = await self._generate_email_patterns(company_name, contacts)
        contacts.extend(email_contacts)
        
        # Filter and rank contacts
        filtered_contacts = self._filter_relevant_contacts(contacts, job_title)
        return sorted(filtered_contacts, key=lambda x: x.confidence_score, reverse=True)
    
    async def _search_linkedin(self, company_name: str) -> List[Contact]:
        """Search LinkedIn for company employees (placeholder - needs LinkedIn API)"""
        # This would require LinkedIn API access or web scraping
        # For now, return empty list - you'd need to implement based on your access
        return []
    
    async def _search_company_website(self, company_name: str) -> List[Contact]:
        """Search company website for contact information"""
        contacts = []
        
        try:
            # Try to find company website
            website_url = await self._find_company_website(company_name)
            if not website_url:
                return contacts
            
            # Search common pages for contacts
            pages_to_check = [
                f"{website_url}/about",
                f"{website_url}/team", 
                f"{website_url}/leadership",
                f"{website_url}/contact",
                f"{website_url}/careers"
            ]
            
            for page_url in pages_to_check:
                try:
                    response = await self.client.get(page_url)
                    if response.status_code == 200:
                        page_contacts = self._extract_contacts_from_html(response.text, company_name)
                        contacts.extend(page_contacts)
                except:
                    continue
                    
        except Exception as e:
            print(f"❌ Error searching company website: {e}")
            
        return contacts
    
    async def _find_company_website(self, company_name: str) -> Optional[str]:
        """Find company website URL"""
        try:
            # Search for company website
            search_query = f"{company_name} official website"
            # This is a simplified approach - you might want to use Google Search API
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
            response = await self.client.get(search_url)
            if response.status_code == 200:
                # Extract first result URL (simplified)
                # In practice, you'd want to use Google Search API or similar
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if 'url?q=' in href:
                        url = href.split('url?q=')[1].split('&')[0]
                        if self._is_likely_company_website(url, company_name):
                            return url
                            
        except Exception as e:
            print(f"❌ Error finding company website: {e}")
            
        return None
    
    def _is_likely_company_website(self, url: str, company_name: str) -> bool:
        """Check if URL is likely the company's official website"""
        domain = urlparse(url).netloc.lower()
        company_lower = company_name.lower().replace(' ', '').replace(',', '').replace('.', '')
        
        # Simple heuristics
        if company_lower in domain:
            return True
        if any(word in domain for word in ['linkedin', 'facebook', 'twitter', 'instagram']):
            return False
            
        return True
    
    def _extract_contacts_from_html(self, html: str, company_name: str) -> List[Contact]:
        """Extract contact information from HTML"""
        contacts = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, html)
        
        # Look for names and titles in common patterns
        text = soup.get_text()
        
        # Common title patterns for HR and Engineering
        title_patterns = [
            r'(HR Manager|Human Resources Manager|People Manager)',
            r'(Engineering Manager|Tech Lead|CTO|VP Engineering)',
            r'(Talent Acquisition|Recruiter|Hiring Manager)',
            r'(Head of Engineering|Director of Engineering)'
        ]
        
        for email in emails:
            # Try to find associated name and title
            contact = Contact(
                name=self._extract_name_near_email(text, email),
                title="",
                email=email,
                company=company_name,
                confidence_score=30
            )
            contacts.append(contact)
        
        return contacts
    
    def _extract_name_near_email(self, text: str, email: str) -> str:
        """Extract name that appears near an email address"""
        # Simple approach - look for capitalized words near the email
        email_index = text.find(email)
        if email_index == -1:
            return "Unknown"
            
        # Look in surrounding text
        start = max(0, email_index - 100)
        end = min(len(text), email_index + 100)
        surrounding = text[start:end]
        
        # Find capitalized words that could be names
        name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
        names = re.findall(name_pattern, surrounding)
        
        return names[0] if names else "Unknown"
    
    async def _generate_email_patterns(self, company_name: str, existing_contacts: List[Contact]) -> List[Contact]:
        """Generate likely email patterns for the company"""
        contacts = []
        
        # Get company domain
        domain = await self._get_company_domain(company_name)
        if not domain:
            return contacts
        
        # Common name patterns for key roles
        key_roles = [
            ("HR Manager", ["hr", "people", "talent"]),
            ("Engineering Manager", ["engineering", "tech", "dev"]),
            ("CTO", ["cto"]),
            ("VP Engineering", ["vp.engineering", "vpeng"])
        ]
        
        for title, email_prefixes in key_roles:
            for prefix in email_prefixes:
                email = f"{prefix}@{domain}"
                contact = Contact(
                    name="Unknown",
                    title=title,
                    email=email,
                    company=company_name,
                    confidence_score=20  # Lower confidence for generated emails
                )
                contacts.append(contact)
        
        return contacts
    
    async def _get_company_domain(self, company_name: str) -> Optional[str]:
        """Get company email domain"""
        # Try common patterns
        clean_name = company_name.lower().replace(' ', '').replace(',', '').replace('.', '')
        
        common_patterns = [
            f"{clean_name}.com",
            f"{clean_name}.io", 
            f"{clean_name}.co",
            f"{clean_name}.net"
        ]
        
        for domain in common_patterns:
            try:
                # Check if domain exists (simplified check)
                response = await self.client.head(f"https://{domain}", timeout=5.0)
                if response.status_code < 400:
                    return domain
            except:
                continue
                
        return None
    
    def _filter_relevant_contacts(self, contacts: List[Contact], job_title: str = "") -> List[Contact]:
        """Filter contacts to focus on HR and Engineering roles"""
        relevant_keywords = [
            'hr', 'human resources', 'people', 'talent', 'recruiter', 'hiring',
            'engineering', 'tech', 'cto', 'vp', 'director', 'manager', 'lead'
        ]
        
        filtered = []
        for contact in contacts:
            title_lower = contact.title.lower()
            
            # Boost confidence for relevant titles
            if any(keyword in title_lower for keyword in relevant_keywords):
                contact.confidence_score += 30
                
            # Boost confidence for engineering roles if it's a tech job
            if job_title and any(tech_word in job_title.lower() for tech_word in ['engineer', 'developer', 'tech']):
                if any(eng_word in title_lower for eng_word in ['engineering', 'tech', 'cto', 'vp']):
                    contact.confidence_score += 20
            
            # Only include contacts with reasonable confidence
            if contact.confidence_score >= 20:
                filtered.append(contact)
        
        return filtered
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()