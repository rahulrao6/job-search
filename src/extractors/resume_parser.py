"""Parse resumes to extract schools, past companies, skills"""

import re
import os
from typing import List, Dict
from src.models.job_context import CandidateProfile


class ResumeParser:
    """
    Extract structured data from resumes.
    
    Finds: schools, past companies, skills for alumni matching.
    """
    
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai and bool(os.getenv("OPENAI_API_KEY"))
        
        if self.use_ai:
            try:
                from openai import OpenAI
                self.client = OpenAI()
            except:
                self.use_ai = False
    
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
        if not self.use_ai:
            return {}
        
        try:
            # Truncate to save tokens
            resume_text = resume_text[:6000]
            
            prompt = f"""Extract structured information from this resume:

{resume_text}

Return JSON with:
{{
  "schools": ["list of universities/colleges attended"],
  "companies": ["list of previous employers"],
  "skills": ["list of technical skills"]
}}"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You extract structured data from resumes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            import json
            return json.loads(response.choices[0].message.content)
        
        except Exception as e:
            print(f"⚠️  AI parsing error: {e}")
            return {}

