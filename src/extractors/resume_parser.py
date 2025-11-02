"""Parse resumes to extract schools, past companies, skills"""

import re
import os
import json
from typing import List, Dict, Optional
from src.models.job_context import CandidateProfile


class ResumeParser:
    """
    Extract structured data from resumes.
    
    Finds: schools, past companies, skills for alumni matching.
    """
    
    def __init__(self, use_ai: bool = True):
        self.use_ai = False  # Default to False, enable if key is valid
        self.client = None
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not use_ai:
            print("ℹ️  AI parsing disabled by parameter")
            return
        
        if not openai_key:
            print("ℹ️  OPENAI_API_KEY not set. AI parsing disabled. Using pattern-based extraction only.")
            return
        
        # Validate key format (starts with sk-)
        if not openai_key.startswith('sk-'):
            print(f"⚠️  OpenAI API key format invalid (should start with 'sk-'). Got: {openai_key[:10]}...")
            print("   Disabling AI parsing. Using pattern-based extraction only.")
            return
        
        try:
            from openai import OpenAI
            # Initialize client with explicit API key
            self.client = OpenAI(api_key=openai_key)
            
            # Test connection with a simple API call
            try:
                # This will verify the key is valid
                self.client.models.list()
                self.use_ai = True
                print("✅ OpenAI AI parsing enabled and verified")
            except Exception as test_error:
                error_str = str(test_error)
                if "quota" in error_str.lower() or "insufficient_quota" in error_str.lower():
                    print("⚠️  OpenAI API quota exceeded. Check billing: https://platform.openai.com/account/billing")
                    print("   AI parsing disabled. Using pattern-based extraction only.")
                elif "api_key" in error_str.lower() or "authentication" in error_str.lower():
                    print("⚠️  OpenAI API key invalid or expired. Check your OPENAI_API_KEY environment variable.")
                    print("   AI parsing disabled. Using pattern-based extraction only.")
                else:
                    print(f"⚠️  OpenAI connection test failed: {error_str}")
                    print("   AI parsing disabled. Using pattern-based extraction only.")
                
        except ImportError:
            print("⚠️  OpenAI package not installed. Install with: pip install openai")
            print("   AI parsing disabled. Using pattern-based extraction only.")
        except Exception as e:
            print(f"⚠️  OpenAI initialization failed: {str(e)}")
            print("   AI parsing disabled. Using pattern-based extraction only.")
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF bytes.
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            Extracted text as string
        """
        text = ""
        
        # Try pdfplumber first (better for formatted text)
        try:
            import pdfplumber
            import io
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            if text.strip():
                return text.strip()
        except ImportError:
            # pdfplumber not installed, will fall back to PyPDF2
            print("⚠️  pdfplumber not installed. Install with: pip install pdfplumber. Using PyPDF2 fallback.")
        except Exception as e:
            # pdfplumber failed, fall back to PyPDF2
            print(f"⚠️  pdfplumber extraction failed: {str(e)}. Trying PyPDF2 fallback...")
        
        # Fallback to PyPDF2
        try:
            import PyPDF2
            import io
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            return text.strip()
            
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def parse(self, resume_text: str) -> CandidateProfile:
        """
        Parse resume to extract candidate profile.
        
        Args:
            resume_text: Resume as text
        
        Returns:
            CandidateProfile with schools, companies, skills
        """
        profile = CandidateProfile()
        
        # Extract using patterns
        profile.schools = self._extract_schools(resume_text)
        profile.past_companies = self._extract_companies(resume_text)
        profile.skills = self._extract_skills(resume_text)
        
        # Use AI for better extraction if available
        if self.use_ai:
            ai_profile = self._parse_with_ai(resume_text)
            # Merge results
            profile.schools = list(set(profile.schools + ai_profile.get('schools', [])))
            profile.past_companies = list(set(profile.past_companies + ai_profile.get('companies', [])))
            profile.skills = list(set(profile.skills + ai_profile.get('skills', [])))
            
            # Extract current_title from AI if available
            if ai_profile.get('current_title'):
                profile.current_title = ai_profile.get('current_title')
            # Note: years_experience field not available in CandidateProfile model
            # If needed in future, add it to the model definition
        
        return profile
    
    def _extract_schools(self, text: str) -> List[str]:
        """Extract university/school names"""
        schools = []
        
        # Common university keywords
        uni_patterns = [
            r'(University of [A-Z][a-z\s]+)',
            r'([A-Z][a-z]+\s+University)',
            r'([A-Z][a-z]+\s+Institute of Technology)',
            r'(MIT|Stanford|Harvard|Yale|Princeton|Columbia|Cornell|Penn|Brown|Dartmouth)',
            r'([A-Z][a-z]+\s+College)',
        ]
        
        for pattern in uni_patterns:
            matches = re.findall(pattern, text)
            schools.extend(matches)
        
        # Look in education section
        edu_section = re.search(r'(?:EDUCATION|Education)(.*?)(?:EXPERIENCE|Experience|$)', text, re.DOTALL)
        if edu_section:
            section_text = edu_section.group(1)
            # Extract proper nouns (capitalized words)
            words = section_text.split()
            current_school = []
            for word in words:
                if word[0].isupper() and len(word) > 2:
                    current_school.append(word)
                elif current_school:
                    schools.append(' '.join(current_school))
                    current_school = []
        
        return list(set(schools))[:10]  # Limit to 10
    
    def _extract_companies(self, text: str) -> List[str]:
        """Extract past company names"""
        companies = []
        
        # Look in experience section
        exp_section = re.search(r'(?:EXPERIENCE|Experience|WORK EXPERIENCE)(.*?)(?:EDUCATION|Education|SKILLS|Skills|$)', text, re.DOTALL)
        
        if exp_section:
            section_text = exp_section.group(1)
            
            # Pattern: Company name followed by date range
            # Example: "Google | 2020 - 2023"
            company_patterns = [
                r'([A-Z][A-Za-z\s&]+)(?:\s*[\|,]\s*|\s+)\d{4}',
                r'([A-Z][A-Za-z\s&]+)\s*[-–]\s*\d{4}',
            ]
            
            for pattern in company_patterns:
                matches = re.findall(pattern, section_text)
                companies.extend([m.strip() for m in matches])
        
        return list(set(companies))[:15]  # Limit to 15
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills"""
        skills = []
        
        # Look in skills section
        skills_section = re.search(r'(?:SKILLS|Skills|TECHNICAL SKILLS)(.*?)(?:$|EXPERIENCE|EDUCATION|PROJECTS)', text, re.DOTALL)
        
        if skills_section:
            section_text = skills_section.group(1)
            
            # Common skill patterns
            tech_skills = [
                'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'Go', 'Rust',
                'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask',
                'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes',
                'SQL', 'PostgreSQL', 'MongoDB', 'Redis',
                'Machine Learning', 'Deep Learning', 'AI', 'NLP',
                'Git', 'CI/CD', 'Agile', 'Scrum',
            ]
            
            for skill in tech_skills:
                if skill.lower() in section_text.lower():
                    skills.append(skill)
        
        return list(set(skills))[:20]  # Limit to 20
    
    def _parse_with_ai(self, resume_text: str) -> Dict:
        """Use OpenAI to extract resume info"""
        if not self.use_ai or not self.client:
            print("ℹ️  Skipping AI parsing (AI not enabled or client not available)")
            return {}
        
        print("🤖 Using OpenAI to enhance resume parsing...")
        try:
            # Truncate to save tokens
            resume_text = resume_text[:6000]
            
            prompt = f"""Extract structured information from this resume. This data will be used to find job referral connections, so accuracy and completeness are critical.

{resume_text}

Extract ALL relevant information:
1. **Schools**: List every university, college, or educational institution attended (including graduate programs)
2. **Companies**: List every previous employer or company the candidate worked at (be thorough - include internships and part-time work)
3. **Skills**: Extract all technical skills, programming languages, frameworks, tools, and technologies mentioned
4. **Current Title**: The candidate's most recent or current job title
5. **Years of Experience**: Calculate total years of professional experience across all roles

For ambiguous cases:
- If a school name is unclear, use the most likely full name
- If a company name appears multiple times, list it once but note it was multiple roles
- Include all skills even if briefly mentioned
- For experience, sum all employment durations shown in the resume

Return JSON with:
{{
  "schools": ["list of all universities/colleges attended - be comprehensive"],
  "companies": ["list of all previous employers - include all roles"],
  "skills": ["list of all technical skills, languages, frameworks, tools"],
  "current_title": "most recent job title",
  "years_experience": <number> (calculated total years)
}}"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured data from resumes for job matching and connection finding. Your accuracy is critical for helping candidates find relevant professional connections. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=800
            )
            
            content = response.choices[0].message.content.strip()
            # Try to extract JSON if wrapped in markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            
            # Extract additional fields if present
            extracted_fields = {
                'schools': result.get('schools', []),
                'companies': result.get('companies', []),
                'skills': result.get('skills', [])
            }
            
            # Store current_title and years_experience if provided (for future use)
            if 'current_title' in result:
                extracted_fields['current_title'] = result['current_title']
            if 'years_experience' in result:
                extracted_fields['years_experience'] = result['years_experience']
            
            print(f"✅ AI parsing successful: extracted {len(extracted_fields.get('schools', []))} schools, {len(extracted_fields.get('companies', []))} companies, {len(extracted_fields.get('skills', []))} skills")
            return extracted_fields
        
        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse OpenAI JSON response: {str(e)}")
            if 'content' in locals():
                print(f"   Response content: {content[:200]}")
            return {}
        except Exception as e:
            error_msg = str(e)
            # Provide helpful error messages
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                print("⚠️  OpenAI API quota exceeded. Please check your billing at https://platform.openai.com/account/billing")
                print("   Resume parsing will continue with pattern-based extraction only.")
            elif "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                print("⚠️  OpenAI API key invalid or expired. Check your OPENAI_API_KEY environment variable.")
                print("   Resume parsing will continue with pattern-based extraction only.")
            elif "rate_limit" in error_msg.lower():
                print("⚠️  OpenAI API rate limit exceeded. Please wait a moment and try again.")
                print("   Resume parsing will continue with pattern-based extraction only.")
            else:
                print(f"⚠️  AI parsing error: {error_msg}")
                print("   Resume parsing will continue with pattern-based extraction only.")
            
            # Disable AI for future calls to avoid repeated errors
            self.use_ai = False
            return {}

