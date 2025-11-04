"""Parse job postings to extract company, title, department"""

import re
import os
import asyncio
from typing import Optional, Dict
from bs4 import BeautifulSoup


class JobParser:
    """
    Extract structured data from job postings.
    
    Handles various job board formats (LinkedIn, Greenhouse, Lever, etc.)
    """
    
    def __init__(self, use_ai: bool = True):
        self.use_ai = False  # Default to False, enable if key is valid
        openai_key = os.getenv("OPENAI_API_KEY")
        
        # Known job boards and their patterns
        self.job_boards = {
            'linkedin.com': self._parse_linkedin,
            'greenhouse.io': self._parse_greenhouse,
            'lever.co': self._parse_lever,
            'builtin.com': self._parse_builtin,
            'wellfound.com': self._parse_wellfound,
            'indeed.com': self._parse_indeed,
            'glassdoor.com': self._parse_glassdoor,
            'angel.co': self._parse_angellist,
            'workday.com': self._parse_workday,
            'jobs.ashbyhq.com': self._parse_ashby,
            'boards.greenhouse.io': self._parse_greenhouse,
            'jobs.lever.co': self._parse_lever,
        }
        
        if use_ai and openai_key:
            # Validate key format (starts with sk-)
            if not openai_key.startswith('sk-'):
                print("⚠️  OpenAI API key format invalid (should start with 'sk-'). Disabling AI parsing.")
            else:
                try:
                    from openai import OpenAI
                    # Test if key is valid by initializing client
                    self.client = OpenAI(api_key=openai_key)
                    self.use_ai = True
                except ImportError:
                    print("⚠️  OpenAI package not installed. Install with: pip install openai")
                except Exception as e:
                    print(f"⚠️  OpenAI initialization failed: {str(e)}. AI parsing disabled.")
    
    async def fetch_html_with_playwright(self, job_url: str) -> Optional[str]:
        """
        Fetch HTML from job URL using Playwright (for JavaScript-heavy sites).
        
        Args:
            job_url: URL of job posting
            
        Returns:
            HTML content or None if failed
        """
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                try:
                    await page.goto(job_url, wait_until='networkidle', timeout=30000)
                    # Wait a bit for dynamic content
                    await page.wait_for_timeout(2000)
                    html = await page.content()
                    await browser.close()
                    return html
                except Exception as e:
                    await browser.close()
                    print(f"Playwright fetch error: {e}")
                    return None
        except ImportError:
            print("Playwright not available")
            return None
        except Exception as e:
            print(f"Playwright error: {e}")
            return None
    
    def fetch_html_simple(self, job_url: str) -> Optional[str]:
        """
        Fetch HTML using simple HTTP request.
        
        Args:
            job_url: URL of job posting
            
        Returns:
            HTML content or None if failed
        """
        try:
            import requests
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(job_url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Simple fetch error: {e}")
            return None
    
    def fetch_job_html(self, job_url: str, use_playwright: bool = True) -> Optional[str]:
        """
        Fetch HTML from job URL using best available method.
        
        Args:
            job_url: URL of job posting
            use_playwright: Whether to try Playwright first
            
        Returns:
            HTML content or None if failed
        """
        # Try Playwright first for JavaScript-heavy sites
        if use_playwright:
            try:
                html = asyncio.run(self.fetch_html_with_playwright(job_url))
                if html:
                    return html
            except Exception as e:
                print(f"Playwright fetch failed: {e}")
        
        # Fallback to simple HTTP
        return self.fetch_html_simple(job_url)
    
    def parse(self, job_url: str, job_html: Optional[str] = None, 
              job_text: Optional[str] = None, auto_fetch: bool = True) -> Dict:
        """
        Parse job posting to extract key information.
        
        Args:
            job_url: URL of job posting
            job_html: Raw HTML (optional)
            job_text: Extracted text (optional)
            auto_fetch: If True and no HTML/text provided, fetch from URL
        
        Returns:
            Dict with company, title, department, required_skills, job_description, etc.
        """
        result = {
            "company": None,
            "company_domain": None,
            "job_title": None,
            "department": None,
            "location": None,
            "seniority": None,
            "required_skills": [],
            "job_description": None,
        }
        
        # Keep track of source for debugging
        is_builtin = 'builtin.com' in job_url
        
        # Extract from URL first
        url_results = self._parse_from_url(job_url)
        result.update(url_results)
        
        # Auto-fetch HTML if not provided and auto_fetch is True
        if not job_html and not job_text and auto_fetch:
            job_html = self.fetch_job_html(job_url)
        
        # If we have HTML, parse it
        if job_html:
            html_results = self._parse_from_html(job_html)
            # For Built In, trust HTML parsing over URL parsing
            if is_builtin:
                for key, value in html_results.items():
                    if value:  # Override with non-None values
                        result[key] = value
            else:
                result.update(html_results)
                
            # Extract text from HTML for AI parsing
            if not job_text:
                soup = BeautifulSoup(job_html, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "header", "footer"]):
                    script.decompose()
                job_text = soup.get_text(separator="\n", strip=True)
                result['job_description'] = job_text[:2000]  # Store truncated description
        
        # If we have text, parse it
        if job_text:
            text_results = self._parse_from_text(job_text)
            # Only update missing fields from text parsing
            for key, value in text_results.items():
                if not result.get(key) and value:
                    result[key] = value
            
            # Extract required skills from job text
            result['required_skills'] = self._extract_required_skills(job_text)
            
            # Store full description if not already set
            if not result.get('job_description'):
                result['job_description'] = job_text[:2000]
        
        # Use AI for better extraction if enabled
        if self.use_ai and (job_html or job_text):
            # For Built In, help AI by providing context about expected company
            ai_text = job_text or job_html
            if is_builtin and not result.get('company'):
                # Try to find company name in text
                company_pattern = r'(?:^|\n)([A-Z][A-Za-z\s&]+(?:\([^)]+\))?)\s*\n\s*(?:AI Engineer|Software Engineer|Engineer)'
                company_match = re.search(company_pattern, ai_text[:1000])
                if company_match:
                    ai_text = f"Company: {company_match.group(1)}\n\n{ai_text}"
                    
            ai_result = self._parse_with_ai(ai_text)
            # Fill in missing fields
            for key, value in ai_result.items():
                if not result.get(key) and value:
                    result[key] = value
            
            # Extract skills using AI (prioritize AI extraction)
            if 'required_skills' in ai_result and ai_result.get('required_skills'):
                result['required_skills'] = ai_result.get('required_skills', [])
            elif 'nice_to_have_skills' in ai_result:
                # Store nice-to-have separately if available
                result['nice_to_have_skills'] = ai_result.get('nice_to_have_skills', [])
        
        # Final cleanup - ensure company domain is not job board domain
        if result.get('company_domain') in ['builtin.com', 'linkedin.com', 'indeed.com', 'glassdoor.com']:
            result['company_domain'] = None
        
        # Validate company name isn't obviously wrong
        if result.get('company'):
            company_text = result['company']
            # Check if company name contains job board artifacts
            bad_patterns = [
                'Software • SEO • Marketing Tech',
                'Information Technology • Security',
                'View All Jobs',
                'For Employers',
                'Built In',
                'LinkedIn',
            ]
            
            if any(bad in company_text for bad in bad_patterns):
                # Try to extract real company from job title or description
                if result.get('job_title') and ' at ' in result['job_title']:
                    # Pattern: "AI Engineer at Root"
                    at_match = re.search(r' at ([A-Z][A-Za-z\s&]+)$', result['job_title'])
                    if at_match:
                        result['company'] = at_match.group(1).strip()
                elif result.get('job_description'):
                    # Look for company in first few lines of description
                    desc_lines = result['job_description'].split('\n')[:10]
                    for line in desc_lines:
                        line = line.strip()
                        # Pattern: Just company name on its own line
                        if re.match(r'^[A-Z][A-Za-z\s&]+(?:\([^)]+\))?$', line) and len(line) < 50:
                            # Verify it's not a job board name
                            if not any(board in line.lower() for board in ['built in', 'linkedin', 'indeed']):
                                result['company'] = line.split('(')[0].strip()
                                # Extract domain if in parentheses
                                domain_match = re.search(r'\(([^)]+\.[^)]+)\)', line)
                                if domain_match:
                                    result['company_domain'] = domain_match.group(1)
                                break
        
        # Store job URL
        result['job_url'] = job_url
        
        # Calculate confidence score
        result['confidence_score'] = self._calculate_extraction_confidence(result)
        
        # Try to discover company domain if missing
        if result.get('company') and not result.get('company_domain'):
            result['company_domain'] = self._guess_company_domain(result['company'])
        
        return result
    
    def _extract_required_skills(self, text: str) -> list:
        """Extract required skills from job description"""
        skills = []
        
        # Common skill keywords
        tech_skills = [
            'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'C++', 'C#',
            'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring',
            'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Terraform',
            'SQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Cassandra',
            'Machine Learning', 'Deep Learning', 'AI', 'NLP', 'TensorFlow', 'PyTorch',
            'Git', 'CI/CD', 'Jenkins', 'Agile', 'Scrum',
        ]
        
        text_lower = text.lower()
        for skill in tech_skills:
            if skill.lower() in text_lower:
                skills.append(skill)
        
        return list(set(skills))[:20]  # Limit to 20
    
    def _parse_from_url(self, url: str) -> Dict:
        """Extract info from job posting URL"""
        result = {}
        
        # Extract domain
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if match:
            domain = match.group(1).lower()
            
            # Check if it's a known job board
            for board_domain, parser_func in self.job_boards.items():
                if board_domain in domain:
                    board_results = parser_func(url)
                    result.update(board_results)
                    result['_job_board'] = board_domain
                    break
            else:
                # Direct company career page
                result['company_domain'] = domain
                # Extract company name from domain
                company_name = domain.split('.')[0]
                # Handle subdomains like careers.company.com
                if company_name in ['careers', 'jobs', 'apply', 'hire']:
                    parts = domain.split('.')
                    if len(parts) > 2:
                        company_name = parts[1]
                
                # Clean up company name
                company_name = company_name.replace('-', ' ')
                # Handle known patterns like company-ai -> Company AI
                if company_name.endswith(' ai'):
                    company_name = company_name[:-3] + ' AI'
                elif company_name.endswith(' io'):
                    company_name = company_name[:-3]
                    
                result['company'] = company_name.title()
        
        return result
    
    def _parse_from_html(self, html: str) -> Dict:
        """Parse job posting HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        result = {}
        
        # Look for structured data (JSON-LD) - most reliable
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for json_ld in json_ld_scripts:
            try:
                import json
                data = json.loads(json_ld.string)
                
                # Handle both single dict and array of dicts
                if isinstance(data, list):
                    data = data[0] if data else {}
                
                if isinstance(data, dict):
                    # JobPosting schema
                    if data.get('@type') == 'JobPosting':
                        result['job_title'] = data.get('title')
                        
                        if 'hiringOrganization' in data:
                            org = data['hiringOrganization']
                            result['company'] = org.get('name')
                            # Sometimes has URL
                            if org.get('url'):
                                domain = re.search(r'https?://(?:www\.)?([^/]+)', org['url'])
                                if domain:
                                    result['company_domain'] = domain.group(1)
                        
                        if 'jobLocation' in data:
                            loc = data['jobLocation']
                            if isinstance(loc, dict):
                                address = loc.get('address', {})
                                if isinstance(address, dict):
                                    parts = []
                                    if address.get('addressLocality'):
                                        parts.append(address['addressLocality'])
                                    if address.get('addressRegion'):
                                        parts.append(address['addressRegion'])
                                    if parts:
                                        result['location'] = ', '.join(parts)
                        
                        # Extract department from description sometimes
                        if data.get('description'):
                            dept_match = re.search(r'(?:team|department|group):\s*([^\n]+)', 
                                                 data['description'], re.I)
                            if dept_match:
                                result['department'] = dept_match.group(1).strip()
            except:
                pass
        
        # Look for Open Graph meta tags
        og_site = soup.find('meta', property='og:site_name')
        if og_site and og_site.get('content'):
            # Sometimes contains company name
            site_name = og_site['content']
            if not any(board in site_name.lower() for board in 
                       ['linkedin', 'indeed', 'glassdoor', 'built in']):
                result['company'] = site_name
        
        # Built In specific parsing
        if 'builtin.com' in str(soup):
            # Look for company name in specific patterns
            # Pattern 1: Company profile link
            company_link = soup.find('a', href=re.compile(r'/companies/[^/]+$'))
            if company_link and not result.get('company'):
                company_text = company_link.get_text(strip=True)
                # Extract company name, removing any trailing info
                if company_text:
                    # Handle cases like "Root (root.io)"
                    company_name = company_text.split('(')[0].strip()
                    result['company'] = company_name
                    
                    # Try to extract domain from parentheses
                    domain_match = re.search(r'\(([^)]+\.[^)]+)\)', company_text)
                    if domain_match:
                        result['company_domain'] = domain_match.group(1)
            
            # Pattern 2: Look for company in page title
            if not result.get('company'):
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text()
                    # Pattern like "AI Engineer - Root | Built In"
                    title_match = re.search(r'[^-]+\s*-\s*([^|]+)\s*\|', title_text)
                    if title_match:
                        result['company'] = title_match.group(1).strip()
        
        # Generic parsing as fallback
        if not result.get('job_title'):
            title_elem = soup.find(['h1', 'h2'], class_=re.compile(r'(job.?title|position|role)', re.I))
            if not title_elem:
                # Try just h1
                title_elem = soup.find('h1')
            if title_elem:
                result['job_title'] = title_elem.get_text(strip=True)
        
        # More careful company extraction - avoid ads/related companies
        if not result.get('company'):
            # Try specific patterns that indicate the actual hiring company
            for pattern in [r'company.?name', r'hiring.?company', r'employer']:
                company_elem = soup.find(['span', 'div', 'h2', 'h3'], class_=re.compile(pattern, re.I))
                if company_elem:
                    result['company'] = company_elem.get_text(strip=True)
                    break
            
            # Last resort - but be more specific
            if not result.get('company'):
                company_elem = soup.find(['span', 'div', 'a'], 
                                       class_=re.compile(r'company(?!.*(list|related|similar))', re.I))
                if company_elem:
                    result['company'] = company_elem.get_text(strip=True)
        
        if not result.get('location'):
            location_elem = soup.find(['span', 'div'], class_=re.compile(r'location|city', re.I))
            if location_elem:
                result['location'] = location_elem.get_text(strip=True)
        
        # Extract department if present
        dept_elem = soup.find(['span', 'div'], class_=re.compile(r'department|team', re.I))
        if dept_elem:
            result['department'] = dept_elem.get_text(strip=True)
        
        return result
    
    def _parse_from_text(self, text: str) -> Dict:
        """Parse job posting text"""
        result = {}
        
        # For Built In pages, company often appears near the top
        # Pattern: Company name (sometimes with domain) followed by job title
        lines = text.split('\n')
        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            line = line.strip()
            # Look for patterns like "Root (root.io)" or just "Root"
            if re.match(r'^[A-Z][A-Za-z\s&]+(\([^)]+\))?$', line) and len(line) < 50:
                # Check if next lines contain job-related keywords
                next_text = ' '.join(lines[i:i+5]).lower()
                if any(keyword in next_text for keyword in ['engineer', 'manager', 'developer', 'designer', 'analyst']):
                    # Extract company and domain
                    company_match = re.match(r'^([^(]+)(?:\(([^)]+)\))?$', line)
                    if company_match:
                        result['company'] = company_match.group(1).strip()
                        if company_match.group(2) and '.' in company_match.group(2):
                            result['company_domain'] = company_match.group(2).strip()
                    break
        
        # Alternative: Look for "at Company" patterns
        if not result.get('company'):
            at_company_pattern = r'(?:at|@|for)\s+([A-Z][A-Za-z\s&]+?)(?:\s*\([^)]+\))?\s*(?:\n|$|[,.])'
            at_match = re.search(at_company_pattern, text[:1000])  # Check first 1000 chars
            if at_match:
                company_text = at_match.group(1).strip()
                # Validate it's not a generic phrase
                if len(company_text) < 50 and not any(skip in company_text.lower() for skip in ['the company', 'our company', 'a company']):
                    result['company'] = company_text
        
        # Look for department mentions
        dept_patterns = [
            r'(?:department|team|group):\s*([^\n]+)',
            r'join\s+(?:the|our)\s+([^\n]+)\s+team',
        ]
        
        for pattern in dept_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dept_text = match.group(1).strip()
                # Clean up department text
                if len(dept_text) < 50:
                    result['department'] = dept_text
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
            
            prompt = f"""Extract comprehensive structured information from this job posting. This data will be used to find relevant professional connections for job referrals, so accuracy is critical.

