"""Parse job postings to extract company, title, department"""

import re
import os
from typing import Optional, Dict
from bs4 import BeautifulSoup


class JobParser:
    """
    Extract structured data from job postings.
    
    Handles various job board formats (LinkedIn, Greenhouse, Lever, etc.)
    """
    
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai and bool(os.getenv("OPENAI_API_KEY"))
        
        if self.use_ai:
            try:
                from openai import OpenAI
                self.client = OpenAI()
            except:
                self.use_ai = False
    
    def parse(self, job_url: str, job_html: Optional[str] = None, 
              job_text: Optional[str] = None) -> Dict:
        """
        Parse job posting to extract key information.
        
        Args:
            job_url: URL of job posting
            job_html: Raw HTML (optional)
            job_text: Extracted text (optional)
        
        Returns:
            Dict with company, title, department, etc.
        """
        result = {
            "company": None,
            "company_domain": None,
            "job_title": None,
            "department": None,
            "location": None,
            "seniority": None,
        }
        
        # Extract from URL first
        result.update(self._parse_from_url(job_url))
        
        # If we have HTML, parse it
        if job_html:
            result.update(self._parse_from_html(job_html))
        
        # If we have text, parse it
        if job_text:
            result.update(self._parse_from_text(job_text))
        
        # Use AI as fallback if enabled
        if self.use_ai and (job_html or job_text):
            ai_result = self._parse_with_ai(job_text or job_html)
            # Fill in missing fields
            for key, value in ai_result.items():
                if not result.get(key) and value:
                    result[key] = value
        
        return result
    
    def _parse_from_url(self, url: str) -> Dict:
        """Extract info from job posting URL"""
        result = {}
        
        # Extract domain
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if match:
            domain = match.group(1)
            
            # Common job boards
            if 'linkedin.com' in domain:
                # LinkedIn: https://www.linkedin.com/jobs/view/123456
                company_match = re.search(r'/company/([^/]+)', url)
                if company_match:
                    result['company'] = company_match.group(1).replace('-', ' ').title()
            
            elif 'greenhouse.io' in domain:
                # Greenhouse: https://boards.greenhouse.io/company/jobs/123456
                company_match = re.search(r'greenhouse\.io/([^/]+)', url)
                if company_match:
                    result['company'] = company_match.group(1).replace('-', ' ').title()
            
            elif 'lever.co' in domain:
                # Lever: https://jobs.lever.co/company/job-slug
                company_match = re.search(r'lever\.co/([^/]+)', url)
                if company_match:
                    result['company'] = company_match.group(1).replace('-', ' ').title()
            
            # Try to extract company domain
            if not any(board in domain for board in ['greenhouse', 'lever', 'linkedin', 'indeed', 'glassdoor']):
                # Direct company career page
                result['company_domain'] = domain
                company_name = domain.split('.')[0]
                result['company'] = company_name.title()
        
        return result
    
    def _parse_from_html(self, html: str) -> Dict:
        """Parse job posting HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        result = {}
        
        # Look for structured data (JSON-LD)
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                import json
                data = json.loads(json_ld.string)
                
                if isinstance(data, dict):
                    result['job_title'] = data.get('title')
                    
                    if 'hiringOrganization' in data:
                        org = data['hiringOrganization']
                        result['company'] = org.get('name')
                    
                    if 'jobLocation' in data:
                        loc = data['jobLocation']
                        if isinstance(loc, dict):
                            result['location'] = loc.get('address', {}).get('addressLocality')
            except:
                pass
        
        # Look for common class names
        title_elem = soup.find(['h1', 'h2'], class_=re.compile(r'(job.?title|position)', re.I))
        if title_elem and not result.get('job_title'):
            result['job_title'] = title_elem.get_text(strip=True)
        
        company_elem = soup.find(['span', 'div', 'a'], class_=re.compile(r'company', re.I))
        if company_elem and not result.get('company'):
            result['company'] = company_elem.get_text(strip=True)
        
        location_elem = soup.find(['span', 'div'], class_=re.compile(r'location', re.I))
        if location_elem and not result.get('location'):
            result['location'] = location_elem.get_text(strip=True)
        
        return result
    
    def _parse_from_text(self, text: str) -> Dict:
        """Parse job posting text"""
        result = {}
        
        # Look for department mentions
        dept_patterns = [
            r'(?:department|team|group):\s*([^\n]+)',
            r'join\s+(?:the|our)\s+([^\n]+)\s+team',
        ]
        
        for pattern in dept_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['department'] = match.group(1).strip()
                break
        
        # Look for seniority
        if any(word in text.lower() for word in ['senior', 'sr.', 'lead', 'staff', 'principal']):
            result['seniority'] = 'senior'
        elif any(word in text.lower() for word in ['junior', 'jr.', 'entry', 'associate']):
            result['seniority'] = 'junior'
        else:
            result['seniority'] = 'mid'
        
        return result
    
    def _parse_with_ai(self, content: str) -> Dict:
        """Use OpenAI to extract job info"""
        if not self.use_ai:
            return {}
        
        try:
            # Truncate content to save tokens
            content = content[:4000]
            
            prompt = f"""Extract structured information from this job posting:

{content}

Return JSON with these fields (or null if not found):
{{
  "company": "Company name",
  "job_title": "Job title",
  "department": "Department/team",
  "location": "Location",
  "seniority": "junior|mid|senior"
}}"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You extract structured data from job postings."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=200
            )
            
            import json
            return json.loads(response.choices[0].message.content)
        
        except Exception as e:
            print(f"⚠️  AI parsing error: {e}")
            return {}

