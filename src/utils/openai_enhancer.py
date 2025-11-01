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
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                print("⚠️  OpenAI package not installed. Run: pip install openai")
                self.enabled = False
    
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
        
        # Build prompt
        prompt = f"""Given this person's info from {person.source}:
Name: {person.name}
Title/Bio: {person.title or 'Unknown'}
Company: {person.company}

Target job: {target_title}

Please analyze and respond in JSON format:
{{
  "cleaned_title": "clean job title if messy",
  "category": "manager|recruiter|senior|peer|unknown",
  "confidence": 0.0-1.0,
  "reasoning": "why this category"
}}

If the title is messy (like a GitHub bio), extract the actual job title."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Cheap model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes professional profiles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=150
            )
            
            result = response.choices[0].message.content
            
            # Parse JSON response
            import json
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
            
            if data.get("confidence"):
                person.confidence_score = float(data["confidence"])
            
        except Exception as e:
            # Silent failure - just return original person
            pass
        
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

