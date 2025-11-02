"""Use OpenAI to enhance and categorize people data"""

import os
from typing import List, Optional
from src.models.person import Person, PersonCategory


class OpenAIEnhancer:
    """
    Use OpenAI to enhance scraped people data:
    - Better categorization
    - Extract structured info from messy bios
    - Infer missing details
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.enabled = False
        
        if self.api_key:
            # Validate key format
            if not self.api_key.startswith('sk-'):
                print("⚠️  OpenAI API key format invalid (should start with 'sk-'). AI enhancement disabled.")
            else:
                try:
                    from openai import OpenAI
                    self.client = OpenAI(api_key=self.api_key)
                    self.enabled = True
                except ImportError:
                    print("⚠️  OpenAI package not installed. Install with: pip install openai")
                except Exception as e:
                    print(f"⚠️  OpenAI initialization failed: {str(e)}. AI enhancement disabled.")
    
    def enhance_person(self, person: Person, target_title: str) -> Person:
        """
        Enhance a person's data using OpenAI.
        
        Args:
            person: Person object to enhance
            target_title: Target job title for context
        
        Returns:
            Enhanced Person object
        """
        if not self.enabled:
            return person
        
        # Build prompt with context about relevance and categorization
        prompt = f"""Analyze this professional profile for job referral connection matching.

Person Information (from {person.source}):
- Name: {person.name}
- Title/Bio: {person.title or 'Unknown'}
- Company: {person.company}
- Location: {person.location or 'Not specified'}
- Skills: {', '.join(person.skills[:5]) if person.skills else 'Not specified'}

Target Job: {target_title}

Your task:
1. **Clean the title**: If messy (e.g., GitHub bio, LinkedIn summary), extract the actual job title
2. **Categorize**: Determine if this person is a:
   - "recruiter": HR, Talent, Recruiting roles
   - "manager": Manager, Director, VP, Head, Chief roles (would be your manager)
   - "senior": Senior, Staff, Principal, Architect roles (one level above target)
   - "peer": Same level as target job (similar title, similar experience)
   - "unknown": Can't determine or doesn't fit categories

3. **Assess relevance**: Score how relevant this person is for the target job (0.0-1.0)
   - Consider: title match, company match, skills overlap, location
   - Higher score = more likely to help with job referral

4. **Extract additional metadata**: If available, extract:
   - Department/team
   - Years of experience (if mentioned)
   - Additional skills not already listed

Respond in JSON format:
{{
  "cleaned_title": "clean, standardized job title",
  "category": "manager|recruiter|senior|peer|unknown",
  "confidence": 0.0-1.0 (how confident in categorization),
  "relevance_score": 0.0-1.0 (how relevant for target job),
  "department": "department/team name if mentioned",
  "reasoning": "brief explanation of category and relevance"
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing professional profiles for job referral matching. Your categorization and relevance scoring help candidates find the most valuable connections. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=300
            )
            
            result = response.choices[0].message.content
            
            # Parse JSON response
            import json
            # Try to extract JSON if wrapped in markdown code blocks
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
                result = result.strip()
            
            data = json.loads(result)
            
            # Update person with AI insights
            if data.get("cleaned_title"):
                person.title = data["cleaned_title"]
            
            if data.get("category"):
                category_map = {
                    "manager": PersonCategory.MANAGER,
                    "recruiter": PersonCategory.RECRUITER,
                    "senior": PersonCategory.SENIOR,
                    "peer": PersonCategory.PEER,
                    "unknown": PersonCategory.UNKNOWN,
                }
                person.category = category_map.get(data["category"], PersonCategory.UNKNOWN)
            
            # Update confidence (prioritize AI confidence if available, otherwise use relevance score)
            if data.get("confidence"):
                person.confidence_score = float(data["confidence"])
            elif data.get("relevance_score"):
                # Use relevance score as fallback confidence
                person.confidence_score = float(data["relevance_score"])
            
            # Extract additional metadata if available
            if data.get("department") and not person.department:
                person.department = data["department"]
            
        except Exception as e:
            error_msg = str(e)
            # Only log if it's not a quota/auth error (those are logged elsewhere)
            if "quota" not in error_msg.lower() and "api_key" not in error_msg.lower() and "authentication" not in error_msg.lower():
                # Silent failure for individual person enhancement to avoid spam
                pass
            # If it's a quota/auth error, disable for future calls
            elif "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower():
                self.enabled = False
                print("⚠️  OpenAI quota exceeded. Disabling AI enhancement for this session.")
            elif "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                self.enabled = False
                print("⚠️  OpenAI API key invalid. Disabling AI enhancement.")
        
        return person
    
    def enhance_batch(self, people: List[Person], target_title: str, max_enhance: int = 20) -> List[Person]:
        """
        Enhance multiple people (but limit to save costs)
        
        Args:
            people: List of people to enhance
            target_title: Target job title for context
            max_enhance: Maximum number to enhance (default 20, can increase for production)
        
        Returns:
            List of enhanced people
        """
        if not self.enabled or not people:
            return people
        
        # Cost: ~$0.001 per person with gpt-3.5-turbo
        # For production with 50 people: ~$0.05 per search (very affordable)
        
        enhanced = []
        for i, person in enumerate(people):
            if i < max_enhance:
                enhanced.append(self.enhance_person(person, target_title))
            else:
                enhanced.append(person)
        
        print(f"✓ Enhanced {min(len(people), max_enhance)} people with OpenAI")
        return enhanced


def get_openai_enhancer() -> OpenAIEnhancer:
    """Get global OpenAI enhancer instance"""
    return OpenAIEnhancer()

