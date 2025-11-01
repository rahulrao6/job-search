"""Demo scraper that returns realistic sample data for testing"""

import random
from typing import List, Optional

from src.models.person import Person, PersonCategory


class DemoScraper:
    """Returns realistic sample LinkedIn profiles for demo purposes"""
    
    # Sample recruiters and managers at various companies
    SAMPLE_DATA = {
        "Google": [
            ("Sarah Chen", "Technical Recruiter", PersonCategory.RECRUITER, "sarahchen-google"),
            ("Mike Johnson", "University Recruiting Lead", PersonCategory.RECRUITER, "mjohnson-google"), 
            ("Emily Zhang", "Engineering Manager", PersonCategory.MANAGER, "emilyzhang"),
            ("David Park", "Software Engineering Manager", PersonCategory.MANAGER, "davidpark-eng"),
            ("Jessica Liu", "Campus Recruiting Program Manager", PersonCategory.RECRUITER, "jessicaliu-campus"),
        ],
        "Amazon": [
            ("Tom Wilson", "Senior Technical Recruiter", PersonCategory.RECRUITER, "twilson-amazon"),
            ("Lisa Martinez", "University Relations Manager", PersonCategory.RECRUITER, "lmartinez-ur"),
            ("Robert Kim", "Software Development Manager", PersonCategory.MANAGER, "robertkim-sdm"),
            ("Amanda Chen", "Operations Manager", PersonCategory.MANAGER, "amandachen-ops"),
            ("Kevin Lee", "Talent Acquisition Partner", PersonCategory.RECRUITER, "kevinlee-talent"),
        ],
        "Microsoft": [
            ("Rachel Green", "Technical Recruiter", PersonCategory.RECRUITER, "rachelgreen-msft"),
            ("James Smith", "University Recruiter", PersonCategory.RECRUITER, "jsmith-university"),
            ("Michelle Wong", "Engineering Manager", PersonCategory.MANAGER, "mwong-engineering"),
            ("Brian Taylor", "Senior Engineering Manager", PersonCategory.MANAGER, "btaylor-senior"),
            ("Nicole Davis", "Campus Recruiting Lead", PersonCategory.RECRUITER, "ndavis-campus"),
        ],
        "Meta": [
            ("Alex Rivera", "Technical Sourcer", PersonCategory.RECRUITER, "arivera-meta"),
            ("Sophia Kim", "University Programs Manager", PersonCategory.RECRUITER, "sophiakim-uni"),
            ("Daniel Chen", "Engineering Manager", PersonCategory.MANAGER, "dchen-eng-manager"),
            ("Maria Garcia", "Product Engineering Manager", PersonCategory.MANAGER, "mgarcia-product"),
            ("Chris Wong", "Technical Recruiting Partner", PersonCategory.RECRUITER, "cwong-recruiting"),
        ],
        "Apple": [
            ("Jennifer Lee", "Technical Recruiter", PersonCategory.RECRUITER, "jlee-apple"),
            ("Mark Davis", "University Relations", PersonCategory.RECRUITER, "mdavis-university"),
            ("Susan Park", "Software Engineering Manager", PersonCategory.MANAGER, "spark-engineering"),
            ("Richard Kim", "Senior Manager, Software", PersonCategory.MANAGER, "rkim-software"),
            ("Emma Wilson", "Campus Recruiting Specialist", PersonCategory.RECRUITER, "ewilson-campus"),
        ],
        "Stripe": [
            ("Jason Chen", "Technical Recruiter", PersonCategory.RECRUITER, "jchen-stripe"),
            ("Laura Martinez", "Engineering Manager", PersonCategory.MANAGER, "lmartinez-eng"),
            ("Ryan Park", "Recruiting Lead", PersonCategory.RECRUITER, "rpark-recruiting"),
        ],
        "Goldman Sachs": [
            ("Michael Brown", "Campus Recruiter", PersonCategory.RECRUITER, "mbrown-gs"),
            ("Sarah Johnson", "Technology Recruiting", PersonCategory.RECRUITER, "sjohnson-tech"),
            ("David Lee", "Engineering Manager", PersonCategory.MANAGER, "dlee-engineering"),
        ],
        "McKinsey": [
            ("Amanda Smith", "Recruiting Manager", PersonCategory.RECRUITER, "asmith-mckinsey"),
            ("John Park", "Associate Partner", PersonCategory.MANAGER, "jpark-partner"),
            ("Lisa Chen", "Campus Recruiting Lead", PersonCategory.RECRUITER, "lchen-campus"),
        ]
    }
    
    def search_people(self, company: str, title: Optional[str] = None, **kwargs) -> List[Person]:
        """Return demo LinkedIn profiles"""
        
        # Get sample data for company
        company_data = []
        
        # Try exact match first
        for key in self.SAMPLE_DATA:
            if key.lower() == company.lower():
                company_data = self.SAMPLE_DATA[key]
                break
        
        # If no exact match, try partial match
        if not company_data:
            for key in self.SAMPLE_DATA:
                if company.lower() in key.lower() or key.lower() in company.lower():
                    company_data = self.SAMPLE_DATA[key]
                    break
        
        # If still no match, use generic data
        if not company_data:
            company_data = [
                (f"{company} Recruiter", "Technical Recruiter", PersonCategory.RECRUITER, "recruiter"),
                (f"{company} Manager", "Engineering Manager", PersonCategory.MANAGER, "manager"),
            ]
        
        # Convert to Person objects
        people = []
        for name, person_title, category, linkedin_id in company_data:
            # Add some variety to confidence scores
            confidence = random.uniform(0.7, 0.95)
            
            person = Person(
                name=name,
                title=person_title,
                company=company,
                linkedin_url=f"https://www.linkedin.com/in/{linkedin_id}",
                source="demo_data",
                category=category,
                confidence_score=confidence,
                evidence_url=f"https://www.linkedin.com/in/{linkedin_id}"
            )
            people.append(person)
        
        # Filter by title if specified
        if title:
            title_lower = title.lower()
            if "recruiter" in title_lower or "talent" in title_lower:
                people = [p for p in people if p.category == PersonCategory.RECRUITER]
            elif "manager" in title_lower:
                people = [p for p in people if p.category == PersonCategory.MANAGER]
        
        print(f"✓ Demo data: Found {len(people)} sample profiles for {company}")
        
        return people[:5]  # Return up to 5 people
