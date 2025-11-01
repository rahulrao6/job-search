"""Test core functionality"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.person import Person, PersonCategory
from src.core.categorizer import PersonCategorizer
from src.core.aggregator import PeopleAggregator


class TestPersonCategorizer:
    """Test person categorization"""
    
    def test_manager_categorization(self):
        categorizer = PersonCategorizer("Software Engineer")
        
        person = Person(
            name="John Manager",
            title="Engineering Manager",
            company="Meta",
            source="test"
        )
        
        categorized = categorizer.categorize(person)
        assert categorized.category == PersonCategory.MANAGER
    
    def test_recruiter_categorization(self):
        categorizer = PersonCategorizer("Software Engineer")
        
        person = Person(
            name="Jane Recruiter",
            title="Technical Recruiter",
            company="Meta",
            source="test"
        )
        
        categorized = categorizer.categorize(person)
        assert categorized.category == PersonCategory.RECRUITER
    
    def test_senior_categorization(self):
        categorizer = PersonCategorizer("Software Engineer")
        
        person = Person(
            name="Bob Senior",
            title="Senior Software Engineer",
            company="Meta",
            source="test"
        )
        
        categorized = categorizer.categorize(person)
        assert categorized.category == PersonCategory.SENIOR
    
    def test_peer_categorization(self):
        categorizer = PersonCategorizer("Software Engineer")
        
        person = Person(
            name="Alice Peer",
            title="Software Engineer",
            company="Meta",
            source="test"
        )
        
        categorized = categorizer.categorize(person)
        assert categorized.category == PersonCategory.PEER


class TestPeopleAggregator:
    """Test people aggregation and deduplication"""
    
    def test_add_person(self):
        aggregator = PeopleAggregator()
        
        person = Person(
            name="John Doe",
            title="Engineer",
            company="Meta",
            source="test"
        )
        
        aggregator.add(person)
        assert len(aggregator.get_all()) == 1
    
    def test_deduplication(self):
        aggregator = PeopleAggregator()
        
        person1 = Person(
            name="John Doe",
            title="Engineer",
            company="Meta",
            source="source1"
        )
        
        person2 = Person(
            name="john doe",  # Different case
            title="Senior Engineer",
            company="META",  # Different case
            source="source2"
        )
        
        aggregator.add(person1)
        aggregator.add(person2)
        
        # Should be deduplicated to 1 person
        assert len(aggregator.get_all()) == 1
        
        # Should have merged data
        merged = aggregator.get_all()[0]
        assert "source1" in merged.source or "source2" in merged.source
    
    def test_batch_add(self):
        aggregator = PeopleAggregator()
        
        people = [
            Person(name=f"Person {i}", title="Engineer", company="Meta", source="test")
            for i in range(5)
        ]
        
        aggregator.add_batch(people)
        assert len(aggregator.get_all()) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