{content}

Extract ALL relevant information:

1. **Company**: Official company name
2. **Job Title**: Exact job title (e.g., "Senior Software Engineer", "Product Manager")
3. **Department/Team**: The specific department, team, or division (e.g., "Engineering", "Product", "Data Science")
4. **Location**: City, state, or remote/in-person status
5. **Seniority Level**: "junior", "mid", or "senior" based on requirements and title
6. **Required Skills**: Technical skills, programming languages, frameworks, or tools that are explicitly required
7. **Nice-to-Have Skills**: Skills mentioned as preferred but not required (separate from required)

For skills extraction:
- Look for sections like "Requirements", "Qualifications", "Must Have", "Required"
- Distinguish between "Required" and "Preferred/Nice to Have"
- Include specific technologies mentioned (e.g., Python, React, AWS)
- Be comprehensive but accurate

Return JSON with these fields (use null if not found):
{{
  "company": "Company name",
  "job_title": "Job title",
  "department": "Department/team name",
  "location": "Location (city, state, or remote)",
  "seniority": "junior|mid|senior",
  "required_skills": ["list of skills that are explicitly required"],
  "nice_to_have_skills": ["list of skills that are preferred but not required"]
}}"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured data from job postings for connection finding and job matching. Your accuracy helps candidates find the right professional connections. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            import json
            response_content = response.choices[0].message.content.strip()
            # Try to extract JSON if wrapped in markdown code blocks
            if response_content.startswith("```"):
                response_content = response_content.split("```")[1]
                if response_content.startswith("json"):
                    response_content = response_content[4:]
                response_content = response_content.strip()
            
            return json.loads(response_content)
        
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                print("⚠️  OpenAI API quota exceeded. Please check your billing at https://platform.openai.com/account/billing")
                print("   Job parsing will continue with pattern-based extraction only.")
            elif "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                print("⚠️  OpenAI API key invalid or expired. Check your OPENAI_API_KEY environment variable.")
                print("   Job parsing will continue with pattern-based extraction only.")
            elif "rate_limit" in error_msg.lower():
                print("⚠️  OpenAI API rate limit exceeded. Please wait a moment and try again.")
                print("   Job parsing will continue with pattern-based extraction only.")
            else:
                print(f"⚠️  AI parsing error: {error_msg}")
                print("   Job parsing will continue with pattern-based extraction only.")
            
            # Disable AI for future calls to avoid repeated errors
            self.use_ai = False
            return {}
    
    def _calculate_extraction_confidence(self, result: Dict) -> float:
        """Calculate confidence score for extracted data"""
        score = 0.5  # Base score
        
        # Check completeness
        if result.get('company'):
            score += 0.1
        if result.get('company_domain'):
            score += 0.15  # Domain is strong signal
        if result.get('job_title'):
            score += 0.1
        if result.get('department'):
            score += 0.05
        if result.get('location'):
            score += 0.05
        if result.get('required_skills'):
            score += 0.05
        
        # Penalize if company looks like it contains job board artifacts
        if result.get('company'):
            bad_patterns = ['•', 'View All', 'For Employers', '|']
            if any(bad in result['company'] for bad in bad_patterns):
                score -= 0.2
        
        return min(1.0, max(0.1, score))
    
    def _guess_company_domain(self, company_name: str) -> Optional[str]:
        """Guess company domain from name"""
        # Common tech company mappings
        known_domains = {
            'google': 'google.com',
            'meta': 'meta.com',
            'facebook': 'meta.com',
            'amazon': 'amazon.com',
            'apple': 'apple.com',
            'microsoft': 'microsoft.com',
            'netflix': 'netflix.com',
            'uber': 'uber.com',
            'lyft': 'lyft.com',
            'airbnb': 'airbnb.com',
            'stripe': 'stripe.com',
            'square': 'squareup.com',
            'twitter': 'twitter.com',
            'x': 'x.com',
            'openai': 'openai.com',
            'anthropic': 'anthropic.com',
            'databricks': 'databricks.com',
            'snowflake': 'snowflake.com',
            'palantir': 'palantir.com',
            'root': 'root.io',
            'root insurance': 'joinroot.com',
        }
        
        company_lower = company_name.lower().strip()
        
        # Direct match
        if company_lower in known_domains:
            return known_domains[company_lower]
        
        # Try without common suffixes
        for suffix in [' inc', ' corp', ' llc', ' ltd', ' co']:
            if company_lower.endswith(suffix):
                base_name = company_lower[:-len(suffix)].strip()
                if base_name in known_domains:
                    return known_domains[base_name]
        
        # Common patterns for startups
        clean_name = company_lower.replace(' ', '').replace('-', '')
        common_tlds = ['.com', '.io', '.ai', '.co', '.dev']
        
        # Will be enhanced with actual domain discovery in Phase 1.3
        return None
    
    # Job board specific parsers
    def _parse_linkedin(self, url: str) -> Dict:
        """Parse LinkedIn job URL"""
        result = {}
        
        # LinkedIn patterns:
        # https://www.linkedin.com/jobs/view/123456
        # https://www.linkedin.com/jobs/company-name-jobs
        # Sometimes has /company/company-name in referrer
        
        # Try to extract job ID
        job_match = re.search(r'/jobs/view/(\d+)', url)
        if job_match:
            result['_job_id'] = job_match.group(1)
        
        # Try to extract company from URL (rare but sometimes present)
        company_match = re.search(r'/company/([^/]+)', url)
        if company_match:
            company_slug = company_match.group(1)
            result['company'] = company_slug.replace('-', ' ').title()
            result['_company_linkedin_slug'] = company_slug
        
        return result
    
    def _parse_greenhouse(self, url: str) -> Dict:
        """Parse Greenhouse job URL"""
        result = {}
        
        # Greenhouse patterns:
        # https://boards.greenhouse.io/companyname/jobs/123456
        # https://companyname.greenhouse.io/jobs/123456
        
        if 'boards.greenhouse.io' in url:
            company_match = re.search(r'boards\.greenhouse\.io/([^/]+)', url)
            if company_match:
                company_slug = company_match.group(1)
                result['company'] = company_slug.replace('-', ' ').title()
                # Many companies use their actual domain as slug
                if '.' not in company_slug:
                    result['company_domain'] = f"{company_slug}.com"
        else:
            # Direct subdomain
            domain_match = re.search(r'https?://([^.]+)\.greenhouse\.io', url)
            if domain_match:
                company_slug = domain_match.group(1)
                result['company'] = company_slug.replace('-', ' ').title()
                result['company_domain'] = f"{company_slug}.com"
        
        # Extract job ID
        job_match = re.search(r'/jobs/(\d+)', url)
        if job_match:
            result['_job_id'] = job_match.group(1)
        
        return result
    
    def _parse_lever(self, url: str) -> Dict:
        """Parse Lever job URL"""
        result = {}
        
        # Lever patterns:
        # https://jobs.lever.co/companyname/job-id
        # https://companyname.lever.co/job-id
        
        if 'jobs.lever.co' in url:
            company_match = re.search(r'jobs\.lever\.co/([^/]+)', url)
            if company_match:
                company_slug = company_match.group(1)
                result['company'] = company_slug.replace('-', ' ').title()
                # Lever slugs often match domain
                result['company_domain'] = f"{company_slug}.com"
        else:
            # Direct subdomain
            domain_match = re.search(r'https?://([^.]+)\.lever\.co', url)
            if domain_match:
                company_slug = domain_match.group(1)
                result['company'] = company_slug.replace('-', ' ').title()
                result['company_domain'] = f"{company_slug}.com"
        
        return result
    
    def _parse_builtin(self, url: str) -> Dict:
        """Parse Built In job URL"""
        # Built In doesn't have company in URL
        # We'll extract from page content
        return {'_is_builtin': True}
    
    def _parse_wellfound(self, url: str) -> Dict:
        """Parse Wellfound (formerly AngelList) job URL"""
        result = {}
        
        # Wellfound patterns:
        # https://wellfound.com/company/companyname/jobs/123456
        
        company_match = re.search(r'/company/([^/]+)', url)
        if company_match:
            company_slug = company_match.group(1)
            result['company'] = company_slug.replace('-', ' ').title()
        
        return result
    
    def _parse_indeed(self, url: str) -> Dict:
        """Parse Indeed job URL"""
        # Indeed doesn't have company in URL typically
        return {'_is_aggregator': True}
    
    def _parse_glassdoor(self, url: str) -> Dict:
        """Parse Glassdoor job URL"""
        # Glassdoor URLs are complex, extract from content
        return {'_is_aggregator': True}
    
    def _parse_angellist(self, url: str) -> Dict:
        """Parse AngelList job URL"""
        result = {}
        
        # Legacy AngelList patterns
        company_match = re.search(r'/company/([^/]+)', url)
        if company_match:
            result['company'] = company_match.group(1).replace('-', ' ').title()
        
        return result
    
    def _parse_workday(self, url: str) -> Dict:
        """Parse Workday job URL"""
        result = {}
        
        # Workday patterns vary by company
        # https://company.wd5.myworkdayjobs.com/en-US/careers/job/...
        domain_match = re.search(r'https?://([^.]+)\.wd\d+\.myworkdayjobs', url)
        if domain_match:
            company_slug = domain_match.group(1)
            result['company'] = company_slug.replace('-', ' ').title()
            # Often matches real domain
            result['company_domain'] = f"{company_slug}.com"
        
        return result
    
    def _parse_ashby(self, url: str) -> Dict:
        """Parse Ashby job URL"""
        result = {}
        
        # Ashby patterns:
        # https://jobs.ashbyhq.com/companyname/job-id
        
        company_match = re.search(r'jobs\.ashbyhq\.com/([^/]+)', url)
        if company_match:
            company_slug = company_match.group(1)
            result['company'] = company_slug.replace('-', ' ').title()
            result['company_domain'] = f"{company_slug}.com"
        
        return result

