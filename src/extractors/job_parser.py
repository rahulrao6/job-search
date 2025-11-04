"""Parse job postings to extract company, title, department"""

import re
import os
import asyncio
import logging
from typing import Optional, Dict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class JobParser:
    """
    Extract structured data from job postings.
    
    Handles various job board formats (LinkedIn, Greenhouse, Lever, etc.)
    """
    
    def __init__(self, use_ai: bool = True):
        self.use_ai = False  # Default to False, enable if key is valid
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if use_ai and openai_key:
            # Validate key format (starts with sk-)
            if not openai_key.startswith('sk-'):
                logger.warning("OpenAI API key format invalid (should start with 'sk-'). Disabling AI parsing.")
            else:
                try:
                    from openai import OpenAI
                    
                    # Verify OpenAI SDK version (should be >= 1.0.0)
                    try:
                        import openai
                        version_parts = openai.__version__.split('.')
                        major_version = int(version_parts[0])
                        if major_version < 1:
                            raise ValueError(f"OpenAI SDK version {openai.__version__} is too old. Need >= 1.0.0")
                    except (AttributeError, ValueError, IndexError):
                        pass  # Continue anyway
                    
                    # Initialize client with ONLY api_key parameter (no proxies, etc.)
                    # OpenAI SDK >=1.0.0 doesn't support 'proxies' in constructor
                    # If proxies are needed, configure via HTTP_PROXY/HTTPS_PROXY environment variables
                    # Be explicit and only pass api_key - do not use **kwargs pattern that might pick up unwanted params
                    try:
                        # Import httpx to create a client without proxies
                        import httpx
                        # Create httpx client explicitly without proxies to avoid any auto-detection
                        # trust_env=False prevents httpx from reading HTTP_PROXY/HTTPS_PROXY env vars
                        http_client = httpx.Client(trust_env=False, timeout=60.0)
                        self.client = OpenAI(api_key=openai_key, http_client=http_client)
                        self.use_ai = True
                        logger.info("OpenAI client initialized successfully for job parsing")
                    except Exception as init_error:
                        # If httpx approach fails, try without custom http_client
                        try:
                            self.client = OpenAI(api_key=openai_key)
                            self.use_ai = True
                            logger.info("OpenAI client initialized successfully for job parsing")
                        except Exception as fallback_error:
                            error_msg = str(fallback_error)
                            if 'proxies' in error_msg.lower():
                                logger.error(f"OpenAI initialization failed: Proxies parameter detected. This is not supported in OpenAI SDK >=1.0.0. Error: {error_msg}")
                            else:
                                logger.error(f"OpenAI initialization failed: {error_msg}. AI parsing disabled.", exc_info=True)
                except ImportError:
                    logger.warning("OpenAI package not installed. Install with: pip install openai")
                except Exception as e:
                    error_msg = str(e)
                    if 'proxies' in error_msg.lower():
                        logger.error(f"OpenAI initialization failed: Proxies parameter detected. This is not supported in OpenAI SDK >=1.0.0. Error: {error_msg}")
                    else:
                        logger.error(f"OpenAI initialization failed: {error_msg}. AI parsing disabled.", exc_info=True)
    
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
        
        # Extract from URL first
        result.update(self._parse_from_url(job_url))
        
        # Auto-fetch HTML if not provided and auto_fetch is True
        if not job_html and not job_text and auto_fetch:
            job_html = self.fetch_job_html(job_url)
        
        # If we have HTML, parse it
        if job_html:
            result.update(self._parse_from_html(job_html))
            # Extract text from HTML for AI parsing
            if not job_text:
                soup = BeautifulSoup(job_html, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                job_text = soup.get_text(separator="\n", strip=True)
                result['job_description'] = job_text[:2000]  # Store truncated description
        
        # If we have text, parse it
        if job_text:
            text_results = self._parse_from_text(job_text)
            result.update(text_results)
            
            # Extract required skills from job text
            result['required_skills'] = self._extract_required_skills(job_text)
            
            # Store full description if not already set
            if not result.get('job_description'):
                result['job_description'] = job_text[:2000]
        
        # Use AI for better extraction if enabled
        if self.use_ai and (job_html or job_text):
            ai_result = self._parse_with_ai(job_text or job_html)
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

